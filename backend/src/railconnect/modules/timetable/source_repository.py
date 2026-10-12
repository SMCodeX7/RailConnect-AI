from sqlalchemy import select
from sqlalchemy.orm import Session

from railconnect.modules.timetable.models.source_record import SourceRecord


def get_source_records(
    session: Session,
    source_refs: set[str],
) -> dict[str, SourceRecord]:
    if not source_refs:
        return {}

    records = session.scalars(select(SourceRecord).where(SourceRecord.source_ref.in_(source_refs)))

    return {record.source_ref: record for record in records}
