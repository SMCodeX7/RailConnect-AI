from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from railconnect.modules.stations.models import Station
from railconnect.modules.timetable.models.run_stop import RunStop
from railconnect.modules.timetable.models.service_run import ServiceRun
from railconnect.modules.timetable.models.service_stop import ServiceStop
from railconnect.modules.timetable.models.train_service import TrainService


def get_service_for_update(
    session: Session,
    service_id: UUID,
) -> TrainService | None:
    return session.scalar(
        select(TrainService).where(TrainService.id == service_id).with_for_update()
    )


def list_service_stops(
    session: Session,
    service_id: UUID,
) -> list[ServiceStop]:
    return list(
        session.scalars(
            select(ServiceStop)
            .where(ServiceStop.service_id == service_id)
            .order_by(ServiceStop.stop_sequence)
        )
    )


def all_stations_active(
    session: Session,
    station_ids: set[UUID],
) -> bool:
    active_ids = set(
        session.scalars(
            select(Station.id).where(
                Station.id.in_(station_ids),
                Station.is_active.is_(True),
            )
        )
    )
    return active_ids == station_ids


def get_service_run(
    session: Session,
    service_id: UUID,
    service_date: date,
) -> ServiceRun | None:
    return session.scalar(
        select(ServiceRun).where(
            ServiceRun.service_id == service_id,
            ServiceRun.service_date == service_date,
        )
    )


def list_run_stops(
    session: Session,
    run_id: UUID,
) -> list[RunStop]:
    return list(
        session.scalars(
            select(RunStop).where(RunStop.run_id == run_id).order_by(RunStop.stop_sequence)
        )
    )
