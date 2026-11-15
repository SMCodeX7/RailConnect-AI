from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from railconnect.modules.journeys.disruption_effects import (
    ApprovedJourneyEffect,
    ScheduledLeg,
    estimated_time,
    evaluate_segment_disruption,
)

RUN_ID = UUID(int=1)
START = datetime(2026, 11, 15, 23, 30, tzinfo=UTC)
LEGS = [
    ScheduledLeg(1, 2, START, START + timedelta(minutes=20)),
    ScheduledLeg(2, 3, START + timedelta(minutes=25), START + timedelta(minutes=45)),
    ScheduledLeg(3, 4, START + timedelta(minutes=50), START + timedelta(minutes=70)),
]


def approved_delay() -> ApprovedJourneyEffect:
    return ApprovedJourneyEffect(
        incident_id=UUID(int=2),
        revision_id=UUID(int=3),
        run_id=RUN_ID,
        impact_kind="delay",
        departure_stop_sequence=1,
        arrival_stop_sequence=2,
        effective_from=START,
        effective_until=START + timedelta(minutes=20),
        resolution_effective_at=None,
        estimated_delay_minutes=20,
    )


def test_delay_propagates_to_passengers_boarding_downstream() -> None:
    effect = approved_delay()

    result = evaluate_segment_disruption(RUN_ID, LEGS, 3, 4, [effect])

    assert result.departure_delay_minutes == 20
    assert result.arrival_delay_minutes == 20
    assert result.effects == (effect,)
    assert estimated_time(LEGS[2].arrival_at, result.arrival_delay_minutes) == (
        START + timedelta(minutes=90)
    )


def test_delay_first_encountered_on_leg_changes_arrival_estimate() -> None:
    result = evaluate_segment_disruption(RUN_ID, LEGS, 1, 2, [approved_delay()])

    assert result.departure_delay_minutes == 0
    assert result.arrival_delay_minutes == 20
    assert estimated_time(LEGS[0].departure_at, result.departure_delay_minutes) is None


def test_overlapping_delays_use_largest_estimate() -> None:
    first = approved_delay()
    second = replace(
        first,
        incident_id=UUID(int=4),
        revision_id=UUID(int=5),
        estimated_delay_minutes=35,
    )

    result = evaluate_segment_disruption(RUN_ID, LEGS, 1, 3, [second, first])

    assert result.arrival_delay_minutes == 35
    assert result.effects == (first, second)


def test_restriction_applies_only_to_overlapping_passenger_segment() -> None:
    restriction = replace(
        approved_delay(),
        impact_kind="restriction",
        departure_stop_sequence=2,
        arrival_stop_sequence=3,
        effective_until=START + timedelta(hours=1),
        estimated_delay_minutes=None,
    )

    first_leg = evaluate_segment_disruption(RUN_ID, LEGS, 1, 2, [restriction])
    crossing = evaluate_segment_disruption(RUN_ID, LEGS, 1, 3, [restriction])
    last_leg = evaluate_segment_disruption(RUN_ID, LEGS, 3, 4, [restriction])

    assert not first_leg.restricted
    assert crossing.restricted
    assert crossing.effects == (restriction,)
    assert not last_leg.restricted


def test_other_run_effect_is_ignored() -> None:
    unrelated = replace(approved_delay(), run_id=UUID(int=6))

    result = evaluate_segment_disruption(RUN_ID, LEGS, 1, 4, [unrelated])

    assert result.effects == ()
    assert result.arrival_delay_minutes == 0


@pytest.mark.parametrize("resolved", [False, True])
def test_end_at_boarding_time_does_not_block_boarding(resolved: bool) -> None:
    boarding = LEGS[1].departure_at
    cancellation = replace(
        approved_delay(),
        impact_kind="cancellation",
        departure_stop_sequence=None,
        arrival_stop_sequence=None,
        effective_until=START + timedelta(hours=2) if resolved else boarding,
        resolution_effective_at=boarding if resolved else None,
        estimated_delay_minutes=None,
    )

    earlier_segment = evaluate_segment_disruption(RUN_ID, LEGS, 1, 2, [cancellation])
    later_segment = evaluate_segment_disruption(RUN_ID, LEGS, 2, 3, [cancellation])

    assert earlier_segment.cancelled
    assert not later_segment.cancelled
    assert later_segment.effects == ()


def test_effect_window_can_overlap_an_overnight_leg() -> None:
    effect = replace(
        approved_delay(),
        departure_stop_sequence=2,
        arrival_stop_sequence=3,
        effective_from=START + timedelta(minutes=30),
        effective_until=START + timedelta(minutes=40),
    )

    result = evaluate_segment_disruption(RUN_ID, LEGS, 2, 3, [effect])

    assert LEGS[1].departure_at.date() < LEGS[1].arrival_at.date()
    assert result.departure_delay_minutes == 0
    assert result.arrival_delay_minutes == 20
