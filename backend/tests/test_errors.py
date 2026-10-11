from collections.abc import Iterator

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from railconnect.app import create_app
from railconnect.core.config import Settings


@pytest.fixture
def client() -> Iterator[TestClient]:
    settings = Settings(
        _env_file=None,
        app_name="RailConnect Test API",
        environment="test",
        debug=False,
    )
    app = create_app(settings)

    @app.get("/test/number/{value}")
    def read_number(value: int) -> dict[str, int]:
        return {"value": value}

    @app.get("/test/failure")
    def trigger_failure() -> None:
        raise RuntimeError("private-debug-detail")

    @app.get("/test/protected")
    def trigger_authentication_error() -> None:
        raise HTTPException(
            status_code=401,
            detail="private-auth-detail",
            headers={"WWW-Authenticate": "Bearer"},
        )

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.mark.parametrize(
    ("method", "path", "status_code", "code"),
    [
        ("GET", "/missing-route", 404, "NOT_FOUND"),
        ("POST", "/health/live", 405, "METHOD_NOT_ALLOWED"),
    ],
)
def test_http_error_response(
    client: TestClient,
    method: str,
    path: str,
    status_code: int,
    code: str,
) -> None:
    response = client.request(method, path)
    body = response.json()

    assert response.status_code == status_code
    assert body["code"] == code
    assert body["request_id"] == response.headers["X-Request-ID"]

    if status_code == 405:
        assert "GET" in response.headers["Allow"]


def test_validation_error_response(client: TestClient) -> None:
    response = client.get("/test/number/private-input")
    body = response.json()

    assert response.status_code == 422
    assert body["code"] == "VALIDATION_ERROR"
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert "private-input" not in response.text


def test_unexpected_error_response(client: TestClient) -> None:
    response = client.get("/test/failure")
    body = response.json()

    assert response.status_code == 500
    assert body["code"] == "INTERNAL_ERROR"
    assert body["message"] == "An unexpected error occurred."
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert "private-debug-detail" not in response.text
    assert "Traceback" not in response.text


def test_authentication_error_preserves_header(client: TestClient) -> None:
    response = client.get("/test/protected")
    body = response.json()

    assert response.status_code == 401
    assert body["code"] == "UNAUTHENTICATED"
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert "private-auth-detail" not in response.text
