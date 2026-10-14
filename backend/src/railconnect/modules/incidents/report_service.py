from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from railconnect.core.config import Settings
from railconnect.modules.incidents.errors import (
    InvalidReportError,
    ReportRateLimitedError,
)
from railconnect.modules.incidents.report_rate_service import consume_report_attempt
from railconnect.modules.incidents.report_repository import (
    create_pending_report,
    validate_report_references,
)
from railconnect.modules.incidents.report_schemas import (
    ReportSubmissionResponse,
    SubmitReportInput,
)


def submit_report(
    session: Session,
    data: SubmitReportInput,
    client_key: str,
    settings: Settings,
    clock: Callable[[], datetime],
    submitted_by_user_id: UUID | None = None,
) -> ReportSubmissionResponse:
    if session.in_transaction():
        raise ValueError("Report submission requires a fresh session.")

    now = clock()

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Report submission requires a timezone-aware clock.")

    timestamp = now.astimezone(UTC)

    with session.begin():
        decision = consume_report_attempt(
            session,
            client_key=client_key,
            settings=settings,
            now=timestamp,
        )

    if not decision.allowed:
        raise ReportRateLimitedError(decision.retry_after)

    if data.observed_at.astimezone(UTC) > timestamp:
        raise InvalidReportError("The observation time cannot be in the future.")

    with session.begin():
        validate_report_references(
            session,
            data,
            submitted_by_user_id,
        )
        report = create_pending_report(
            session,
            data,
            submitted_at=timestamp,
            submitted_by_user_id=submitted_by_user_id,
        )

        response = ReportSubmissionResponse(
            report_id=report.id,
            status="pending",
            submitted_at=report.submitted_at,
        )

    return response
