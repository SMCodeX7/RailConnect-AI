from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from railconnect.modules.incidents.models.incident import Incident
from railconnect.modules.incidents.models.incident_report import IncidentReport
from railconnect.modules.incidents.models.incident_revision import IncidentRevision


def get_incident_for_change(
    session: Session,
    incident_id: UUID,
) -> Incident | None:
    return session.scalar(
        select(Incident)
        .where(Incident.id == incident_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def get_current_revision(
    session: Session,
    incident: Incident,
) -> IncidentRevision | None:
    return session.scalar(
        select(IncidentRevision).where(
            IncidentRevision.incident_id == incident.id,
            IncidentRevision.revision_number == incident.current_revision_number,
        )
    )


def get_originating_report(
    session: Session,
    incident: Incident,
) -> IncidentReport | None:
    return session.scalar(
        select(IncidentReport)
        .where(IncidentReport.id == incident.originating_report_id)
        .execution_options(populate_existing=True)
    )
