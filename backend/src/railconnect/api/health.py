from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["Health"])


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"


@router.get("/live", response_model=LivenessResponse)
def check_liveness() -> LivenessResponse:
    return LivenessResponse()
