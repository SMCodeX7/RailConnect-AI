from datetime import date, time
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from railconnect.modules.journeys.errors import InvalidStationSelectionError
from railconnect.modules.journeys.schemas import JourneyListResponse, JourneySearchQuery
from railconnect.modules.journeys.service import search_journeys
from railconnect.modules.stations.models import Station
from railconnect.modules.timetable.models.run_stop import RunStop
from railconnect.modules.timetable.models.service_run import ServiceRun
from railconnect.modules.timetable.models.train_service import TrainService
from railconnect.modules.timetable.run_service import materialize_service_run
from railconnect.modules.timetable.seed_schemas import DemoTimetableDataset
from railconnect.modules.timetable.seeding import seed_timetable


def prepare_runs(
    session: Session,
    dataset: DemoTimetableDataset,
    dates: list[date],
) -> None:
    seed_timetable(session, dataset)
    codes = [service.code for service in dataset.services]
    services = list(session.scalars(select(TrainService).where(TrainService.code.in_(codes))))

    for service_date in dates:
        for service in services:
            if (
                service.valid_from <= service_date <= service.valid_until
                and service.operating_days & (1 << service_date.weekday())
            ):
                materialize_service_run(session, service.id, service_date)


@pytest.fixture
def journey_timetable(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> tuple[Session, DemoTimetableDataset]:
    session, dataset = timetable_database
    prepare_runs(session, dataset, [date(2026, 10, 11), date(2026, 10, 12)])
    return session, dataset


@pytest.fixture
def overnight_timetable(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> tuple[Session, DemoTimetableDataset]:
    session, dataset = timetable_database
    data = dataset.model_dump()
    service = data["services"][0]

    service["operating_days"] = 1
    service["stops"][0]["departure_minutes"] = 1260
    service["stops"][1]["arrival_minutes"] = 1660
    service["stops"][1]["departure_minutes"] = 1665
    service["stops"][2]["arrival_minutes"] = 1800

    data["services"] = [service]
    data["valid_from"] = date(2026, 10, 12)
    data["valid_until"] = date(2026, 10, 19)

    overnight = DemoTimetableDataset.model_validate(data)
    prepare_runs(session, overnight, [date(2026, 10, 12), date(2026, 10, 19)])
    return session, overnight


def search(
    session: Session,
    dataset: DemoTimetableDataset,
    departure_index: int,
    arrival_index: int,
    travel_date: date,
    offset: int = 0,
) -> JourneyListResponse:
    stops = dataset.services[0].stops
    departure = session.scalar(
        select(Station).where(Station.code == stops[departure_index].station_code)
    )
    arrival = session.scalar(
        select(Station).where(Station.code == stops[arrival_index].station_code)
    )
    assert departure is not None
    assert arrival is not None

    return search_journeys(
        session,
        JourneySearchQuery(
            departure_station_id=departure.id,
            arrival_station_id=arrival.id,
            travel_date=travel_date,
            limit=1,
            offset=offset,
        ),
    )


def test_forward_journey(
    journey_timetable: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = journey_timetable
    result = search(session, dataset, 0, 2, date(2026, 10, 12))

    assert result.total == 1
    journey = result.items[0]
    assert journey.service_code == dataset.services[0].code
    assert journey.departure_at.isoformat() == "2026-10-12T10:00:00+05:30"
    assert journey.arrival_at.isoformat() == "2026-10-12T12:00:00+05:30"
    assert journey.duration_minutes == 120
    assert journey.service_date == date(2026, 10, 12)
    assert journey.departure_stop_sequence == 1
    assert journey.arrival_stop_sequence == 3
    assert journey.run_status == "scheduled"
    assert journey.run_version == 1
    assert session.get(ServiceRun, journey.run_id) is not None
    assert result.data_kind == "demonstration"


def test_boarding_at_intermediate_station(
    journey_timetable: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = journey_timetable
    result = search(session, dataset, 1, 2, date(2026, 10, 12))

    assert result.total == 1
    assert result.items[0].departure_at.hour == 11
    assert result.items[0].departure_at.minute == 5
    assert result.items[0].duration_minutes == 55
    assert result.items[0].departure_stop_sequence == 2


def test_reverse_search_uses_reverse_service(
    journey_timetable: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = journey_timetable
    result = search(session, dataset, 2, 0, date(2026, 10, 12))

    assert result.total == 1
    assert result.items[0].service_code == dataset.services[1].code
    assert result.items[0].departure_at.hour == 13
    assert result.items[0].arrival_at.hour == 15


def test_weekday_service_is_excluded_on_sunday(
    journey_timetable: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = journey_timetable
    result = search(session, dataset, 2, 0, date(2026, 10, 11))

    assert result.total == 0
    assert result.items == []


def test_inactive_service_is_excluded(
    journey_timetable: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = journey_timetable
    service = session.scalar(
        select(TrainService).where(TrainService.code == dataset.services[0].code)
    )
    assert service is not None
    service.is_active = False
    session.flush()

    result = search(session, dataset, 0, 2, date(2026, 10, 12))
    assert result.total == 0


def test_inactive_station_is_rejected(
    journey_timetable: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = journey_timetable
    station = session.scalar(
        select(Station).where(Station.code == dataset.services[0].stops[0].station_code)
    )
    assert station is not None
    station.is_active = False
    session.flush()

    with pytest.raises(InvalidStationSelectionError):
        search(session, dataset, 0, 2, date(2026, 10, 12))


def test_unknown_station_is_rejected(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    arrival = session.scalar(
        select(Station).where(Station.code == dataset.services[0].stops[-1].station_code)
    )
    assert arrival is not None

    with pytest.raises(InvalidStationSelectionError):
        search_journeys(
            session,
            JourneySearchQuery(
                departure_station_id=uuid4(),
                arrival_station_id=arrival.id,
                travel_date=date(2026, 10, 12),
            ),
        )


def test_offset_preserves_total(
    journey_timetable: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = journey_timetable
    result = search(session, dataset, 0, 2, date(2026, 10, 12), offset=1)

    assert result.total == 1
    assert result.items == []
    assert result.limit == 1
    assert result.offset == 1


@pytest.mark.parametrize("travel_date", [date(2025, 12, 31), date(2029, 1, 1)])
def test_outside_validity_returns_no_journeys(
    journey_timetable: tuple[Session, DemoTimetableDataset],
    travel_date: date,
) -> None:
    session, dataset = journey_timetable
    result = search(session, dataset, 0, 2, travel_date)

    assert result.total == 0
    assert result.items == []


def test_overnight_arrival_is_on_next_day(
    overnight_timetable: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = overnight_timetable
    result = search(session, dataset, 0, 2, date(2026, 10, 12))

    assert result.total == 1
    assert result.items[0].departure_at.isoformat() == "2026-10-12T21:00:00+05:30"
    assert result.items[0].arrival_at.isoformat() == "2026-10-13T06:00:00+05:30"
    assert result.items[0].duration_minutes == 540


def test_overnight_boarding_uses_starting_weekday_and_validity(
    overnight_timetable: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = overnight_timetable
    result = search(session, dataset, 1, 2, date(2026, 10, 20))

    assert result.total == 1
    assert result.items[0].service_date == date(2026, 10, 19)
    assert result.items[0].departure_stop_sequence == 2
    assert result.items[0].arrival_stop_sequence == 3
    assert result.items[0].departure_at.isoformat() == "2026-10-20T03:45:00+05:30"
    assert result.items[0].arrival_at.isoformat() == "2026-10-20T06:00:00+05:30"
    assert result.items[0].duration_minutes == 135


def test_overnight_service_is_excluded_on_wrong_starting_weekday(
    overnight_timetable: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = overnight_timetable
    result = search(session, dataset, 1, 2, date(2026, 10, 14))

    assert result.total == 0
    assert result.items == []


def test_cancelled_run_is_excluded(
    journey_timetable: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = journey_timetable
    initial = search(session, dataset, 0, 2, date(2026, 10, 12))
    run = session.get(ServiceRun, initial.items[0].run_id)
    assert run is not None
    run.status = "cancelled"
    session.flush()

    assert search(session, dataset, 0, 2, date(2026, 10, 12)).total == 0


def test_restricted_run_exposes_status(
    journey_timetable: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = journey_timetable
    initial = search(session, dataset, 0, 2, date(2026, 10, 12))
    run = session.get(ServiceRun, initial.items[0].run_id)
    assert run is not None
    run.status = "restricted"
    run.version = 2
    session.flush()

    result = search(session, dataset, 0, 2, date(2026, 10, 12))
    assert result.items[0].run_status == "restricted"
    assert result.items[0].run_version == 2


@pytest.mark.parametrize(
    ("sequence", "permission"),
    [(1, "pickup_allowed"), (3, "dropoff_allowed")],
)
def test_disallowed_boarding_or_alighting_is_excluded(
    journey_timetable: tuple[Session, DemoTimetableDataset],
    sequence: int,
    permission: str,
) -> None:
    session, dataset = journey_timetable
    initial = search(session, dataset, 0, 2, date(2026, 10, 12))
    stop = session.scalar(
        select(RunStop).where(
            RunStop.run_id == initial.items[0].run_id,
            RunStop.stop_sequence == sequence,
        )
    )
    assert stop is not None
    setattr(stop, permission, False)
    session.flush()

    assert search(session, dataset, 0, 2, date(2026, 10, 12)).total == 0


def test_search_does_not_create_runs(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    seed_timetable(session, dataset)
    before = session.scalar(select(func.count()).select_from(ServiceRun))

    result = search(session, dataset, 0, 2, date(2026, 10, 12))

    after = session.scalar(select(func.count()).select_from(ServiceRun))
    assert result.total == 0
    assert result.items == []
    assert after == before


@pytest.mark.parametrize(
    ("arrival_date", "deadline", "expected_total"),
    [
        (None, time(23, 59), 0),
        (date(2026, 10, 13), time(5, 59), 0),
        (date(2026, 10, 13), time(6, 0), 1),
    ],
)
def test_overnight_arrival_deadline(
    overnight_timetable: tuple[Session, DemoTimetableDataset],
    arrival_date: date | None,
    deadline: time,
    expected_total: int,
) -> None:
    session, dataset = overnight_timetable
    initial = search(session, dataset, 0, 2, date(2026, 10, 12))
    journey = initial.items[0]

    result = search_journeys(
        session,
        JourneySearchQuery(
            departure_station_id=journey.departure_station.id,
            arrival_station_id=journey.arrival_station.id,
            travel_date=date(2026, 10, 12),
            arrive_before=deadline,
            arrival_date=arrival_date,
        ),
    )

    assert result.total == expected_total
