from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from railconnect.core.config import Settings
from railconnect.db.session import create_db_engine
from railconnect.modules.identity.models.login_rate_limit import LoginRateLimit
from railconnect.modules.identity.rate_limit_service import (
    LoginRateDecision,
    consume_login_attempt,
    login_limit_key,
)

NOW = datetime(2026, 10, 14, 12, tzinfo=UTC)
WORKERS = 8


@dataclass
class ConcurrentLimitDatabase:
    engine: Engine
    settings: Settings
    prefix: str
    keys: set[str] = field(default_factory=set)


@pytest.fixture
def concurrent_database() -> Iterator[ConcurrentLimitDatabase]:
    settings = Settings()

    if settings.database_url is None:
        pytest.skip("PostgreSQL is required for concurrency tests.")

    if settings.environment not in {"development", "test"}:
        pytest.fail("Concurrency tests require a development or test database.")

    engine = create_db_engine(settings)
    database = ConcurrentLimitDatabase(
        engine=engine,
        settings=settings,
        prefix=uuid4().hex,
    )

    try:
        yield database
    finally:
        try:
            if database.keys:
                with engine.begin() as connection:
                    connection.execute(
                        delete(LoginRateLimit).where(LoginRateLimit.key_hash.in_(database.keys))
                    )
        finally:
            engine.dispose()


@pytest.mark.parametrize("scope", ["account", "client"])
def test_simultaneous_attempts_cannot_exceed_limit(
    concurrent_database: ConcurrentLimitDatabase,
    scope: str,
) -> None:
    database = concurrent_database
    settings = database.settings.model_copy(
        update={
            "login_rate_window_seconds": 60,
            "login_account_max_attempts": 3 if scope == "account" else 100,
            "login_client_max_attempts": 3 if scope == "client" else 100,
        }
    )
    shared_client = f"client_{database.prefix}"
    shared_account = f"staff_{database.prefix}"

    inputs = [
        (
            shared_client if scope == "client" else f"{shared_client}_{index}",
            shared_account if scope == "account" else f"{shared_account}_{index}",
        )
        for index in range(WORKERS)
    ]

    for client, account in inputs:
        database.keys.add(login_limit_key("client", client))
        database.keys.add(login_limit_key("account", account))

    barrier = Barrier(WORKERS)

    def attempt(values: tuple[str, str]) -> LoginRateDecision:
        client, account = values

        with Session(database.engine) as session:
            with session.begin():
                session.execute(text("SET LOCAL statement_timeout = '10s'"))
                barrier.wait(timeout=15)
                decision = consume_login_attempt(
                    session,
                    client,
                    account,
                    settings,
                    NOW,
                )

        return decision

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(attempt, values) for values in inputs]
        decisions = [future.result(timeout=30) for future in futures]

    assert sum(decision.allowed for decision in decisions) == 3
    blocked = [decision for decision in decisions if not decision.allowed]
    assert len(blocked) == 5
    assert all(decision.retry_after == 60 for decision in blocked)

    shared_value = shared_account if scope == "account" else shared_client

    with Session(database.engine) as session:
        record = session.scalar(
            select(LoginRateLimit).where(
                LoginRateLimit.scope == scope,
                LoginRateLimit.key_hash == login_limit_key(scope, shared_value),
            )
        )
        assert record is not None
        assert record.attempt_count == 4
