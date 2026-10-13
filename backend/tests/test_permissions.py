from railconnect.modules.identity.permissions import Permission, resolve_permissions


def test_unknown_roles_grant_nothing() -> None:
    assert resolve_permissions(["unknown", "superadmin"]) == frozenset()


def test_controller_permissions_are_explicit() -> None:
    permissions = resolve_permissions(["controller"])

    assert permissions == frozenset(
        {
            Permission.REPORTS_READ,
            Permission.REPORTS_REVIEW,
            Permission.INCIDENTS_EDIT,
            Permission.INCIDENTS_RESOLVE,
        }
    )
    assert Permission.TIMETABLE_MANAGE not in permissions
    assert Permission.AUDIT_READ not in permissions


def test_administrator_permissions_are_explicit() -> None:
    assert resolve_permissions(["administrator"]) == frozenset(
        {
            Permission.REPORTS_READ,
            Permission.REPORTS_REVIEW,
            Permission.INCIDENTS_EDIT,
            Permission.INCIDENTS_RESOLVE,
            Permission.TIMETABLE_MANAGE,
            Permission.AUDIT_READ,
        }
    )


def test_duplicate_and_unknown_roles_do_not_expand_permissions() -> None:
    assert resolve_permissions(["controller", "controller", "unknown"]) == resolve_permissions(
        ["controller"]
    )
