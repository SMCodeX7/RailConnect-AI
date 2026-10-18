from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from railconnect.modules.incidents.models.incident import Incident
from railconnect.modules.incidents.models.incident_report import IncidentReport
from railconnect.modules.incidents.models.incident_revision import IncidentRevision
from railconnect.modules.timetable.models.service_run import ServiceRun


def approved_incident_rows() -> Select[
    Incident,
    IncidentRevision,
    ServiceRun,
]:
    return (
        select(Incident, IncidentRevision, ServiceRun)
        .join(
            IncidentRevision,
            (IncidentRevision.incident_id == Incident.id)
            & (IncidentRevision.revision_number == Incident.current_revision_number),
        )
        .join(
            IncidentReport,
            IncidentReport.id == Incident.originating_report_id,
        )
        .join(
            ServiceRun,
            ServiceRun.id == IncidentRevision.run_id,
        )
        .where(
            IncidentReport.status == "verified",
            Incident.status.in_(("active", "resolved")),
        )
    )


def find_public_incident(
    session: Session,
    incident_id: UUID,
) -> tuple[Incident, IncidentRevision, ServiceRun] | None:
    row = session.execute(approved_incident_rows().where(Incident.id == incident_id)).one_or_none()

    if row is None:
        return None

    incident, revision, run = row
    return incident, revision, run
