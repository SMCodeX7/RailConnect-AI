import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from railconnect.modules.stations.models import Station
from railconnect.modules.timetable.models.service_stop import ServiceStop
from railconnect.modules.timetable.models.train_service import TrainService
from railconnect.modules.timetable.seed_schemas import DemoTimetableDataset
from railconnect.modules.timetable.seeding import seed_timetable


def test_seed_is_repeatable(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database

    first = seed_timetable(session, dataset)
    second = seed_timetable(session, dataset)

    assert first.inserted_services == 2
    assert first.inserted_stops == 6
    assert first.existing_services == 0
    assert second.inserted_services == 0
    assert second.inserted_stops == 0
    assert second.existing_services == 2


def test_rejects_missing_station(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    code = dataset.services[0].stops[1].station_code
    session.execute(delete(Station).where(Station.code == code))

    with pytest.raises(ValueError, match="Missing stations"):
        seed_timetable(session, dataset)


def test_rejects_inactive_station(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    code = dataset.services[0].stops[1].station_code
    station = session.scalar(select(Station).where(Station.code == code))
    assert station is not None

    station.is_active = False
    session.flush()

    with pytest.raises(ValueError, match="Inactive stations"):
        seed_timetable(session, dataset)


def test_rejects_changed_service(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    seed_timetable(session, dataset)

    service = session.scalar(
        select(TrainService).where(TrainService.code == dataset.services[0].code)
    )
    assert service is not None

    service.name = "Changed Service Name"
    session.flush()

    with pytest.raises(ValueError, match="Existing service differs"):
        seed_timetable(session, dataset)


def test_rejects_changed_stops(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    seed_timetable(session, dataset)

    stop = session.scalar(
        select(ServiceStop)
        .join(TrainService, TrainService.id == ServiceStop.service_id)
        .where(
            TrainService.code == dataset.services[0].code,
            ServiceStop.stop_sequence == 2,
        )
    )
    assert stop is not None

    stop.arrival_minutes = 661
    session.flush()

    with pytest.raises(ValueError, match="Existing stops differ"):
        seed_timetable(session, dataset)


def test_failure_rolls_back_preceding_service_insert(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    conflicting = dataset.services[1]

    session.add(
        TrainService(
            code=conflicting.code,
            name="Conflicting Existing Service",
            source_ref=dataset.source_ref,
            operating_days=conflicting.operating_days,
            valid_from=dataset.valid_from,
            valid_until=dataset.valid_until,
            is_active=True,
        )
    )
    session.flush()

    with pytest.raises(ValueError, match="Existing service differs"):
        with session.begin_nested():
            seed_timetable(session, dataset)

    first_service = session.scalar(
        select(TrainService).where(TrainService.code == dataset.services[0].code)
    )
    assert first_service is None

    retained_service = session.scalar(
        select(TrainService).where(TrainService.code == conflicting.code)
    )
    assert retained_service is not None
    assert retained_service.name == "Conflicting Existing Service"
