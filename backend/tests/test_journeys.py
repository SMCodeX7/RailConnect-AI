from collections.abc import Iterator
from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from railconnect.app import create_app
from railconnect.core.config import Settings
from railconnect.db.dependencies import get_db_session
from railconnect.modules.stations.models import Station
from railconnect.modules.timetable.models.train_service import TrainService
from railconnect.modules.timetable.run_service import materialize_service_run
from railconnect.modules.timetable.seed_schemas import DemoTimetableDataset
from railconnect.modules.timetable.seeding import seed_timetable


@pytest.fixture
def journey_client(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> Iterator[tuple[TestClient, dict[str, str]]]:
    session, dataset = timetable_database
    seed_timetable(session, dataset)

    service_codes = [service.code for service in dataset.services]
    services = session.scalars(
        select(TrainService).where(TrainService.code.in_(service_codes))
    ).all()

    for service in services:
        materialize_service_run(session, service.id, date(2026, 10, 12))

    stops = dataset.services[0].stops
    departure = session.scalar(select(Station).where(Station.code == stops[0].station_code))
    arrival = session.scalar(select(Station).where(Station.code == stops[-1].station_code))
    assert departure is not None
    assert arrival is not None

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

    parameters = {
        "departure_station_id": str(departure.id),
        "arrival_station_id": str(arrival.id),
        "travel_date": "2026-10-12",
    }

    try:
        with TestClient(app) as client:
            yield client, parameters
    finally:
        app.dependency_overrides.clear()


def test_returns_journey_response(
    journey_client: tuple[TestClient, dict[str, str]],
) -> None:
    client, parameters = journey_client

    response = client.get("/api/v1/journeys", params=parameters)

    assert response.status_code == 200
    body = response.json()
    assert body["data_kind"] == "demonstration"
    assert body["timezone"] == "Asia/Colombo"
    assert body["travel_date"] == parameters["travel_date"]
    assert body["total"] == 1
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert len(body["items"]) == 1

    journey = body["items"][0]
    assert journey["run_id"]
    assert journey["service_date"] == "2026-10-12"
    assert journey["run_version"] == 1
    assert journey["run_status"] == "scheduled"
    assert journey["departure_stop_sequence"] == 1
    assert journey["arrival_stop_sequence"] == 3
    assert journey["service_code"].endswith("_OUT")
    assert journey["source_ref"] == "timetable-test"
    assert journey["departure_station"]["id"] == parameters["departure_station_id"]
    assert journey["arrival_station"]["id"] == parameters["arrival_station_id"]
    assert journey["departure_at"] == "2026-10-12T10:00:00+05:30"
    assert journey["arrival_at"] == "2026-10-12T12:00:00+05:30"
    assert journey["duration_minutes"] == 120
    assert response.headers["X-Request-ID"]


def test_pagination_preserves_total(
    journey_client: tuple[TestClient, dict[str, str]],
) -> None:
    client, parameters = journey_client

    response = client.get(
        "/api/v1/journeys",
        params={**parameters, "limit": "1", "offset": "1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"] == []
    assert body["limit"] == 1
    assert body["offset"] == 1


def test_reverse_selection_returns_reverse_service(
    journey_client: tuple[TestClient, dict[str, str]],
) -> None:
    client, parameters = journey_client
    reverse_parameters = {
        **parameters,
        "departure_station_id": parameters["arrival_station_id"],
        "arrival_station_id": parameters["departure_station_id"],
    }

    response = client.get("/api/v1/journeys", params=reverse_parameters)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["service_code"].endswith("_RETURN")


def test_valid_search_without_services_returns_empty_list(
    journey_client: tuple[TestClient, dict[str, str]],
) -> None:
    client, parameters = journey_client

    response = client.get(
        "/api/v1/journeys",
        params={**parameters, "travel_date": "2025-12-31"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["items"] == []


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("departure_station_id", "invalid"),
        ("arrival_station_id", "invalid"),
        ("travel_date", "invalid"),
        ("travel_date", "2026-02-30"),
        ("limit", "0"),
        ("limit", "101"),
        ("offset", "-1"),
        ("offset", "invalid"),
        ("unexpected_parameter", "value"),
    ],
)
def test_rejects_invalid_query_values(
    journey_client: tuple[TestClient, dict[str, str]],
    key: str,
    value: str,
) -> None:
    client, parameters = journey_client

    response = client.get(
        "/api/v1/journeys",
        params={**parameters, key: value},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.parametrize(
    "missing_key",
    ["departure_station_id", "arrival_station_id", "travel_date"],
)
def test_rejects_missing_required_query(
    journey_client: tuple[TestClient, dict[str, str]],
    missing_key: str,
) -> None:
    client, parameters = journey_client
    incomplete_parameters = {key: value for key, value in parameters.items() if key != missing_key}

    response = client.get("/api/v1/journeys", params=incomplete_parameters)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_rejects_identical_stations(
    journey_client: tuple[TestClient, dict[str, str]],
) -> None:
    client, parameters = journey_client

    response = client.get(
        "/api/v1/journeys",
        params={
            **parameters,
            "arrival_station_id": parameters["departure_station_id"],
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_unknown_station_returns_not_found(
    journey_client: tuple[TestClient, dict[str, str]],
) -> None:
    client, parameters = journey_client

    response = client.get(
        "/api/v1/journeys",
        params={**parameters, "departure_station_id": str(uuid4())},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
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
        response = client.get(
            "/api/v1/journeys",
            params={
                "departure_station_id": str(uuid4()),
                "arrival_station_id": str(uuid4()),
                "travel_date": "2026-10-12",
            },
        )

    assert response.status_code == 503
    assert response.json()["code"] == "SERVICE_UNAVAILABLE"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.parametrize(
    ("deadline", "expected_total"),
    [
        ("11:59", 0),
        ("12:00", 1),
        ("12:01", 1),
    ],
)
def test_arrival_deadline_is_inclusive(
    journey_client: tuple[TestClient, dict[str, str]],
    deadline: str,
    expected_total: int,
) -> None:
    client, parameters = journey_client

    response = client.get(
        "/api/v1/journeys",
        params={**parameters, "arrive_before": deadline},
    )

    assert response.status_code == 200
    assert response.json()["total"] == expected_total


def test_explicit_arrival_date_is_used(
    journey_client: tuple[TestClient, dict[str, str]],
) -> None:
    client, parameters = journey_client

    response = client.get(
        "/api/v1/journeys",
        params={
            **parameters,
            "arrive_before": "06:00",
            "arrival_date": "2026-10-13",
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_deadline_filter_precedes_pagination(
    journey_client: tuple[TestClient, dict[str, str]],
) -> None:
    client, parameters = journey_client

    response = client.get(
        "/api/v1/journeys",
        params={
            **parameters,
            "arrive_before": "11:59",
            "offset": "1",
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["items"] == []


@pytest.mark.parametrize(
    "extra_parameters",
    [
        {"arrive_before": "invalid"},
        {"arrive_before": "25:00"},
        {"arrive_before": "12:00:00+05:30"},
        {"arrival_date": "2026-10-13"},
        {"arrive_before": "12:00", "arrival_date": "invalid"},
        {"arrive_before": "12:00", "arrival_date": "2026-10-11"},
    ],
)
def test_rejects_invalid_arrival_deadline(
    journey_client: tuple[TestClient, dict[str, str]],
    extra_parameters: dict[str, str],
) -> None:
    client, parameters = journey_client

    response = client.get(
        "/api/v1/journeys",
        params={**parameters, **extra_parameters},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
