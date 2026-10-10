from fastapi.testclient import TestClient

from railconnect.app import create_app


def test_liveness_returns_ok() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
