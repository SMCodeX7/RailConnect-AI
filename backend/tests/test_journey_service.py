from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from railconnect.modules.journeys.errors import InvalidStationSelectionError
from railconnect.modules.journeys.schemas import JourneyListResponse, JourneySearchQuery
from railconnect.modules.journeys.service import search_journeys
from railconnect.modules.stations.models import Station
from railconnect.modules.timetable.models.train_service import TrainService
from railconnect.modules.timetable.seed_schemas import DemoTimetableDataset
from railconnect.modules.timetable.seeding import seed_timetable


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
    seed_timetable(session, overnight)

    return session, overnight


def test_forward_journey(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    seed_timetable(session, dataset)

    result = search(session, dataset, 0, 2, date(2026, 10, 12))

    assert result.total == 1
    assert result.items[0].service_code == dataset.services[0].code
    assert result.items[0].departure_at.isoformat() == "2026-10-12T10:00:00+05:30"
    assert result.items[0].arrival_at.isoformat() == "2026-10-12T12:00:00+05:30"
    assert result.items[0].duration_minutes == 120
    assert result.data_kind == "demonstration"


def test_boarding_at_intermediate_station(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    seed_timetable(session, dataset)

    result = search(session, dataset, 1, 2, date(2026, 10, 12))

    assert result.total == 1
    assert result.items[0].departure_at.hour == 11
    assert result.items[0].departure_at.minute == 5
    assert result.items[0].duration_minutes == 55


def test_reverse_search_uses_reverse_service(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    seed_timetable(session, dataset)

    result = search(session, dataset, 2, 0, date(2026, 10, 12))

    assert result.total == 1
    assert result.items[0].service_code == dataset.services[1].code
    assert result.items[0].departure_at.hour == 13
    assert result.items[0].arrival_at.hour == 15


def test_weekday_service_is_excluded_on_sunday(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    seed_timetable(session, dataset)

    result = search(session, dataset, 2, 0, date(2026, 10, 11))

    assert result.total == 0
    assert result.items == []


def test_inactive_service_is_excluded(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    seed_timetable(session, dataset)
    service = session.scalar(
        select(TrainService).where(TrainService.code == dataset.services[0].code)
    )
    assert service is not None
    service.is_active = False
    session.flush()

    result = search(session, dataset, 0, 2, date(2026, 10, 12))

    assert result.total == 0
    assert result.items == []


def test_inactive_station_is_rejected(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    seed_timetable(session, dataset)
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

    query = JourneySearchQuery(
        departure_station_id=uuid4(),
        arrival_station_id=arrival.id,
        travel_date=date(2026, 10, 12),
    )

    with pytest.raises(InvalidStationSelectionError):
        search_journeys(session, query)


def test_offset_preserves_total(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    seed_timetable(session, dataset)

    result = search(session, dataset, 0, 2, date(2026, 10, 12), offset=1)

    assert result.total == 1
    assert result.items == []
    assert result.limit == 1
    assert result.offset == 1


@pytest.mark.parametrize("travel_date", [date(2025, 12, 31), date(2029, 1, 1)])
def test_outside_validity_returns_no_journeys(
    timetable_database: tuple[Session, DemoTimetableDataset],
    travel_date: date,
) -> None:
    session, dataset = timetable_database
    seed_timetable(session, dataset)

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
