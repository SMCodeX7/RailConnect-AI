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
from railconnect.modules.identity.permissions import (
    ROLE_PERMISSIONS,
    Permission,
    RoleCode,
)
from railconnect.modules.identity.provisioning_schemas import ProvisionStaffInput
from railconnect.modules.identity.provisioning_service import provision_staff_user
from railconnect.modules.incidents.dependencies import get_report_session
from railconnect.modules.incidents.models.incident_report import IncidentReport

PASSWORD = "Fictional report queue test passphrase"
ORIGIN = "http://127.0.0.1:5173"
NOW = datetime(2026, 10, 18, 6, 0, tzinfo=UTC)


@dataclass
class QueueContext:
    client: TestClient
    database: Session
    user: User
    clock_value: list[datetime]
    pending_ids: list[UUID]
    reviewed_ids: list[UUID]
    expected_total: int


@pytest.fixture(scope="module")
def queue_password_hash() -> str:
    return hash_password(PASSWORD)


@pytest.fixture
def queue_context(
    identity_database: Session,
    queue_password_hash: str,
) -> Iterator[QueueContext]:
    database = identity_database

    user = provision_staff_user(
        database,
        ProvisionStaffInput(
            username=f"queue_{uuid4().hex}",
            display_name="Synthetic Queue Controller",
            role=RoleCode.CONTROLLER,
        ),
        queue_password_hash,
    )

    baseline = database.scalar(
        select(func.count()).select_from(IncidentReport).where(IncidentReport.status == "pending")
    )
    assert baseline is not None

    pending_ids: list[UUID] = []
    reviewed_ids: list[UUID] = []

    for index, status in enumerate(["pending", "pending", "pending", "verified", "rejected"]):
        submitted_at = NOW - timedelta(minutes=10 - index)
        report = IncidentReport(
            title=f"Queue fixture {uuid4().hex}",
            narrative="Unverified synthetic passenger narrative.",
            observed_at=submitted_at,
            submitted_at=submitted_at,
            status=status,
            version=1 if status == "pending" else 2,
            reviewed_by_id=None if status == "pending" else user.id,
            reviewed_at=None if status == "pending" else NOW,
            review_reason=None if status == "pending" else "Synthetic decision.",
        )
        database.add(report)
        database.flush()

        if status == "pending":
            pending_ids.append(report.id)
        else:
            reviewed_ids.append(report.id)

    settings = Settings(
        _env_file=None,
        environment="test",
        database_url=None,
        session_cookie_secure=False,
        trusted_origins=[ORIGIN],
    )
    clock_value = [NOW]
    app = create_app(settings)

    def override_session() -> Iterator[Session]:
        with Session(
            bind=database.get_bind(),
            join_transaction_mode="create_savepoint",
        ) as session:
            yield session

    app.dependency_overrides[get_identity_session] = override_session
    app.dependency_overrides[get_report_session] = override_session
    app.dependency_overrides[get_identity_clock] = lambda: lambda: clock_value[0]

    try:
        with TestClient(app, base_url="https://testserver") as client:
            yield QueueContext(
                client=client,
                database=database,
                user=user,
                clock_value=clock_value,
                pending_ids=pending_ids,
                reviewed_ids=reviewed_ids,
                expected_total=baseline + 3,
            )
    finally:
        app.dependency_overrides.clear()


def sign_in(context: QueueContext) -> None:
    response = context.client.post(
        "/api/v1/auth/login",
        json={"username": context.user.username, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200


def test_queue_requires_authentication(queue_context: QueueContext) -> None:
    response = queue_context.client.get("/api/v1/staff/reports")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


def test_queue_returns_explicit_staff_fields(queue_context: QueueContext) -> None:
    sign_in(queue_context)

    response = queue_context.client.get("/api/v1/staff/reports?limit=1")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    body = response.json()
    assert set(body) == {"items", "total", "limit", "offset"}
    assert body["total"] == queue_context.expected_total
    assert len(body["items"]) == 1

    assert set(body["items"][0]) == {
        "report_id",
        "title",
        "narrative",
        "observed_at",
        "submitted_at",
        "run_hint_id",
        "station_hint_id",
        "departure_stop_sequence_hint",
        "arrival_stop_sequence_hint",
        "status",
        "version",
    }


def test_queue_returns_only_pending_reports(queue_context: QueueContext) -> None:
    context = queue_context
    sign_in(context)
    seen_ids: set[UUID] = set()

    for offset in range(0, context.expected_total, 100):
        response = context.client.get(
            "/api/v1/staff/reports",
            params={"limit": 100, "offset": offset},
        )
        assert response.status_code == 200

        for item in response.json()["items"]:
            assert item["status"] == "pending"
            seen_ids.add(UUID(item["report_id"]))

    assert set(context.pending_ids).issubset(seen_ids)
    assert set(context.reviewed_ids).isdisjoint(seen_ids)


def test_queue_orders_oldest_submissions_first(queue_context: QueueContext) -> None:
    context = queue_context
    sign_in(context)
    ordering: list[tuple[datetime, UUID]] = []

    for offset in range(0, context.expected_total, 100):
        response = context.client.get(
            "/api/v1/staff/reports",
            params={"limit": 100, "offset": offset},
        )
        assert response.status_code == 200

        ordering.extend(
            (
                datetime.fromisoformat(item["submitted_at"].replace("Z", "+00:00")),
                UUID(item["report_id"]),
            )
            for item in response.json()["items"]
        )

    assert ordering == sorted(ordering)


def test_queue_pages_do_not_overlap(queue_context: QueueContext) -> None:
    sign_in(queue_context)

    first = queue_context.client.get(
        "/api/v1/staff/reports",
        params={"limit": 2, "offset": 0},
    )
    second = queue_context.client.get(
        "/api/v1/staff/reports",
        params={"limit": 2, "offset": 2},
    )

    assert first.status_code == second.status_code == 200
    first_body = first.json()
    second_body = second.json()

    assert len(first_body["items"]) == 2
    assert len(second_body["items"]) >= 1
    assert first_body["total"] == second_body["total"]

    first_ids = {item["report_id"] for item in first_body["items"]}
    second_ids = {item["report_id"] for item in second_body["items"]}
    assert first_ids.isdisjoint(second_ids)


def test_offset_after_last_report_returns_empty_page(
    queue_context: QueueContext,
) -> None:
    sign_in(queue_context)

    response = queue_context.client.get(
        "/api/v1/staff/reports",
        params={"limit": 20, "offset": queue_context.expected_total},
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == queue_context.expected_total


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=101",
        "offset=-1",
        "unexpected=value",
    ],
)
def test_queue_rejects_invalid_query(
    queue_context: QueueContext,
    query: str,
) -> None:
    sign_in(queue_context)

    response = queue_context.client.get(f"/api/v1/staff/reports?{query}")

    assert response.status_code == 422


def test_authenticated_actor_without_read_permission_is_denied(
    queue_context: QueueContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sign_in(queue_context)

    monkeypatch.setitem(
        ROLE_PERMISSIONS,
        RoleCode.CONTROLLER,
        frozenset({Permission.INCIDENTS_EDIT}),
    )

    response = queue_context.client.get("/api/v1/staff/reports")

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_disabled_staff_cannot_read_queue(queue_context: QueueContext) -> None:
    sign_in(queue_context)
    queue_context.user.is_active = False
    queue_context.database.flush()

    response = queue_context.client.get("/api/v1/staff/reports")

    assert response.status_code == 401


def test_expired_session_cannot_read_queue(queue_context: QueueContext) -> None:
    sign_in(queue_context)
    queue_context.clock_value[0] = NOW + timedelta(minutes=31)

    response = queue_context.client.get("/api/v1/staff/reports")

    assert response.status_code == 401


def test_reading_queue_does_not_change_report_state(
    queue_context: QueueContext,
) -> None:
    context = queue_context
    sign_in(context)

    response = context.client.get("/api/v1/staff/reports")

    assert response.status_code == 200

    for report_id in context.pending_ids:
        context.database.expire_all()
        report = context.database.get(IncidentReport, report_id)

        assert report is not None
        assert report.status == "pending"
        assert report.version == 1
        assert report.reviewed_by_id is None
        assert report.reviewed_at is None
        assert report.review_reason is None
