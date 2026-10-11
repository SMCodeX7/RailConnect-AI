from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from railconnect.modules.stations.models import Station


def list_stations(
    session: Session,
    search: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Station], int]:
    query = select(Station).where(Station.is_active.is_(True))

    if search is not None:
        query = query.where(
            or_(
                func.lower(Station.name).contains(search.lower(), autoescape=True),
                func.lower(Station.code).contains(search.lower(), autoescape=True),
            )
        )

    total = session.scalar(select(func.count()).select_from(query.subquery()))
    stations = session.scalars(
        query.order_by(func.lower(Station.name), Station.code).limit(limit).offset(offset)
    ).all()

    return list(stations), int(total or 0)
