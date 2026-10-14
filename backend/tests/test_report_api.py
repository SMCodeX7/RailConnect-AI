from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from railconnect.app import create_app
from railconnect.core.config import Settings
from railconnect.modules.identity.dependencies import (
    get_identity_clock,
    get_identity_session,
)
from railconnect.modules.identity.models.user import User
from railconnect.modules.identity.passwords import hash_password
from railconnect.modules.identity.permissions import RoleCode
from railconnect.modules.identity.provisioning_schemas import ProvisionStaffInput
from railconnect.modules.identity.provisioning_service import provision_staff_user
from railconnect.modules.incidents.dependencies import get_report_session
from railconnect.modules.incidents.models.incident_report import IncidentReport

PASSWORD = "Fictional report API test passphrase"
ORIGIN = "http://127.0.0.1:5173"
NOW = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


@dataclass
class ReportAPIContext:
    client: TestClient
    database: Session
    user: User
    settings: Settings
    clock_value: list[datetime]


@pytest.fixture(scope="module")
def report_api_password_hash() -> str:
    return hash_password(PASSWORD)


@pytest.fixture
def report_api_context(
    identity_database: Session,
    report_api_password_hash: str,
) -> Iterator[ReportAPIContext]:
    user = provision_staff_user(
        identity_database,
        ProvisionStaffInput(
            username=f"report_{uuid4().hex}",
            display_name="Fictional Report Staff",
            role=RoleCode.CONTROLLER,
        ),
        report_api_password_hash,
    )

    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=None,
        session_cookie_secure=False,
        trusted_origins=[ORIGIN],
        report_rate_window_seconds=60,
        report_client_max_attempts=2,
    )
    clock_value = [NOW]
    app = create_app(settings)

    def override_session() -> Iterator[Session]:
        with Session(
            bind=identity_database.get_bind(),
            join_transaction_mode="create_savepoint",
        ) as session:
            yield session

    app.dependency_overrides[get_identity_session] = override_session
    app.dependency_overrides[get_report_session] = override_session
    app.dependency_overrides[get_identity_clock] = lambda: lambda: clock_value[0]

    try:
        with TestClient(app, base_url="https://testserver") as client:
            yield ReportAPIContext(
                client=client,
                database=identity_database,
                user=user,
                settings=settings,
                clock_value=clock_value,
            )
    finally:
        app.dependency_overrides.clear()


def report_payload(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": f"Report API test {uuid4().hex}",
        "narrative": "Synthetic passenger claim, not verified operational evidence.",
        "observed_at": (NOW - timedelta(minutes=5)).isoformat(),
    }
    payload.update(changes)
    return payload


def sign_in(context: ReportAPIContext) -> str:
    response = context.client.post(
        "/api/v1/auth/login",
        json={"username": context.user.username, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200

    csrf_token = response.json()["csrf_token"]
    assert isinstance(csrf_token, str)
    return csrf_token


def reports_with_title(context: ReportAPIContext, title: object) -> int:
    count = context.database.scalar(
        select(func.count()).select_from(IncidentReport).where(IncidentReport.title == title)
    )
    assert count is not None
    return count


def test_anonymous_submission_returns_safe_pending_receipt(
    report_api_context: ReportAPIContext,
) -> None:
    context = report_api_context
    payload = report_payload()

    response = context.client.post(
        "/api/v1/reports",
        json=payload,
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"report_id", "status", "submitted_at", "message"}
    assert body["status"] == "pending"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Request-ID"]

    report = context.database.get(IncidentReport, UUID(body["report_id"]))
    assert report is not None
    assert report.status == "pending"
    assert report.version == 1
    assert report.submitted_by_user_id is None
    assert report.reviewed_by_id is None
    assert report.review_reason is None
    assert reports_with_title(context, payload["title"]) == 1


def test_authenticated_submission_records_server_actor(
    report_api_context: ReportAPIContext,
) -> None:
    context = report_api_context
    csrf_token = sign_in(context)

    response = context.client.post(
        "/api/v1/reports",
        json=report_payload(),
        headers={
            "Origin": ORIGIN,
            "X-CSRF-Token": csrf_token,
        },
    )

    assert response.status_code == 201
    report = context.database.get(
        IncidentReport,
        UUID(response.json()["report_id"]),
    )
    assert report is not None
    assert report.submitted_by_user_id == context.user.id
    assert report.status == "pending"


@pytest.mark.parametrize("csrf_token", [None, "invalid"])
def test_staff_cookie_requires_valid_csrf(
    report_api_context: ReportAPIContext,
    csrf_token: str | None,
) -> None:
    context = report_api_context
    sign_in(context)
    payload = report_payload()
    headers = {"Origin": ORIGIN}

    if csrf_token is not None:
        headers["X-CSRF-Token"] = csrf_token

    response = context.client.post(
        "/api/v1/reports",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
    assert reports_with_title(context, payload["title"]) == 0


@pytest.mark.parametrize(
    "origin",
    [None, "null", "https://untrusted.example"],
)
def test_rejects_missing_or_untrusted_origin(
    report_api_context: ReportAPIContext,
    origin: str | None,
) -> None:
    context = report_api_context
    payload = report_payload()
    headers = {"Origin": origin} if origin is not None else {}

    response = context.client.post(
        "/api/v1/reports",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 403
    assert reports_with_title(context, payload["title"]) == 0


def test_submission_requires_json(
    report_api_context: ReportAPIContext,
) -> None:
    response = report_api_context.client.post(
        "/api/v1/reports",
        content="title=fictional&narrative=fictional",
        headers={
            "Origin": ORIGIN,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    assert response.status_code == 415
    assert response.json()["code"] == "UNSUPPORTED_MEDIA_TYPE"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "verified"),
        ("reviewed_by_id", str(uuid4())),
        ("estimated_delay_minutes", 45),
    ],
)
def test_rejects_passenger_supplied_approval_fields(
    report_api_context: ReportAPIContext,
    field: str,
    value: object,
) -> None:
    context = report_api_context
    payload = report_payload(**{field: value})

    response = context.client.post(
        "/api/v1/reports",
        json=payload,
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert reports_with_title(context, payload["title"]) == 0


def test_rejects_future_observation(
    report_api_context: ReportAPIContext,
) -> None:
    context = report_api_context
    payload = report_payload(observed_at=(NOW + timedelta(seconds=1)).isoformat())

    response = context.client.post(
        "/api/v1/reports",
        json=payload,
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 422
    assert response.headers["Cache-Control"] == "no-store"
    assert reports_with_title(context, payload["title"]) == 0


def test_rejects_unknown_run_hint(
    report_api_context: ReportAPIContext,
) -> None:
    context = report_api_context
    payload = report_payload(run_hint_id=str(uuid4()))

    response = context.client.post(
        "/api/v1/reports",
        json=payload,
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 422
    assert reports_with_title(context, payload["title"]) == 0


def test_rate_limit_returns_retry_after_and_creates_no_extra_report(
    report_api_context: ReportAPIContext,
) -> None:
    context = report_api_context
    payload = report_payload()

    for _ in range(2):
        response = context.client.post(
            "/api/v1/reports",
            json=payload,
            headers={"Origin": ORIGIN},
        )
        assert response.status_code == 201

    blocked = context.client.post(
        "/api/v1/reports",
        json=payload,
        headers={"Origin": ORIGIN},
    )

    assert blocked.status_code == 429
    assert blocked.json()["code"] == "RATE_LIMITED"
    assert blocked.headers["Retry-After"] == "60"
    assert blocked.headers["Cache-Control"] == "no-store"
    assert blocked.json()["request_id"] == blocked.headers["X-Request-ID"]
    assert reports_with_title(context, payload["title"]) == 2


def test_invalid_staff_cookie_does_not_fall_back_to_anonymous(
    report_api_context: ReportAPIContext,
) -> None:
    context = report_api_context
    payload = report_payload()
    context.client.cookies.set(
        context.settings.session_cookie_name,
        "invalid-session-token",
    )

    response = context.client.post(
        "/api/v1/reports",
        json=payload,
        headers={
            "Origin": ORIGIN,
            "X-CSRF-Token": "f" * 64,
        },
    )

    assert response.status_code == 401
    assert reports_with_title(context, payload["title"]) == 0


def test_expired_staff_session_cannot_submit(
    report_api_context: ReportAPIContext,
) -> None:
    context = report_api_context
    csrf_token = sign_in(context)
    context.clock_value[0] = NOW + timedelta(minutes=31)
    payload = report_payload()

    response = context.client.post(
        "/api/v1/reports",
        json=payload,
        headers={
            "Origin": ORIGIN,
            "X-CSRF-Token": csrf_token,
        },
    )

    assert response.status_code == 401
    assert reports_with_title(context, payload["title"]) == 0


def test_missing_database_returns_service_unavailable() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            environment="test",
            database_url=None,
            session_cookie_secure=False,
            trusted_origins=[ORIGIN],
        )
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/reports",
            json=report_payload(),
            headers={"Origin": ORIGIN},
        )

    assert response.status_code == 503
    assert response.json()["code"] == "SERVICE_UNAVAILABLE"
