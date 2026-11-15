from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AssistantQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=500)


class PolicyCitation(BaseModel):
    source_id: str
    source_version: str
    chunk_id: str
    title: str


class AssistantAnswer(BaseModel):
    status: Literal["answered", "unavailable"]
    answer: str
    citations: list[PolicyCitation]
