from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from railconnect.db.dependencies import DatabaseSession
from railconnect.modules.journeys.errors import InvalidStationSelectionError
from railconnect.modules.journeys.schemas import JourneyListResponse, JourneySearchQuery
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
