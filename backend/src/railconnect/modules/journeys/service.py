from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

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

LOCAL_TIMEZONE = ZoneInfo("Asia/Colombo")


def search_journeys(
    session: Session,
    query: JourneySearchQuery,
) -> JourneyListResponse:
    departure_station = get_active_station(session, query.departure_station_id)
    arrival_station = get_active_station(session, query.arrival_station_id)

    if departure_station is None or arrival_station is None:
        raise InvalidStationSelectionError("Both selected stations must exist and be active.")

    departure_response = StationResponse.model_validate(departure_station)
    arrival_response = StationResponse.model_validate(arrival_station)
    candidates = list_journey_candidates(
        session,
        query.departure_station_id,
        query.arrival_station_id,
        query.travel_date,
    )

    journeys: list[JourneyResponse] = []

    for candidate in candidates:
        service = candidate.service
        starting_ordinal = query.travel_date.toordinal() - candidate.departure_minutes // 1440

        if starting_ordinal < 1:
            continue

        starting_date = date.fromordinal(starting_ordinal)

        if not service.valid_from <= starting_date <= service.valid_until:
            continue

        weekday_flag = 1 << starting_date.weekday()
        if service.operating_days & weekday_flag == 0:
            continue

        duration_minutes = candidate.arrival_minutes - candidate.departure_minutes

        try:
            departure_at = datetime.combine(
                query.travel_date,
                time.min,
                tzinfo=LOCAL_TIMEZONE,
            ) + timedelta(minutes=candidate.departure_minutes % 1440)
            arrival_at = departure_at + timedelta(minutes=duration_minutes)
        except OverflowError:
            continue

        journeys.append(
            JourneyResponse(
                service_id=service.id,
                service_code=service.code,
                service_name=service.name,
                source_ref=service.source_ref,
                departure_station=departure_response,
                arrival_station=arrival_response,
                departure_at=departure_at,
                arrival_at=arrival_at,
                duration_minutes=duration_minutes,
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
