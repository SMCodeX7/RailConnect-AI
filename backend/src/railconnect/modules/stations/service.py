from sqlalchemy.orm import Session

from railconnect.modules.stations.repository import list_stations
from railconnect.modules.stations.schemas import (
    StationListResponse,
    StationResponse,
)


def search_stations(
    session: Session,
    search: str | None,
    limit: int,
    offset: int,
) -> StationListResponse:
    normalized_search = search.strip() if search is not None else None
    stations, total = list_stations(
        session,
        normalized_search,
        limit,
        offset,
    )

    return StationListResponse(
        items=[StationResponse.model_validate(station) for station in stations],
        total=total,
        limit=limit,
        offset=offset,
    )
