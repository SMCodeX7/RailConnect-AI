from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from railconnect.modules.identity.permissions import Permission
from railconnect.modules.identity.session_service import (
    AuthenticatedSession,
    require_actor_permission,
)
from railconnect.modules.incidents.errors import (
    IncidentConflictError,
    IncidentHistoryError,
    IncidentNotFoundError,
    InvalidIncidentLifecycleError,
)
from railconnect.modules.incidents.lifecycle_repository import (
    get_current_revision,
    get_incident_for_change,
    get_originating_report,
)
from railconnect.modules.incidents.lifecycle_schemas import (
    AmendIncidentInput,
    IncidentLifecycleResponse,
    ResolveIncidentInput,
)
from railconnect.modules.incidents.models.incident import Incident
from railconnect.modules.incidents.models.incident_audit_event import IncidentAuditEvent
from railconnect.modules.incidents.models.incident_report import IncidentReport
from railconnect.modules.incidents.models.incident_revision import IncidentRevision
from railconnect.modules.incidents.review_repository import validate_approved_run_scope
from railconnect.modules.incidents.staff_policy import require_current_staff_permission


def _validate_context(
    session: Session,
    authenticated: AuthenticatedSession,
    permission: Permission,
    request_id: str,
    now: datetime,
) -> datetime:
    require_actor_permission(authenticated.actor, permission)

    if session.in_transaction():
        raise ValueError("Incident lifecycle changes require a fresh session.")

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Incident lifecycle changes require a timezone-aware clock.")

    if not request_id.strip() or len(request_id) > 64:
        raise ValueError("Incident lifecycle changes require a bounded request ID.")

    return now.astimezone(UTC)


def _load_active_incident(
    session: Session,
    incident_id: UUID,
    expected_version: int,
    timestamp: datetime,
) -> tuple[Incident, IncidentRevision, IncidentReport]:
    incident = get_incident_for_change(session, incident_id)

    if incident is None:
        raise IncidentNotFoundError("The incident does not exist.")

    if incident.status != "active" or incident.version != expected_version:
        raise IncidentConflictError("The incident has changed or is already resolved.")

    revision = get_current_revision(session, incident)
    report = get_originating_report(session, incident)

    if revision is None or report is None or report.status != "verified":
        raise IncidentHistoryError("The incident history is incomplete or inconsistent.")

    if timestamp < incident.created_at or timestamp < revision.verified_at:
        raise InvalidIncidentLifecycleError(
            "The decision time cannot precede the incident's verified history."
        )

    return incident, revision, report


def _response(
    incident: Incident,
    revision: IncidentRevision,
) -> IncidentLifecycleResponse:
    return IncidentLifecycleResponse(
        incident_id=incident.id,
        originating_report_id=incident.originating_report_id,
        status="resolved" if incident.status == "resolved" else "active",
        incident_version=incident.version,
        current_revision_number=incident.current_revision_number,
        current_revision_id=revision.id,
    )


def amend_incident(
    session: Session,
    authenticated: AuthenticatedSession,
    incident_id: UUID,
    data: AmendIncidentInput,
    request_id: str,
    now: datetime,
) -> IncidentLifecycleResponse:
    timestamp = _validate_context(
        session,
        authenticated,
        Permission.INCIDENTS_EDIT,
        request_id,
        now,
    )

    with session.begin():
        actor_id = require_current_staff_permission(
            session,
            authenticated,
            Permission.INCIDENTS_EDIT,
        )

        incident, current_revision, report = _load_active_incident(
            session,
            incident_id,
            data.expected_version,
            timestamp,
        )
        validate_approved_run_scope(session, data.approved)

        approved = data.approved
        revision = IncidentRevision(
            incident_id=incident.id,
            revision_number=current_revision.revision_number + 1,
            run_id=approved.run_id,
            scope_kind=approved.scope_kind,
            departure_stop_sequence=approved.departure_stop_sequence,
            arrival_stop_sequence=approved.arrival_stop_sequence,
            impact_kind=approved.impact_kind,
            estimated_delay_minutes=approved.estimated_delay_minutes,
            effective_from=approved.effective_from.astimezone(UTC),
            effective_until=approved.effective_until.astimezone(UTC),
            public_summary=approved.public_summary,
            evidence_basis=approved.evidence_basis,
            verification_reason=data.reason,
            verified_by_id=actor_id,
            verified_at=timestamp,
        )
        session.add(revision)
        session.flush()

        incident.version += 1
        incident.current_revision_number = revision.revision_number
        session.flush()

        session.add(
            IncidentAuditEvent(
                report_id=report.id,
                incident_id=incident.id,
                revision_id=revision.id,
                actor_id=actor_id,
                action="incident_revised",
                reason=data.reason,
                request_id=request_id,
                report_version=report.version,
                incident_version=incident.version,
                occurred_at=timestamp,
            )
        )
        session.flush()

        response = _response(incident, revision)

    return response


def resolve_incident(
    session: Session,
    authenticated: AuthenticatedSession,
    incident_id: UUID,
    data: ResolveIncidentInput,
    request_id: str,
    now: datetime,
) -> IncidentLifecycleResponse:
    timestamp = _validate_context(
        session,
        authenticated,
        Permission.INCIDENTS_RESOLVE,
        request_id,
        now,
    )

    with session.begin():
        actor_id = require_current_staff_permission(
            session,
            authenticated,
            Permission.INCIDENTS_RESOLVE,
        )

        incident, revision, report = _load_active_incident(
            session,
            incident_id,
            data.expected_version,
            timestamp,
        )

        effective_at = data.resolution_effective_at.astimezone(UTC)

        if effective_at > timestamp:
            raise InvalidIncidentLifecycleError("Resolution cannot take effect in the future.")

        if effective_at < revision.effective_from:
            raise InvalidIncidentLifecycleError(
                "Resolution cannot precede the current revision's effective start."
            )

        incident.status = "resolved"
        incident.version += 1
        incident.resolved_by_id = actor_id
        incident.resolved_at = timestamp
        incident.resolution_effective_at = effective_at
        incident.resolution_reason = data.reason
        session.flush()

        session.add(
            IncidentAuditEvent(
                report_id=report.id,
                incident_id=incident.id,
                revision_id=revision.id,
                actor_id=actor_id,
                action="incident_resolved",
                reason=data.reason,
                request_id=request_id,
                report_version=report.version,
                incident_version=incident.version,
                occurred_at=timestamp,
            )
        )
        session.flush()

        response = _response(incident, revision)

    return response
