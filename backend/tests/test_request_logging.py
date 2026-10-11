import json
import logging
from collections.abc import Iterator
from datetime import datetime
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from railconnect.app import create_app
from railconnect.core.config import Settings
from railconnect.core.logging import JsonFormatter, configure_logging


@pytest.fixture
def request_logs(
    caplog: pytest.LogCaptureFixture,
) -> Iterator[pytest.LogCaptureFixture]:
    logger = logging.getLogger("railconnect")
    logger.addHandler(caplog.handler)

    try:
        yield caplog
    finally:
        logger.removeHandler(caplog.handler)


@pytest.fixture
def app() -> FastAPI:
    return create_app(
        Settings(
            _env_file=None,
            environment="test",
            debug=False,
            database_url=None,
        )
    )


def get_request_log(caplog: pytest.LogCaptureFixture) -> dict[str, object]:
    records = [record for record in caplog.records if record.name == "railconnect.requests"]
    assert len(records) == 1

    return cast(
        dict[str, object],
        json.loads(JsonFormatter().format(records[0])),
    )


@pytest.mark.parametrize(
    ("path", "expected_status", "expected_level"),
    [
        ("/health/live", 200, "INFO"),
        ("/missing", 404, "WARNING"),
        ("/health/ready", 503, "ERROR"),
    ],
)
def test_request_log_matches_response(
    app: FastAPI,
    request_logs: pytest.LogCaptureFixture,
    path: str,
    expected_status: int,
    expected_level: str,
) -> None:
    with TestClient(app) as client:
        response = client.get(path)

    payload = get_request_log(request_logs)

    assert response.status_code == expected_status
    assert payload["status_code"] == expected_status
    assert payload["level"] == expected_level
    assert payload["event"] == "http_request"
    assert payload["method"] == "GET"
    assert payload["request_id"] == response.headers["X-Request-ID"]

    duration = payload["duration_ms"]
    assert isinstance(duration, (int, float))
    assert duration >= 0

    timestamp = payload["timestamp"]
    assert isinstance(timestamp, str)
    assert datetime.fromisoformat(timestamp).tzinfo is not None


def test_unexpected_failure_is_logged(
    app: FastAPI,
    request_logs: pytest.LogCaptureFixture,
) -> None:
    @app.get("/test/failure")
    def fail() -> None:
        raise RuntimeError("private_database_password")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test/failure")

    payload = get_request_log(request_logs)

    assert response.status_code == 500
    assert payload["status_code"] == 500
    assert payload["level"] == "ERROR"
    assert payload["event"] == "http_request_failed"
    assert payload["request_id"] == response.headers["X-Request-ID"]
    assert "private_database_password" not in json.dumps(payload)


def test_log_uses_route_template_and_omits_request_values(
    app: FastAPI,
    request_logs: pytest.LogCaptureFixture,
) -> None:
    @app.post("/test/resources/{resource_id}")
    def resource(resource_id: str) -> dict[str, str]:
        return {"status": "ok"}

    with TestClient(app) as client:
        response = client.post(
            "/test/resources/private-path-value",
            params={"token": "private-query-value"},
            headers={"Authorization": "Bearer private-header-value"},
            json={"password": "private-body-value"},
        )

    payload = get_request_log(request_logs)
    serialized = json.dumps(payload)

    assert response.status_code == 200
    assert payload["route"] == "/test/resources/{resource_id}"
    assert payload["method"] == "POST"

    for value in (
        "private-path-value",
        "private-query-value",
        "private-header-value",
        "private-body-value",
    ):
        assert value not in serialized


def test_logging_configuration_does_not_duplicate_handlers() -> None:
    configure_logging()
    configure_logging()

    handlers = [
        handler
        for handler in logging.getLogger("railconnect").handlers
        if handler.name == "railconnect-json"
    ]

    assert len(handlers) == 1
