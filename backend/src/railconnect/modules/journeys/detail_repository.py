from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from railconnect.modules.stations.models import Station
from railconnect.modules.timetable.models.run_stop import RunStop
from railconnect.modules.timetable.models.service_run import ServiceRun
from railconnect.modules.timetable.models.train_service import TrainService


@dataclass(frozen=True)
class JourneyRun:
    run: ServiceRun
    service: TrainService


def get_journey_run(session: Session, run_id: UUID) -> JourneyRun | None:
    row = session.execute(
        select(ServiceRun, TrainService)
        .join(TrainService, TrainService.id == ServiceRun.service_id)
        .where(
            ServiceRun.id == run_id,
            TrainService.is_active.is_(True),
        )
    ).one_or_none()

    if row is None:
        return None

    run, service = row
    return JourneyRun(run=run, service=service)


def list_journey_stops(
    session: Session,
    run_id: UUID,
) -> list[tuple[RunStop, Station]]:
    rows = session.execute(
        select(RunStop, Station)
        .join(Station, Station.id == RunStop.station_id)
        .where(RunStop.run_id == run_id)
        .order_by(RunStop.stop_sequence)
    )

    return [(stop, station) for stop, station in rows]
