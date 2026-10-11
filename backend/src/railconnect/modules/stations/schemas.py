from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DemoStation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: str = Field(pattern=r"^DEMO_[A-Z0-9_]{1,15}$")
    name: str = Field(min_length=1, max_length=120)


class DemoStationDataset(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: Literal["demonstration"]
    source_ref: str = Field(min_length=1, max_length=200)
    stations: list[DemoStation] = Field(min_length=1, max_length=1000)


class StationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    source_ref: str
    is_active: bool


class StationListResponse(BaseModel):
    items: list[StationResponse]
    total: int
    limit: int
    offset: int
