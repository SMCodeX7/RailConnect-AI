from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class IncidentAuditQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10000)


class IncidentAuditEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    report_id: UUID
    incident_id: UUID | None
    revision_id: UUID | None
    actor_id: UUID
    action: str
    reason: str
    request_id: str
    report_version: int
    incident_version: int | None
    occurred_at: AwareDatetime


class IncidentAuditHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: UUID
    items: list[IncidentAuditEventResponse]
    total: int
    limit: int
    offset: int
