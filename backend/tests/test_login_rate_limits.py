from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from railconnect.core.config import Settings
from railconnect.modules.identity.models.login_rate_limit import LoginRateLimit
from railconnect.modules.identity.rate_limit_service import (
    consume_login_attempt,
    login_limit_key,
)

NOW = datetime(2026, 10, 12, 12, tzinfo=UTC)


@pytest.fixture
def limit_settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        login_rate_window_seconds=60,
        login_client_max_attempts=3,
        login_account_max_attempts=2,
    )


def test_account_limit_applies_across_clients(
    identity_database: Session,
    limit_settings: Settings,
) -> None:
    username = f"limit_{uuid4().hex}"

    first = consume_login_attempt(
        identity_database, f"client_{uuid4().hex}", username, limit_settings, NOW
    )
    second = consume_login_attempt(
        identity_database, f"client_{uuid4().hex}", username, limit_settings, NOW
    )
    third = consume_login_attempt(
        identity_database, f"client_{uuid4().hex}", username, limit_settings, NOW
    )

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False
    assert third.retry_after == 60


def test_client_limit_applies_across_accounts(
    identity_database: Session,
    limit_settings: Settings,
) -> None:
    client = f"client_{uuid4().hex}"

    for _ in range(3):
        decision = consume_login_attempt(
            identity_database,
            client,
            f"limit_{uuid4().hex}",
            limit_settings,
            NOW,
        )
        assert decision.allowed is True

    blocked_account = f"limit_{uuid4().hex}"
    blocked = consume_login_attempt(
        identity_database,
        client,
        blocked_account,
        limit_settings,
        NOW,
    )

    assert blocked.allowed is False
    assert blocked.retry_after == 60
    assert (
        identity_database.scalar(
            select(LoginRateLimit).where(
                LoginRateLimit.scope == "account",
                LoginRateLimit.key_hash == login_limit_key("account", blocked_account),
            )
        )
        is None
    )


def test_account_normalization_does_not_bypass_limit(
    identity_database: Session,
    limit_settings: Settings,
) -> None:
    username = f"limit_{uuid4().hex}"

    first = consume_login_attempt(
        identity_database,
        f"client_{uuid4().hex}",
        username.upper(),
        limit_settings,
        NOW,
    )
    second = consume_login_attempt(
        identity_database,
        f"client_{uuid4().hex}",
        f"  {username}  ",
        limit_settings,
        NOW,
    )
    third = consume_login_attempt(
        identity_database,
        f"client_{uuid4().hex}",
        username,
        limit_settings,
        NOW,
    )

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False


def test_expired_window_resets_at_boundary(
    identity_database: Session,
    limit_settings: Settings,
) -> None:
    client = f"client_{uuid4().hex}"
    username = f"limit_{uuid4().hex}"

    for _ in range(2):
        assert (
            consume_login_attempt(identity_database, client, username, limit_settings, NOW).allowed
            is True
        )

    blocked = consume_login_attempt(
        identity_database,
        client,
        username,
        limit_settings,
        NOW + timedelta(seconds=59),
    )
    reset = consume_login_attempt(
        identity_database,
        client,
        username,
        limit_settings,
        NOW + timedelta(seconds=60),
    )

    assert blocked.allowed is False
    assert blocked.retry_after == 1
    assert reset.allowed is True
    assert reset.retry_after == 0

    account = identity_database.scalar(
        select(LoginRateLimit).where(
            LoginRateLimit.scope == "account",
            LoginRateLimit.key_hash == login_limit_key("account", username),
        )
    )
    assert account is not None
    assert account.attempt_count == 1
    assert account.window_started_at == NOW + timedelta(seconds=60)


def test_rejected_attempts_do_not_extend_window(
    identity_database: Session,
    limit_settings: Settings,
) -> None:
    client = f"client_{uuid4().hex}"
    username = f"limit_{uuid4().hex}"

    for _ in range(2):
        consume_login_attempt(identity_database, client, username, limit_settings, NOW)

    first_block = consume_login_attempt(
        identity_database,
        client,
        username,
        limit_settings,
        NOW + timedelta(seconds=10),
    )
    second_block = consume_login_attempt(
        identity_database,
        client,
        username,
        limit_settings,
        NOW + timedelta(seconds=20),
    )

    assert first_block.allowed is False
    assert first_block.retry_after == 50
    assert second_block.allowed is False
    assert second_block.retry_after == 40


def test_counter_is_bounded_after_repeated_rejections(
    identity_database: Session,
    limit_settings: Settings,
) -> None:
    client = f"client_{uuid4().hex}"
    username = f"limit_{uuid4().hex}"

    for _ in range(10):
        consume_login_attempt(identity_database, client, username, limit_settings, NOW)

    client_record = identity_database.scalar(
        select(LoginRateLimit).where(
            LoginRateLimit.scope == "client",
            LoginRateLimit.key_hash == login_limit_key("client", client),
        )
    )
    assert client_record is not None
    assert client_record.attempt_count == 4


def test_stored_keys_do_not_contain_raw_identifiers(
    identity_database: Session,
    limit_settings: Settings,
) -> None:
    client = f"client_{uuid4().hex}"
    username = f"limit_{uuid4().hex}"

    consume_login_attempt(identity_database, client, username, limit_settings, NOW)

    keys = [
        login_limit_key("client", client),
        login_limit_key("account", username),
    ]
    records = list(
        identity_database.scalars(select(LoginRateLimit).where(LoginRateLimit.key_hash.in_(keys)))
    )

    assert len(records) == 2
    assert all(len(record.key_hash) == 64 for record in records)
    assert all(client not in record.key_hash for record in records)
    assert all(username not in record.key_hash for record in records)


@pytest.mark.parametrize(
    ("client", "username"),
    [
        ("", "valid_staff"),
        ("x" * 129, "valid_staff"),
        ("valid_client", ""),
        ("valid_client", "x" * 65),
    ],
)
def test_invalid_identifiers_are_rejected(
    identity_database: Session,
    limit_settings: Settings,
    client: str,
    username: str,
) -> None:
    with pytest.raises(ValueError):
        consume_login_attempt(identity_database, client, username, limit_settings, NOW)


def test_naive_clock_is_rejected(
    identity_database: Session,
    limit_settings: Settings,
) -> None:
    with pytest.raises(ValueError, match="timezone-aware clock"):
        consume_login_attempt(
            identity_database,
            "valid_client",
            "valid_staff",
            limit_settings,
            datetime(2026, 10, 12, 12),
        )


def test_requires_caller_owned_transaction(
    identity_database: Session,
    limit_settings: Settings,
) -> None:
    with Session(bind=identity_database.get_bind()) as separate_session:
        with pytest.raises(ValueError, match="caller-owned transaction"):
            consume_login_attempt(
                separate_session,
                "valid_client",
                "valid_staff",
                limit_settings,
                NOW,
            )
