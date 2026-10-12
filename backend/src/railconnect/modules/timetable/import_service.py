from dataclasses import dataclass
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from railconnect.modules.timetable.import_preview import (
    preview_timetable_import,
    verify_source_record,
)
from railconnect.modules.timetable.import_schemas import TimetableImportSnapshot
from railconnect.modules.timetable.models.source_record import SourceRecord
from railconnect.modules.timetable.models.timetable_import import TimetableImport
from railconnect.modules.timetable.seeding import SeedResult, seed_timetable

IMPORTER_VERSION = "demo-timetable-import-v1"


@dataclass(frozen=True)
class TimetableImportResult:
    source: SourceRecord
    summary: TimetableImport
    seed_result: SeedResult
    summary_created: bool


def import_timetable(
    session: Session,
    snapshot: TimetableImportSnapshot,
    execution_context: str,
) -> TimetableImportResult:
    if not session.in_transaction():
        raise ValueError("Timetable import requires a caller-owned transaction.")

    context = execution_context.strip()
    if not context or len(context) > 100:
        raise ValueError("Execution context must contain between 1 and 100 characters.")

    lock_digest = sha256(snapshot.dataset.source_ref.encode("utf-8")).digest()
    lock_key = int.from_bytes(lock_digest[:8], byteorder="big", signed=True)
    session.execute(select(func.pg_advisory_xact_lock(lock_key)))

    preview = preview_timetable_import(session, snapshot)
    if not preview.can_import:
        raise ValueError("Import conflicts: " + "; ".join(preview.conflicts))

    source = session.scalar(
        select(SourceRecord)
        .where(SourceRecord.source_ref == snapshot.dataset.source_ref)
        .with_for_update()
    )

    if source is None:
        source = SourceRecord(
            id=uuid5(
                NAMESPACE_URL,
                f"railconnect:source:{snapshot.dataset.source_ref}",
            ),
            source_ref=snapshot.dataset.source_ref,
            title=snapshot.metadata.title,
            source_uri=snapshot.metadata.source_uri,
            reuse_basis=snapshot.metadata.reuse_basis,
            data_kind=snapshot.dataset.kind,
            content_sha256=snapshot.content_sha256,
            effective_from=snapshot.dataset.valid_from,
            effective_until=snapshot.dataset.valid_until,
            retrieved_at=snapshot.metadata.retrieved_at,
        )
        session.add(source)
        session.flush()
    else:
        verify_source_record(source, snapshot)

    seed_result = seed_timetable(session, snapshot.dataset)

    summary = session.scalar(select(TimetableImport).where(TimetableImport.source_id == source.id))
    summary_created = summary is None

    if summary is None:
        summary = TimetableImport(
            id=uuid5(
                NAMESPACE_URL,
                f"railconnect:timetable-import:{source.id}",
            ),
            source_id=source.id,
            importer_version=IMPORTER_VERSION,
            execution_context=context,
            services_in_dataset=len(snapshot.dataset.services),
            stops_in_dataset=sum(len(service.stops) for service in snapshot.dataset.services),
            inserted_services=seed_result.inserted_services,
            existing_services=seed_result.existing_services,
            inserted_stops=seed_result.inserted_stops,
        )
        session.add(summary)
        session.flush()

    return TimetableImportResult(
        source=source,
        summary=summary,
        seed_result=seed_result,
        summary_created=summary_created,
    )
