from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from railconnect.modules.journeys.detail_repository import (
    get_journey_run,
    list_journey_stops,
)
from railconnect.modules.journeys.errors import (
    JourneyDataUnavailableError,
    JourneyNotFoundError,
)
from railconnect.modules.journeys.schemas import (
    JourneyDetailQuery,
    JourneyDetailResponse,
    JourneySegmentResponse,
    JourneyStopResponse,
)
from railconnect.modules.stations.schemas import StationResponse

LOCAL_TIMEZONE = ZoneInfo("Asia/Colombo")


def get_journey_detail(
    session: Session,
    run_id: UUID,
    query: JourneyDetailQuery,
) -> JourneyDetailResponse:
    journey = get_journey_run(session, run_id)
    if journey is None:
        raise JourneyNotFoundError("The journey run was not found.")

    rows = list_journey_stops(session, run_id)
    if len(rows) < 2:
        raise JourneyDataUnavailableError("The run schedule is incomplete.")

    stops = [
        JourneyStopResponse(
            stop_sequence=stop.stop_sequence,
            station=StationResponse.model_validate(station),
            scheduled_arrival_at=(
                stop.scheduled_arrival_at.astimezone(LOCAL_TIMEZONE)
                if stop.scheduled_arrival_at is not None
                else None
            ),
            scheduled_departure_at=(
                stop.scheduled_departure_at.astimezone(LOCAL_TIMEZONE)
                if stop.scheduled_departure_at is not None
                else None
            ),
            pickup_allowed=stop.pickup_allowed,
            dropoff_allowed=stop.dropoff_allowed,
        )
        for stop, station in rows
    ]

    segment = None
    if query.departure_stop_sequence is not None:
        by_sequence = {stop.stop_sequence: stop for stop in stops}
        departure = by_sequence.get(query.departure_stop_sequence)
        arrival = by_sequence.get(query.arrival_stop_sequence or 0)

        if departure is None or arrival is None:
            raise JourneyNotFoundError("The requested segment was not found.")

        if (
            not departure.station.is_active
            or not arrival.station.is_active
            or not departure.pickup_allowed
            or not arrival.dropoff_allowed
        ):
            raise JourneyNotFoundError("The requested passenger segment is unavailable.")

        departure_at = departure.scheduled_departure_at
        arrival_at = arrival.scheduled_arrival_at

        if departure_at is None or arrival_at is None or arrival_at <= departure_at:
            raise JourneyDataUnavailableError("The segment schedule is invalid.")

        segment = JourneySegmentResponse(
            departure_stop_sequence=departure.stop_sequence,
            arrival_stop_sequence=arrival.stop_sequence,
            departure_station=departure.station,
            arrival_station=arrival.station,
            scheduled_departure_at=departure_at,
            scheduled_arrival_at=arrival_at,
            duration_minutes=int((arrival_at - departure_at).total_seconds() // 60),
        )

    status: Literal["scheduled", "cancelled", "restricted"]
    if journey.run.status == "scheduled":
        status = "scheduled"
    elif journey.run.status == "cancelled":
        status = "cancelled"
    elif journey.run.status == "restricted":
        status = "restricted"
    else:
        raise JourneyDataUnavailableError("The run status is invalid.")

    return JourneyDetailResponse(
        run_id=journey.run.id,
        service_id=journey.service.id,
        service_code=journey.service.code,
        service_name=journey.service.name,
        service_date=journey.run.service_date,
        run_version=journey.run.version,
        run_status=status,
        source_ref=journey.run.source_ref,
        stops=stops,
        selected_segment=segment,
    )
