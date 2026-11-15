from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

ImpactKind = Literal["cancellation", "restriction", "delay"]


@dataclass(frozen=True)
class ScheduledLeg:
    departure_stop_sequence: int
    arrival_stop_sequence: int
    departure_at: datetime
    arrival_at: datetime


@dataclass(frozen=True)
class ApprovedJourneyEffect:
    incident_id: UUID
    revision_id: UUID
    run_id: UUID
    impact_kind: ImpactKind
    departure_stop_sequence: int | None
    arrival_stop_sequence: int | None
    effective_from: datetime
    effective_until: datetime
    resolution_effective_at: datetime | None
    estimated_delay_minutes: int | None


@dataclass(frozen=True)
class SegmentDisruption:
    cancelled: bool
    restricted: bool
    departure_delay_minutes: int
    arrival_delay_minutes: int
    effects: tuple[ApprovedJourneyEffect, ...]


def _matches_leg(effect: ApprovedJourneyEffect, leg: ScheduledLeg) -> bool:
    scope_start = effect.departure_stop_sequence
    scope_end = effect.arrival_stop_sequence

    if scope_start is not None and leg.arrival_stop_sequence <= scope_start:
        return False
    if scope_end is not None and leg.departure_stop_sequence >= scope_end:
        return False

    end = effect.effective_until
    if effect.resolution_effective_at is not None:
        end = min(end, effect.resolution_effective_at)

    return (
        effect.effective_from < end
        and leg.departure_at < end
        and effect.effective_from < leg.arrival_at
    )


def evaluate_segment_disruption(
    run_id: UUID,
    legs: list[ScheduledLeg],
    departure_stop_sequence: int,
    arrival_stop_sequence: int,
    effects: list[ApprovedJourneyEffect],
) -> SegmentDisruption:
    applicable_run_effects = [effect for effect in effects if effect.run_id == run_id]
    applied: dict[UUID, ApprovedJourneyEffect] = {}
    cancelled = False
    restricted = False
    departure_delay = 0
    downstream_delay = 0

    for leg in legs:
        if leg.departure_stop_sequence >= arrival_stop_sequence:
            break

        on_passenger_segment = leg.departure_stop_sequence >= departure_stop_sequence
        if leg.departure_stop_sequence == departure_stop_sequence:
            departure_delay = downstream_delay

        for effect in applicable_run_effects:
            if not _matches_leg(effect, leg):
                continue

            if effect.impact_kind == "delay":
                minutes = effect.estimated_delay_minutes
                if minutes is not None:
                    downstream_delay = max(downstream_delay, minutes)
                    applied[effect.incident_id] = effect
            elif on_passenger_segment:
                cancelled = cancelled or effect.impact_kind == "cancellation"
                restricted = restricted or effect.impact_kind == "restriction"
                applied[effect.incident_id] = effect

    return SegmentDisruption(
        cancelled=cancelled,
        restricted=restricted,
        departure_delay_minutes=departure_delay,
        arrival_delay_minutes=downstream_delay,
        effects=tuple(
            sorted(applied.values(), key=lambda effect: (effect.effective_from, effect.incident_id))
        ),
    )


def estimated_time(scheduled_at: datetime, delay_minutes: int) -> datetime | None:
    if delay_minutes == 0:
        return None

    return scheduled_at + timedelta(minutes=delay_minutes)
