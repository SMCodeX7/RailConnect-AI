from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from railconnect.modules.identity.models.role import Role
from railconnect.modules.identity.models.user import User
from railconnect.modules.identity.models.user_role import UserRole
from railconnect.modules.identity.passwords import hash_password, verify_password
from railconnect.modules.identity.permissions import RoleCode
from railconnect.modules.identity.provisioning_schemas import ProvisionStaffInput
from railconnect.modules.identity.provisioning_service import provision_staff_user


@pytest.fixture(scope="module")
def encoded_password() -> str:
    return hash_password("Fictional provisioning test password")


def staff_input(
    role: RoleCode = RoleCode.CONTROLLER,
) -> ProvisionStaffInput:
    return ProvisionStaffInput(
        username=f"staff_{uuid4().hex}",
        display_name="Fictional Staff",
        role=role,
    )


def test_username_is_normalized_without_password_processing() -> None:
    data = ProvisionStaffInput(
        username="  Alice.Staff  ",
        display_name=" Alice Staff ",
        role=RoleCode.CONTROLLER,
    )

    assert data.username == "alice.staff"
    assert data.display_name == "Alice Staff"


@pytest.mark.parametrize("username", ["ab", "1staff", "staff user", "x" * 65])
def test_invalid_usernames_are_rejected(username: str) -> None:
    with pytest.raises(ValidationError):
        ProvisionStaffInput(
            username=username,
            display_name="Fictional Staff",
            role=RoleCode.CONTROLLER,
        )


def test_unknown_provisioning_role_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ProvisionStaffInput.model_validate(
            {
                "username": "fictional_staff",
                "display_name": "Fictional Staff",
                "role": "superadmin",
            }
        )


def test_creates_user_and_role_assignment(
    identity_database: Session,
    encoded_password: str,
) -> None:
    session = identity_database
    data = staff_input()

    user = provision_staff_user(session, data, encoded_password)
    assignment = session.scalar(select(UserRole).where(UserRole.user_id == user.id))
    assert assignment is not None
    role = session.get(Role, assignment.role_id)
    assert role is not None

    assert user.username == data.username
    assert user.display_name == data.display_name
    assert user.is_active is True
    assert user.auth_version == 1
    assert user.created_at.tzinfo is not None
    assert user.password_hash == encoded_password
    assert (
        verify_password(
            user.password_hash,
            "Fictional provisioning test password",
        )
        is True
    )
    assert role.code == "controller"


def test_reuses_role_for_another_user(
    identity_database: Session,
    encoded_password: str,
) -> None:
    session = identity_database
    first = provision_staff_user(session, staff_input(), encoded_password)
    second = provision_staff_user(session, staff_input(), encoded_password)

    assignments = list(
        session.scalars(select(UserRole).where(UserRole.user_id.in_([first.id, second.id])))
    )

    assert len(assignments) == 2
    assert assignments[0].role_id == assignments[1].role_id


def test_duplicate_username_does_not_change_account_or_role(
    identity_database: Session,
    encoded_password: str,
) -> None:
    session = identity_database
    data = staff_input()
    original = provision_staff_user(session, data, encoded_password)
    assignments_before = list(
        session.scalars(select(UserRole.role_id).where(UserRole.user_id == original.id))
    )
    changed = ProvisionStaffInput(
        username=data.username,
        display_name="Changed Name",
        role=RoleCode.ADMINISTRATOR,
    )

    with pytest.raises(ValueError, match="already exists"):
        provision_staff_user(session, changed, encoded_password)

    session.refresh(original)
    assignments_after = list(
        session.scalars(select(UserRole.role_id).where(UserRole.user_id == original.id))
    )

    assert original.display_name == data.display_name
    assert original.password_hash == encoded_password
    assert assignments_after == assignments_before


def test_caller_rollback_removes_provisioned_account(
    identity_database: Session,
    encoded_password: str,
) -> None:
    session = identity_database
    data = staff_input()
    users_before = session.scalar(select(func.count()).select_from(User))
    roles_before = session.scalar(select(func.count()).select_from(Role))
    assignments_before = session.scalar(select(func.count()).select_from(UserRole))

    with pytest.raises(RuntimeError, match="abort provisioning"):
        with session.begin_nested():
            provision_staff_user(session, data, encoded_password)
            raise RuntimeError("abort provisioning")

    assert session.scalar(select(User).where(User.username == data.username)) is None
    assert session.scalar(select(func.count()).select_from(User)) == users_before
    assert session.scalar(select(func.count()).select_from(Role)) == roles_before
    assert session.scalar(select(func.count()).select_from(UserRole)) == assignments_before


def test_rejects_plaintext_instead_of_encoded_password(
    identity_database: Session,
) -> None:
    with pytest.raises(ValueError, match="Argon2id hash"):
        provision_staff_user(
            identity_database,
            staff_input(),
            "Fictional plaintext password",
        )


def test_requires_caller_owned_transaction(
    identity_database: Session,
    encoded_password: str,
) -> None:
    with Session(bind=identity_database.get_bind()) as separate_session:
        with pytest.raises(ValueError, match="caller-owned transaction"):
            provision_staff_user(
                separate_session,
                staff_input(),
                encoded_password,
            )
