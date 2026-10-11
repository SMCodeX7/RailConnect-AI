from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from railconnect.modules.stations.models import Station
from railconnect.modules.timetable.models.service_stop import ServiceStop
from railconnect.modules.timetable.models.train_service import TrainService


@dataclass(frozen=True)
class JourneyCandidate:
    service: TrainService
    departure_minutes: int
    arrival_minutes: int


def get_active_station(session: Session, station_id: UUID) -> Station | None:
    return session.scalar(
        select(Station).where(
            Station.id == station_id,
            Station.is_active.is_(True),
        )
    )


def list_journey_candidates(
    session: Session,
    departure_station_id: UUID,
    arrival_station_id: UUID,
    travel_date: date,
) -> list[JourneyCandidate]:
    departure_stop = aliased(ServiceStop)
    arrival_stop = aliased(ServiceStop)
    earliest_start = date.fromordinal(max(1, travel_date.toordinal() - 2))

    statement = (
        select(
            TrainService,
            departure_stop.departure_minutes,
            arrival_stop.arrival_minutes,
        )
        .join(departure_stop, departure_stop.service_id == TrainService.id)
        .join(arrival_stop, arrival_stop.service_id == TrainService.id)
        .where(
            TrainService.is_active.is_(True),
            TrainService.valid_from <= travel_date,
            TrainService.valid_until >= earliest_start,
            departure_stop.station_id == departure_station_id,
            arrival_stop.station_id == arrival_station_id,
            departure_stop.stop_sequence < arrival_stop.stop_sequence,
            departure_stop.departure_minutes.is_not(None),
            arrival_stop.arrival_minutes.is_not(None),
            arrival_stop.arrival_minutes > departure_stop.departure_minutes,
        )
    )

    candidates: list[JourneyCandidate] = []

    for service, departure_minutes, arrival_minutes in session.execute(statement):
        if departure_minutes is None or arrival_minutes is None:
            continue

        candidates.append(
            JourneyCandidate(
                service=service,
                departure_minutes=departure_minutes,
                arrival_minutes=arrival_minutes,
            )
        )

    return candidates
