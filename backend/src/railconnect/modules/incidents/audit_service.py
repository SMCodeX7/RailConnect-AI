from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from railconnect.modules.identity.permissions import Permission
from railconnect.modules.identity.session_service import AuthenticatedSession
from railconnect.modules.incidents.audit_schemas import (
    IncidentAuditEventResponse,
    IncidentAuditHistoryResponse,
    IncidentAuditQuery,
)
from railconnect.modules.incidents.errors import ReportNotFoundError
from railconnect.modules.incidents.models.incident_audit_event import IncidentAuditEvent
from railconnect.modules.incidents.models.incident_report import IncidentReport
from railconnect.modules.incidents.staff_policy import require_current_staff_permission


def get_report_audit_history(
    session: Session,
    authenticated: AuthenticatedSession,
    report_id: UUID,
    query: IncidentAuditQuery,
) -> IncidentAuditHistoryResponse:
    require_current_staff_permission(
        session,
        authenticated,
        Permission.AUDIT_READ,
    )

    report = session.get(IncidentReport, report_id)
    if report is None:
        raise ReportNotFoundError("The report was not found.")

    total = session.scalar(
        select(func.count())
        .select_from(IncidentAuditEvent)
        .where(IncidentAuditEvent.report_id == report_id)
    )
    assert total is not None

    events = session.scalars(
        select(IncidentAuditEvent)
        .where(IncidentAuditEvent.report_id == report_id)
        .order_by(
            IncidentAuditEvent.occurred_at,
            IncidentAuditEvent.id,
        )
        .limit(query.limit)
        .offset(query.offset)
    ).all()

    return IncidentAuditHistoryResponse(
        report_id=report_id,
        items=[
            IncidentAuditEventResponse(
                event_id=event.id,
                report_id=event.report_id,
                incident_id=event.incident_id,
                revision_id=event.revision_id,
                actor_id=event.actor_id,
                action=event.action,
                reason=event.reason,
                request_id=event.request_id,
                report_version=event.report_version,
                incident_version=event.incident_version,
                occurred_at=event.occurred_at,
            )
            for event in events
        ],
        total=total,
        limit=query.limit,
        offset=query.offset,
    )
