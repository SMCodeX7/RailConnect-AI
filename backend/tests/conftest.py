from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from railconnect.core.config import Settings
from railconnect.db.session import create_db_engine
from railconnect.modules.stations.models import Station
from railconnect.modules.timetable.seed_schemas import DemoTimetableDataset


@pytest.fixture
def timetable_database() -> Iterator[tuple[Session, DemoTimetableDataset]]:
    settings = Settings()

    if settings.database_url is None:
        pytest.skip("PostgreSQL is required for timetable tests.")

    if settings.environment not in {"development", "test"}:
        pytest.fail("Timetable tests require a development or test database.")

    engine = create_db_engine(settings)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    try:
        prefix = f"DEMO_T{uuid4().hex[:8].upper()}"
        station_codes = [f"{prefix}{suffix}" for suffix in ("A", "B", "C")]

        session.add_all(
            [
                Station(
                    code=code,
                    name=f"Timetable Test {code}",
                    source_ref="timetable-test",
                    is_active=True,
                )
                for code in station_codes
            ]
        )
        session.flush()

        dataset = DemoTimetableDataset.model_validate(
            {
                "kind": "demonstration",
                "timezone": "Asia/Colombo",
                "source_ref": "timetable-test",
                "valid_from": "2026-01-01",
                "valid_until": "2028-12-31",
                "services": [
                    {
                        "code": f"{prefix}_OUT",
                        "name": "Test Outbound",
                        "operating_days": 127,
                        "stops": [
                            {
                                "station_code": station_codes[0],
                                "departure_minutes": 600,
                            },
                            {
                                "station_code": station_codes[1],
                                "arrival_minutes": 660,
                                "departure_minutes": 665,
                            },
                            {
                                "station_code": station_codes[2],
                                "arrival_minutes": 720,
                            },
                        ],
                    },
                    {
                        "code": f"{prefix}_RETURN",
                        "name": "Test Return",
                        "operating_days": 31,
                        "stops": [
                            {
                                "station_code": station_codes[2],
                                "departure_minutes": 780,
                            },
                            {
                                "station_code": station_codes[1],
                                "arrival_minutes": 835,
                                "departure_minutes": 840,
                            },
                            {
                                "station_code": station_codes[0],
                                "arrival_minutes": 900,
                            },
                        ],
                    },
                ],
            }
        )

        yield session, dataset
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()
