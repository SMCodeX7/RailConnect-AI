from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from railconnect.core.config import Settings
from railconnect.db.session import create_db_engine
from railconnect.modules.incidents.models.report_rate_limit import ReportRateLimit
from railconnect.modules.incidents.report_rate_service import (
    ReportRateDecision,
    consume_report_attempt,
    report_limit_key,
)


def test_concurrent_report_attempts_preserve_admission_limit() -> None:
    database_settings = Settings()

    if database_settings.database_url is None:
        pytest.skip("PostgreSQL is required for report concurrency tests.")

    if database_settings.environment not in {"development", "test"}:
        pytest.fail("Report concurrency tests require a development or test database.")

    limit_settings = Settings(
        _env_file=None,
        environment="test",
        report_rate_window_seconds=60,
        report_client_max_attempts=3,
    )

    engine = create_db_engine(database_settings)
    client_key = f"report-concurrency-{uuid4().hex}"
    key_hash = report_limit_key(client_key)
    now = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)
    barrier = Barrier(8)

    def attempt() -> ReportRateDecision:
        barrier.wait(timeout=15)

        with Session(engine) as session:
            with session.begin():
                session.execute(text("SET LOCAL statement_timeout = '10s'"))

                return consume_report_attempt(
                    session,
                    client_key,
                    limit_settings,
                    now,
                )

    try:
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(attempt) for _ in range(8)]
            decisions = [future.result(timeout=30) for future in futures]

        assert sum(decision.allowed for decision in decisions) == 3
        assert sum(not decision.allowed for decision in decisions) == 5

        for decision in decisions:
            assert decision.retry_after == (0 if decision.allowed else 60)

        with Session(engine) as session:
            stored_count = session.scalar(
                select(ReportRateLimit.attempt_count).where(ReportRateLimit.key_hash == key_hash)
            )

        assert stored_count == 4
    finally:
        try:
            with Session(engine) as session:
                with session.begin():
                    session.execute(
                        delete(ReportRateLimit).where(ReportRateLimit.key_hash == key_hash)
                    )
        finally:
            engine.dispose()
