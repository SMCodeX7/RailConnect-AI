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
from railconnect.modules.incidents.models.report_rate_limit import ReportRateLimit
from railconnect.modules.incidents.report_rate_service import (
    consume_report_attempt,
    report_limit_key,
)

NOW = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


@pytest.fixture
def report_settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        report_rate_window_seconds=60,
        report_client_max_attempts=2,
    )


@pytest.fixture
def client_key() -> str:
    return f"report-test-{uuid4().hex}"


def stored_count(session: Session, client: str) -> int | None:
    return session.scalar(
        select(ReportRateLimit.attempt_count).where(
            ReportRateLimit.key_hash == report_limit_key(client)
        )
    )


def test_first_attempt_is_allowed(
    identity_database: Session,
    report_settings: Settings,
    client_key: str,
) -> None:
    decision = consume_report_attempt(identity_database, client_key, report_settings, NOW)

    assert decision.allowed is True
    assert decision.retry_after == 0
    assert stored_count(identity_database, client_key) == 1


def test_rejects_attempt_above_limit(
    identity_database: Session,
    report_settings: Settings,
    client_key: str,
) -> None:
    decisions = [
        consume_report_attempt(identity_database, client_key, report_settings, NOW)
        for _ in range(3)
    ]

    assert [decision.allowed for decision in decisions] == [True, True, False]
    assert decisions[-1].retry_after == 60
    assert stored_count(identity_database, client_key) == 3


def test_clients_have_independent_limits(
    identity_database: Session,
    report_settings: Settings,
    client_key: str,
) -> None:
    for _ in range(3):
        consume_report_attempt(identity_database, client_key, report_settings, NOW)

    other_client = f"report-test-{uuid4().hex}"
    decision = consume_report_attempt(identity_database, other_client, report_settings, NOW)

    assert decision.allowed is True
    assert stored_count(identity_database, other_client) == 1


def test_window_does_not_reset_before_expiry(
    identity_database: Session,
    report_settings: Settings,
    client_key: str,
) -> None:
    for _ in range(2):
        consume_report_attempt(identity_database, client_key, report_settings, NOW)

    decision = consume_report_attempt(
        identity_database,
        client_key,
        report_settings,
        NOW + timedelta(seconds=59),
    )

    assert decision.allowed is False
    assert decision.retry_after == 1


def test_window_resets_at_exact_expiry(
    identity_database: Session,
    report_settings: Settings,
    client_key: str,
) -> None:
    for _ in range(3):
        consume_report_attempt(identity_database, client_key, report_settings, NOW)

    reset_time = NOW + timedelta(seconds=60)
    decision = consume_report_attempt(identity_database, client_key, report_settings, reset_time)

    assert decision.allowed is True
    assert stored_count(identity_database, client_key) == 1

    row = identity_database.get(ReportRateLimit, report_limit_key(client_key))
    assert row is not None
    assert row.window_started_at == reset_time
    assert row.window_expires_at == reset_time + timedelta(seconds=60)


def test_rejected_counter_is_bounded(
    identity_database: Session,
    report_settings: Settings,
    client_key: str,
) -> None:
    for _ in range(10):
        consume_report_attempt(identity_database, client_key, report_settings, NOW)

    assert stored_count(identity_database, client_key) == 3


def test_retry_interval_rounds_up(
    identity_database: Session,
    report_settings: Settings,
    client_key: str,
) -> None:
    for _ in range(2):
        consume_report_attempt(identity_database, client_key, report_settings, NOW)

    decision = consume_report_attempt(
        identity_database,
        client_key,
        report_settings,
        NOW + timedelta(seconds=58, milliseconds=500),
    )

    assert decision.allowed is False
    assert decision.retry_after == 2


def test_report_limits_do_not_change_login_counters(
    identity_database: Session,
    report_settings: Settings,
    client_key: str,
) -> None:
    username = f"staff_{uuid4().hex}"

    login_decision = consume_login_attempt(
        identity_database,
        client_key,
        username,
        report_settings,
        NOW,
    )
    assert login_decision.allowed is True

    for _ in range(3):
        consume_report_attempt(identity_database, client_key, report_settings, NOW)

    login_count = identity_database.scalar(
        select(LoginRateLimit.attempt_count).where(
            LoginRateLimit.scope == "client",
            LoginRateLimit.key_hash == login_limit_key("client", client_key),
        )
    )

    assert login_count == 1
    assert stored_count(identity_database, client_key) == 3


@pytest.mark.parametrize("client", ["   ", "x" * 129])
def test_rejects_invalid_client_identifiers(
    identity_database: Session,
    report_settings: Settings,
    client: str,
) -> None:
    with pytest.raises(ValueError, match="bounded client identifier"):
        consume_report_attempt(identity_database, client, report_settings, NOW)


def test_rejects_naive_clock(
    identity_database: Session,
    report_settings: Settings,
    client_key: str,
) -> None:
    with pytest.raises(ValueError, match="timezone-aware clock"):
        consume_report_attempt(
            identity_database,
            client_key,
            report_settings,
            NOW.replace(tzinfo=None),
        )

    assert stored_count(identity_database, client_key) is None


def test_requires_caller_owned_transaction(
    report_settings: Settings,
    client_key: str,
) -> None:
    with Session() as session:
        with pytest.raises(ValueError, match="caller-owned transaction"):
            consume_report_attempt(session, client_key, report_settings, NOW)


def test_counter_write_rolls_back_with_transaction(
    identity_database: Session,
    report_settings: Settings,
    client_key: str,
) -> None:
    with pytest.raises(RuntimeError, match="Synthetic failure"):
        with identity_database.begin_nested():
            consume_report_attempt(identity_database, client_key, report_settings, NOW)
            assert stored_count(identity_database, client_key) == 1
            raise RuntimeError("Synthetic failure")

    assert stored_count(identity_database, client_key) is None
