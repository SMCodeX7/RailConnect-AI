from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from railconnect.core.config import Settings
from railconnect.modules.identity.errors import (
    AuthenticationError,
    PermissionDeniedError,
)
from railconnect.modules.identity.models.auth_session import AuthSession
from railconnect.modules.identity.models.user import User
from railconnect.modules.identity.models.user_role import UserRole
from railconnect.modules.identity.passwords import hash_password
from railconnect.modules.identity.permissions import Permission, RoleCode
from railconnect.modules.identity.provisioning_schemas import ProvisionStaffInput
from railconnect.modules.identity.provisioning_service import provision_staff_user
from railconnect.modules.identity.session_service import (
    CreatedSession,
    authenticate_staff_session,
    create_staff_session,
    require_actor_permission,
    revoke_staff_session,
    verify_session_csrf,
)
from railconnect.modules.identity.tokens import (
    generate_session_token,
    hash_session_token,
)

NOW = datetime(2026, 10, 12, 12, tzinfo=UTC)


@pytest.fixture(scope="module")
def session_test_password() -> str:
    return hash_password("Fictional session test passphrase")


@pytest.fixture
def staff_session(
    identity_database: Session,
    session_test_password: str,
) -> tuple[Session, User, Settings, CreatedSession]:
    session = identity_database
    user = provision_staff_user(
        session,
        ProvisionStaffInput(
            username=f"session_{uuid4().hex}",
            display_name="Session Test Staff",
            role=RoleCode.CONTROLLER,
        ),
        session_test_password,
    )
    settings = Settings(
        _env_file=None,
        environment="test",
        session_cookie_secure=False,
        session_ttl_seconds=28800,
        session_idle_timeout_seconds=1800,
    )
    created = create_staff_session(session, user.id, settings, NOW)
    return session, user, settings, created


def test_session_stores_hash_and_returns_safe_actor(
    staff_session: tuple[Session, User, Settings, CreatedSession],
) -> None:
    session, user, _, created = staff_session
    stored = session.get(AuthSession, created.session_id)
    assert stored is not None

    assert stored.token_hash == hash_session_token(created.token)
    assert stored.token_hash != created.token
    assert created.token not in repr(created)
    assert created.csrf_token not in repr(created)
    assert created.actor.user_id == str(user.id)
    assert created.actor.roles == ("controller",)
    assert Permission.REPORTS_REVIEW in created.actor.permissions
    assert "password_hash" not in created.actor.model_dump()
    assert "token" not in created.actor.model_dump()


def test_valid_session_authenticates_and_updates_activity(
    staff_session: tuple[Session, User, Settings, CreatedSession],
) -> None:
    session, user, settings, created = staff_session
    later = NOW + timedelta(minutes=10)

    authenticated = authenticate_staff_session(session, created.token, settings, later)
    stored = session.get(AuthSession, created.session_id)
    assert stored is not None

    assert authenticated.actor.user_id == str(user.id)
    assert stored.last_seen_at == later
    assert authenticated.expires_at == created.expires_at


def test_activity_extends_idle_window_without_extending_absolute_expiry(
    staff_session: tuple[Session, User, Settings, CreatedSession],
) -> None:
    session, _, settings, created = staff_session

    authenticate_staff_session(session, created.token, settings, NOW + timedelta(minutes=20))
    authenticated = authenticate_staff_session(
        session, created.token, settings, NOW + timedelta(minutes=40)
    )

    assert authenticated.expires_at == NOW + timedelta(hours=8)


def test_idle_expiry_boundary_is_rejected(
    staff_session: tuple[Session, User, Settings, CreatedSession],
) -> None:
    session, _, settings, created = staff_session

    with pytest.raises(AuthenticationError):
        authenticate_staff_session(session, created.token, settings, NOW + timedelta(minutes=30))


def test_absolute_expiry_boundary_is_rejected(
    staff_session: tuple[Session, User, Settings, CreatedSession],
) -> None:
    session, _, settings, created = staff_session
    stored = session.get(AuthSession, created.session_id)
    assert stored is not None
    stored.last_seen_at = created.expires_at - timedelta(seconds=1)
    session.flush()

    with pytest.raises(AuthenticationError):
        authenticate_staff_session(session, created.token, settings, created.expires_at)


def test_revocation_prevents_reuse(
    staff_session: tuple[Session, User, Settings, CreatedSession],
) -> None:
    session, _, settings, created = staff_session
    revoked_at = NOW + timedelta(minutes=1)

    revoke_staff_session(session, created.token, settings, revoked_at)
    stored = session.get(AuthSession, created.session_id)
    assert stored is not None
    assert stored.revoked_at == revoked_at

    with pytest.raises(AuthenticationError):
        authenticate_staff_session(
            session, created.token, settings, revoked_at + timedelta(seconds=1)
        )


def test_disabled_user_cannot_authenticate(
    staff_session: tuple[Session, User, Settings, CreatedSession],
) -> None:
    session, user, settings, created = staff_session
    user.is_active = False
    session.flush()

    with pytest.raises(AuthenticationError):
        authenticate_staff_session(session, created.token, settings, NOW)


def test_auth_version_change_invalidates_session(
    staff_session: tuple[Session, User, Settings, CreatedSession],
) -> None:
    session, user, settings, created = staff_session
    user.auth_version += 1
    session.flush()

    with pytest.raises(AuthenticationError):
        authenticate_staff_session(session, created.token, settings, NOW)


def test_role_removal_takes_effect_on_next_authentication(
    staff_session: tuple[Session, User, Settings, CreatedSession],
) -> None:
    session, user, settings, created = staff_session
    session.execute(delete(UserRole).where(UserRole.user_id == user.id))
    session.flush()

    with pytest.raises(AuthenticationError):
        authenticate_staff_session(session, created.token, settings, NOW)


@pytest.mark.parametrize("token", ["", "invalid", "x" * 200])
def test_malformed_tokens_are_rejected(
    staff_session: tuple[Session, User, Settings, CreatedSession],
    token: str,
) -> None:
    session, _, settings, _ = staff_session

    with pytest.raises(AuthenticationError):
        authenticate_staff_session(session, token, settings, NOW)


def test_unknown_well_formed_token_is_rejected(
    staff_session: tuple[Session, User, Settings, CreatedSession],
) -> None:
    session, _, settings, _ = staff_session

    with pytest.raises(AuthenticationError):
        authenticate_staff_session(session, generate_session_token(), settings, NOW)


def test_controller_cannot_manage_timetable(
    staff_session: tuple[Session, User, Settings, CreatedSession],
) -> None:
    _, _, _, created = staff_session

    with pytest.raises(PermissionDeniedError):
        require_actor_permission(created.actor, Permission.TIMETABLE_MANAGE)

    require_actor_permission(created.actor, Permission.REPORTS_REVIEW)


def test_correct_csrf_token_is_accepted(
    staff_session: tuple[Session, User, Settings, CreatedSession],
) -> None:
    session, _, settings, created = staff_session
    authenticated = authenticate_staff_session(session, created.token, settings, NOW)

    verify_session_csrf(authenticated, created.csrf_token)


@pytest.mark.parametrize("csrf_token", ["", "f" * 64, "é" * 64, "a" * 65])
def test_invalid_csrf_tokens_are_rejected(
    staff_session: tuple[Session, User, Settings, CreatedSession],
    csrf_token: str,
) -> None:
    session, _, settings, created = staff_session
    authenticated = authenticate_staff_session(session, created.token, settings, NOW)

    with pytest.raises(PermissionDeniedError):
        verify_session_csrf(authenticated, csrf_token)


def test_creation_rollback_removes_session(
    staff_session: tuple[Session, User, Settings, CreatedSession],
) -> None:
    session, user, settings, _ = staff_session
    before = session.scalar(select(func.count()).select_from(AuthSession))
    new_session_id = None

    with pytest.raises(RuntimeError, match="abort session"):
        with session.begin_nested():
            created = create_staff_session(session, user.id, settings, NOW)
            new_session_id = created.session_id
            raise RuntimeError("abort session")

    assert new_session_id is not None
    assert session.get(AuthSession, new_session_id) is None
    assert session.scalar(select(func.count()).select_from(AuthSession)) == before


def test_creation_rejects_disabled_user(
    staff_session: tuple[Session, User, Settings, CreatedSession],
) -> None:
    session, user, settings, _ = staff_session
    user.is_active = False
    session.flush()

    with pytest.raises(AuthenticationError):
        create_staff_session(session, user.id, settings, NOW)


def test_naive_clock_is_rejected(
    staff_session: tuple[Session, User, Settings, CreatedSession],
) -> None:
    session, _, settings, created = staff_session

    with pytest.raises(ValueError, match="timezone-aware clock"):
        authenticate_staff_session(
            session,
            created.token,
            settings,
            datetime(2026, 10, 12, 12),
        )
