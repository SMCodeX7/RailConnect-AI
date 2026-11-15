from datetime import UTC, datetime, time
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from railconnect.modules.journeys.disruption_service import JourneyDisruptions
from railconnect.modules.journeys.errors import InvalidStationSelectionError
from railconnect.modules.journeys.repository import (
    get_active_station,
    list_journey_candidates,
)
from railconnect.modules.journeys.schemas import (
    JourneyListResponse,
    JourneyResponse,
    JourneySearchQuery,
)
from railconnect.modules.stations.schemas import StationResponse
from railconnect.modules.timetable.source_repository import get_source_records
from railconnect.modules.timetable.source_schemas import TimetableSourceResponse

LOCAL_TIMEZONE = ZoneInfo("Asia/Colombo")


def search_journeys(
    session: Session,
    query: JourneySearchQuery,
    *,
    exclude_run_id: UUID | None = None,
    earliest_departure: datetime | None = None,
) -> JourneyListResponse:
    departure_station = get_active_station(session, query.departure_station_id)
    arrival_station = get_active_station(session, query.arrival_station_id)

    if departure_station is None or arrival_station is None:
        raise InvalidStationSelectionError("Both selected stations must exist and be active.")

    departure_response = StationResponse.model_validate(departure_station)
    arrival_response = StationResponse.model_validate(arrival_station)
    journeys: list[JourneyResponse] = []

    try:
        departure_from = datetime.combine(
            query.travel_date,
            time.min,
            tzinfo=LOCAL_TIMEZONE,
        ).astimezone(UTC)
        departure_until = datetime.combine(
            query.travel_date,
            time.max,
            tzinfo=LOCAL_TIMEZONE,
        ).astimezone(UTC)

        arrival_deadline = (
            datetime.combine(
                query.arrival_date or query.travel_date,
                query.arrive_before,
                tzinfo=LOCAL_TIMEZONE,
            ).astimezone(UTC)
            if query.arrive_before is not None
            else None
        )
    except (OverflowError, ValueError):
        return JourneyListResponse(
            departure_station_id=query.departure_station_id,
            arrival_station_id=query.arrival_station_id,
            travel_date=query.travel_date,
            items=[],
            total=0,
            limit=query.limit,
            offset=query.offset,
        )

    candidates = list_journey_candidates(
        session,
        query.departure_station_id,
        query.arrival_station_id,
        departure_from,
        departure_until,
    )

    if exclude_run_id is not None:
        candidates = [
            candidate
            for candidate in candidates
            if candidate.run.id != exclude_run_id and candidate.run.status == "scheduled"
        ]

    disruptions = JourneyDisruptions(session, {candidate.run.id for candidate in candidates})
    sources = get_source_records(
        session,
        {candidate.run.source_ref for candidate in candidates},
    )

    for candidate in candidates:
        departure = candidate.departure_stop.scheduled_departure_at
        arrival = candidate.arrival_stop.scheduled_arrival_at

        if departure is None or arrival is None:
            continue

        departure_local = departure.astimezone(LOCAL_TIMEZONE)
        arrival_local = arrival.astimezone(LOCAL_TIMEZONE)
        disruption = disruptions.for_segment(
            candidate.run.id,
            candidate.departure_stop.stop_sequence,
            candidate.arrival_stop.stop_sequence,
            departure_local,
            arrival_local,
        )

        if disruption is not None and (disruption.cancelled or disruption.restricted):
            continue

        effective_departure = (
            disruption.estimated_departure_at
            if disruption is not None and disruption.estimated_departure_at is not None
            else departure
        )
        if earliest_departure is not None and effective_departure < earliest_departure:
            continue

        deadline_arrival = (
            disruption.estimated_arrival_at
            if disruption is not None and disruption.estimated_arrival_at is not None
            else arrival
        )
        if arrival_deadline is not None and deadline_arrival > arrival_deadline:
            continue

        status: Literal["scheduled", "restricted"]
        if candidate.run.status == "scheduled":
            status = "scheduled"
        elif candidate.run.status == "restricted":
            status = "restricted"
        else:
            continue

        duration_minutes = int((arrival - departure).total_seconds() // 60)

        journeys.append(
            JourneyResponse(
                run_id=candidate.run.id,
                service_date=candidate.run.service_date,
                run_version=candidate.run.version,
                run_status=status,
                departure_stop_sequence=candidate.departure_stop.stop_sequence,
                arrival_stop_sequence=candidate.arrival_stop.stop_sequence,
                service_id=candidate.service.id,
                service_code=candidate.service.code,
                service_name=candidate.service.name,
                source_ref=candidate.run.source_ref,
                source=(
                    TimetableSourceResponse.model_validate(sources[candidate.run.source_ref])
                    if candidate.run.source_ref in sources
                    else None
                ),
                departure_station=departure_response,
                arrival_station=arrival_response,
                departure_at=departure_local,
                arrival_at=arrival_local,
                duration_minutes=duration_minutes,
                disruption=disruption,
            )
        )

    journeys.sort(
        key=lambda journey: (
            journey.departure_at,
            journey.arrival_at,
            journey.service_code,
        )
    )

    return JourneyListResponse(
        departure_station_id=query.departure_station_id,
        arrival_station_id=query.arrival_station_id,
        travel_date=query.travel_date,
        items=journeys[query.offset : query.offset + query.limit],
        total=len(journeys),
        limit=query.limit,
        offset=query.offset,
    )
