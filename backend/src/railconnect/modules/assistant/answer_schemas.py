from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JourneyLookup(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: Literal["journey"]
    departure: str | None = Field(default=None, min_length=1, max_length=120)
    arrival: str | None = Field(default=None, min_length=1, max_length=120)
    travel_date: date | None = None


class IncidentLookup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["incident"]
    incident_id: UUID | None = None


class AssistantQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=500)
    lookup: Annotated[JourneyLookup | IncidentLookup, Field(discriminator="kind")] | None = None


class PolicyCitation(BaseModel):
    source_id: str
    source_version: str
    chunk_id: str
    title: str


class RecordCitation(BaseModel):
    kind: Literal["journey", "incident"]
    title: str
    href: str
    record_version: int = Field(ge=1)
    revision_id: UUID | None = None


class AssistantAnswer(BaseModel):
    status: Literal["answered", "clarify", "unavailable"]
    answer: str
    citations: list[PolicyCitation | RecordCitation]
