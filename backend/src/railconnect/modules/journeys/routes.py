from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import ValidationError

from railconnect.db.dependencies import DatabaseSession
from railconnect.modules.journeys.alternatives_service import find_journey_alternatives
from railconnect.modules.journeys.detail_service import get_journey_detail
from railconnect.modules.journeys.errors import (
    InvalidStationSelectionError,
    JourneyDataUnavailableError,
    JourneyNotFoundError,
)
from railconnect.modules.journeys.schemas import (
    JourneyAlternativesQuery,
    JourneyAlternativesResponse,
    JourneyDetailQuery,
    JourneyDetailResponse,
    JourneyListResponse,
    JourneySearchQuery,
)
from railconnect.modules.journeys.service import search_journeys

router = APIRouter(prefix="/journeys", tags=["Journeys"])


@router.get("", response_model=JourneyListResponse)
def get_journeys(
    query: Annotated[JourneySearchQuery, Query()],
    session: DatabaseSession,
) -> JourneyListResponse:
    try:
        return search_journeys(session, query)
    except InvalidStationSelectionError as exc:
        raise HTTPException(status_code=404) from exc


@router.get("/{run_id}", response_model=JourneyDetailResponse)
def get_journey(
    run_id: UUID,
    query: Annotated[JourneyDetailQuery, Query()],
    session: DatabaseSession,
) -> JourneyDetailResponse:
    try:
        return get_journey_detail(session, run_id, query)
    except JourneyNotFoundError as exc:
        raise HTTPException(status_code=404) from exc
    except JourneyDataUnavailableError as exc:
        raise HTTPException(status_code=503) from exc


@router.get("/{run_id}/alternatives", response_model=JourneyAlternativesResponse)
def get_alternatives(
    run_id: UUID,
    query: Annotated[JourneyAlternativesQuery, Query()],
    response: Response,
    session: DatabaseSession,
) -> JourneyAlternativesResponse:
    try:
        result = find_journey_alternatives(session, run_id, query)
    except ValidationError as exc:
        raise HTTPException(status_code=422) from exc
    except (InvalidStationSelectionError, JourneyNotFoundError) as exc:
        raise HTTPException(status_code=404) from exc
    except JourneyDataUnavailableError as exc:
        raise HTTPException(status_code=503) from exc

    response.headers["Cache-Control"] = "no-store"
    return result
