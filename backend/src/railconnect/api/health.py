from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from railconnect.db.dependencies import DatabaseSession
from railconnect.modules.stations.models import Station

router = APIRouter(prefix="/health", tags=["Health"])


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadinessResponse(BaseModel):
    status: Literal["ready"] = "ready"


@router.get("/live", response_model=LivenessResponse)
def check_liveness() -> LivenessResponse:
    return LivenessResponse()


@router.get("/ready", response_model=ReadinessResponse)
def check_readiness(session: DatabaseSession) -> ReadinessResponse:
    try:
        session.scalar(select(Station.id).limit(1))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503) from exc

    return ReadinessResponse()
