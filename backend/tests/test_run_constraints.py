from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from railconnect.modules.timetable.models.run_stop import RunStop
from railconnect.modules.timetable.models.service_run import ServiceRun
from railconnect.modules.timetable.models.service_stop import ServiceStop
from railconnect.modules.timetable.models.train_service import TrainService
from railconnect.modules.timetable.seed_schemas import DemoTimetableDataset
from railconnect.modules.timetable.seeding import seed_timetable


def create_test_run(
    session: Session,
    dataset: DemoTimetableDataset,
) -> tuple[ServiceRun, ServiceStop]:
    seed_timetable(session, dataset)

    service = session.scalar(
        select(TrainService).where(TrainService.code == dataset.services[0].code)
    )
    assert service is not None

    first_stop = session.scalar(
        select(ServiceStop).where(
            ServiceStop.service_id == service.id,
            ServiceStop.stop_sequence == 1,
        )
    )
    assert first_stop is not None

    run = ServiceRun(
        service_id=service.id,
        service_date=date(2026, 10, 12),
        source_ref=dataset.source_ref,
    )
    session.add(run)
    session.flush()

    return run, first_stop


def test_run_defaults(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    run, _ = create_test_run(session, dataset)

    assert run.status == "scheduled"
    assert run.version == 1
    assert run.created_at.tzinfo is not None


def test_duplicate_service_date_is_rejected(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    run, _ = create_test_run(session, dataset)

    with pytest.raises(IntegrityError) as caught:
        with session.begin_nested():
            session.add(
                ServiceRun(
                    service_id=run.service_id,
                    service_date=run.service_date,
                    source_ref=dataset.source_ref,
                )
            )
            session.flush()

    assert "uq_service_runs_service_date" in str(caught.value.orig)


@pytest.mark.parametrize(
    ("status", "version", "constraint"),
    [
        ("unknown", 1, "ck_service_runs_valid_status"),
        ("scheduled", 0, "ck_service_runs_positive_version"),
    ],
)
def test_invalid_run_state_is_rejected(
    timetable_database: tuple[Session, DemoTimetableDataset],
    status: str,
    version: int,
    constraint: str,
) -> None:
    session, dataset = timetable_database
    run, _ = create_test_run(session, dataset)

    with pytest.raises(IntegrityError) as caught:
        with session.begin_nested():
            run.status = status
            run.version = version
            session.flush()

    assert constraint in str(caught.value.orig)


@pytest.mark.parametrize(
    ("arrival_hour", "departure_hour", "pickup", "dropoff", "constraint"),
    [
        (None, None, False, False, "ck_run_stops_has_scheduled_time"),
        (11, 10, True, True, "ck_run_stops_valid_scheduled_time_order"),
        (10, None, True, True, "ck_run_stops_pickup_requires_departure"),
        (None, 10, True, True, "ck_run_stops_dropoff_requires_arrival"),
    ],
)
def test_invalid_run_stop_is_rejected(
    timetable_database: tuple[Session, DemoTimetableDataset],
    arrival_hour: int | None,
    departure_hour: int | None,
    pickup: bool,
    dropoff: bool,
    constraint: str,
) -> None:
    session, dataset = timetable_database
    run, first_stop = create_test_run(session, dataset)

    arrival = datetime(2026, 10, 12, arrival_hour, tzinfo=UTC) if arrival_hour is not None else None
    departure = (
        datetime(2026, 10, 12, departure_hour, tzinfo=UTC) if departure_hour is not None else None
    )

    with pytest.raises(IntegrityError) as caught:
        with session.begin_nested():
            session.add(
                RunStop(
                    run_id=run.id,
                    station_id=first_stop.station_id,
                    stop_sequence=1,
                    scheduled_arrival_at=arrival,
                    scheduled_departure_at=departure,
                    pickup_allowed=pickup,
                    dropoff_allowed=dropoff,
                )
            )
            session.flush()

    assert constraint in str(caught.value.orig)


def test_duplicate_run_stop_sequence_is_rejected(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    run, first_stop = create_test_run(session, dataset)
    departure = datetime(2026, 10, 12, 10, tzinfo=UTC)

    session.add(
        RunStop(
            run_id=run.id,
            station_id=first_stop.station_id,
            stop_sequence=1,
            scheduled_departure_at=departure,
            pickup_allowed=True,
            dropoff_allowed=False,
        )
    )
    session.flush()

    with pytest.raises(IntegrityError) as caught:
        with session.begin_nested():
            session.add(
                RunStop(
                    run_id=run.id,
                    station_id=first_stop.station_id,
                    stop_sequence=1,
                    scheduled_departure_at=departure,
                    pickup_allowed=True,
                    dropoff_allowed=False,
                )
            )
            session.flush()

    assert "uq_run_stops_run_sequence" in str(caught.value.orig)


@pytest.mark.parametrize(
    ("field", "constraint"),
    [
        ("pickup_allowed", "ck_service_stops_pickup_requires_departure"),
        ("dropoff_allowed", "ck_service_stops_dropoff_requires_arrival"),
    ],
)
def test_recurring_stop_permissions_require_times(
    timetable_database: tuple[Session, DemoTimetableDataset],
    field: str,
    constraint: str,
) -> None:
    session, dataset = timetable_database
    run, first_stop = create_test_run(session, dataset)

    stop = first_stop
    if field == "pickup_allowed":
        final_stop = session.scalar(
            select(ServiceStop)
            .where(ServiceStop.service_id == run.service_id)
            .order_by(ServiceStop.stop_sequence.desc())
            .limit(1)
        )
        assert final_stop is not None
        stop = final_stop

    with pytest.raises(IntegrityError) as caught:
        with session.begin_nested():
            setattr(stop, field, True)
            session.flush()

    assert constraint in str(caught.value.orig)
