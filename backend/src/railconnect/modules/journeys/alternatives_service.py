from uuid import UUID

from sqlalchemy.orm import Session

from railconnect.modules.journeys.detail_service import get_journey_detail
from railconnect.modules.journeys.errors import JourneyDataUnavailableError
from railconnect.modules.journeys.schemas import (
    JourneyAlternativesQuery,
    JourneyAlternativesResponse,
    JourneySearchQuery,
)
from railconnect.modules.journeys.service import search_journeys

ALTERNATIVE_LIMIT = 5


def find_journey_alternatives(
    session: Session,
    run_id: UUID,
    query: JourneyAlternativesQuery,
) -> JourneyAlternativesResponse:
    detail = get_journey_detail(session, run_id, query)
    segment = detail.selected_segment
    if segment is None:
        raise JourneyDataUnavailableError("The original journey segment is unavailable.")

    search = search_journeys(
        session,
        JourneySearchQuery(
            departure_station_id=segment.departure_station.id,
            arrival_station_id=segment.arrival_station.id,
            travel_date=segment.scheduled_departure_at.date(),
            arrive_before=query.arrive_before,
            arrival_date=query.arrival_date,
            limit=ALTERNATIVE_LIMIT,
        ),
        exclude_run_id=run_id,
        earliest_departure=segment.scheduled_departure_at,
    )

    if search.items:
        explanation = (
            "These prepared direct services depart at or after the original boarding time "
            "and meet the search criteria."
        )
    else:
        explanation = "No prepared direct alternative meets these criteria."

    return JourneyAlternativesResponse(
        original_run_id=run_id,
        items=search.items,
        total=search.total,
        explanation=explanation,
    )
