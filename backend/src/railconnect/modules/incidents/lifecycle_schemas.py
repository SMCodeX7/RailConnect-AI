from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from railconnect.modules.incidents.review_schemas import ApprovedIncidentInput


class AmendIncidentInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    expected_version: int = Field(ge=1, strict=True)
    reason: str = Field(min_length=1, max_length=2000)
    approved: ApprovedIncidentInput


class ResolveIncidentInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    expected_version: int = Field(ge=1, strict=True)
    reason: str = Field(min_length=1, max_length=2000)
    resolution_effective_at: AwareDatetime


class IncidentLifecycleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: UUID
    originating_report_id: UUID
    status: Literal["active", "resolved"]
    incident_version: int = Field(ge=1)
    current_revision_number: int = Field(ge=1)
    current_revision_id: UUID
