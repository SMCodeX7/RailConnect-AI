from collections.abc import Iterator
from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from railconnect.app import create_app
from railconnect.core.config import Settings
from railconnect.db.dependencies import get_db_session
from railconnect.modules.stations import routes
from railconnect.modules.stations.schemas import (
    StationListResponse,
    StationResponse,
)


@pytest.fixture
def station_response() -> StationResponse:
    return StationResponse(
        id=UUID("02eb7cbc-e6b1-5f00-849f-da81724d34cf"),
        code="DEMO_JAFFNA",
        name="Jaffna",
        source_ref="demo-stations-v1",
        is_active=True,
    )


@pytest.fixture
def station_service(
    monkeypatch: pytest.MonkeyPatch,
    station_response: StationResponse,
) -> Mock:
    service = Mock(
        return_value=StationListResponse(
            items=[station_response],
            total=1,
            limit=50,
            offset=0,
        )
    )
    monkeypatch.setattr(routes, "search_stations", service)
    return service


@pytest.fixture
def client(station_service: Mock) -> Iterator[TestClient]:
    app = create_app(
        Settings(
            _env_file=None,
            environment="test",
            debug=False,
            database_url=None,
        )
    )

    def override_session() -> Iterator[Session]:
        with Session() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session

    with TestClient(app) as test_client:
        yield test_client


def test_station_response(
    client: TestClient,
    station_response: StationResponse,
    station_service: Mock,
) -> None:
    response = client.get("/api/v1/stations")

    assert response.status_code == 200
    assert response.json() == {
        "items": [station_response.model_dump(mode="json")],
        "total": 1,
        "limit": 50,
        "offset": 0,
    }
    assert response.headers["X-Request-ID"]
    station_service.assert_called_once()
    session, search, limit, offset = station_service.call_args.args
    assert isinstance(session, Session)
    assert search is None
    assert limit == 50
    assert offset == 0


def test_search_and_pagination(
    client: TestClient,
    station_service: Mock,
) -> None:
    station_service.return_value = StationListResponse(
        items=[],
        total=1,
        limit=5,
        offset=5,
    )

    response = client.get(
        "/api/v1/stations",
        params={"q": "jaffna", "limit": 5, "offset": 5},
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 1,
        "limit": 5,
        "offset": 5,
    }
    station_service.assert_called_once()
    assert station_service.call_args.args[1:] == ("jaffna", 5, 5)


@pytest.mark.parametrize(
    "params",
    [
        {"limit": "0"},
        {"limit": "101"},
        {"limit": "invalid"},
        {"offset": "-1"},
        {"q": ""},
        {"q": "   "},
        {"q": "a" * 121},
    ],
)
def test_invalid_query_parameters(
    client: TestClient,
    station_service: Mock,
    params: dict[str, str],
) -> None:
    response = client.get("/api/v1/stations", params=params)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    station_service.assert_not_called()


def test_missing_database_returns_service_unavailable() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            environment="test",
            debug=False,
            database_url=None,
        )
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/stations")

    assert response.status_code == 503
    assert response.json()["code"] == "SERVICE_UNAVAILABLE"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
