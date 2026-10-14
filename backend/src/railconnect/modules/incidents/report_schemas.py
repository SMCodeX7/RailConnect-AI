from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class SubmitReportInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    title: str = Field(min_length=1, max_length=160)
    narrative: str = Field(min_length=1, max_length=4000)
    observed_at: AwareDatetime

    run_hint_id: UUID | None = None
    station_hint_id: UUID | None = None

    departure_stop_sequence_hint: int | None = Field(
        default=None,
        ge=1,
        strict=True,
    )
    arrival_stop_sequence_hint: int | None = Field(
        default=None,
        ge=1,
        strict=True,
    )

    @model_validator(mode="after")
    def validate_segment_hints(self) -> Self:
        departure = self.departure_stop_sequence_hint
        arrival = self.arrival_stop_sequence_hint

        if departure is None and arrival is None:
            return self

        if departure is None or arrival is None:
            raise ValueError("Both segment stop sequences must be supplied.")

        if self.run_hint_id is None:
            raise ValueError("Segment hints require a dated service run.")

        if arrival <= departure:
            raise ValueError("The arrival stop must follow the departure stop.")

        return self


class ReportSubmissionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: UUID
    status: Literal["pending"]
    submitted_at: AwareDatetime
    message: str = "Your report was received and awaits staff review."
