from datetime import datetime, timedelta

from sqlalchemy import case, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from railconnect.modules.incidents.models.report_rate_limit import ReportRateLimit


def consume_report_window(
    session: Session,
    key_hash: str,
    now: datetime,
    window_seconds: int,
    maximum_attempts: int,
) -> tuple[int, datetime]:
    expired = ReportRateLimit.window_expires_at <= now
    new_expiry = now + timedelta(seconds=window_seconds)

    statement = (
        insert(ReportRateLimit)
        .values(
            key_hash=key_hash,
            attempt_count=1,
            window_started_at=now,
            window_expires_at=new_expiry,
            updated_at=now,
        )
        .on_conflict_do_update(
            index_elements=[ReportRateLimit.key_hash],
            set_={
                "attempt_count": case(
                    (expired, 1),
                    else_=func.least(
                        ReportRateLimit.attempt_count + 1,
                        maximum_attempts + 1,
                    ),
                ),
                "window_started_at": case(
                    (expired, now),
                    else_=ReportRateLimit.window_started_at,
                ),
                "window_expires_at": case(
                    (expired, new_expiry),
                    else_=ReportRateLimit.window_expires_at,
                ),
                "updated_at": now,
            },
        )
        .returning(
            ReportRateLimit.attempt_count,
            ReportRateLimit.window_expires_at,
        )
    )

    count, expires_at = session.execute(statement).one()
    return count, expires_at
