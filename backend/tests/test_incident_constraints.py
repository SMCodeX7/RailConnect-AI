from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, insert, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from railconnect.modules.identity.models.user import User
from railconnect.modules.incidents.errors import InvalidReportError
from railconnect.modules.incidents.models.incident import Incident
from railconnect.modules.incidents.models.incident_audit_event import IncidentAuditEvent
from railconnect.modules.incidents.models.incident_report import IncidentReport
from railconnect.modules.incidents.models.incident_revision import IncidentRevision
from railconnect.modules.incidents.report_repository import validate_report_references
from railconnect.modules.incidents.report_schemas import SubmitReportInput
from railconnect.modules.stations.models import Station
from railconnect.modules.timetable.models.run_stop import RunStop
from railconnect.modules.timetable.models.service_run import ServiceRun
from railconnect.modules.timetable.models.train_service import TrainService


@dataclass(frozen=True)
class IncidentRecords:
    session: Session
    actor_id: UUID
    report_id: UUID
    incident_id: UUID
    revision_id: UUID
    audit_id: UUID
    run_id: UUID
    now: datetime


@pytest.fixture
def incident_records(identity_database: Session) -> IncidentRecords:
    session = identity_database
    suffix = uuid4().hex
    now = datetime(2026, 10, 14, 8, 0, tzinfo=UTC)

    actor = User(
        username=f"incident_{suffix}",
        display_name="Incident Test Controller",
        password_hash="unused-test-hash",
        is_active=True,
    )
    stations = [
        Station(
            code=f"DEMO_{suffix[:10].upper()}{index}",
            name=f"Incident Test Station {index}",
            source_ref="incident-constraint-test",
            is_active=True,
        )
        for index in range(1, 4)
    ]
    service = TrainService(
        code=f"DEMO_{suffix.upper()}",
        name="Incident Constraint Test Service",
        source_ref="incident-constraint-test",
        operating_days=127,
        valid_from=date(2026, 1, 1),
        valid_until=date(2028, 12, 31),
        is_active=True,
    )

    session.add_all([actor, service, *stations])
    session.flush()

    run = ServiceRun(
        service_id=service.id,
        service_date=now.date(),
        source_ref="incident-constraint-test",
        status="scheduled",
        version=1,
    )
    session.add(run)
    session.flush()

    session.add_all(
        [
            RunStop(
                run_id=run.id,
                station_id=station.id,
                stop_sequence=sequence,
                scheduled_arrival_at=(None if sequence == 1 else now + timedelta(hours=sequence)),
                scheduled_departure_at=(
                    None if sequence == 3 else now + timedelta(hours=sequence, minutes=5)
                ),
                pickup_allowed=sequence != 3,
                dropoff_allowed=sequence != 1,
            )
            for sequence, station in enumerate(stations, start=1)
        ]
    )
    session.flush()

    report = IncidentReport(
        title="Fictional test report",
        narrative="Synthetic report used only by database tests.",
        observed_at=now,
        submitted_at=now,
        run_hint_id=run.id,
        status="verified",
        version=2,
        reviewed_by_id=actor.id,
        reviewed_at=now + timedelta(minutes=1),
        review_reason="Verified synthetic test scenario.",
    )
    session.add(report)
    session.flush()

    incident = Incident(
        originating_report_id=report.id,
        created_by_id=actor.id,
        created_at=now + timedelta(minutes=1),
        status="active",
        version=1,
        current_revision_number=1,
    )
    session.add(incident)
    session.flush()

    revision = IncidentRevision(
        incident_id=incident.id,
        revision_number=1,
        run_id=run.id,
        scope_kind="segment",
        departure_stop_sequence=1,
        arrival_stop_sequence=3,
        impact_kind="delay",
        estimated_delay_minutes=15,
        effective_from=now,
        effective_until=now + timedelta(hours=6),
        public_summary="Synthetic demonstration delay.",
        evidence_basis="Controlled test fixture.",
        verification_reason="Approved synthetic test facts.",
        verified_by_id=actor.id,
        verified_at=now + timedelta(minutes=1),
    )
    session.add(revision)
    session.flush()

    audit = IncidentAuditEvent(
        report_id=report.id,
        incident_id=incident.id,
        revision_id=revision.id,
        actor_id=actor.id,
        action="report_verified",
        reason="Verified synthetic test scenario.",
        request_id=f"incident-test-{suffix}",
        report_version=2,
        incident_version=1,
        occurred_at=now + timedelta(minutes=1),
    )
    session.add(audit)
    session.flush()

    return IncidentRecords(
        session=session,
        actor_id=actor.id,
        report_id=report.id,
        incident_id=incident.id,
        revision_id=revision.id,
        audit_id=audit.id,
        run_id=run.id,
        now=now,
    )


def test_valid_incident_history_is_persisted(
    incident_records: IncidentRecords,
) -> None:
    records = incident_records

    assert records.session.get(IncidentReport, records.report_id) is not None
    assert records.session.get(Incident, records.incident_id) is not None
    assert records.session.get(IncidentRevision, records.revision_id) is not None
    assert records.session.get(IncidentAuditEvent, records.audit_id) is not None


def test_report_defaults_to_pending(
    incident_records: IncidentRecords,
) -> None:
    records = incident_records
    report = IncidentReport(
        title="New passenger report",
        narrative="Unverified synthetic passenger claim.",
        observed_at=records.now,
        submitted_at=records.now,
    )
    records.session.add(report)
    records.session.flush()

    assert report.status == "pending"
    assert report.version == 1
    assert report.reviewed_by_id is None
    assert report.reviewed_at is None
    assert report.review_reason is None


@pytest.mark.parametrize("status", ["verified", "rejected"])
def test_reviewed_report_requires_review_metadata(
    incident_records: IncidentRecords,
    status: str,
) -> None:
    records = incident_records

    with pytest.raises(IntegrityError):
        with records.session.begin_nested():
            records.session.execute(
                insert(IncidentReport).values(
                    id=uuid4(),
                    title="Incomplete review",
                    narrative="Synthetic report without review metadata.",
                    observed_at=records.now,
                    submitted_at=records.now,
                    status=status,
                    version=1,
                )
            )


def test_pending_report_cannot_have_review_metadata(
    incident_records: IncidentRecords,
) -> None:
    records = incident_records

    with pytest.raises(IntegrityError):
        with records.session.begin_nested():
            records.session.execute(
                insert(IncidentReport).values(
                    id=uuid4(),
                    title="Invalid pending report",
                    narrative="Synthetic inconsistent review state.",
                    observed_at=records.now,
                    submitted_at=records.now,
                    status="pending",
                    version=1,
                    reviewed_by_id=records.actor_id,
                    reviewed_at=records.now,
                    review_reason="Should not exist on a pending report.",
                )
            )


def test_staff_cannot_review_own_identified_report(
    incident_records: IncidentRecords,
) -> None:
    records = incident_records

    with pytest.raises(IntegrityError):
        with records.session.begin_nested():
            records.session.execute(
                insert(IncidentReport).values(
                    id=uuid4(),
                    title="Self-review attempt",
                    narrative="Synthetic identified staff submission.",
                    observed_at=records.now,
                    submitted_at=records.now,
                    submitted_by_user_id=records.actor_id,
                    status="rejected",
                    version=2,
                    reviewed_by_id=records.actor_id,
                    reviewed_at=records.now,
                    review_reason="Invalid self-review.",
                )
            )


def test_report_segment_requires_a_run(
    incident_records: IncidentRecords,
) -> None:
    records = incident_records

    with pytest.raises(IntegrityError):
        with records.session.begin_nested():
            records.session.execute(
                insert(IncidentReport).values(
                    id=uuid4(),
                    title="Incomplete segment hint",
                    narrative="Synthetic segment with no run reference.",
                    observed_at=records.now,
                    submitted_at=records.now,
                    departure_stop_sequence_hint=1,
                    arrival_stop_sequence_hint=3,
                )
            )


def test_resolved_incident_requires_resolution_metadata(
    incident_records: IncidentRecords,
) -> None:
    records = incident_records

    with pytest.raises(IntegrityError):
        with records.session.begin_nested():
            records.session.execute(
                update(Incident).where(Incident.id == records.incident_id).values(status="resolved")
            )

    status = records.session.scalar(
        select(Incident.status).where(Incident.id == records.incident_id)
    )
    assert status == "active"


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_revisions_reject_mutation(
    incident_records: IncidentRecords,
    operation: str,
) -> None:
    records = incident_records

    with pytest.raises(DBAPIError, match="append-only"):
        with records.session.begin_nested():
            if operation == "update":
                records.session.execute(
                    update(IncidentRevision)
                    .where(IncidentRevision.id == records.revision_id)
                    .values(public_summary="Attempted overwrite.")
                )
            else:
                records.session.execute(
                    delete(IncidentRevision).where(IncidentRevision.id == records.revision_id)
                )

    summary = records.session.scalar(
        select(IncidentRevision.public_summary).where(IncidentRevision.id == records.revision_id)
    )
    assert summary == "Synthetic demonstration delay."


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_audit_events_reject_mutation(
    incident_records: IncidentRecords,
    operation: str,
) -> None:
    records = incident_records

    with pytest.raises(DBAPIError, match="append-only"):
        with records.session.begin_nested():
            if operation == "update":
                records.session.execute(
                    update(IncidentAuditEvent)
                    .where(IncidentAuditEvent.id == records.audit_id)
                    .values(reason="Attempted overwrite.")
                )
            else:
                records.session.execute(
                    delete(IncidentAuditEvent).where(IncidentAuditEvent.id == records.audit_id)
                )

    reason = records.session.scalar(
        select(IncidentAuditEvent.reason).where(IncidentAuditEvent.id == records.audit_id)
    )
    assert reason == "Verified synthetic test scenario."


@pytest.mark.parametrize(
    "statement",
    [
        "TRUNCATE TABLE incident_audit_events",
        "TRUNCATE TABLE incident_revisions CASCADE",
    ],
)
def test_history_rejects_truncation(
    incident_records: IncidentRecords,
    statement: str,
) -> None:
    records = incident_records

    with pytest.raises(DBAPIError, match="append-only"):
        with records.session.begin_nested():
            records.session.execute(text(statement))

    assert records.session.get(IncidentRevision, records.revision_id) is not None
    assert records.session.get(IncidentAuditEvent, records.audit_id) is not None


def revision_values(
    records: IncidentRecords,
    changes: dict[str, object],
) -> dict[str, object]:
    values: dict[str, object] = {
        "id": uuid4(),
        "incident_id": records.incident_id,
        "revision_number": 2,
        "run_id": records.run_id,
        "scope_kind": "segment",
        "departure_stop_sequence": 1,
        "arrival_stop_sequence": 3,
        "impact_kind": "delay",
        "estimated_delay_minutes": 15,
        "effective_from": records.now,
        "effective_until": records.now + timedelta(hours=6),
        "public_summary": "Synthetic demonstration impact.",
        "evidence_basis": "Controlled test fixture.",
        "verification_reason": "Approved synthetic test facts.",
        "verified_by_id": records.actor_id,
        "verified_at": records.now + timedelta(minutes=2),
    }
    values.update(changes)
    return values


@pytest.mark.parametrize(
    ("changes", "constraint"),
    [
        (
            {"estimated_delay_minutes": None},
            "ck_incident_revisions_consistent_delay",
        ),
        (
            {"estimated_delay_minutes": 0},
            "ck_incident_revisions_consistent_delay",
        ),
        (
            {"estimated_delay_minutes": 1441},
            "ck_incident_revisions_consistent_delay",
        ),
        (
            {
                "impact_kind": "cancellation",
                "estimated_delay_minutes": None,
            },
            "ck_incident_revisions_cancellation_requires_run_scope",
        ),
        (
            {"scope_kind": "run"},
            "ck_incident_revisions_consistent_scope",
        ),
        (
            {
                "effective_from": datetime(2026, 10, 14, 8, 0, tzinfo=UTC),
                "effective_until": datetime(2026, 10, 14, 8, 0, tzinfo=UTC),
            },
            "ck_incident_revisions_valid_effective_interval",
        ),
        (
            {
                "departure_stop_sequence": 3,
                "arrival_stop_sequence": 1,
            },
            "ck_incident_revisions_consistent_scope",
        ),
        (
            {"arrival_stop_sequence": 99},
            "fk_incident_revisions_arrival_run_stop",
        ),
        (
            {"revision_number": 0},
            "ck_incident_revisions_positive_revision_number",
        ),
        (
            {"evidence_basis": "   "},
            "ck_incident_revisions_valid_evidence_basis",
        ),
    ],
)
def test_rejects_invalid_revision_facts(
    incident_records: IncidentRecords,
    changes: dict[str, object],
    constraint: str,
) -> None:
    records = incident_records

    with pytest.raises(IntegrityError, match=constraint):
        with records.session.begin_nested():
            records.session.execute(
                insert(IncidentRevision).values(**revision_values(records, changes))
            )


def test_revision_number_is_unique_within_incident(
    incident_records: IncidentRecords,
) -> None:
    records = incident_records

    with pytest.raises(
        IntegrityError,
        match="uq_incident_revisions_incident_number",
    ):
        with records.session.begin_nested():
            records.session.execute(
                insert(IncidentRevision).values(**revision_values(records, {"revision_number": 1}))
            )


def test_accepts_whole_run_cancellation(
    incident_records: IncidentRecords,
) -> None:
    records = incident_records
    values = revision_values(
        records,
        {
            "scope_kind": "run",
            "departure_stop_sequence": None,
            "arrival_stop_sequence": None,
            "impact_kind": "cancellation",
            "estimated_delay_minutes": None,
        },
    )

    records.session.execute(insert(IncidentRevision).values(**values))

    revision = records.session.get(IncidentRevision, values["id"])

    assert revision is not None
    assert revision.scope_kind == "run"
    assert revision.impact_kind == "cancellation"
    assert revision.estimated_delay_minutes is None


@pytest.mark.parametrize(
    "action",
    ["report_verified", "report_rejected"],
)
def test_audit_requires_consistent_action_references(
    incident_records: IncidentRecords,
    action: str,
) -> None:
    records = incident_records

    values: dict[str, object] = {
        "id": uuid4(),
        "report_id": records.report_id,
        "actor_id": records.actor_id,
        "action": action,
        "reason": "Synthetic invalid audit references.",
        "request_id": f"incident-test-{uuid4().hex}",
        "report_version": 2,
        "occurred_at": records.now + timedelta(minutes=2),
    }

    if action == "report_rejected":
        values.update(
            {
                "incident_id": records.incident_id,
                "revision_id": records.revision_id,
                "incident_version": 1,
            }
        )

    with pytest.raises(
        IntegrityError,
        match="ck_incident_audit_events_consistent_action_references",
    ):
        with records.session.begin_nested():
            records.session.execute(insert(IncidentAuditEvent).values(**values))


def scope_input(
    records: IncidentRecords,
    **changes: object,
) -> SubmitReportInput:
    values: dict[str, object] = {
        "title": "Synthetic scope validation",
        "narrative": "An unverified passenger scope hint.",
        "observed_at": records.now,
        "run_hint_id": records.run_id,
        "departure_stop_sequence_hint": 1,
        "arrival_stop_sequence_hint": 3,
    }
    values.update(changes)
    return SubmitReportInput.model_validate(values)


def station_at_stop(records: IncidentRecords, sequence: int) -> UUID:
    station_id = records.session.scalar(
        select(RunStop.station_id).where(
            RunStop.run_id == records.run_id,
            RunStop.stop_sequence == sequence,
        )
    )
    assert station_id is not None
    return station_id


def test_accepts_station_inside_hinted_segment(
    incident_records: IncidentRecords,
) -> None:
    records = incident_records
    data = scope_input(
        records,
        station_hint_id=station_at_stop(records, 2),
    )

    validate_report_references(records.session, data, None)


def test_rejects_segment_endpoint_missing_from_run(
    incident_records: IncidentRecords,
) -> None:
    records = incident_records
    data = scope_input(records, arrival_stop_sequence_hint=99)

    with pytest.raises(InvalidReportError, match="do not identify stops"):
        validate_report_references(records.session, data, None)


def test_rejects_station_outside_hinted_segment(
    incident_records: IncidentRecords,
) -> None:
    records = incident_records
    data = scope_input(
        records,
        arrival_stop_sequence_hint=2,
        station_hint_id=station_at_stop(records, 3),
    )

    with pytest.raises(InvalidReportError, match="outside the hinted segment"):
        validate_report_references(records.session, data, None)


def test_rejects_station_not_on_hinted_run(
    incident_records: IncidentRecords,
) -> None:
    records = incident_records
    station = Station(
        code=f"DEMO_{uuid4().hex[:12].upper()}",
        name="Synthetic Off-route Station",
        source_ref="incident-scope-test",
        is_active=True,
    )
    records.session.add(station)
    records.session.flush()

    data = scope_input(records, station_hint_id=station.id)

    with pytest.raises(InvalidReportError, match="not on the dated service run"):
        validate_report_references(records.session, data, None)


def test_rejects_inactive_station_hint(
    incident_records: IncidentRecords,
) -> None:
    records = incident_records
    station_id = station_at_stop(records, 2)

    records.session.execute(update(Station).where(Station.id == station_id).values(is_active=False))
    data = scope_input(records, station_hint_id=station_id)

    with pytest.raises(InvalidReportError, match="station hint is unavailable"):
        validate_report_references(records.session, data, None)


@pytest.mark.parametrize("status", ["cancelled", "restricted"])
def test_passenger_can_report_cancelled_or_restricted_run(
    incident_records: IncidentRecords,
    status: str,
) -> None:
    records = incident_records
    records.session.execute(
        update(ServiceRun).where(ServiceRun.id == records.run_id).values(status=status)
    )

    validate_report_references(
        records.session,
        scope_input(records),
        None,
    )


def test_rejects_disabled_staff_submitter(
    incident_records: IncidentRecords,
) -> None:
    records = incident_records
    records.session.execute(update(User).where(User.id == records.actor_id).values(is_active=False))

    with pytest.raises(InvalidReportError, match="staff account is unavailable"):
        validate_report_references(
            records.session,
            scope_input(records),
            records.actor_id,
        )
