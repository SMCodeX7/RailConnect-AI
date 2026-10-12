from collections.abc import Iterator
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from railconnect.app import create_app
from railconnect.core.config import Settings
from railconnect.db.dependencies import get_db_session
from railconnect.modules.timetable.models.run_stop import RunStop
from railconnect.modules.timetable.models.service_run import ServiceRun
from railconnect.modules.timetable.models.train_service import TrainService
from railconnect.modules.timetable.run_service import materialize_service_run
from railconnect.modules.timetable.seed_schemas import DemoTimetableDataset
from railconnect.modules.timetable.seeding import seed_timetable


@pytest.fixture
def detail_client(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> Iterator[tuple[TestClient, Session, UUID]]:
    session, dataset = timetable_database
    seed_timetable(session, dataset)

    service = session.scalar(
        select(TrainService).where(TrainService.code == dataset.services[0].code)
    )
    assert service is not None

    result = materialize_service_run(session, service.id, date(2026, 10, 12))
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
            yield client, session, result.run.id
    finally:
        app.dependency_overrides.clear()


def test_returns_full_ordered_schedule(
    detail_client: tuple[TestClient, Session, UUID],
) -> None:
    client, _, run_id = detail_client

    response = client.get(f"/api/v1/journeys/{run_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == str(run_id)
    assert body["service_date"] == "2026-10-12"
    assert body["run_status"] == "scheduled"
    assert body["run_version"] == 1
    assert body["source_ref"] == "timetable-test"
    assert body["data_kind"] == "demonstration"
    assert body["timezone"] == "Asia/Colombo"
    assert body["selected_segment"] is None

    stops = body["stops"]
    assert [stop["stop_sequence"] for stop in stops] == [1, 2, 3]
    assert len({stop["station"]["id"] for stop in stops}) == 3
    assert stops[0]["scheduled_arrival_at"] is None
    assert stops[0]["scheduled_departure_at"] == "2026-10-12T10:00:00+05:30"
    assert stops[0]["pickup_allowed"] is True
    assert stops[0]["dropoff_allowed"] is False
    assert stops[1]["scheduled_arrival_at"] == "2026-10-12T11:00:00+05:30"
    assert stops[1]["scheduled_departure_at"] == "2026-10-12T11:05:00+05:30"
    assert stops[2]["scheduled_arrival_at"] == "2026-10-12T12:00:00+05:30"
    assert stops[2]["scheduled_departure_at"] is None
    assert stops[2]["pickup_allowed"] is False
    assert stops[2]["dropoff_allowed"] is True
    assert response.headers["X-Request-ID"]


def test_returns_selected_intermediate_segment(
    detail_client: tuple[TestClient, Session, UUID],
) -> None:
    client, _, run_id = detail_client

    response = client.get(
        f"/api/v1/journeys/{run_id}",
        params={
            "departure_stop_sequence": 2,
            "arrival_stop_sequence": 3,
        },
    )

    assert response.status_code == 200
    body = response.json()
    segment = body["selected_segment"]
    assert segment["departure_stop_sequence"] == 2
    assert segment["arrival_stop_sequence"] == 3
    assert segment["departure_station"]["id"] == body["stops"][1]["station"]["id"]
    assert segment["arrival_station"]["id"] == body["stops"][2]["station"]["id"]
    assert segment["scheduled_departure_at"] == "2026-10-12T11:05:00+05:30"
    assert segment["scheduled_arrival_at"] == "2026-10-12T12:00:00+05:30"
    assert segment["duration_minutes"] == 55
    assert len(body["stops"]) == 3


def test_returns_overnight_stop_dates(
    detail_client: tuple[TestClient, Session, UUID],
) -> None:
    client, session, run_id = detail_client
    stops = list(
        session.scalars(
            select(RunStop).where(RunStop.run_id == run_id).order_by(RunStop.stop_sequence)
        )
    )

    stops[0].scheduled_departure_at = datetime(2026, 10, 12, 15, 30, tzinfo=UTC)
    stops[1].scheduled_arrival_at = datetime(2026, 10, 12, 22, 10, tzinfo=UTC)
    stops[1].scheduled_departure_at = datetime(2026, 10, 12, 22, 15, tzinfo=UTC)
    stops[2].scheduled_arrival_at = datetime(2026, 10, 13, 0, 30, tzinfo=UTC)
    session.flush()

    response = client.get(
        f"/api/v1/journeys/{run_id}",
        params={
            "departure_stop_sequence": 1,
            "arrival_stop_sequence": 3,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["service_date"] == "2026-10-12"
    assert body["stops"][0]["scheduled_departure_at"] == "2026-10-12T21:00:00+05:30"
    assert body["stops"][2]["scheduled_arrival_at"] == "2026-10-13T06:00:00+05:30"
    assert body["selected_segment"]["duration_minutes"] == 540


@pytest.mark.parametrize("status", ["cancelled", "restricted"])
def test_operational_status_remains_visible(
    detail_client: tuple[TestClient, Session, UUID],
    status: str,
) -> None:
    client, session, run_id = detail_client
    run = session.get(ServiceRun, run_id)
    assert run is not None
    run.status = status
    run.version = 2
    session.flush()

    response = client.get(f"/api/v1/journeys/{run_id}")

    assert response.status_code == 200
    assert response.json()["run_status"] == status
    assert response.json()["run_version"] == 2


@pytest.mark.parametrize(
    "parameters",
    [
        {"departure_stop_sequence": "1"},
        {"arrival_stop_sequence": "3"},
        {"departure_stop_sequence": "0", "arrival_stop_sequence": "3"},
        {"departure_stop_sequence": "1", "arrival_stop_sequence": "-1"},
        {"departure_stop_sequence": "2", "arrival_stop_sequence": "2"},
        {"departure_stop_sequence": "3", "arrival_stop_sequence": "1"},
        {"departure_stop_sequence": "invalid", "arrival_stop_sequence": "3"},
        {"unexpected_parameter": "value"},
    ],
)
def test_rejects_invalid_segment_query(
    detail_client: tuple[TestClient, Session, UUID],
    parameters: dict[str, str],
) -> None:
    client, _, run_id = detail_client

    response = client.get(f"/api/v1/journeys/{run_id}", params=parameters)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_unknown_run_returns_not_found(
    detail_client: tuple[TestClient, Session, UUID],
) -> None:
    client, _, _ = detail_client

    response = client.get(f"/api/v1/journeys/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_invalid_run_id_returns_validation_error(
    detail_client: tuple[TestClient, Session, UUID],
) -> None:
    client, _, _ = detail_client

    response = client.get("/api/v1/journeys/invalid")

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_unknown_segment_returns_not_found(
    detail_client: tuple[TestClient, Session, UUID],
) -> None:
    client, _, run_id = detail_client

    response = client.get(
        f"/api/v1/journeys/{run_id}",
        params={
            "departure_stop_sequence": 1,
            "arrival_stop_sequence": 99,
        },
    )

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


@pytest.mark.parametrize(
    ("sequence", "permission"),
    [(1, "pickup_allowed"), (3, "dropoff_allowed")],
)
def test_disallowed_segment_returns_not_found(
    detail_client: tuple[TestClient, Session, UUID],
    sequence: int,
    permission: str,
) -> None:
    client, session, run_id = detail_client
    stop = session.scalar(
        select(RunStop).where(
            RunStop.run_id == run_id,
            RunStop.stop_sequence == sequence,
        )
    )
    assert stop is not None
    setattr(stop, permission, False)
    session.flush()

    response = client.get(
        f"/api/v1/journeys/{run_id}",
        params={
            "departure_stop_sequence": 1,
            "arrival_stop_sequence": 3,
        },
    )

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_inactive_service_returns_not_found(
    detail_client: tuple[TestClient, Session, UUID],
) -> None:
    client, session, run_id = detail_client
    run = session.get(ServiceRun, run_id)
    assert run is not None
    service = session.get(TrainService, run.service_id)
    assert service is not None
    service.is_active = False
    session.flush()

    response = client.get(f"/api/v1/journeys/{run_id}")

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_incomplete_schedule_returns_service_unavailable(
    detail_client: tuple[TestClient, Session, UUID],
) -> None:
    client, session, run_id = detail_client
    session.execute(
        delete(RunStop).where(
            RunStop.run_id == run_id,
            RunStop.stop_sequence > 1,
        )
    )
    session.flush()

    response = client.get(f"/api/v1/journeys/{run_id}")

    assert response.status_code == 503
    assert response.json()["code"] == "SERVICE_UNAVAILABLE"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_unconfigured_database_returns_service_unavailable() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            environment="test",
            debug=False,
            database_url=None,
        )
    )

    with TestClient(app) as client:
        response = client.get(f"/api/v1/journeys/{uuid4()}")

    assert response.status_code == 503
    assert response.json()["code"] == "SERVICE_UNAVAILABLE"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
