from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import NAMESPACE_URL, UUID, uuid5
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from railconnect.modules.timetable.models.run_stop import RunStop
from railconnect.modules.timetable.models.service_run import ServiceRun
from railconnect.modules.timetable.models.service_stop import ServiceStop
from railconnect.modules.timetable.run_repository import (
    all_stations_active,
    get_service_for_update,
    get_service_run,
    list_run_stops,
    list_service_stops,
)

LOCAL_TIMEZONE = ZoneInfo("Asia/Colombo")


@dataclass(frozen=True)
class MaterializedRun:
    run: ServiceRun
    inserted: bool


@dataclass(frozen=True)
class ScheduledStop:
    station_id: UUID
    stop_sequence: int
    arrival_at: datetime | None
    departure_at: datetime | None
    pickup_allowed: bool
    dropoff_allowed: bool


def _scheduled_stops(
    service_date: date,
    stops: list[ServiceStop],
) -> list[ScheduledStop]:
    if len(stops) < 2:
        raise ValueError("A service requires at least two stops.")

    first = stops[0]
    last = stops[-1]

    if first.arrival_minutes is not None or first.departure_minutes is None:
        raise ValueError("The first stop requires only a departure time.")

    if first.departure_minutes >= 1440:
        raise ValueError("The service must start on its service date.")

    if last.arrival_minutes is None or last.departure_minutes is not None:
        raise ValueError("The final stop requires only an arrival time.")

    midnight = datetime.combine(service_date, time.min, tzinfo=LOCAL_TIMEZONE)
    scheduled: list[ScheduledStop] = []
    previous_departure: int | None = None
    previous_sequence = 0

    for index, stop in enumerate(stops):
        if stop.stop_sequence <= previous_sequence:
            raise ValueError("Stop sequences must increase.")

        if 0 < index < len(stops) - 1:
            if stop.arrival_minutes is None or stop.departure_minutes is None:
                raise ValueError("Intermediate stops require both times.")

        if (
            previous_departure is not None
            and stop.arrival_minutes is not None
            and stop.arrival_minutes <= previous_departure
        ):
            raise ValueError("Each arrival must follow the previous departure.")

        if (
            stop.arrival_minutes is not None
            and stop.departure_minutes is not None
            and stop.departure_minutes < stop.arrival_minutes
        ):
            raise ValueError("Departure cannot precede arrival.")

        if stop.pickup_allowed and stop.departure_minutes is None:
            raise ValueError("Boarding requires a departure time.")

        if stop.dropoff_allowed and stop.arrival_minutes is None:
            raise ValueError("Alighting requires an arrival time.")

        try:
            arrival = (
                (midnight + timedelta(minutes=stop.arrival_minutes)).astimezone(UTC)
                if stop.arrival_minutes is not None
                else None
            )
            departure = (
                (midnight + timedelta(minutes=stop.departure_minutes)).astimezone(UTC)
                if stop.departure_minutes is not None
                else None
            )
        except (OverflowError, ValueError) as error:
            raise ValueError("Stop timestamps fall outside the supported date range.") from error

        scheduled.append(
            ScheduledStop(
                station_id=stop.station_id,
                stop_sequence=stop.stop_sequence,
                arrival_at=arrival,
                departure_at=departure,
                pickup_allowed=stop.pickup_allowed,
                dropoff_allowed=stop.dropoff_allowed,
            )
        )
        previous_sequence = stop.stop_sequence
        if stop.departure_minutes is not None:
            previous_departure = stop.departure_minutes

    return scheduled


def materialize_service_run(
    session: Session,
    service_id: UUID,
    service_date: date,
) -> MaterializedRun:
    if not session.in_transaction():
        raise ValueError("Run materialization requires a caller-owned transaction.")

    service = get_service_for_update(session, service_id)
    if service is None or not service.is_active:
        raise ValueError("The service must exist and be active.")

    if not service.valid_from <= service_date <= service.valid_until:
        raise ValueError("The service date is outside its validity period.")

    if service.operating_days & (1 << service_date.weekday()) == 0:
        raise ValueError("The service does not operate on this date.")

    stops = list_service_stops(session, service.id)
    if not all_stations_active(session, {stop.station_id for stop in stops}):
        raise ValueError("All service stations must exist and be active.")

    scheduled = _scheduled_stops(service_date, stops)
    existing = get_service_run(session, service.id, service_date)

    if existing is not None:
        if existing.source_ref != service.source_ref:
            raise ValueError("Existing run source differs from the service.")

        actual = [
            ScheduledStop(
                station_id=stop.station_id,
                stop_sequence=stop.stop_sequence,
                arrival_at=stop.scheduled_arrival_at,
                departure_at=stop.scheduled_departure_at,
                pickup_allowed=stop.pickup_allowed,
                dropoff_allowed=stop.dropoff_allowed,
            )
            for stop in list_run_stops(session, existing.id)
        ]

        if actual != scheduled:
            raise ValueError("Existing run stops differ from the service schedule.")

        return MaterializedRun(run=existing, inserted=False)

    run_id = uuid5(
        NAMESPACE_URL,
        f"railconnect:service-run:{service.id}:{service_date.isoformat()}",
    )
    run = ServiceRun(
        id=run_id,
        service_id=service.id,
        service_date=service_date,
        source_ref=service.source_ref,
        status="scheduled",
        version=1,
    )
    session.add(run)
    session.flush()

    session.add_all(
        [
            RunStop(
                id=uuid5(
                    NAMESPACE_URL,
                    f"railconnect:run-stop:{run_id}:{stop.stop_sequence}",
                ),
                run_id=run_id,
                station_id=stop.station_id,
                stop_sequence=stop.stop_sequence,
                scheduled_arrival_at=stop.arrival_at,
                scheduled_departure_at=stop.departure_at,
                pickup_allowed=stop.pickup_allowed,
                dropoff_allowed=stop.dropoff_allowed,
            )
            for stop in scheduled
        ]
    )
    session.flush()

    return MaterializedRun(run=run, inserted=True)
