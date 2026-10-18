from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from railconnect.modules.identity.errors import PermissionDeniedError
from railconnect.modules.identity.models.role import Role
from railconnect.modules.identity.models.user import User
from railconnect.modules.identity.models.user_role import UserRole
from railconnect.modules.identity.permissions import Permission, resolve_permissions
from railconnect.modules.identity.session_service import (
    AuthenticatedSession,
    require_actor_permission,
)
from railconnect.modules.incidents.errors import (
    ReportNotFoundError,
    ReportReviewConflictError,
)
from railconnect.modules.incidents.models.incident import Incident
from railconnect.modules.incidents.models.incident_audit_event import IncidentAuditEvent
from railconnect.modules.incidents.models.incident_report import IncidentReport
from railconnect.modules.incidents.models.incident_revision import IncidentRevision
from railconnect.modules.incidents.review_repository import (
    get_report_for_review,
    validate_approved_run_scope,
)
from railconnect.modules.incidents.review_schemas import (
    RejectReportInput,
    ReportReviewResponse,
    VerifyReportInput,
)


def _validate_review_context(
    session: Session,
    authenticated: AuthenticatedSession,
    request_id: str,
    now: datetime,
) -> tuple[UUID, datetime]:
    require_actor_permission(authenticated.actor, Permission.REPORTS_REVIEW)

    if session.in_transaction():
        raise ValueError("Report review requires a fresh session.")

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Report review requires a timezone-aware clock.")

    if not request_id.strip() or len(request_id) > 64:
        raise ValueError("Report review requires a bounded request ID.")

    return UUID(authenticated.actor.user_id), now.astimezone(UTC)


def _check_current_reviewer(
    session: Session,
    actor_id: UUID,
) -> None:
    user = session.scalar(
        select(User)
        .where(User.id == actor_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )

    if user is None or not user.is_active:
        raise PermissionDeniedError("The reviewer account is unavailable.")

    role_codes = session.scalars(
        select(Role.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == actor_id)
    ).all()

    if Permission.REPORTS_REVIEW not in resolve_permissions(role_codes):
        raise PermissionDeniedError("Report review permission is required.")


def _pending_report(
    session: Session,
    report_id: UUID,
    expected_version: int,
    actor_id: UUID,
    timestamp: datetime,
) -> IncidentReport:
    report = get_report_for_review(session, report_id)

    if report is None:
        raise ReportNotFoundError("The report does not exist.")

    if report.status != "pending" or report.version != expected_version:
        raise ReportReviewConflictError("The report has changed or was already reviewed.")

    if report.submitted_by_user_id == actor_id:
        raise PermissionDeniedError("Staff cannot review their own identified reports.")

    if timestamp < report.submitted_at:
        raise ValueError("The review clock cannot precede report submission.")

    return report


def verify_report(
    session: Session,
    authenticated: AuthenticatedSession,
    report_id: UUID,
    data: VerifyReportInput,
    request_id: str,
    now: datetime,
) -> ReportReviewResponse:
    actor_id, timestamp = _validate_review_context(
        session,
        authenticated,
        request_id,
        now,
    )

    with session.begin():
        _check_current_reviewer(session, actor_id)

        report = _pending_report(
            session,
            report_id,
            data.expected_version,
            actor_id,
            timestamp,
        )
        validate_approved_run_scope(session, data.approved)

        report.status = "verified"
        report.version += 1
        report.reviewed_by_id = actor_id
        report.reviewed_at = timestamp
        report.review_reason = data.reason
        session.flush()

        incident = Incident(
            originating_report_id=report.id,
            status="active",
            version=1,
            current_revision_number=1,
            created_by_id=actor_id,
            created_at=timestamp,
        )
        session.add(incident)
        session.flush()

        approved = data.approved
        revision = IncidentRevision(
            incident_id=incident.id,
            revision_number=1,
            run_id=approved.run_id,
            scope_kind=approved.scope_kind,
            departure_stop_sequence=approved.departure_stop_sequence,
            arrival_stop_sequence=approved.arrival_stop_sequence,
            impact_kind=approved.impact_kind,
            estimated_delay_minutes=approved.estimated_delay_minutes,
            effective_from=approved.effective_from.astimezone(UTC),
            effective_until=approved.effective_until.astimezone(UTC),
            public_summary=approved.public_summary,
            evidence_basis=approved.evidence_basis,
            verification_reason=data.reason,
            verified_by_id=actor_id,
            verified_at=timestamp,
        )
        session.add(revision)
        session.flush()

        session.add(
            IncidentAuditEvent(
                report_id=report.id,
                incident_id=incident.id,
                revision_id=revision.id,
                actor_id=actor_id,
                action="report_verified",
                reason=data.reason,
                request_id=request_id,
                report_version=report.version,
                incident_version=incident.version,
                occurred_at=timestamp,
            )
        )
        session.flush()

        response = ReportReviewResponse(
            report_id=report.id,
            status="verified",
            report_version=report.version,
            incident_id=incident.id,
            revision_id=revision.id,
            incident_version=incident.version,
        )

    return response


def reject_report(
    session: Session,
    authenticated: AuthenticatedSession,
    report_id: UUID,
    data: RejectReportInput,
    request_id: str,
    now: datetime,
) -> ReportReviewResponse:
    actor_id, timestamp = _validate_review_context(
        session,
        authenticated,
        request_id,
        now,
    )

    with session.begin():
        _check_current_reviewer(session, actor_id)

        report = _pending_report(
            session,
            report_id,
            data.expected_version,
            actor_id,
            timestamp,
        )

        report.status = "rejected"
        report.version += 1
        report.reviewed_by_id = actor_id
        report.reviewed_at = timestamp
        report.review_reason = data.reason
        session.flush()

        session.add(
            IncidentAuditEvent(
                report_id=report.id,
                actor_id=actor_id,
                action="report_rejected",
                reason=data.reason,
                request_id=request_id,
                report_version=report.version,
                occurred_at=timestamp,
            )
        )
        session.flush()

        response = ReportReviewResponse(
            report_id=report.id,
            status="rejected",
            report_version=report.version,
        )

    return response
