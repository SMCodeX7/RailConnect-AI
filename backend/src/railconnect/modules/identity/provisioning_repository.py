from hashlib import sha256

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from railconnect.modules.identity.models.role import Role
from railconnect.modules.identity.models.user import User


def lock_provisioning(session: Session) -> None:
    digest = sha256(b"railconnect:staff-provisioning").digest()
    lock_key = int.from_bytes(digest[:8], byteorder="big", signed=True)
    session.execute(select(func.pg_advisory_xact_lock(lock_key)))


def get_user_by_username(session: Session, username: str) -> User | None:
    return session.scalar(select(User).where(User.username == username).with_for_update())


def get_role_by_code(session: Session, code: str) -> Role | None:
    return session.scalar(select(Role).where(Role.code == code).with_for_update())
