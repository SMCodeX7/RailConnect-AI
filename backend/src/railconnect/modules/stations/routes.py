from typing import Annotated

from fastapi import APIRouter, Query

from railconnect.db.dependencies import DatabaseSession
from railconnect.modules.stations.schemas import StationListResponse
from railconnect.modules.stations.service import search_stations

router = APIRouter(prefix="/stations", tags=["Stations"])


@router.get("", response_model=StationListResponse)
def get_stations(
    session: DatabaseSession,
    q: Annotated[
        str | None,
        Query(min_length=1, max_length=120, pattern=r"\S"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> StationListResponse:
    return search_stations(session, q, limit, offset)
