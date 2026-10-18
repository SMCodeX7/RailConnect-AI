from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from railconnect.modules.incidents.report_cleanup_repository import (
    delete_report_counters,
    preview_report_counters,
)


@dataclass(frozen=True)
class ReportCleanupResult:
    applied: bool
    records: int


def cleanup_report_counters(
    session: Session,
    now: datetime,
    apply: bool = False,
    retention_days: int = 1,
    batch_limit: int = 500,
) -> ReportCleanupResult:
    if not session.in_transaction():
        raise ValueError("Report cleanup requires a caller-owned transaction.")

    if session.new or session.dirty or session.deleted:
        raise ValueError("Report cleanup requires a session without pending changes.")

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Report cleanup requires a timezone-aware clock.")

    if not 1 <= retention_days <= 365:
        raise ValueError("Retention days must be between 1 and 365.")

    if not 1 <= batch_limit <= 1000:
        raise ValueError("Batch limit must be between 1 and 1000.")

    cutoff = now.astimezone(UTC) - timedelta(days=retention_days)

    if apply:
        count = delete_report_counters(session, cutoff, batch_limit)
    else:
        count = preview_report_counters(session, cutoff, batch_limit)

    return ReportCleanupResult(applied=apply, records=count)
