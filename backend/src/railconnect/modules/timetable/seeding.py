from dataclasses import dataclass
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from railconnect.modules.stations.models import Station
from railconnect.modules.timetable.models.service_stop import ServiceStop
from railconnect.modules.timetable.models.train_service import TrainService
from railconnect.modules.timetable.seed_schemas import DemoService, DemoTimetableDataset


@dataclass(frozen=True)
class SeedResult:
    inserted_services: int
    existing_services: int
    inserted_stops: int


def verify_existing_service(
    session: Session,
    service: TrainService,
    expected: DemoService,
    dataset: DemoTimetableDataset,
    station_ids: dict[str, UUID],
) -> None:
    actual_details = (
        service.name,
        service.source_ref,
        service.operating_days,
        service.valid_from,
        service.valid_until,
        service.is_active,
    )
    expected_details = (
        expected.name,
        dataset.source_ref,
        expected.operating_days,
        dataset.valid_from,
        dataset.valid_until,
        True,
    )

    if actual_details != expected_details:
        raise ValueError(f"Existing service differs from demo dataset: {expected.code}")

    stops = session.scalars(
        select(ServiceStop)
        .where(ServiceStop.service_id == service.id)
        .order_by(ServiceStop.stop_sequence)
    ).all()

    actual_stops = [
        (
            stop.stop_sequence,
            stop.station_id,
            stop.arrival_minutes,
            stop.departure_minutes,
            stop.pickup_allowed,
            stop.dropoff_allowed,
        )
        for stop in stops
    ]
    expected_stops = [
        (
            sequence,
            station_ids[stop.station_code],
            stop.arrival_minutes,
            stop.departure_minutes,
            stop.pickup_allowed,
            stop.dropoff_allowed,
        )
        for sequence, stop in enumerate(expected.stops, start=1)
    ]

    if actual_stops != expected_stops:
        raise ValueError(f"Existing stops differ from demo dataset: {expected.code}")


def seed_timetable(
    session: Session,
    dataset: DemoTimetableDataset,
) -> SeedResult:
    required_codes = {stop.station_code for service in dataset.services for stop in service.stops}

    stations = session.scalars(select(Station).where(Station.code.in_(required_codes))).all()
    station_ids = {station.code: station.id for station in stations}
    missing_codes = required_codes - station_ids.keys()

    if missing_codes:
        raise ValueError(f"Missing stations: {', '.join(sorted(missing_codes))}")

    inactive_codes = sorted(station.code for station in stations if not station.is_active)
    if inactive_codes:
        raise ValueError(f"Inactive stations: {', '.join(inactive_codes)}")

    inserted_services = 0
    existing_services = 0
    inserted_stops = 0

    for expected in dataset.services:
        existing = session.scalar(
            select(TrainService).where(TrainService.code == expected.code).with_for_update()
        )

        if existing is not None:
            verify_existing_service(
                session,
                existing,
                expected,
                dataset,
                station_ids,
            )
            existing_services += 1
            continue

        service_id = uuid5(
            NAMESPACE_URL,
            f"railconnect:service:{expected.code}",
        )
        service = TrainService(
            id=service_id,
            code=expected.code,
            name=expected.name,
            source_ref=dataset.source_ref,
            operating_days=expected.operating_days,
            valid_from=dataset.valid_from,
            valid_until=dataset.valid_until,
            is_active=True,
        )
        session.add(service)
        session.flush()

        stops = [
            ServiceStop(
                id=uuid5(
                    NAMESPACE_URL,
                    f"railconnect:service-stop:{expected.code}:{sequence}",
                ),
                service_id=service_id,
                station_id=station_ids[stop.station_code],
                stop_sequence=sequence,
                arrival_minutes=stop.arrival_minutes,
                departure_minutes=stop.departure_minutes,
                pickup_allowed=stop.pickup_allowed,
                dropoff_allowed=stop.dropoff_allowed,
            )
            for sequence, stop in enumerate(expected.stops, start=1)
        ]
        session.add_all(stops)
        session.flush()

        inserted_services += 1
        inserted_stops += len(stops)

    return SeedResult(
        inserted_services=inserted_services,
        existing_services=existing_services,
        inserted_stops=inserted_stops,
    )
