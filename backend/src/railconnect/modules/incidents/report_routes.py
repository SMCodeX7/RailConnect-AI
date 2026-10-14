from fastapi import APIRouter, Depends, HTTPException, Request, Response

from railconnect.modules.identity.dependencies import (
    NO_STORE_HEADERS,
    IdentityClock,
    IdentitySettings,
)
from railconnect.modules.incidents.dependencies import (
    ReportSession,
    ReportSubmitter,
    validate_report_request,
)
from railconnect.modules.incidents.errors import (
    InvalidReportError,
    ReportRateLimitedError,
)
from railconnect.modules.incidents.report_schemas import (
    ReportSubmissionResponse,
    SubmitReportInput,
)
from railconnect.modules.incidents.report_service import submit_report

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post(
    "",
    status_code=201,
    response_model=ReportSubmissionResponse,
    dependencies=[Depends(validate_report_request)],
)
def post_report(
    data: SubmitReportInput,
    request: Request,
    response: Response,
    session: ReportSession,
    settings: IdentitySettings,
    clock: IdentityClock,
    submitted_by_user_id: ReportSubmitter,
) -> ReportSubmissionResponse:
    if request.client is None:
        raise HTTPException(status_code=503, headers=NO_STORE_HEADERS)

    try:
        result = submit_report(
            session=session,
            data=data,
            client_key=request.client.host,
            settings=settings,
            clock=clock,
            submitted_by_user_id=submitted_by_user_id,
        )
    except ReportRateLimitedError as error:
        raise HTTPException(
            status_code=429,
            headers={
                **NO_STORE_HEADERS,
                "Retry-After": str(error.retry_after),
            },
        ) from error
    except InvalidReportError as error:
        raise HTTPException(
            status_code=422,
            headers=NO_STORE_HEADERS,
        ) from error

    response.headers["Cache-Control"] = "no-store"
    return result
