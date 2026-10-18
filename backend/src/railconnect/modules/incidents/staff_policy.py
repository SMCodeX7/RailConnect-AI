from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from railconnect.modules.identity.errors import PermissionDeniedError
from railconnect.modules.identity.models.role import Role
from railconnect.modules.identity.models.user import User
from railconnect.modules.identity.models.user_role import UserRole
from railconnect.modules.identity.permissions import Permission, resolve_permissions
from railconnect.modules.identity.session_service import (
    AuthenticatedSession,
    require_actor_permission,
)


def require_current_staff_permission(
    session: Session,
    authenticated: AuthenticatedSession,
    permission: Permission,
) -> UUID:
    require_actor_permission(authenticated.actor, permission)

    if not session.in_transaction():
        raise ValueError("Staff authorization requires a caller-owned transaction.")

    actor_id = UUID(authenticated.actor.user_id)

    user = session.scalar(
        select(User)
        .where(User.id == actor_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )

    if user is None or not user.is_active:
        raise PermissionDeniedError("The staff account is unavailable.")

    role_codes = session.scalars(
        select(Role.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == actor_id)
    ).all()

    if permission not in resolve_permissions(role_codes):
        raise PermissionDeniedError("The required staff permission is unavailable.")

    return actor_id
