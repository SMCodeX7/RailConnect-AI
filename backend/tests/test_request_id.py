from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from railconnect.app import create_app
from railconnect.core.config import Settings


@pytest.mark.parametrize(
    ("path", "expected_status"),
    [("/health/live", 200), ("/missing-route", 404)],
)
def test_response_has_request_id(path: str, expected_status: int) -> None:
    settings = Settings(_env_file=None, environment="test", debug=False)

    with TestClient(create_app(settings)) as client:
        response = client.get(path)

    assert response.status_code == expected_status
    assert UUID(response.headers["X-Request-ID"]).version == 4


def test_requests_receive_different_ids() -> None:
    settings = Settings(_env_file=None, environment="test", debug=False)

    with TestClient(create_app(settings)) as client:
        first = client.get("/health/live")
        second = client.get("/health/live")

    assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]


def test_client_cannot_choose_server_request_id() -> None:
    settings = Settings(_env_file=None, environment="test", debug=False)
    supplied_id = "11111111-1111-4111-8111-111111111111"

    with TestClient(create_app(settings)) as client:
        response = client.get(
            "/health/live",
            headers={"X-Request-ID": supplied_id},
        )

    assert response.headers["X-Request-ID"] != supplied_id
    assert UUID(response.headers["X-Request-ID"]).version == 4
