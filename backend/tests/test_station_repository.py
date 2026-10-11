from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from railconnect.core.config import Settings
from railconnect.db.session import create_db_engine
from railconnect.modules.stations.models import Station
from railconnect.modules.stations.repository import list_stations


@pytest.fixture
def station_database() -> Iterator[tuple[Session, str]]:
    settings = Settings()

    if settings.database_url is None:
        pytest.skip("PostgreSQL is not configured.")

    if settings.environment not in {"development", "test"}:
        pytest.fail("Repository tests require development or test configuration.")

    engine = create_db_engine(settings)
    prefix = f"Test{uuid4().hex[:8]}"
    names = [
        "Alpha Jaffna",
        "Beta Trincomalee",
        "Central 100%",
        "Central 100X",
        "Platform_One",
        "PlatformXOne",
        "Hidden",
    ]

    try:
        with engine.connect() as connection:
            transaction = connection.begin()

            try:
                with Session(
                    bind=connection,
                    join_transaction_mode="create_savepoint",
                ) as session:
                    session.add_all(
                        [
                            Station(
                                code=f"TEST_{uuid4().hex[:12].upper()}",
                                name=f"{prefix} {name}",
                                source_ref="repository-test",
                                is_active=name != "Hidden",
                            )
                            for name in names
                        ]
                    )
                    session.flush()
                    yield session, prefix
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


def test_only_active_stations_are_returned(
    station_database: tuple[Session, str],
) -> None:
    session, prefix = station_database

    stations, total = list_stations(session, prefix, limit=50, offset=0)

    assert total == 6
    assert len(stations) == 6
    assert all(station.is_active for station in stations)
    assert {station.name for station in stations} == {
        f"{prefix} Alpha Jaffna",
        f"{prefix} Beta Trincomalee",
        f"{prefix} Central 100%",
        f"{prefix} Central 100X",
        f"{prefix} Platform_One",
        f"{prefix} PlatformXOne",
    }


def test_search_is_case_insensitive(
    station_database: tuple[Session, str],
) -> None:
    session, prefix = station_database

    stations, total = list_stations(
        session,
        f"{prefix.lower()} alpha JAFFNA",
        limit=50,
        offset=0,
    )

    assert total == 1
    assert stations[0].name == f"{prefix} Alpha Jaffna"


def test_pagination_preserves_total(
    station_database: tuple[Session, str],
) -> None:
    session, prefix = station_database

    stations, total = list_stations(session, prefix, limit=2, offset=2)

    assert total == 6
    assert [station.name for station in stations] == [
        f"{prefix} Central 100%",
        f"{prefix} Central 100X",
    ]


@pytest.mark.parametrize(
    ("search_suffix", "expected_suffix"),
    [
        ("100%", "Central 100%"),
        ("Platform_", "Platform_One"),
    ],
)
def test_search_treats_wildcards_as_literal_characters(
    station_database: tuple[Session, str],
    search_suffix: str,
    expected_suffix: str,
) -> None:
    session, prefix = station_database

    stations, total = list_stations(
        session,
        search=f"{prefix} {expected_suffix}"
        if search_suffix == "100%"
        else (f"{prefix} {search_suffix}"),
        limit=50,
        offset=0,
    )

    assert total == 1
    assert stations[0].name == f"{prefix} {expected_suffix}"


def test_search_matches_station_code(
    station_database: tuple[Session, str],
) -> None:
    session, prefix = station_database
    existing, _ = list_stations(session, prefix, limit=50, offset=0)
    target = existing[0]

    stations, total = list_stations(
        session,
        target.code.lower(),
        limit=50,
        offset=0,
    )

    assert total == 1
    assert stations[0].id == target.id


def test_search_without_matches_returns_empty_list(
    station_database: tuple[Session, str],
) -> None:
    session, prefix = station_database

    stations, total = list_stations(
        session,
        f"{prefix} nonexistent",
        limit=50,
        offset=0,
    )

    assert stations == []
    assert total == 0
