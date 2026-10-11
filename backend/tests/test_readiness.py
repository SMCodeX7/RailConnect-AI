from collections.abc import Iterator
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from railconnect.app import create_app
from railconnect.core.config import Settings
from railconnect.db.dependencies import get_db_session


@pytest.fixture
def database_session() -> Mock:
    session = Mock(spec=Session)
    session.scalar.return_value = None
    return session


@pytest.fixture
def client(database_session: Mock) -> Iterator[TestClient]:
    app = create_app(
        Settings(
            _env_file=None,
            environment="test",
            debug=False,
            database_url=None,
        )
    )

    def override_session() -> Iterator[Session]:
        yield database_session

    app.dependency_overrides[get_db_session] = override_session

    with TestClient(app) as test_client:
        yield test_client


def test_readiness_accepts_an_empty_table(
    client: TestClient,
    database_session: Mock,
) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    database_session.scalar.assert_called_once()


@pytest.mark.parametrize("error_type", [OperationalError, ProgrammingError])
def test_database_failure_returns_service_unavailable(
    client: TestClient,
    database_session: Mock,
    error_type: type[OperationalError] | type[ProgrammingError],
) -> None:
    database_session.scalar.side_effect = error_type(
        "SELECT sensitive_database_details",
        {},
        RuntimeError("private database error"),
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["code"] == "SERVICE_UNAVAILABLE"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert "sensitive_database_details" not in response.text
    assert "private database error" not in response.text


def test_readiness_without_database_configuration() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            environment="test",
            debug=False,
            database_url=None,
        )
    )

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["code"] == "SERVICE_UNAVAILABLE"
