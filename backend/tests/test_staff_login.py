from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from railconnect.core.config import Settings
from railconnect.modules.identity import login_service
from railconnect.modules.identity.auth_schemas import LoginInput
from railconnect.modules.identity.errors import AuthenticationError, LoginRateLimitError
from railconnect.modules.identity.login_service import login_staff
from railconnect.modules.identity.models.auth_session import AuthSession
from railconnect.modules.identity.models.login_rate_limit import LoginRateLimit
from railconnect.modules.identity.models.user import User
from railconnect.modules.identity.models.user_role import UserRole
from railconnect.modules.identity.passwords import hash_password, verify_password
from railconnect.modules.identity.permissions import Permission, RoleCode
from railconnect.modules.identity.provisioning_schemas import ProvisionStaffInput
from railconnect.modules.identity.provisioning_service import provision_staff_user
from railconnect.modules.identity.rate_limit_service import login_limit_key
from railconnect.modules.identity.tokens import hash_session_token

PASSWORD = "Fictional login test passphrase"
NOW = datetime(2026, 10, 13, 12, tzinfo=UTC)


@dataclass(frozen=True)
class LoginContext:
    database: Session
    session: Session
    user: User
    settings: Settings
    client_key: str


@pytest.fixture(scope="module")
def login_password_hash() -> str:
    return hash_password(PASSWORD)


@pytest.fixture
def login_context(
    identity_database: Session,
    login_password_hash: str,
) -> Iterator[LoginContext]:
    user = provision_staff_user(
        identity_database,
        ProvisionStaffInput(
            username=f"login_{uuid4().hex}",
            display_name="Fictional Login Staff",
            role=RoleCode.CONTROLLER,
        ),
        login_password_hash,
    )
    settings = Settings(
        _env_file=None,
        environment="test",
        session_cookie_secure=False,
        login_account_max_attempts=2,
        login_client_max_attempts=20,
    )

    with Session(
        bind=identity_database.get_bind(),
        join_transaction_mode="create_savepoint",
    ) as login_session:
        yield LoginContext(
            database=identity_database,
            session=login_session,
            user=user,
            settings=settings,
            client_key=f"client_{uuid4().hex}",
        )


def credentials(username: str, password: str = PASSWORD) -> LoginInput:
    return LoginInput.model_validate({"username": username, "password": password})


def test_login_input_preserves_password_and_normalizes_username() -> None:
    data = credentials("  Alice.Staff  ", "  A private staff passphrase  ")

    assert data.username == "alice.staff"
    assert data.password.get_secret_value() == "  A private staff passphrase  "
    assert "A private staff passphrase" not in repr(data)


def test_successful_login_commits_session(login_context: LoginContext) -> None:
    context = login_context
    created = login_staff(
        context.session,
        credentials(context.user.username),
        context.client_key,
        context.settings,
        clock=lambda: NOW,
    )

    assert context.session.in_transaction() is False
    assert created.actor.user_id == str(context.user.id)
    assert Permission.REPORTS_REVIEW in created.actor.permissions

    with context.session.begin():
        stored = context.session.get(AuthSession, created.session_id)
        assert stored is not None
        assert stored.token_hash == hash_session_token(created.token)
        assert stored.token_hash != created.token
        assert stored.auth_version == context.user.auth_version


def test_wrong_password_commits_attempt_without_session(
    login_context: LoginContext,
) -> None:
    context = login_context

    with pytest.raises(AuthenticationError):
        login_staff(
            context.session,
            credentials(context.user.username, "A different fictional password"),
            context.client_key,
            context.settings,
            clock=lambda: NOW,
        )

    assert context.session.in_transaction() is False

    with context.session.begin():
        counter = context.session.scalar(
            select(LoginRateLimit).where(
                LoginRateLimit.scope == "account",
                LoginRateLimit.key_hash == login_limit_key("account", context.user.username),
            )
        )
        assert counter is not None
        assert counter.attempt_count == 1
        assert (
            context.session.scalar(
                select(func.count())
                .select_from(AuthSession)
                .where(AuthSession.user_id == context.user.id)
            )
            == 0
        )


def test_unknown_account_has_generic_failure(login_context: LoginContext) -> None:
    context = login_context

    with pytest.raises(AuthenticationError, match="Authentication failed"):
        login_staff(
            context.session,
            credentials(f"unknown_{uuid4().hex}"),
            context.client_key,
            context.settings,
            clock=lambda: NOW,
        )


def test_disabled_account_cannot_login(login_context: LoginContext) -> None:
    context = login_context
    context.user.is_active = False
    context.database.flush()

    with pytest.raises(AuthenticationError):
        login_staff(
            context.session,
            credentials(context.user.username),
            context.client_key,
            context.settings,
            clock=lambda: NOW,
        )


def test_account_without_staff_permissions_cannot_login(
    login_context: LoginContext,
) -> None:
    context = login_context
    context.database.execute(delete(UserRole).where(UserRole.user_id == context.user.id))
    context.database.flush()

    with pytest.raises(AuthenticationError):
        login_staff(
            context.session,
            credentials(context.user.username),
            context.client_key,
            context.settings,
            clock=lambda: NOW,
        )

    with context.session.begin():
        assert (
            context.session.scalar(
                select(func.count())
                .select_from(AuthSession)
                .where(AuthSession.user_id == context.user.id)
            )
            == 0
        )


def test_rate_limit_blocks_even_correct_password_before_verification(
    login_context: LoginContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = login_context

    for _ in range(2):
        with pytest.raises(AuthenticationError):
            login_staff(
                context.session,
                credentials(context.user.username, "A different fictional password"),
                context.client_key,
                context.settings,
                clock=lambda: NOW,
            )

    def unexpected_verification(encoded_hash: str, password: str) -> bool:
        raise AssertionError("Blocked login must not verify a password.")

    monkeypatch.setattr(login_service, "verify_password", unexpected_verification)

    with pytest.raises(LoginRateLimitError) as caught:
        login_staff(
            context.session,
            credentials(context.user.username),
            context.client_key,
            context.settings,
            clock=lambda: NOW,
        )

    assert caught.value.retry_after == 300
    assert context.session.in_transaction() is False

    with context.session.begin():
        counter = context.session.scalar(
            select(LoginRateLimit).where(
                LoginRateLimit.scope == "account",
                LoginRateLimit.key_hash == login_limit_key("account", context.user.username),
            )
        )
        assert counter is not None
        assert counter.attempt_count == 3


def test_correct_login_after_one_failure_keeps_attempt_history(
    login_context: LoginContext,
) -> None:
    context = login_context

    with pytest.raises(AuthenticationError):
        login_staff(
            context.session,
            credentials(context.user.username, "A different fictional password"),
            context.client_key,
            context.settings,
            clock=lambda: NOW,
        )

    created = login_staff(
        context.session,
        credentials(context.user.username),
        context.client_key,
        context.settings,
        clock=lambda: NOW,
    )

    assert created.actor.username == context.user.username

    with context.session.begin():
        counter = context.session.scalar(
            select(LoginRateLimit).where(
                LoginRateLimit.scope == "account",
                LoginRateLimit.key_hash == login_limit_key("account", context.user.username),
            )
        )
        assert counter is not None
        assert counter.attempt_count == 2


@pytest.mark.parametrize("change", ["disable", "password", "auth_version"])
def test_account_changes_during_verification_prevent_login(
    login_context: LoginContext,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    context = login_context

    def verify_then_change(encoded_hash: str, password: str) -> bool:
        verified = verify_password(encoded_hash, password)

        if change == "disable":
            context.user.is_active = False
        elif change == "password":
            context.user.password_hash = hash_password("A changed fictional staff passphrase")
        else:
            context.user.auth_version += 1

        context.database.flush()
        return verified

    monkeypatch.setattr(login_service, "verify_password", verify_then_change)

    with pytest.raises(AuthenticationError):
        login_staff(
            context.session,
            credentials(context.user.username),
            context.client_key,
            context.settings,
            clock=lambda: NOW,
        )

    with context.session.begin():
        assert (
            context.session.scalar(
                select(func.count())
                .select_from(AuthSession)
                .where(AuthSession.user_id == context.user.id)
            )
            == 0
        )


def test_login_rejects_session_with_active_transaction(
    login_context: LoginContext,
) -> None:
    context = login_context

    with pytest.raises(ValueError, match="fresh session"):
        login_staff(
            context.database,
            credentials(context.user.username),
            context.client_key,
            context.settings,
            clock=lambda: NOW,
        )
