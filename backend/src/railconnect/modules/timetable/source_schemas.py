from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict


class TimetableSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_ref: str
    title: str
    source_uri: str
    reuse_basis: str
    data_kind: Literal["demonstration", "observed"]
    content_sha256: str
    effective_from: date
    effective_until: date
    retrieved_at: AwareDatetime | None
    registered_at: AwareDatetime
