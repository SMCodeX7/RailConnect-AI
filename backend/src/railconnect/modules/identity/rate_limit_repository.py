from datetime import datetime, timedelta

from sqlalchemy import case, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from railconnect.modules.identity.models.login_rate_limit import LoginRateLimit


def consume_login_window(
    session: Session,
    scope: str,
    key_hash: str,
    now: datetime,
    window_seconds: int,
    maximum_attempts: int,
) -> tuple[int, datetime]:
    expired = LoginRateLimit.window_expires_at <= now
    new_expiry = now + timedelta(seconds=window_seconds)

    statement = (
        insert(LoginRateLimit)
        .values(
            scope=scope,
            key_hash=key_hash,
            attempt_count=1,
            window_started_at=now,
            window_expires_at=new_expiry,
            updated_at=now,
        )
        .on_conflict_do_update(
            index_elements=[
                LoginRateLimit.scope,
                LoginRateLimit.key_hash,
            ],
            set_={
                "attempt_count": case(
                    (expired, 1),
                    else_=func.least(
                        LoginRateLimit.attempt_count + 1,
                        maximum_attempts + 1,
                    ),
                ),
                "window_started_at": case(
                    (expired, now),
                    else_=LoginRateLimit.window_started_at,
                ),
                "window_expires_at": case(
                    (expired, new_expiry),
                    else_=LoginRateLimit.window_expires_at,
                ),
                "updated_at": now,
            },
        )
        .returning(
            LoginRateLimit.attempt_count,
            LoginRateLimit.window_expires_at,
        )
    )

    count, expires_at = session.execute(statement).one()
    return count, expires_at
