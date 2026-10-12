from collections.abc import Iterator
from datetime import date
from hashlib import sha256
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from railconnect.app import create_app
from railconnect.core.config import Settings
from railconnect.db.dependencies import get_db_session
from railconnect.modules.journeys.schemas import JourneySearchQuery
from railconnect.modules.stations.models import Station
from railconnect.modules.timetable.import_schemas import (
    TimetableImportSnapshot,
    TimetableSourceMetadata,
)
from railconnect.modules.timetable.import_service import import_timetable
from railconnect.modules.timetable.models.train_service import TrainService
from railconnect.modules.timetable.run_service import materialize_service_run
from railconnect.modules.timetable.seed_schemas import DemoTimetableDataset
from railconnect.modules.timetable.seeding import seed_timetable


@pytest.fixture(params=[False, True], ids=["unregistered", "registered"])
def source_client(
    timetable_database: tuple[Session, DemoTimetableDataset],
    request: pytest.FixtureRequest,
) -> Iterator[tuple[TestClient, UUID, JourneySearchQuery, bool, str]]:
    session, dataset = timetable_database
    registered = bool(request.param)
    digest = sha256(dataset.model_dump_json().encode("utf-8")).hexdigest()

    if registered:
        snapshot = TimetableImportSnapshot(
            dataset=dataset,
            metadata=TimetableSourceMetadata(
                title="Fictional source fixture",
                source_uri="test-fixtures/timetable.json",
                reuse_basis="Project-generated fictional test data.",
            ),
            content_sha256=digest,
        )
        import_timetable(session, snapshot, execution_context="pytest")
    else:
        seed_timetable(session, dataset)

    service = session.scalar(
        select(TrainService).where(TrainService.code == dataset.services[0].code)
    )
    assert service is not None
    run = materialize_service_run(session, service.id, date(2026, 10, 12)).run

    departure = session.scalar(
        select(Station).where(Station.code == dataset.services[0].stops[0].station_code)
    )
    arrival = session.scalar(
        select(Station).where(Station.code == dataset.services[0].stops[-1].station_code)
    )
    assert departure is not None
    assert arrival is not None

    query = JourneySearchQuery(
        departure_station_id=departure.id,
        arrival_station_id=arrival.id,
        travel_date=date(2026, 10, 12),
    )
    app = create_app(
        Settings(
            _env_file=None,
            environment="test",
            debug=False,
            database_url=None,
        )
    )

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_db_session] = override_session

    try:
        with TestClient(app) as client:
            yield client, run.id, query, registered, digest
    finally:
        app.dependency_overrides.clear()


def test_search_exposes_registered_source_or_null(
    source_client: tuple[TestClient, UUID, JourneySearchQuery, bool, str],
) -> None:
    client, _, query, registered, digest = source_client

    response = client.get(
        "/api/v1/journeys",
        params=query.model_dump(mode="json", exclude_none=True),
    )

    assert response.status_code == 200
    source = response.json()["items"][0]["source"]

    if registered:
        assert source["source_ref"] == "timetable-test"
        assert source["title"] == "Fictional source fixture"
        assert source["data_kind"] == "demonstration"
        assert source["content_sha256"] == digest
        assert source["effective_from"] == "2026-01-01"
        assert source["effective_until"] == "2028-12-31"
        assert source["retrieved_at"] is None
        assert source["registered_at"]
    else:
        assert source is None


def test_details_expose_registered_source_or_null(
    source_client: tuple[TestClient, UUID, JourneySearchQuery, bool, str],
) -> None:
    client, run_id, _, registered, digest = source_client

    response = client.get(f"/api/v1/journeys/{run_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["source_ref"] == "timetable-test"
    source = body["source"]

    if registered:
        assert source["content_sha256"] == digest
        assert source["source_uri"] == "test-fixtures/timetable.json"
        assert source["reuse_basis"] == "Project-generated fictional test data."
        assert source["retrieved_at"] is None
    else:
        assert source is None
