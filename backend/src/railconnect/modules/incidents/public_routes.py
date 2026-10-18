from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response

from railconnect.modules.identity.dependencies import NO_STORE_HEADERS
from railconnect.modules.incidents.dependencies import ReportSession
from railconnect.modules.incidents.errors import IncidentNotFoundError
from railconnect.modules.incidents.public_schemas import (
    PublicIncidentListResponse,
    PublicIncidentQuery,
    PublicIncidentResponse,
)
from railconnect.modules.incidents.public_service import (
    get_public_incident,
    list_public_incidents,
)

router = APIRouter(
    prefix="/incidents",
    tags=["Public incidents"],
)


@router.get("", response_model=PublicIncidentListResponse)
def read_public_incidents(
    query: Annotated[PublicIncidentQuery, Query()],
    response: Response,
    session: ReportSession,
) -> PublicIncidentListResponse:
    with session.begin():
        result = list_public_incidents(session, query)

    response.headers.update(NO_STORE_HEADERS)
    return result


@router.get(
    "/{incident_id}",
    response_model=PublicIncidentResponse,
)
def read_public_incident(
    incident_id: UUID,
    response: Response,
    session: ReportSession,
) -> PublicIncidentResponse:
    try:
        with session.begin():
            result = get_public_incident(session, incident_id)
    except IncidentNotFoundError as error:
        raise HTTPException(
            status_code=404,
            headers=NO_STORE_HEADERS,
        ) from error

    response.headers.update(NO_STORE_HEADERS)
    return result
