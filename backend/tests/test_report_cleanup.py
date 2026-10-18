from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from railconnect.modules.incidents.models.report_rate_limit import ReportRateLimit
from railconnect.modules.incidents.report_cleanup_service import cleanup_report_counters
from railconnect.modules.incidents.report_rate_service import report_limit_key

NOW = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


def add_counter(
    session: Session,
    expires_at: datetime,
) -> str:
    key = report_limit_key(f"cleanup-test-{uuid4().hex}")
    session.add(
        ReportRateLimit(
            key_hash=key,
            attempt_count=1,
            window_started_at=expires_at - timedelta(minutes=5),
            window_expires_at=expires_at,
            updated_at=expires_at - timedelta(minutes=1),
        )
    )
    session.flush()
    return key


def counter_exists(session: Session, key: str) -> bool:
    return (
        session.scalar(select(ReportRateLimit.key_hash).where(ReportRateLimit.key_hash == key))
        is not None
    )


def test_preview_preserves_eligible_counter(
    identity_database: Session,
) -> None:
    key = add_counter(identity_database, NOW - timedelta(days=2))

    result = cleanup_report_counters(identity_database, NOW)

    assert result.applied is False
    assert result.records >= 1
    assert counter_exists(identity_database, key)


def test_apply_deletes_old_counter(
    identity_database: Session,
) -> None:
    key = add_counter(identity_database, NOW - timedelta(days=2))

    result = cleanup_report_counters(identity_database, NOW, apply=True)

    assert result.applied is True
    assert result.records >= 1
    assert not counter_exists(identity_database, key)


@pytest.mark.parametrize(
    "expiry",
    [
        NOW + timedelta(minutes=5),
        NOW - timedelta(hours=12),
    ],
)
def test_preserves_current_and_recently_expired_counters(
    identity_database: Session,
    expiry: datetime,
) -> None:
    key = add_counter(identity_database, expiry)

    cleanup_report_counters(identity_database, NOW, apply=True)

    assert counter_exists(identity_database, key)


def test_counter_is_eligible_at_exact_retention_boundary(
    identity_database: Session,
) -> None:
    key = add_counter(identity_database, NOW - timedelta(days=1))

    cleanup_report_counters(identity_database, NOW, apply=True)

    assert not counter_exists(identity_database, key)


def test_custom_retention_preserves_younger_counter(
    identity_database: Session,
) -> None:
    key = add_counter(identity_database, NOW - timedelta(days=2))

    cleanup_report_counters(
        identity_database,
        NOW,
        apply=True,
        retention_days=3,
    )

    assert counter_exists(identity_database, key)


def test_apply_obeys_batch_limit(
    identity_database: Session,
) -> None:
    for index in range(3):
        add_counter(
            identity_database,
            datetime(2000, 1, 1, tzinfo=UTC) + timedelta(minutes=index),
        )

    before = identity_database.scalar(select(func.count()).select_from(ReportRateLimit))
    assert before is not None

    result = cleanup_report_counters(
        identity_database,
        NOW,
        apply=True,
        batch_limit=2,
    )

    after = identity_database.scalar(select(func.count()).select_from(ReportRateLimit))
    assert after is not None

    assert result.records == 2
    assert before - after == 2


def test_applied_cleanup_rolls_back(
    identity_database: Session,
) -> None:
    key = add_counter(identity_database, NOW - timedelta(days=2))

    with pytest.raises(RuntimeError, match="Synthetic failure"):
        with identity_database.begin_nested():
            cleanup_report_counters(identity_database, NOW, apply=True)
            assert not counter_exists(identity_database, key)
            raise RuntimeError("Synthetic failure")

    assert counter_exists(identity_database, key)


@pytest.mark.parametrize(
    ("retention_days", "batch_limit"),
    [
        (0, 500),
        (366, 500),
        (1, 0),
        (1, 1001),
    ],
)
def test_rejects_invalid_cleanup_bounds(
    identity_database: Session,
    retention_days: int,
    batch_limit: int,
) -> None:
    with pytest.raises(ValueError):
        cleanup_report_counters(
            identity_database,
            NOW,
            retention_days=retention_days,
            batch_limit=batch_limit,
        )


def test_rejects_naive_cleanup_clock(
    identity_database: Session,
) -> None:
    with pytest.raises(ValueError, match="timezone-aware clock"):
        cleanup_report_counters(
            identity_database,
            NOW.replace(tzinfo=None),
        )


def test_requires_caller_owned_transaction() -> None:
    with Session() as session:
        with pytest.raises(ValueError, match="caller-owned transaction"):
            cleanup_report_counters(session, NOW)


def test_rejects_pending_session_changes(
    identity_database: Session,
) -> None:
    identity_database.add(
        ReportRateLimit(
            key_hash=report_limit_key(f"pending-test-{uuid4().hex}"),
            attempt_count=1,
            window_started_at=NOW,
            window_expires_at=NOW + timedelta(minutes=5),
            updated_at=NOW,
        )
    )

    with pytest.raises(ValueError, match="without pending changes"):
        cleanup_report_counters(identity_database, NOW)
