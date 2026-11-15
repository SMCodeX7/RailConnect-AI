from typing import cast
from uuid import UUID

from sqlalchemy.orm import Session

from railconnect.modules.incidents.models.incident_revision import IncidentRevision
from railconnect.modules.incidents.public_repository import approved_incident_rows
from railconnect.modules.journeys.disruption_effects import ApprovedJourneyEffect, ImpactKind


def list_approved_journey_effects(
    session: Session,
    run_ids: set[UUID],
) -> list[ApprovedJourneyEffect]:
    if not run_ids:
        return []

    statement = approved_incident_rows().where(IncidentRevision.run_id.in_(run_ids))

    return [
        ApprovedJourneyEffect(
            incident_id=incident.id,
            revision_id=revision.id,
            run_id=revision.run_id,
            impact_kind=cast(ImpactKind, revision.impact_kind),
            departure_stop_sequence=revision.departure_stop_sequence,
            arrival_stop_sequence=revision.arrival_stop_sequence,
            effective_from=revision.effective_from,
            effective_until=revision.effective_until,
            resolution_effective_at=incident.resolution_effective_at,
            estimated_delay_minutes=revision.estimated_delay_minutes,
        )
        for incident, revision, _ in session.execute(statement)
    ]
