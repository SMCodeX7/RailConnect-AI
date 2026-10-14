from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from math import ceil

from sqlalchemy.orm import Session

from railconnect.core.config import Settings
from railconnect.modules.incidents.report_rate_repository import consume_report_window


@dataclass(frozen=True)
class ReportRateDecision:
    allowed: bool
    retry_after: int


def report_limit_key(client_key: str) -> str:
    client = client_key.strip()

    if not client or len(client) > 128:
        raise ValueError("A bounded client identifier is required.")

    return sha256(f"railconnect:report-submission:client:{client}".encode()).hexdigest()


def consume_report_attempt(
    session: Session,
    client_key: str,
    settings: Settings,
    now: datetime,
) -> ReportRateDecision:
    if not session.in_transaction():
        raise ValueError("Report limiting requires a caller-owned transaction.")

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Report limiting requires a timezone-aware clock.")

    timestamp = now.astimezone(UTC)

    count, expires_at = consume_report_window(
        session,
        key_hash=report_limit_key(client_key),
        now=timestamp,
        window_seconds=settings.report_rate_window_seconds,
        maximum_attempts=settings.report_client_max_attempts,
    )

    if count > settings.report_client_max_attempts:
        return ReportRateDecision(
            allowed=False,
            retry_after=max(
                1,
                ceil((expires_at - timestamp).total_seconds()),
            ),
        )

    return ReportRateDecision(allowed=True, retry_after=0)
