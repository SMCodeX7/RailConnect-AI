from sqlalchemy import select
from sqlalchemy.orm import Session

from railconnect.modules.identity.models.auth_session import AuthSession
from railconnect.modules.identity.models.role import Role
from railconnect.modules.identity.models.user import User
from railconnect.modules.identity.models.user_role import UserRole


def get_session_and_user_for_update(
    session: Session,
    token_hash: str,
) -> tuple[AuthSession, User] | None:
    row = session.execute(
        select(AuthSession, User)
        .join(User, User.id == AuthSession.user_id)
        .where(AuthSession.token_hash == token_hash)
        .with_for_update()
    ).one_or_none()

    if row is None:
        return None

    auth_session, user = row
    return auth_session, user


def list_user_role_codes(session: Session, user: User) -> tuple[str, ...]:
    return tuple(
        session.scalars(
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id)
            .order_by(Role.code)
        )
    )
