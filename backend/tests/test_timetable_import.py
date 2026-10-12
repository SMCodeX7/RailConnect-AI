from dataclasses import replace
from hashlib import sha256

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from railconnect.modules.timetable import import_service
from railconnect.modules.timetable.import_preview import preview_timetable_import
from railconnect.modules.timetable.import_schemas import (
    TimetableImportSnapshot,
    TimetableSourceMetadata,
)
from railconnect.modules.timetable.import_service import import_timetable
from railconnect.modules.timetable.models.service_stop import ServiceStop
from railconnect.modules.timetable.models.source_record import SourceRecord
from railconnect.modules.timetable.models.timetable_import import TimetableImport
from railconnect.modules.timetable.models.train_service import TrainService
from railconnect.modules.timetable.seed_schemas import DemoTimetableDataset
from railconnect.modules.timetable.seeding import SeedResult, seed_timetable


@pytest.fixture
def import_database(
    timetable_database: tuple[Session, DemoTimetableDataset],
) -> tuple[Session, TimetableImportSnapshot]:
    session, dataset = timetable_database
    content = dataset.model_dump_json().encode("utf-8")
    metadata = TimetableSourceMetadata(
        title="Fictional test timetable",
        source_uri="test-fixtures/timetable.json",
        reuse_basis="Project-generated fictional test data.",
        retrieved_at=None,
    )

    return session, TimetableImportSnapshot(
        dataset=dataset,
        metadata=metadata,
        content_sha256=sha256(content).hexdigest(),
    )


def database_counts(session: Session) -> tuple[int, int, int, int]:
    sources = session.scalar(select(func.count()).select_from(SourceRecord))
    summaries = session.scalar(select(func.count()).select_from(TimetableImport))
    services = session.scalar(select(func.count()).select_from(TrainService))
    stops = session.scalar(select(func.count()).select_from(ServiceStop))

    assert sources is not None
    assert summaries is not None
    assert services is not None
    assert stops is not None

    return sources, summaries, services, stops


def test_preview_executes_no_mutations(
    import_database: tuple[Session, TimetableImportSnapshot],
) -> None:
    session, snapshot = import_database
    before = database_counts(session)
    statements: list[str] = []

    def record_statement(*arguments: object) -> None:
        statement = arguments[2]
        if isinstance(statement, str):
            statements.append(statement.strip().upper())

    bind = session.get_bind()
    event.listen(bind, "before_cursor_execute", record_statement)
    try:
        preview = preview_timetable_import(session, snapshot)
    finally:
        event.remove(bind, "before_cursor_execute", record_statement)

    assert preview.can_import is True
    assert preview.source_registered is False
    assert preview.import_recorded is False
    assert len(preview.new_service_codes) == 2
    assert preview.stops_to_insert == 6
    assert database_counts(session) == before
    assert statements
    assert all(not statement.startswith(("INSERT", "UPDATE", "DELETE")) for statement in statements)


def test_import_registers_source_and_summary(
    import_database: tuple[Session, TimetableImportSnapshot],
) -> None:
    session, snapshot = import_database

    result = import_timetable(session, snapshot, execution_context="pytest")

    assert result.summary_created is True
    assert result.source.content_sha256 == snapshot.content_sha256
    assert result.source.retrieved_at is None
    assert result.source.registered_at.tzinfo is not None
    assert result.summary.source_id == result.source.id
    assert result.summary.execution_context == "pytest"
    assert result.summary.services_in_dataset == 2
    assert result.summary.stops_in_dataset == 6
    assert result.summary.inserted_services == 2
    assert result.summary.existing_services == 0
    assert result.summary.inserted_stops == 6


def test_repeated_import_preserves_original_summary(
    import_database: tuple[Session, TimetableImportSnapshot],
) -> None:
    session, snapshot = import_database

    first = import_timetable(session, snapshot, execution_context="first-test")
    original_time = first.summary.imported_at
    second = import_timetable(session, snapshot, execution_context="second-test")

    assert second.summary_created is False
    assert second.source.id == first.source.id
    assert second.summary.id == first.summary.id
    assert second.summary.execution_context == "first-test"
    assert second.summary.imported_at == original_time
    assert second.summary.inserted_services == 2
    assert second.seed_result.inserted_services == 0
    assert second.seed_result.existing_services == 2
    assert second.seed_result.inserted_stops == 0


def test_registration_accepts_matching_preexisting_services(
    import_database: tuple[Session, TimetableImportSnapshot],
) -> None:
    session, snapshot = import_database
    seed_timetable(session, snapshot.dataset)

    result = import_timetable(session, snapshot, execution_context="pytest")

    assert result.summary_created is True
    assert result.summary.inserted_services == 0
    assert result.summary.existing_services == 2
    assert result.summary.inserted_stops == 0


def test_preview_reports_registered_import(
    import_database: tuple[Session, TimetableImportSnapshot],
) -> None:
    session, snapshot = import_database
    import_timetable(session, snapshot, execution_context="pytest")

    preview = preview_timetable_import(session, snapshot)

    assert preview.can_import is True
    assert preview.source_registered is True
    assert preview.import_recorded is True
    assert preview.new_service_codes == ()
    assert len(preview.existing_service_codes) == 2
    assert preview.stops_to_insert == 0


def test_changed_content_under_same_source_is_rejected(
    import_database: tuple[Session, TimetableImportSnapshot],
) -> None:
    session, snapshot = import_database
    first = import_timetable(session, snapshot, execution_context="pytest")
    changed = replace(snapshot, content_sha256="f" * 64)

    preview = preview_timetable_import(session, changed)
    assert preview.can_import is False

    with pytest.raises(ValueError, match="Registered source"):
        import_timetable(session, changed, execution_context="pytest")

    assert first.source.content_sha256 == snapshot.content_sha256


def test_changed_metadata_under_same_source_is_rejected(
    import_database: tuple[Session, TimetableImportSnapshot],
) -> None:
    session, snapshot = import_database
    import_timetable(session, snapshot, execution_context="pytest")
    changed = replace(
        snapshot,
        metadata=snapshot.metadata.model_copy(update={"title": "Changed title"}),
    )

    with pytest.raises(ValueError, match="Registered source"):
        import_timetable(session, changed, execution_context="pytest")


def test_conflicting_service_prevents_source_registration(
    import_database: tuple[Session, TimetableImportSnapshot],
) -> None:
    session, snapshot = import_database
    seed_timetable(session, snapshot.dataset)
    service = session.scalar(
        select(TrainService).where(TrainService.code == snapshot.dataset.services[0].code)
    )
    assert service is not None
    service.name = "Conflicting service"
    session.flush()
    before = database_counts(session)

    with pytest.raises(ValueError, match="Existing service differs"):
        import_timetable(session, snapshot, execution_context="pytest")

    assert database_counts(session) == before
    assert (
        session.scalar(
            select(SourceRecord).where(SourceRecord.source_ref == snapshot.dataset.source_ref)
        )
        is None
    )


def test_failure_rolls_back_source_services_and_stops(
    import_database: tuple[Session, TimetableImportSnapshot],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session, snapshot = import_database
    before = database_counts(session)

    def failing_seed(
        target_session: Session,
        dataset: DemoTimetableDataset,
    ) -> SeedResult:
        seed_timetable(target_session, dataset)
        raise RuntimeError("Simulated import failure")

    monkeypatch.setattr(import_service, "seed_timetable", failing_seed)

    with pytest.raises(RuntimeError, match="Simulated import failure"):
        with session.begin_nested():
            import_timetable(session, snapshot, execution_context="pytest")

    assert database_counts(session) == before


@pytest.mark.parametrize("context", ["", "   ", "x" * 101])
def test_invalid_execution_context_is_rejected(
    import_database: tuple[Session, TimetableImportSnapshot],
    context: str,
) -> None:
    session, snapshot = import_database
    before = database_counts(session)

    with pytest.raises(ValueError, match="Execution context"):
        import_timetable(session, snapshot, execution_context=context)

    assert database_counts(session) == before


def test_import_requires_caller_owned_transaction(
    import_database: tuple[Session, TimetableImportSnapshot],
) -> None:
    session, snapshot = import_database

    with Session(bind=session.get_bind()) as separate_session:
        with pytest.raises(ValueError, match="caller-owned transaction"):
            import_timetable(
                separate_session,
                snapshot,
                execution_context="pytest",
            )
