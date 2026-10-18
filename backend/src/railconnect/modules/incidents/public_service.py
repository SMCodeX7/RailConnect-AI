from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from railconnect.modules.incidents.errors import IncidentNotFoundError
from railconnect.modules.incidents.models.incident import Incident
from railconnect.modules.incidents.models.incident_revision import IncidentRevision
from railconnect.modules.incidents.public_repository import (
    approved_incident_rows,
    find_public_incident,
)
from railconnect.modules.incidents.public_schemas import (
    PublicIncidentListResponse,
    PublicIncidentQuery,
    PublicIncidentResponse,
)
from railconnect.modules.timetable.models.service_run import ServiceRun


def _public_response(
    incident: Incident,
    revision: IncidentRevision,
    run: ServiceRun,
) -> PublicIncidentResponse:
    return PublicIncidentResponse.model_validate(
        {
            "incident_id": incident.id,
            "incident_version": incident.version,
            "revision_id": revision.id,
            "revision_number": revision.revision_number,
            "status": incident.status,
            "run_id": revision.run_id,
            "timetable_source_ref": run.source_ref,
            "scope_kind": revision.scope_kind,
            "departure_stop_sequence": revision.departure_stop_sequence,
            "arrival_stop_sequence": revision.arrival_stop_sequence,
            "impact_kind": revision.impact_kind,
            "estimated_delay_minutes": revision.estimated_delay_minutes,
            "effective_from": revision.effective_from,
            "effective_until": revision.effective_until,
            "public_summary": revision.public_summary,
            "verified_at": revision.verified_at,
            "resolution_effective_at": incident.resolution_effective_at,
        }
    )


def get_public_incident(
    session: Session,
    incident_id: UUID,
) -> PublicIncidentResponse:
    row = find_public_incident(session, incident_id)

    if row is None:
        raise IncidentNotFoundError("The incident was not found.")

    return _public_response(*row)


def list_public_incidents(
    session: Session,
    query: PublicIncidentQuery,
) -> PublicIncidentListResponse:
    statement = approved_incident_rows().where(IncidentRevision.run_id == query.run_id)

    total = session.scalar(select(func.count()).select_from(statement.subquery()))
    assert total is not None

    rows = session.execute(
        statement.order_by(
            IncidentRevision.effective_from,
            Incident.id,
        )
        .limit(query.limit)
        .offset(query.offset)
    ).all()

    return PublicIncidentListResponse(
        items=[_public_response(incident, revision, run) for incident, revision, run in rows],
        total=total,
        limit=query.limit,
        offset=query.offset,
    )
