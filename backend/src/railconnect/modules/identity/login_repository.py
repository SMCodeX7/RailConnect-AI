from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from railconnect.modules.identity.models.user import User


@dataclass(frozen=True)
class CredentialSnapshot:
    user_id: UUID
    password_hash: str = field(repr=False)
    auth_version: int
    is_active: bool


def get_credentials(
    session: Session,
    username: str,
) -> CredentialSnapshot | None:
    row = session.execute(
        select(
            User.id,
            User.password_hash,
            User.auth_version,
            User.is_active,
        ).where(User.username == username)
    ).one_or_none()

    if row is None:
        return None

    user_id, password_hash, auth_version, is_active = row
    return CredentialSnapshot(
        user_id=user_id,
        password_hash=password_hash,
        auth_version=auth_version,
        is_active=is_active,
    )


def get_login_user_for_update(
    session: Session,
    user_id: UUID,
) -> User | None:
    return session.scalar(select(User).where(User.id == user_id).with_for_update())
