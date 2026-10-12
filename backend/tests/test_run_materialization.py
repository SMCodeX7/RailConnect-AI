from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from railconnect.modules.timetable.models.run_stop import RunStop
from railconnect.modules.timetable.models.service_run import ServiceRun
from railconnect.modules.timetable.models.service_stop import ServiceStop
from railconnect.modules.timetable.models.train_service import TrainService
from railconnect.modules.timetable.run_service import materialize_service_run
from railconnect.modules.timetable.seed_schemas import DemoTimetableDataset
from railconnect.modules.timetable.seeding import seed_timetable

SERVICE_DATE = date(2026, 10, 12)


def prepare_service(
    session: Session,
    dataset: DemoTimetableDataset,
    service_index: int = 0,
) -> tuple[TrainService, list[ServiceStop]]:
    seed_timetable(session, dataset)

    service = session.scalar(
        select(TrainService).where(TrainService.code == dataset.services[service_index].code)
    )
    assert service is not None

    stops = list(
        session.scalars(
            select(ServiceStop)
            .where(ServiceStop.service_id == service.id)
            .order_by(ServiceStop.stop_sequence)
        )
    )
    return service, stops


def test_materialization_is_repeatable(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    service, pattern_stops = prepare_service(session, dataset)

    first = materialize_service_run(session, service.id, SERVICE_DATE)
    second = materialize_service_run(session, service.id, SERVICE_DATE)

    assert first.inserted is True
    assert second.inserted is False
    assert first.run.id == second.run.id
    assert first.run.service_date == SERVICE_DATE

    stops = list(
        session.scalars(
            select(RunStop).where(RunStop.run_id == first.run.id).order_by(RunStop.stop_sequence)
        )
    )
    assert len(stops) == len(pattern_stops)
    assert [stop.stop_sequence for stop in stops] == [1, 2, 3]
    assert [stop.station_id for stop in stops] == [stop.station_id for stop in pattern_stops]
    assert stops[0].scheduled_departure_at == datetime(2026, 10, 12, 4, 30, tzinfo=UTC)
    assert stops[-1].scheduled_arrival_at == datetime(2026, 10, 12, 6, 30, tzinfo=UTC)


def test_overnight_times_preserve_starting_date(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    service, stops = prepare_service(session, dataset)

    stops[0].departure_minutes = 1260
    stops[1].arrival_minutes = 1660
    stops[1].departure_minutes = 1665
    stops[2].arrival_minutes = 1800
    session.flush()

    result = materialize_service_run(session, service.id, SERVICE_DATE)
    run_stops = list(
        session.scalars(
            select(RunStop).where(RunStop.run_id == result.run.id).order_by(RunStop.stop_sequence)
        )
    )

    assert result.run.service_date == SERVICE_DATE
    assert run_stops[0].scheduled_departure_at == datetime(2026, 10, 12, 15, 30, tzinfo=UTC)
    assert run_stops[1].scheduled_departure_at == datetime(2026, 10, 12, 22, 15, tzinfo=UTC)
    assert run_stops[2].scheduled_arrival_at == datetime(2026, 10, 13, 0, 30, tzinfo=UTC)


def test_explicit_permissions_are_copied(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    service, stops = prepare_service(session, dataset)

    stops[1].pickup_allowed = False
    stops[1].dropoff_allowed = False
    session.flush()

    result = materialize_service_run(session, service.id, SERVICE_DATE)
    middle = session.scalar(
        select(RunStop).where(
            RunStop.run_id == result.run.id,
            RunStop.stop_sequence == 2,
        )
    )
    assert middle is not None
    assert middle.pickup_allowed is False
    assert middle.dropoff_allowed is False


@pytest.mark.parametrize("status", ["cancelled", "restricted"])
def test_repeating_materialization_preserves_operational_state(
    timetable_database: tuple[Session, DemoTimetableDataset],
    status: str,
) -> None:
    session, dataset = timetable_database
    service, _ = prepare_service(session, dataset)

    first = materialize_service_run(session, service.id, SERVICE_DATE)
    first.run.status = status
    first.run.version = 2
    session.flush()

    repeated = materialize_service_run(session, service.id, SERVICE_DATE)

    assert repeated.inserted is False
    assert repeated.run.status == status
    assert repeated.run.version == 2


@pytest.mark.parametrize(
    "service_date",
    [date(2025, 12, 31), date(2029, 1, 1)],
)
def test_rejects_date_outside_validity(
    timetable_database: tuple[Session, DemoTimetableDataset],
    service_date: date,
) -> None:
    session, dataset = timetable_database
    service, _ = prepare_service(session, dataset)

    with pytest.raises(ValueError, match="validity period"):
        materialize_service_run(session, service.id, service_date)

    assert session.scalar(select(ServiceRun).where(ServiceRun.service_id == service.id)) is None


def test_rejects_nonoperating_day(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    service, _ = prepare_service(session, dataset, service_index=1)

    with pytest.raises(ValueError, match="does not operate"):
        materialize_service_run(session, service.id, date(2026, 10, 11))


def test_rejects_inactive_service(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    service, _ = prepare_service(session, dataset)
    service.is_active = False
    session.flush()

    with pytest.raises(ValueError, match="exist and be active"):
        materialize_service_run(session, service.id, SERVICE_DATE)


def test_rejects_missing_service(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, _ = timetable_database

    with pytest.raises(ValueError, match="exist and be active"):
        materialize_service_run(session, uuid4(), SERVICE_DATE)


def test_rejects_changed_run_source(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    service, _ = prepare_service(session, dataset)

    result = materialize_service_run(session, service.id, SERVICE_DATE)
    result.run.source_ref = "different-source"
    session.flush()

    with pytest.raises(ValueError, match="run source differs"):
        materialize_service_run(session, service.id, SERVICE_DATE)


def test_rejects_changed_schedule_snapshot(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    service, _ = prepare_service(session, dataset)

    result = materialize_service_run(session, service.id, SERVICE_DATE)
    middle = session.scalar(
        select(RunStop).where(
            RunStop.run_id == result.run.id,
            RunStop.stop_sequence == 2,
        )
    )
    assert middle is not None
    middle.pickup_allowed = False
    session.flush()

    with pytest.raises(ValueError, match="run stops differ"):
        materialize_service_run(session, service.id, SERVICE_DATE)

    assert middle.pickup_allowed is False


def test_caller_rollback_removes_run_and_stops(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, dataset = timetable_database
    service, _ = prepare_service(session, dataset)
    run_id = None

    with pytest.raises(RuntimeError, match="abort transaction"):
        with session.begin_nested():
            result = materialize_service_run(session, service.id, SERVICE_DATE)
            run_id = result.run.id
            raise RuntimeError("abort transaction")

    assert run_id is not None
    assert session.scalar(select(ServiceRun).where(ServiceRun.id == run_id)) is None
    assert session.scalar(select(RunStop).where(RunStop.run_id == run_id)) is None


def test_requires_caller_owned_transaction(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> None:
    session, _ = timetable_database

    with Session(bind=session.get_bind()) as separate_session:
        with pytest.raises(ValueError, match="caller-owned transaction"):
            materialize_service_run(separate_session, uuid4(), SERVICE_DATE)
