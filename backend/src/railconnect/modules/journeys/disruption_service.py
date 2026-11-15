from collections import defaultdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from railconnect.modules.journeys.disruption_effects import (
    ApprovedJourneyEffect,
    ScheduledLeg,
    estimated_time,
    evaluate_segment_disruption,
)
from railconnect.modules.journeys.disruption_repository import list_approved_journey_effects
from railconnect.modules.journeys.schemas import JourneyDisruptionResponse, JourneyEffectReference
from railconnect.modules.timetable.models.run_stop import RunStop


class JourneyDisruptions:
    def __init__(self, session: Session, run_ids: set[UUID]) -> None:
        self._effects: dict[UUID, list[ApprovedJourneyEffect]] = defaultdict(list)
        self._legs: dict[UUID, list[ScheduledLeg]] = defaultdict(list)

        for effect in list_approved_journey_effects(session, run_ids):
            self._effects[effect.run_id].append(effect)

        if not self._effects:
            return

        stops_by_run: dict[UUID, list[RunStop]] = defaultdict(list)
        statement = (
            select(RunStop)
            .where(RunStop.run_id.in_(self._effects.keys()))
            .order_by(RunStop.run_id, RunStop.stop_sequence)
        )
        for stop in session.scalars(statement):
            stops_by_run[stop.run_id].append(stop)

        for run_id, stops in stops_by_run.items():
            for previous, following in zip(stops, stops[1:], strict=False):
                departure = previous.scheduled_departure_at
                arrival = following.scheduled_arrival_at
                if departure is not None and arrival is not None and departure < arrival:
                    self._legs[run_id].append(
                        ScheduledLeg(
                            previous.stop_sequence,
                            following.stop_sequence,
                            departure,
                            arrival,
                        )
                    )

    def for_segment(
        self,
        run_id: UUID,
        departure_sequence: int,
        arrival_sequence: int,
        scheduled_departure: datetime,
        scheduled_arrival: datetime,
    ) -> JourneyDisruptionResponse | None:
        effects = self._effects.get(run_id)
        if not effects:
            return None

        result = evaluate_segment_disruption(
            run_id,
            self._legs[run_id],
            departure_sequence,
            arrival_sequence,
            effects,
        )
        if not result.effects:
            return None

        blocked = result.cancelled or result.restricted
        return JourneyDisruptionResponse(
            cancelled=result.cancelled,
            restricted=result.restricted,
            estimated_departure_at=(
                None
                if blocked
                else estimated_time(scheduled_departure, result.departure_delay_minutes)
            ),
            estimated_arrival_at=(
                None if blocked else estimated_time(scheduled_arrival, result.arrival_delay_minutes)
            ),
            effects=[
                JourneyEffectReference(
                    incident_id=effect.incident_id,
                    revision_id=effect.revision_id,
                    impact_kind=effect.impact_kind,
                )
                for effect in result.effects
            ],
        )
