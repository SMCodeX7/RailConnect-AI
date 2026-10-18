from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class PublicIncidentQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10000)


class PublicIncidentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: UUID
    incident_version: int = Field(ge=1)
    revision_id: UUID
    revision_number: int = Field(ge=1)
    status: Literal["active", "resolved"]

    run_id: UUID
    timetable_source_ref: str

    scope_kind: Literal["run", "segment"]
    departure_stop_sequence: int | None
    arrival_stop_sequence: int | None

    impact_kind: Literal["cancellation", "restriction", "delay"]
    estimated_delay_minutes: int | None

    effective_from: AwareDatetime
    effective_until: AwareDatetime
    public_summary: str
    verified_at: AwareDatetime
    resolution_effective_at: AwareDatetime | None


class PublicIncidentListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[PublicIncidentResponse]
    total: int
    limit: int
    offset: int
