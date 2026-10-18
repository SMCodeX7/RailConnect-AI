from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response

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
    IncidentConflictError,
    IncidentHistoryError,
    IncidentNotFoundError,
    InvalidApprovedIncidentError,
    InvalidIncidentLifecycleError,
)
from railconnect.modules.incidents.lifecycle_schemas import (
    AmendIncidentInput,
    IncidentLifecycleResponse,
    ResolveIncidentInput,
)
from railconnect.modules.incidents.lifecycle_service import (
    amend_incident,
    resolve_incident,
)

router = APIRouter(prefix="/staff/incidents", tags=["Staff incidents"])

IncidentEditor = Annotated[
    AuthenticatedSession,
    Depends(
        require_staff_permission(
            Permission.INCIDENTS_EDIT,
            mutation=True,
        )
    ),
]

IncidentResolver = Annotated[
    AuthenticatedSession,
    Depends(
        require_staff_permission(
            Permission.INCIDENTS_RESOLVE,
            mutation=True,
        )
    ),
]


def lifecycle_http_error(
    error: PermissionDeniedError
    | IncidentNotFoundError
    | IncidentConflictError
    | InvalidApprovedIncidentError
    | InvalidIncidentLifecycleError
    | IncidentHistoryError,
) -> HTTPException:
    if isinstance(error, PermissionDeniedError):
        status_code = 403
    elif isinstance(error, IncidentNotFoundError):
        status_code = 404
    elif isinstance(error, IncidentConflictError):
        status_code = 409
    elif isinstance(error, IncidentHistoryError):
        status_code = 503
    else:
        status_code = 422

    return HTTPException(
        status_code=status_code,
        headers=NO_STORE_HEADERS,
    )


@router.post("/{incident_id}/amend", response_model=IncidentLifecycleResponse)
def post_amend_incident(
    incident_id: UUID,
    data: AmendIncidentInput,
    request: Request,
    response: Response,
    authenticated: IncidentEditor,
    session: ReportSession,
    clock: IdentityClock,
) -> IncidentLifecycleResponse:
    try:
        result = amend_incident(
            session=session,
            authenticated=authenticated,
            incident_id=incident_id,
            data=data,
            request_id=request.state.request_id,
            now=clock(),
        )
    except (
        PermissionDeniedError,
        IncidentNotFoundError,
        IncidentConflictError,
        InvalidApprovedIncidentError,
        InvalidIncidentLifecycleError,
        IncidentHistoryError,
    ) as error:
        raise lifecycle_http_error(error) from error

    response.headers["Cache-Control"] = "no-store"
    return result


@router.post("/{incident_id}/resolve", response_model=IncidentLifecycleResponse)
def post_resolve_incident(
    incident_id: UUID,
    data: ResolveIncidentInput,
    request: Request,
    response: Response,
    authenticated: IncidentResolver,
    session: ReportSession,
    clock: IdentityClock,
) -> IncidentLifecycleResponse:
    try:
        result = resolve_incident(
            session=session,
            authenticated=authenticated,
            incident_id=incident_id,
            data=data,
            request_id=request.state.request_id,
            now=clock(),
        )
    except (
        PermissionDeniedError,
        IncidentNotFoundError,
        IncidentConflictError,
        InvalidApprovedIncidentError,
        InvalidIncidentLifecycleError,
        IncidentHistoryError,
    ) as error:
        raise lifecycle_http_error(error) from error

    response.headers["Cache-Control"] = "no-store"
    return result
