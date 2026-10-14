from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from railconnect.modules.identity.cleanup_repository import (
    apply_cleanup,
    preview_cleanup,
)


@dataclass(frozen=True)
class IdentityCleanupResult:
    sessions: int
    login_limits: int
    applied: bool


def cleanup_identity_records(
    session: Session,
    now: datetime,
    *,
    apply: bool = False,
    batch_size: int = 500,
    session_retention_days: int = 7,
    rate_retention_days: int = 1,
) -> IdentityCleanupResult:
    if not session.in_transaction():
        raise ValueError("Identity cleanup requires a caller-owned transaction.")

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Identity cleanup requires a timezone-aware clock.")

    if not 1 <= batch_size <= 1000:
        raise ValueError("Cleanup batch size must be between 1 and 1000.")

    if not 1 <= session_retention_days <= 365:
        raise ValueError("Session retention must be between 1 and 365 days.")

    if not 1 <= rate_retention_days <= 365:
        raise ValueError("Rate-limit retention must be between 1 and 365 days.")

    if session.new or session.dirty or session.deleted:
        raise ValueError("Cleanup requires a session without pending changes.")

    timestamp = now.astimezone(UTC)
    session_cutoff = timestamp - timedelta(days=session_retention_days)
    rate_cutoff = timestamp - timedelta(days=rate_retention_days)

    operation = apply_cleanup if apply else preview_cleanup
    sessions, login_limits = operation(
        session,
        session_cutoff,
        rate_cutoff,
        batch_size,
    )

    return IdentityCleanupResult(
        sessions=sessions,
        login_limits=login_limits,
        applied=apply,
    )
