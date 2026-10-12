from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from railconnect.modules.stations.models import Station
from railconnect.modules.timetable.models.run_stop import RunStop
from railconnect.modules.timetable.models.service_run import ServiceRun
from railconnect.modules.timetable.models.train_service import TrainService


@dataclass(frozen=True)
class JourneyCandidate:
    service: TrainService
    run: ServiceRun
    departure_stop: RunStop
    arrival_stop: RunStop


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
    departure_from: datetime,
    departure_until: datetime,
) -> list[JourneyCandidate]:
    departure_stop = aliased(RunStop)
    arrival_stop = aliased(RunStop)

    statement = (
        select(TrainService, ServiceRun, departure_stop, arrival_stop)
        .join(ServiceRun, ServiceRun.service_id == TrainService.id)
        .join(departure_stop, departure_stop.run_id == ServiceRun.id)
        .join(arrival_stop, arrival_stop.run_id == ServiceRun.id)
        .where(
            TrainService.is_active.is_(True),
            ServiceRun.status.in_(("scheduled", "restricted")),
            departure_stop.station_id == departure_station_id,
            arrival_stop.station_id == arrival_station_id,
            departure_stop.stop_sequence < arrival_stop.stop_sequence,
            departure_stop.pickup_allowed.is_(True),
            arrival_stop.dropoff_allowed.is_(True),
            departure_stop.scheduled_departure_at.is_not(None),
            arrival_stop.scheduled_arrival_at.is_not(None),
            departure_stop.scheduled_departure_at >= departure_from,
            departure_stop.scheduled_departure_at <= departure_until,
            arrival_stop.scheduled_arrival_at > departure_stop.scheduled_departure_at,
        )
    )

    return [
        JourneyCandidate(
            service=service,
            run=run,
            departure_stop=departure,
            arrival_stop=arrival,
        )
        for service, run, departure, arrival in session.execute(statement)
    ]
