from collections.abc import Iterable
from enum import StrEnum


class RoleCode(StrEnum):
    CONTROLLER = "controller"
    ADMINISTRATOR = "administrator"


class Permission(StrEnum):
    REPORTS_READ = "reports.read"
    REPORTS_REVIEW = "reports.review"
    INCIDENTS_EDIT = "incidents.edit"
    INCIDENTS_RESOLVE = "incidents.resolve"
    TIMETABLE_MANAGE = "timetable.manage"
    AUDIT_READ = "audit.read"


ROLE_PERMISSIONS: dict[RoleCode, frozenset[Permission]] = {
    RoleCode.CONTROLLER: frozenset(
        {
            Permission.REPORTS_READ,
            Permission.REPORTS_REVIEW,
            Permission.INCIDENTS_EDIT,
            Permission.INCIDENTS_RESOLVE,
        }
    ),
    RoleCode.ADMINISTRATOR: frozenset(
        {
            Permission.REPORTS_READ,
            Permission.REPORTS_REVIEW,
            Permission.INCIDENTS_EDIT,
            Permission.INCIDENTS_RESOLVE,
            Permission.TIMETABLE_MANAGE,
            Permission.AUDIT_READ,
        }
    ),
}


def resolve_permissions(role_codes: Iterable[str]) -> frozenset[Permission]:
    permissions: set[Permission] = set()

    for code in role_codes:
        try:
            role = RoleCode(code)
        except ValueError:
            continue

        permissions.update(ROLE_PERMISSIONS[role])

    return frozenset(permissions)
