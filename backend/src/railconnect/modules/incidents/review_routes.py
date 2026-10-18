from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from railconnect.modules.identity.dependencies import (
    NO_STORE_HEADERS,
    IdentityClock,
    require_staff_permission,
)
from railconnect.modules.identity.errors import PermissionDeniedError
from railconnect.modules.identity.permissions import Permission
from railconnect.modules.identity.session_service import AuthenticatedSession
from railconnect.modules.incidents.dependencies import ReportSession
from railconnect.modules.incidents.errors import (
    InvalidApprovedIncidentError,
    ReportNotFoundError,
    ReportReviewConflictError,
)
from railconnect.modules.incidents.review_decision_service import (
    reject_report,
    verify_report,
)
from railconnect.modules.incidents.review_schemas import (
    RejectReportInput,
    ReportQueueQuery,
    ReportQueueResponse,
    ReportReviewResponse,
    VerifyReportInput,
)
from railconnect.modules.incidents.review_service import get_pending_report_queue

router = APIRouter(prefix="/staff/reports", tags=["Staff reports"])

ReportReader = Annotated[
    AuthenticatedSession,
    Depends(require_staff_permission(Permission.REPORTS_READ)),
]

ReportReviewer = Annotated[
    AuthenticatedSession,
    Depends(
        require_staff_permission(
            Permission.REPORTS_REVIEW,
            mutation=True,
        )
    ),
]


def review_http_error(
    error: PermissionDeniedError
    | ReportNotFoundError
    | ReportReviewConflictError
    | InvalidApprovedIncidentError,
) -> HTTPException:
    if isinstance(error, PermissionDeniedError):
        status_code = 403
    elif isinstance(error, ReportNotFoundError):
        status_code = 404
    elif isinstance(error, ReportReviewConflictError):
        status_code = 409
    else:
        status_code = 422

    return HTTPException(
        status_code=status_code,
        headers=NO_STORE_HEADERS,
    )


@router.get("", response_model=ReportQueueResponse)
def get_report_queue(
    query: Annotated[ReportQueueQuery, Query()],
    response: Response,
    authenticated: ReportReader,
    session: ReportSession,
) -> ReportQueueResponse:
    try:
        with session.begin():
            result = get_pending_report_queue(
                session,
                authenticated,
                query,
            )
    except PermissionDeniedError as error:
        raise HTTPException(
            status_code=403,
            headers=NO_STORE_HEADERS,
        ) from error

    response.headers["Cache-Control"] = "no-store"
    return result


@router.post("/{report_id}/verify", response_model=ReportReviewResponse)
def post_verify_report(
    report_id: UUID,
    data: VerifyReportInput,
    request: Request,
    response: Response,
    authenticated: ReportReviewer,
    session: ReportSession,
    clock: IdentityClock,
) -> ReportReviewResponse:
    try:
        result = verify_report(
            session=session,
            authenticated=authenticated,
            report_id=report_id,
            data=data,
            request_id=request.state.request_id,
            now=clock(),
        )
    except (
        PermissionDeniedError,
        ReportNotFoundError,
        ReportReviewConflictError,
        InvalidApprovedIncidentError,
    ) as error:
        raise review_http_error(error) from error

    response.headers["Cache-Control"] = "no-store"
    return result


@router.post("/{report_id}/reject", response_model=ReportReviewResponse)
def post_reject_report(
    report_id: UUID,
    data: RejectReportInput,
    request: Request,
    response: Response,
    authenticated: ReportReviewer,
    session: ReportSession,
    clock: IdentityClock,
) -> ReportReviewResponse:
    try:
        result = reject_report(
            session=session,
            authenticated=authenticated,
            report_id=report_id,
            data=data,
            request_id=request.state.request_id,
            now=clock(),
        )
    except (
        PermissionDeniedError,
        ReportNotFoundError,
        ReportReviewConflictError,
        InvalidApprovedIncidentError,
    ) as error:
        raise review_http_error(error) from error

    response.headers["Cache-Control"] = "no-store"
    return result
