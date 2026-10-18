from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from railconnect.modules.identity.dependencies import (
    NO_STORE_HEADERS,
    require_staff_permission,
)
from railconnect.modules.identity.errors import PermissionDeniedError
from railconnect.modules.identity.permissions import Permission
from railconnect.modules.identity.session_service import AuthenticatedSession
from railconnect.modules.incidents.audit_schemas import (
    IncidentAuditHistoryResponse,
    IncidentAuditQuery,
)
from railconnect.modules.incidents.audit_service import get_report_audit_history
from railconnect.modules.incidents.dependencies import ReportSession
from railconnect.modules.incidents.errors import ReportNotFoundError

router = APIRouter(
    prefix="/staff/reports",
    tags=["Staff audit history"],
)

AuditReader = Annotated[
    AuthenticatedSession,
    Depends(require_staff_permission(Permission.AUDIT_READ)),
]


@router.get(
    "/{report_id}/audit",
    response_model=IncidentAuditHistoryResponse,
)
def read_report_audit_history(
    report_id: UUID,
    query: Annotated[IncidentAuditQuery, Query()],
    response: Response,
    authenticated: AuditReader,
    session: ReportSession,
) -> IncidentAuditHistoryResponse:
    try:
        with session.begin():
            result = get_report_audit_history(
                session,
                authenticated,
                report_id,
                query,
            )
    except PermissionDeniedError as error:
        raise HTTPException(
            status_code=403,
            headers=NO_STORE_HEADERS,
        ) from error
    except ReportNotFoundError as error:
        raise HTTPException(
            status_code=404,
            headers=NO_STORE_HEADERS,
        ) from error

    response.headers.update(NO_STORE_HEADERS)
    return result
