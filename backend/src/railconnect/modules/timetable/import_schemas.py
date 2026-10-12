from dataclasses import dataclass

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from railconnect.modules.timetable.seed_schemas import DemoTimetableDataset


class TimetableSourceMetadata(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    title: str = Field(min_length=1, max_length=200)
    source_uri: str = Field(min_length=1, max_length=500)
    reuse_basis: str = Field(min_length=1, max_length=2000)
    retrieved_at: AwareDatetime | None = None


@dataclass(frozen=True)
class TimetableImportSnapshot:
    dataset: DemoTimetableDataset
    metadata: TimetableSourceMetadata
    content_sha256: str
