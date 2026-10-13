from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from secrets import compare_digest
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from railconnect.core.config import Settings
from railconnect.modules.identity.errors import (
    AuthenticationError,
    PermissionDeniedError,
)
from railconnect.modules.identity.models.auth_session import AuthSession
from railconnect.modules.identity.models.user import User
from railconnect.modules.identity.permissions import Permission, resolve_permissions
from railconnect.modules.identity.schemas import Actor
from railconnect.modules.identity.session_repository import (
    get_session_and_user_for_update,
    list_user_role_codes,
)
from railconnect.modules.identity.tokens import (
    generate_csrf_token,
    generate_session_token,
    hash_session_token,
)


@dataclass(frozen=True)
class CreatedSession:
    session_id: UUID
    token: str = field(repr=False)
    csrf_token: str = field(repr=False)
    expires_at: datetime
    actor: Actor


@dataclass(frozen=True)
class AuthenticatedSession:
    session_id: UUID
    csrf_token: str = field(repr=False)
    expires_at: datetime
    actor: Actor


def _validate_transaction_and_time(session: Session, now: datetime) -> datetime:
    if not session.in_transaction():
        raise ValueError("Session operations require a caller-owned transaction.")

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Session operations require a timezone-aware clock.")

    return now.astimezone(UTC)


def _actor_for_user(session: Session, user: User) -> Actor:
    roles = list_user_role_codes(session, user)
    permissions = resolve_permissions(roles)

    if not permissions:
        raise AuthenticationError("Authentication failed.")

    return Actor(
        user_id=str(user.id),
        username=user.username,
        display_name=user.display_name,
        roles=roles,
        permissions=permissions,
    )


def create_staff_session(
    session: Session,
    user_id: UUID,
    settings: Settings,
    now: datetime,
) -> CreatedSession:
    timestamp = _validate_transaction_and_time(session, now)
    user = session.scalar(select(User).where(User.id == user_id).with_for_update())

    if user is None or not user.is_active:
        raise AuthenticationError("Authentication failed.")

    actor = _actor_for_user(session, user)
    token = generate_session_token()
    csrf_token = generate_csrf_token()
    expires_at = timestamp + timedelta(seconds=settings.session_ttl_seconds)

    auth_session = AuthSession(
        user_id=user.id,
        token_hash=hash_session_token(token),
        csrf_token=csrf_token,
        auth_version=user.auth_version,
        created_at=timestamp,
        last_seen_at=timestamp,
        expires_at=expires_at,
    )
    session.add(auth_session)
    session.flush()

    return CreatedSession(
        session_id=auth_session.id,
        token=token,
        csrf_token=csrf_token,
        expires_at=expires_at,
        actor=actor,
    )


def authenticate_staff_session(
    session: Session,
    token: str,
    settings: Settings,
    now: datetime,
) -> AuthenticatedSession:
    timestamp = _validate_transaction_and_time(session, now)

    try:
        token_hash = hash_session_token(token)
    except ValueError as error:
        raise AuthenticationError("Authentication failed.") from error

    row = get_session_and_user_for_update(session, token_hash)
    if row is None:
        raise AuthenticationError("Authentication failed.")

    auth_session, user = row

    if (
        not user.is_active
        or auth_session.revoked_at is not None
        or auth_session.auth_version != user.auth_version
        or timestamp < auth_session.created_at
        or timestamp >= auth_session.expires_at
        or timestamp
        >= auth_session.last_seen_at + timedelta(seconds=settings.session_idle_timeout_seconds)
    ):
        raise AuthenticationError("Authentication failed.")

    actor = _actor_for_user(session, user)
    auth_session.last_seen_at = max(auth_session.last_seen_at, timestamp)
    session.flush()

    return AuthenticatedSession(
        session_id=auth_session.id,
        csrf_token=auth_session.csrf_token,
        expires_at=auth_session.expires_at,
        actor=actor,
    )


def require_actor_permission(actor: Actor, permission: Permission) -> None:
    if permission not in actor.permissions:
        raise PermissionDeniedError("Permission denied.")


def verify_session_csrf(
    authenticated: AuthenticatedSession,
    supplied_token: str,
) -> None:
    if (
        len(supplied_token) != 64
        or not supplied_token.isascii()
        or not compare_digest(authenticated.csrf_token, supplied_token)
    ):
        raise PermissionDeniedError("CSRF verification failed.")


def revoke_staff_session(
    session: Session,
    token: str,
    settings: Settings,
    now: datetime,
) -> None:
    timestamp = _validate_transaction_and_time(session, now)
    authenticated = authenticate_staff_session(
        session,
        token,
        settings,
        timestamp,
    )
    auth_session = session.get(AuthSession, authenticated.session_id)
    if auth_session is None:
        raise AuthenticationError("Authentication failed.")

    auth_session.revoked_at = timestamp
    session.flush()
