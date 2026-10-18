from datetime import datetime

from sqlalchemy import Select, delete, select
from sqlalchemy.orm import Session

from railconnect.modules.incidents.models.report_rate_limit import ReportRateLimit


def _candidates(
    cutoff: datetime,
    batch_limit: int,
) -> Select[str]:
    return (
        select(ReportRateLimit.key_hash)
        .where(ReportRateLimit.window_expires_at <= cutoff)
        .order_by(
            ReportRateLimit.window_expires_at,
            ReportRateLimit.key_hash,
        )
        .limit(batch_limit)
    )


def preview_report_counters(
    session: Session,
    cutoff: datetime,
    batch_limit: int,
) -> int:
    return len(session.scalars(_candidates(cutoff, batch_limit)).all())


def delete_report_counters(
    session: Session,
    cutoff: datetime,
    batch_limit: int,
) -> int:
    keys = session.scalars(_candidates(cutoff, batch_limit).with_for_update(skip_locked=True)).all()

    if not keys:
        return 0

    statement = (
        delete(ReportRateLimit)
        .where(ReportRateLimit.key_hash.in_(keys))
        .returning(ReportRateLimit.key_hash)
        .execution_options(synchronize_session="fetch")
    )

    return len(session.scalars(statement).all())
