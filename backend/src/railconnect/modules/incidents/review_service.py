from sqlalchemy.orm import Session

from railconnect.modules.identity.permissions import Permission
from railconnect.modules.identity.session_service import (
    AuthenticatedSession,
    require_actor_permission,
)
from railconnect.modules.incidents.review_repository import list_pending_reports
from railconnect.modules.incidents.review_schemas import (
    PendingReportResponse,
    ReportQueueQuery,
    ReportQueueResponse,
)


def get_pending_report_queue(
    session: Session,
    authenticated: AuthenticatedSession,
    query: ReportQueueQuery,
) -> ReportQueueResponse:
    require_actor_permission(
        authenticated.actor,
        Permission.REPORTS_READ,
    )

    if not session.in_transaction():
        raise ValueError("Report queue requires a caller-owned transaction.")

    reports, total = list_pending_reports(
        session,
        limit=query.limit,
        offset=query.offset,
    )

    return ReportQueueResponse(
        items=[
            PendingReportResponse(
                report_id=report.id,
                title=report.title,
                narrative=report.narrative,
                observed_at=report.observed_at,
                submitted_at=report.submitted_at,
                run_hint_id=report.run_hint_id,
                station_hint_id=report.station_hint_id,
                departure_stop_sequence_hint=report.departure_stop_sequence_hint,
                arrival_stop_sequence_hint=report.arrival_stop_sequence_hint,
                status="pending",
                version=report.version,
            )
            for report in reports
        ],
        total=total,
        limit=query.limit,
        offset=query.offset,
    )
