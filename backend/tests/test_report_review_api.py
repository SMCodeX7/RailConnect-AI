from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, event, func, select
from sqlalchemy.orm import Session

from railconnect.app import create_app
from railconnect.core.config import Settings
from railconnect.modules.identity.dependencies import (
    get_identity_clock,
    get_identity_session,
)
from railconnect.modules.identity.errors import PermissionDeniedError
from railconnect.modules.identity.models.user import User
from railconnect.modules.identity.models.user_role import UserRole
from railconnect.modules.identity.passwords import hash_password
from railconnect.modules.identity.permissions import (
    ROLE_PERMISSIONS,
    Permission,
    RoleCode,
)
from railconnect.modules.identity.provisioning_schemas import ProvisionStaffInput
from railconnect.modules.identity.provisioning_service import provision_staff_user
from railconnect.modules.identity.session_service import (
    AuthenticatedSession,
    authenticate_staff_session,
)
from railconnect.modules.incidents.dependencies import get_report_session
from railconnect.modules.incidents.models.incident import Incident
from railconnect.modules.incidents.models.incident_audit_event import IncidentAuditEvent
from railconnect.modules.incidents.models.incident_report import IncidentReport
from railconnect.modules.incidents.models.incident_revision import IncidentRevision
from railconnect.modules.incidents.review_decision_service import reject_report
from railconnect.modules.incidents.review_schemas import RejectReportInput
from railconnect.modules.stations.models import Station
from railconnect.modules.timetable.models.run_stop import RunStop
from railconnect.modules.timetable.models.service_run import ServiceRun
from railconnect.modules.timetable.models.train_service import TrainService

PASSWORD = "Fictional review API test passphrase"
ORIGIN = "http://127.0.0.1:5173"
NOW = datetime(2026, 10, 18, 6, 0, tzinfo=UTC)


@dataclass
class ReviewContext:
    client: TestClient
    database: Session
    user: User
    report_id: UUID
    run_id: UUID


@pytest.fixture(scope="module")
def review_password_hash() -> str:
    return hash_password(PASSWORD)


@pytest.fixture
def review_context(
    identity_database: Session,
    review_password_hash: str,
) -> Iterator[ReviewContext]:
    database = identity_database
    suffix = uuid4().hex

    user = provision_staff_user(
        database,
        ProvisionStaffInput(
            username=f"review_{suffix}",
            display_name="Synthetic Review Controller",
            role=RoleCode.CONTROLLER,
        ),
        review_password_hash,
    )

    stations = [
        Station(
            code=f"DEMO_{suffix[:10].upper()}{index}",
            name=f"Synthetic Review Station {index}",
            source_ref="review-api-test",
            is_active=True,
        )
        for index in (1, 2)
    ]
    service = TrainService(
        code=f"DEMO_{suffix.upper()}",
        name="Synthetic Review Service",
        source_ref="review-api-test",
        operating_days=127,
        valid_from=NOW.date(),
        valid_until=NOW.date() + timedelta(days=7),
        is_active=True,
    )
    database.add_all([service, *stations])
    database.flush()

    run = ServiceRun(
        service_id=service.id,
        service_date=NOW.date(),
        source_ref="review-api-test",
        status="scheduled",
        version=1,
    )
    database.add(run)
    database.flush()

    database.add_all(
        [
            RunStop(
                run_id=run.id,
                station_id=stations[0].id,
                stop_sequence=1,
                scheduled_departure_at=NOW + timedelta(hours=1),
                pickup_allowed=True,
                dropoff_allowed=False,
            ),
            RunStop(
                run_id=run.id,
                station_id=stations[1].id,
                stop_sequence=2,
                scheduled_arrival_at=NOW + timedelta(hours=2),
                pickup_allowed=False,
                dropoff_allowed=True,
            ),
        ]
    )

    report = IncidentReport(
        title="Synthetic review report",
        narrative="An unverified synthetic passenger claim.",
        observed_at=NOW - timedelta(minutes=10),
        submitted_at=NOW - timedelta(minutes=5),
        run_hint_id=run.id,
        status="pending",
        version=1,
    )
    database.add(report)
    database.flush()

    app = create_app(
        Settings(
            _env_file=None,
            environment="test",
            database_url=None,
            session_cookie_secure=False,
            trusted_origins=[ORIGIN],
        )
    )

    def override_session() -> Iterator[Session]:
        with Session(
            bind=database.get_bind(),
            join_transaction_mode="create_savepoint",
        ) as session:
            yield session

    app.dependency_overrides[get_identity_session] = override_session
    app.dependency_overrides[get_report_session] = override_session
    app.dependency_overrides[get_identity_clock] = lambda: lambda: NOW

    try:
        with TestClient(
            app,
            base_url="https://testserver",
            raise_server_exceptions=False,
        ) as client:
            yield ReviewContext(
                client=client,
                database=database,
                user=user,
                report_id=report.id,
                run_id=run.id,
            )
    finally:
        app.dependency_overrides.clear()


def sign_in(context: ReviewContext) -> dict[str, str]:
    response = context.client.post(
        "/api/v1/auth/login",
        json={"username": context.user.username, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200

    return {
        "Origin": ORIGIN,
        "X-CSRF-Token": response.json()["csrf_token"],
    }


def verify_payload(context: ReviewContext) -> dict[str, object]:
    return {
        "expected_version": 1,
        "reason": "Reviewed synthetic evidence.",
        "approved": {
            "run_id": str(context.run_id),
            "scope_kind": "segment",
            "departure_stop_sequence": 1,
            "arrival_stop_sequence": 2,
            "impact_kind": "delay",
            "estimated_delay_minutes": 15,
            "effective_from": NOW.isoformat(),
            "effective_until": (NOW + timedelta(hours=4)).isoformat(),
            "public_summary": "Synthetic demonstration delay.",
            "evidence_basis": "Controlled test scenario.",
        },
    }


def report_record(context: ReviewContext) -> IncidentReport:
    context.database.expire_all()
    report = context.database.get(IncidentReport, context.report_id)
    assert report is not None
    return report


def assert_no_operational_records(context: ReviewContext) -> None:
    incident = context.database.scalar(
        select(Incident).where(Incident.originating_report_id == context.report_id)
    )
    audits = context.database.scalar(
        select(func.count())
        .select_from(IncidentAuditEvent)
        .where(IncidentAuditEvent.report_id == context.report_id)
    )

    assert incident is None
    assert audits == 0


def test_verification_creates_linked_incident_revision_and_audit(
    review_context: ReviewContext,
) -> None:
    context = review_context
    response = context.client.post(
        f"/api/v1/staff/reports/{context.report_id}/verify",
        json=verify_payload(context),
        headers=sign_in(context),
    )

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"

    body = response.json()
    assert body["status"] == "verified"
    assert body["report_version"] == 2
    assert body["incident_version"] == 1

    report = report_record(context)
    assert report.status == "verified"
    assert report.reviewed_by_id == context.user.id
    assert report.reviewed_at == NOW

    incident = context.database.get(Incident, UUID(body["incident_id"]))
    revision = context.database.get(
        IncidentRevision,
        UUID(body["revision_id"]),
    )
    audit = context.database.scalar(
        select(IncidentAuditEvent).where(IncidentAuditEvent.report_id == context.report_id)
    )

    assert incident is not None
    assert incident.originating_report_id == context.report_id
    assert incident.current_revision_number == 1
    assert incident.created_by_id == context.user.id

    assert revision is not None
    assert revision.incident_id == incident.id
    assert revision.run_id == context.run_id
    assert revision.estimated_delay_minutes == 15
    assert revision.verified_by_id == context.user.id

    assert audit is not None
    assert audit.action == "report_verified"
    assert audit.actor_id == context.user.id
    assert audit.incident_id == incident.id
    assert audit.revision_id == revision.id
    assert audit.report_version == 2
    assert audit.incident_version == 1
    assert audit.request_id == response.headers["X-Request-ID"]


def test_rejection_records_decision_and_audit_without_incident(
    review_context: ReviewContext,
) -> None:
    context = review_context
    response = context.client.post(
        f"/api/v1/staff/reports/{context.report_id}/reject",
        json={
            "expected_version": 1,
            "reason": "Insufficient synthetic evidence.",
        },
        headers=sign_in(context),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["report_version"] == 2
    assert body["incident_id"] is None
    assert body["revision_id"] is None

    report = report_record(context)
    assert report.status == "rejected"
    assert report.reviewed_by_id == context.user.id

    assert (
        context.database.scalar(
            select(Incident).where(Incident.originating_report_id == context.report_id)
        )
        is None
    )

    audit = context.database.scalar(
        select(IncidentAuditEvent).where(IncidentAuditEvent.report_id == context.report_id)
    )
    assert audit is not None
    assert audit.action == "report_rejected"
    assert audit.incident_id is None
    assert audit.request_id == response.headers["X-Request-ID"]


def test_stale_expected_version_returns_conflict(
    review_context: ReviewContext,
) -> None:
    context = review_context
    payload = verify_payload(context)
    payload["expected_version"] = 2

    response = context.client.post(
        f"/api/v1/staff/reports/{context.report_id}/verify",
        json=payload,
        headers=sign_in(context),
    )

    assert response.status_code == 409
    assert report_record(context).status == "pending"
    assert_no_operational_records(context)


def test_second_decision_cannot_overwrite_first(
    review_context: ReviewContext,
) -> None:
    context = review_context
    headers = sign_in(context)
    url = f"/api/v1/staff/reports/{context.report_id}"

    first = context.client.post(
        f"{url}/reject",
        json={"expected_version": 1, "reason": "First decision."},
        headers=headers,
    )
    second = context.client.post(
        f"{url}/verify",
        json=verify_payload(context),
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 409

    report = report_record(context)
    assert report.status == "rejected"
    assert report.review_reason == "First decision."

    audit_count = context.database.scalar(
        select(func.count())
        .select_from(IncidentAuditEvent)
        .where(IncidentAuditEvent.report_id == context.report_id)
    )
    assert audit_count == 1


def test_missing_report_returns_not_found(
    review_context: ReviewContext,
) -> None:
    response = review_context.client.post(
        f"/api/v1/staff/reports/{uuid4()}/reject",
        json={"expected_version": 1, "reason": "Synthetic rejection."},
        headers=sign_in(review_context),
    )

    assert response.status_code == 404


def test_unknown_approved_run_rolls_back_review(
    review_context: ReviewContext,
) -> None:
    context = review_context
    payload = verify_payload(context)
    approved = payload["approved"]
    assert isinstance(approved, dict)
    approved["run_id"] = str(uuid4())

    response = context.client.post(
        f"/api/v1/staff/reports/{context.report_id}/verify",
        json=payload,
        headers=sign_in(context),
    )

    assert response.status_code == 422
    assert report_record(context).status == "pending"
    assert_no_operational_records(context)


def test_unknown_approved_endpoint_rolls_back_review(
    review_context: ReviewContext,
) -> None:
    context = review_context
    payload = verify_payload(context)
    approved = payload["approved"]
    assert isinstance(approved, dict)
    approved["arrival_stop_sequence"] = 99

    response = context.client.post(
        f"/api/v1/staff/reports/{context.report_id}/verify",
        json=payload,
        headers=sign_in(context),
    )

    assert response.status_code == 422
    assert report_record(context).status == "pending"
    assert_no_operational_records(context)


def test_identified_staff_cannot_review_own_report(
    review_context: ReviewContext,
) -> None:
    context = review_context
    report = report_record(context)
    report.submitted_by_user_id = context.user.id
    context.database.flush()

    response = context.client.post(
        f"/api/v1/staff/reports/{context.report_id}/reject",
        json={"expected_version": 1, "reason": "Self-review attempt."},
        headers=sign_in(context),
    )

    assert response.status_code == 403
    assert report_record(context).status == "pending"
    assert_no_operational_records(context)


@pytest.mark.parametrize("action", ["verify", "reject"])
def test_review_requires_authentication(
    review_context: ReviewContext,
    action: str,
) -> None:
    context = review_context
    payload = (
        verify_payload(context)
        if action == "verify"
        else {"expected_version": 1, "reason": "Synthetic rejection."}
    )

    response = context.client.post(
        f"/api/v1/staff/reports/{context.report_id}/{action}",
        json=payload,
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 401


@pytest.mark.parametrize("csrf", [None, "invalid"])
def test_review_requires_csrf(
    review_context: ReviewContext,
    csrf: str | None,
) -> None:
    context = review_context
    sign_in(context)
    headers = {"Origin": ORIGIN}

    if csrf is not None:
        headers["X-CSRF-Token"] = csrf

    response = context.client.post(
        f"/api/v1/staff/reports/{context.report_id}/reject",
        json={"expected_version": 1, "reason": "Synthetic rejection."},
        headers=headers,
    )

    assert response.status_code == 403
    assert report_record(context).status == "pending"


def test_review_rejects_untrusted_origin(
    review_context: ReviewContext,
) -> None:
    context = review_context
    headers = sign_in(context)
    headers["Origin"] = "https://untrusted.example"

    response = context.client.post(
        f"/api/v1/staff/reports/{context.report_id}/reject",
        json={"expected_version": 1, "reason": "Synthetic rejection."},
        headers=headers,
    )

    assert response.status_code == 403


def test_review_requires_explicit_permission(
    review_context: ReviewContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = review_context
    headers = sign_in(context)

    monkeypatch.setitem(
        ROLE_PERMISSIONS,
        RoleCode.CONTROLLER,
        frozenset({Permission.REPORTS_READ}),
    )

    response = context.client.post(
        f"/api/v1/staff/reports/{context.report_id}/reject",
        json={"expected_version": 1, "reason": "Synthetic rejection."},
        headers=headers,
    )

    assert response.status_code == 403
    assert report_record(context).status == "pending"


def test_review_rejects_forged_actor_field(
    review_context: ReviewContext,
) -> None:
    context = review_context

    response = context.client.post(
        f"/api/v1/staff/reports/{context.report_id}/reject",
        json={
            "expected_version": 1,
            "reason": "Synthetic rejection.",
            "reviewed_by_id": str(uuid4()),
        },
        headers=sign_in(context),
    )

    assert response.status_code == 422
    assert report_record(context).status == "pending"


def test_audit_failure_rolls_back_entire_verification(
    review_context: ReviewContext,
) -> None:
    context = review_context
    headers = sign_in(context)

    def fail_audit_insert(
        mapper: object,
        connection: object,
        target: IncidentAuditEvent,
    ) -> None:
        raise RuntimeError("Synthetic audit storage failure")

    event.listen(IncidentAuditEvent, "before_insert", fail_audit_insert)

    try:
        response = context.client.post(
            f"/api/v1/staff/reports/{context.report_id}/verify",
            json=verify_payload(context),
            headers=headers,
        )
    finally:
        event.remove(IncidentAuditEvent, "before_insert", fail_audit_insert)

    assert response.status_code == 500

    report = report_record(context)
    assert report.status == "pending"
    assert report.version == 1
    assert report.reviewed_by_id is None
    assert_no_operational_records(context)

    assert context.database.get(ServiceRun, context.run_id) is not None


def authenticated_snapshot(context: ReviewContext) -> AuthenticatedSession:
    sign_in(context)

    token = context.client.cookies.get("railconnect_session")
    assert token is not None

    settings = Settings(
        _env_file=None,
        environment="test",
        session_cookie_secure=False,
        trusted_origins=[ORIGIN],
    )

    with Session(
        bind=context.database.get_bind(),
        join_transaction_mode="create_savepoint",
    ) as session:
        with session.begin():
            return authenticate_staff_session(
                session,
                token,
                settings,
                NOW,
            )


def test_service_rechecks_removed_role_after_authentication(
    review_context: ReviewContext,
) -> None:
    context = review_context
    authenticated = authenticated_snapshot(context)

    context.database.execute(delete(UserRole).where(UserRole.user_id == context.user.id))
    context.database.flush()

    with Session(
        bind=context.database.get_bind(),
        join_transaction_mode="create_savepoint",
    ) as session:
        with pytest.raises(PermissionDeniedError):
            reject_report(
                session,
                authenticated,
                context.report_id,
                RejectReportInput(
                    expected_version=1,
                    reason="Synthetic decision after role removal.",
                ),
                request_id=f"review-test-{uuid4().hex}",
                now=NOW,
            )

    assert report_record(context).status == "pending"
    assert_no_operational_records(context)


def test_service_rechecks_disabled_account_after_authentication(
    review_context: ReviewContext,
) -> None:
    context = review_context
    authenticated = authenticated_snapshot(context)

    context.user.is_active = False
    context.database.flush()

    with Session(
        bind=context.database.get_bind(),
        join_transaction_mode="create_savepoint",
    ) as session:
        with pytest.raises(PermissionDeniedError):
            reject_report(
                session,
                authenticated,
                context.report_id,
                RejectReportInput(
                    expected_version=1,
                    reason="Synthetic decision after account disabling.",
                ),
                request_id=f"review-test-{uuid4().hex}",
                now=NOW,
            )

    assert report_record(context).status == "pending"
    assert_no_operational_records(context)


def test_service_requires_fresh_business_session(
    review_context: ReviewContext,
) -> None:
    context = review_context
    authenticated = authenticated_snapshot(context)

    with pytest.raises(ValueError, match="fresh session"):
        reject_report(
            context.database,
            authenticated,
            context.report_id,
            RejectReportInput(
                expected_version=1,
                reason="Synthetic decision.",
            ),
            request_id=f"review-test-{uuid4().hex}",
            now=NOW,
        )

    assert report_record(context).status == "pending"


@pytest.mark.parametrize("request_id", ["   ", "x" * 65])
def test_service_rejects_invalid_audit_request_id(
    review_context: ReviewContext,
    request_id: str,
) -> None:
    context = review_context
    authenticated = authenticated_snapshot(context)

    with Session(
        bind=context.database.get_bind(),
        join_transaction_mode="create_savepoint",
    ) as session:
        with pytest.raises(ValueError, match="bounded request ID"):
            reject_report(
                session,
                authenticated,
                context.report_id,
                RejectReportInput(
                    expected_version=1,
                    reason="Synthetic decision.",
                ),
                request_id=request_id,
                now=NOW,
            )

    assert report_record(context).status == "pending"
    assert_no_operational_records(context)


def test_service_rejects_naive_review_clock(
    review_context: ReviewContext,
) -> None:
    context = review_context
    authenticated = authenticated_snapshot(context)

    with Session(
        bind=context.database.get_bind(),
        join_transaction_mode="create_savepoint",
    ) as session:
        with pytest.raises(ValueError, match="timezone-aware clock"):
            reject_report(
                session,
                authenticated,
                context.report_id,
                RejectReportInput(
                    expected_version=1,
                    reason="Synthetic decision.",
                ),
                request_id=f"review-test-{uuid4().hex}",
                now=NOW.replace(tzinfo=None),
            )

    assert report_record(context).status == "pending"
    assert_no_operational_records(context)


def test_audit_failure_rolls_back_rejection(
    review_context: ReviewContext,
) -> None:
    context = review_context
    headers = sign_in(context)

    def fail_audit_insert(
        mapper: object,
        connection: object,
        target: IncidentAuditEvent,
    ) -> None:
        raise RuntimeError("Synthetic rejection audit failure")

    event.listen(IncidentAuditEvent, "before_insert", fail_audit_insert)

    try:
        response = context.client.post(
            f"/api/v1/staff/reports/{context.report_id}/reject",
            json={
                "expected_version": 1,
                "reason": "Synthetic rejection.",
            },
            headers=headers,
        )
    finally:
        event.remove(IncidentAuditEvent, "before_insert", fail_audit_insert)

    assert response.status_code == 500

    report = report_record(context)
    assert report.status == "pending"
    assert report.version == 1
    assert report.reviewed_by_id is None
    assert_no_operational_records(context)


def verified_incident(
    context: ReviewContext,
) -> tuple[UUID, UUID, dict[str, str]]:
    headers = sign_in(context)
    response = context.client.post(
        f"/api/v1/staff/reports/{context.report_id}/verify",
        json=verify_payload(context),
        headers=headers,
    )
    assert response.status_code == 200

    body = response.json()
    return UUID(body["incident_id"]), UUID(body["revision_id"]), headers


def amendment_payload(context: ReviewContext) -> dict[str, object]:
    payload = verify_payload(context)
    payload["reason"] = "Updated synthetic delay evidence."

    approved = payload["approved"]
    assert isinstance(approved, dict)
    approved["estimated_delay_minutes"] = 30

    return payload


def resolution_payload() -> dict[str, object]:
    return {
        "expected_version": 1,
        "reason": "Synthetic disruption ended.",
        "resolution_effective_at": NOW.isoformat(),
    }


def test_amendment_creates_new_revision_and_preserves_original(
    review_context: ReviewContext,
) -> None:
    context = review_context
    incident_id, original_revision_id, headers = verified_incident(context)

    response = context.client.post(
        f"/api/v1/staff/incidents/{incident_id}/amend",
        json=amendment_payload(context),
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"

    body = response.json()
    assert body["status"] == "active"
    assert body["incident_version"] == 2
    assert body["current_revision_number"] == 2
    assert body["current_revision_id"] != str(original_revision_id)

    context.database.expire_all()
    original = context.database.get(IncidentRevision, original_revision_id)
    current = context.database.get(
        IncidentRevision,
        UUID(body["current_revision_id"]),
    )

    assert original is not None
    assert original.estimated_delay_minutes == 15
    assert original.revision_number == 1

    assert current is not None
    assert current.incident_id == incident_id
    assert current.estimated_delay_minutes == 30
    assert current.revision_number == 2
    assert current.verified_by_id == context.user.id

    audit = context.database.scalar(
        select(IncidentAuditEvent).where(
            IncidentAuditEvent.incident_id == incident_id,
            IncidentAuditEvent.action == "incident_revised",
        )
    )
    assert audit is not None
    assert audit.revision_id == current.id
    assert audit.incident_version == 2
    assert audit.report_version == 2
    assert audit.actor_id == context.user.id
    assert audit.request_id == response.headers["X-Request-ID"]
    assert report_record(context).version == 2


def test_resolution_preserves_revision_and_records_effective_time(
    review_context: ReviewContext,
) -> None:
    context = review_context
    incident_id, revision_id, headers = verified_incident(context)

    response = context.client.post(
        f"/api/v1/staff/incidents/{incident_id}/resolve",
        json=resolution_payload(),
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "resolved"
    assert body["incident_version"] == 2
    assert body["current_revision_number"] == 1
    assert body["current_revision_id"] == str(revision_id)

    context.database.expire_all()
    incident = context.database.get(Incident, incident_id)

    assert incident is not None
    assert incident.resolved_by_id == context.user.id
    assert incident.resolved_at == NOW
    assert incident.resolution_effective_at == NOW
    assert incident.resolution_reason == "Synthetic disruption ended."
    assert context.database.get(IncidentRevision, revision_id) is not None

    audit = context.database.scalar(
        select(IncidentAuditEvent).where(
            IncidentAuditEvent.incident_id == incident_id,
            IncidentAuditEvent.action == "incident_resolved",
        )
    )
    assert audit is not None
    assert audit.revision_id == revision_id
    assert audit.incident_version == 2
    assert audit.request_id == response.headers["X-Request-ID"]


@pytest.mark.parametrize("action", ["amend", "resolve"])
def test_lifecycle_rejects_stale_version(
    review_context: ReviewContext,
    action: str,
) -> None:
    context = review_context
    incident_id, _, headers = verified_incident(context)
    payload = amendment_payload(context) if action == "amend" else resolution_payload()
    payload["expected_version"] = 99

    response = context.client.post(
        f"/api/v1/staff/incidents/{incident_id}/{action}",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 409

    context.database.expire_all()
    incident = context.database.get(Incident, incident_id)
    assert incident is not None
    assert incident.version == 1
    assert incident.status == "active"


@pytest.mark.parametrize("action", ["amend", "resolve"])
def test_resolved_incident_rejects_further_changes(
    review_context: ReviewContext,
    action: str,
) -> None:
    context = review_context
    incident_id, _, headers = verified_incident(context)

    resolved = context.client.post(
        f"/api/v1/staff/incidents/{incident_id}/resolve",
        json=resolution_payload(),
        headers=headers,
    )
    assert resolved.status_code == 200

    payload = amendment_payload(context) if action == "amend" else resolution_payload()
    payload["expected_version"] = 2

    response = context.client.post(
        f"/api/v1/staff/incidents/{incident_id}/{action}",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 409


@pytest.mark.parametrize("seconds", [-1, 1])
def test_resolution_rejects_invalid_effective_time(
    review_context: ReviewContext,
    seconds: int,
) -> None:
    context = review_context
    incident_id, _, headers = verified_incident(context)
    payload = resolution_payload()
    payload["resolution_effective_at"] = (NOW + timedelta(seconds=seconds)).isoformat()

    response = context.client.post(
        f"/api/v1/staff/incidents/{incident_id}/resolve",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 422

    context.database.expire_all()
    incident = context.database.get(Incident, incident_id)
    assert incident is not None
    assert incident.status == "active"
    assert incident.version == 1


@pytest.mark.parametrize("action", ["amend", "resolve"])
def test_lifecycle_requires_authentication(
    review_context: ReviewContext,
    action: str,
) -> None:
    context = review_context
    incident_id, _, _ = verified_incident(context)
    context.client.cookies.clear()

    response = context.client.post(
        f"/api/v1/staff/incidents/{incident_id}/{action}",
        json=(amendment_payload(context) if action == "amend" else resolution_payload()),
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 401


@pytest.mark.parametrize("action", ["amend", "resolve"])
def test_lifecycle_requires_specific_permission(
    review_context: ReviewContext,
    monkeypatch: pytest.MonkeyPatch,
    action: str,
) -> None:
    context = review_context
    incident_id, _, headers = verified_incident(context)

    monkeypatch.setitem(
        ROLE_PERMISSIONS,
        RoleCode.CONTROLLER,
        frozenset({Permission.REPORTS_READ}),
    )

    response = context.client.post(
        f"/api/v1/staff/incidents/{incident_id}/{action}",
        json=(amendment_payload(context) if action == "amend" else resolution_payload()),
        headers=headers,
    )

    assert response.status_code == 403


@pytest.mark.parametrize("action", ["amend", "resolve"])
def test_audit_failure_rolls_back_lifecycle_change(
    review_context: ReviewContext,
    action: str,
) -> None:
    context = review_context
    incident_id, revision_id, headers = verified_incident(context)

    def fail_audit_insert(
        mapper: object,
        connection: object,
        target: IncidentAuditEvent,
    ) -> None:
        raise RuntimeError("Synthetic lifecycle audit failure")

    event.listen(IncidentAuditEvent, "before_insert", fail_audit_insert)

    try:
        response = context.client.post(
            f"/api/v1/staff/incidents/{incident_id}/{action}",
            json=(amendment_payload(context) if action == "amend" else resolution_payload()),
            headers=headers,
        )
    finally:
        event.remove(IncidentAuditEvent, "before_insert", fail_audit_insert)

    assert response.status_code == 500

    context.database.expire_all()
    incident = context.database.get(Incident, incident_id)
    assert incident is not None
    assert incident.status == "active"
    assert incident.version == 1
    assert incident.current_revision_number == 1
    assert incident.resolved_at is None

    revisions = context.database.scalars(
        select(IncidentRevision).where(IncidentRevision.incident_id == incident_id)
    ).all()
    audits = context.database.scalars(
        select(IncidentAuditEvent).where(IncidentAuditEvent.incident_id == incident_id)
    ).all()

    assert [revision.id for revision in revisions] == [revision_id]
    assert len(audits) == 1
    assert audits[0].action == "report_verified"


def allow_audit_access(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        ROLE_PERMISSIONS,
        RoleCode.CONTROLLER,
        ROLE_PERMISSIONS[RoleCode.CONTROLLER] | {Permission.AUDIT_READ},
    )


def test_report_audit_requires_authentication(
    review_context: ReviewContext,
) -> None:
    context = review_context

    response = context.client.get(f"/api/v1/staff/reports/{context.report_id}/audit")

    assert response.status_code == 401


def test_report_audit_requires_explicit_permission(
    review_context: ReviewContext,
) -> None:
    context = review_context
    sign_in(context)

    response = context.client.get(f"/api/v1/staff/reports/{context.report_id}/audit")

    assert response.status_code == 403


def test_pending_report_has_empty_audit_history(
    review_context: ReviewContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = review_context
    allow_audit_access(monkeypatch)
    sign_in(context)

    response = context.client.get(f"/api/v1/staff/reports/{context.report_id}/audit")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"

    payload = response.json()
    assert payload["report_id"] == str(context.report_id)
    assert payload["items"] == []
    assert payload["total"] == 0
    assert payload["limit"] == 20
    assert payload["offset"] == 0


def test_report_audit_returns_verified_decision(
    review_context: ReviewContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = review_context
    allow_audit_access(monkeypatch)
    incident_id, revision_id, _ = verified_incident(context)

    response = context.client.get(f"/api/v1/staff/reports/{context.report_id}/audit")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1

    item = payload["items"][0]
    assert set(item) == {
        "event_id",
        "report_id",
        "incident_id",
        "revision_id",
        "actor_id",
        "action",
        "reason",
        "request_id",
        "report_version",
        "incident_version",
        "occurred_at",
    }
    assert item["report_id"] == str(context.report_id)
    assert item["incident_id"] == str(incident_id)
    assert item["revision_id"] == str(revision_id)
    assert item["actor_id"] == str(context.user.id)
    assert item["action"] == "report_verified"
    assert item["report_version"] == 2
    assert item["incident_version"] == 1


def test_report_audit_includes_rejected_decision(
    review_context: ReviewContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = review_context
    allow_audit_access(monkeypatch)
    headers = sign_in(context)

    decision = context.client.post(
        f"/api/v1/staff/reports/{context.report_id}/reject",
        headers=headers,
        json={
            "expected_version": 1,
            "reason": "Synthetic evidence did not support verification.",
        },
    )
    assert decision.status_code == 200

    response = context.client.get(f"/api/v1/staff/reports/{context.report_id}/audit")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    item = payload["items"][0]
    assert item["action"] == "report_rejected"
    assert item["incident_id"] is None
    assert item["revision_id"] is None
    assert item["incident_version"] is None


def test_report_audit_contains_complete_lifecycle(
    review_context: ReviewContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = review_context
    allow_audit_access(monkeypatch)
    incident_id, _, headers = verified_incident(context)

    amendment = context.client.post(
        f"/api/v1/staff/incidents/{incident_id}/amend",
        headers=headers,
        json=amendment_payload(context),
    )
    assert amendment.status_code == 200

    resolution = resolution_payload()
    resolution["expected_version"] = 2

    resolved = context.client.post(
        f"/api/v1/staff/incidents/{incident_id}/resolve",
        headers=headers,
        json=resolution,
    )
    assert resolved.status_code == 200

    response = context.client.get(f"/api/v1/staff/reports/{context.report_id}/audit")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3

    events_by_action = {item["action"]: item for item in payload["items"]}
    assert set(events_by_action) == {
        "report_verified",
        "incident_revised",
        "incident_resolved",
    }
    assert events_by_action["report_verified"]["incident_version"] == 1
    assert events_by_action["incident_revised"]["incident_version"] == 2
    assert events_by_action["incident_resolved"]["incident_version"] == 3


def test_report_audit_pagination(
    review_context: ReviewContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = review_context
    allow_audit_access(monkeypatch)
    incident_id, _, headers = verified_incident(context)

    amendment = context.client.post(
        f"/api/v1/staff/incidents/{incident_id}/amend",
        headers=headers,
        json=amendment_payload(context),
    )
    assert amendment.status_code == 200

    path = f"/api/v1/staff/reports/{context.report_id}/audit"
    first = context.client.get(path, params={"limit": 1, "offset": 0})
    second = context.client.get(path, params={"limit": 1, "offset": 1})

    assert first.status_code == 200
    assert second.status_code == 200

    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["total"] == 2
    assert second_payload["total"] == 2
    assert len(first_payload["items"]) == 1
    assert len(second_payload["items"]) == 1
    assert first_payload["items"][0]["event_id"] != second_payload["items"][0]["event_id"]


def test_report_audit_missing_report_returns_not_found(
    review_context: ReviewContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = review_context
    allow_audit_access(monkeypatch)
    sign_in(context)

    response = context.client.get(f"/api/v1/staff/reports/{uuid4()}/audit")

    assert response.status_code == 404


@pytest.mark.parametrize(
    "query",
    [
        {"limit": 0},
        {"limit": 101},
        {"offset": -1},
        {"offset": 10001},
        {"unexpected": "value"},
    ],
)
def test_report_audit_rejects_invalid_query(
    review_context: ReviewContext,
    monkeypatch: pytest.MonkeyPatch,
    query: dict[str, object],
) -> None:
    context = review_context
    allow_audit_access(monkeypatch)
    sign_in(context)

    response = context.client.get(
        f"/api/v1/staff/reports/{context.report_id}/audit",
        params=query,
    )

    assert response.status_code == 422


@pytest.mark.parametrize("action", ["amend", "resolve"])
def test_lifecycle_rejects_missing_csrf(
    review_context: ReviewContext,
    action: str,
) -> None:
    context = review_context
    incident_id, _, _ = verified_incident(context)
    payload = amendment_payload(context) if action == "amend" else resolution_payload()

    response = context.client.post(
        f"/api/v1/staff/incidents/{incident_id}/{action}",
        headers={"Origin": ORIGIN},
        json=payload,
    )

    assert response.status_code == 403


@pytest.mark.parametrize("action", ["amend", "resolve"])
def test_lifecycle_rejects_untrusted_origin(
    review_context: ReviewContext,
    action: str,
) -> None:
    context = review_context
    incident_id, _, headers = verified_incident(context)
    payload = amendment_payload(context) if action == "amend" else resolution_payload()

    response = context.client.post(
        f"/api/v1/staff/incidents/{incident_id}/{action}",
        headers={
            **headers,
            "Origin": "https://untrusted.example",
        },
        json=payload,
    )

    assert response.status_code == 403


@pytest.mark.parametrize("action", ["amend", "resolve"])
def test_lifecycle_missing_incident_returns_not_found(
    review_context: ReviewContext,
    action: str,
) -> None:
    context = review_context
    headers = sign_in(context)
    payload = amendment_payload(context) if action == "amend" else resolution_payload()

    response = context.client.post(
        f"/api/v1/staff/incidents/{uuid4()}/{action}",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 404


def test_invalid_amendment_scope_preserves_current_revision(
    review_context: ReviewContext,
) -> None:
    context = review_context
    incident_id, original_revision_id, headers = verified_incident(context)
    payload = amendment_payload(context)

    approved = payload["approved"]
    assert isinstance(approved, dict)
    approved["arrival_stop_sequence"] = 99

    response = context.client.post(
        f"/api/v1/staff/incidents/{incident_id}/amend",
        headers=headers,
        json=payload,
    )

    assert response.status_code == 422

    context.database.expire_all()
    incident = context.database.get(Incident, incident_id)
    assert incident is not None
    assert incident.version == 1
    assert incident.current_revision_number == 1

    revisions = context.database.scalars(
        select(IncidentRevision).where(IncidentRevision.incident_id == incident_id)
    ).all()
    assert [revision.id for revision in revisions] == [original_revision_id]

    audits = context.database.scalars(
        select(IncidentAuditEvent).where(IncidentAuditEvent.incident_id == incident_id)
    ).all()
    assert len(audits) == 1
    assert audits[0].action == "report_verified"


def test_audit_access_is_denied_after_role_assignment_is_removed(
    review_context: ReviewContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = review_context
    allow_audit_access(monkeypatch)
    sign_in(context)

    context.database.execute(delete(UserRole).where(UserRole.user_id == context.user.id))
    context.database.flush()

    response = context.client.get(f"/api/v1/staff/reports/{context.report_id}/audit")

    assert response.status_code == 401
