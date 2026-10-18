from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class ReportQueueQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=10000)


class PendingReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: UUID
    title: str
    narrative: str
    observed_at: AwareDatetime
    submitted_at: AwareDatetime

    run_hint_id: UUID | None
    station_hint_id: UUID | None
    departure_stop_sequence_hint: int | None
    arrival_stop_sequence_hint: int | None

    status: Literal["pending"]
    version: int = Field(ge=1)


class ReportQueueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[PendingReportResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0, le=10000)


class ApprovedIncidentInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    run_id: UUID
    scope_kind: Literal["run", "segment"]

    departure_stop_sequence: int | None = Field(
        default=None,
        ge=1,
        strict=True,
    )
    arrival_stop_sequence: int | None = Field(
        default=None,
        ge=1,
        strict=True,
    )

    impact_kind: Literal["cancellation", "restriction", "delay"]
    estimated_delay_minutes: int | None = Field(
        default=None,
        ge=1,
        le=1440,
        strict=True,
    )

    effective_from: AwareDatetime
    effective_until: AwareDatetime
    public_summary: str = Field(min_length=1, max_length=1000)
    evidence_basis: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_approved_facts(self) -> Self:
        departure = self.departure_stop_sequence
        arrival = self.arrival_stop_sequence

        if self.scope_kind == "run":
            if departure is not None or arrival is not None:
                raise ValueError("Whole-run scope cannot contain segment endpoints.")
        else:
            if departure is None or arrival is None:
                raise ValueError("Segment scope requires both stop sequences.")

            if arrival <= departure:
                raise ValueError("The arrival stop must follow the departure stop.")

        if self.impact_kind == "cancellation" and self.scope_kind != "run":
            raise ValueError("Cancellation requires whole-run scope.")

        if self.impact_kind == "delay":
            if self.estimated_delay_minutes is None:
                raise ValueError("Delay impact requires an estimated delay.")
        elif self.estimated_delay_minutes is not None:
            raise ValueError("Only delay impact can contain estimated delay minutes.")

        if self.effective_until <= self.effective_from:
            raise ValueError("The effective end must follow the effective start.")

        return self


class VerifyReportInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    expected_version: int = Field(ge=1, strict=True)
    reason: str = Field(min_length=1, max_length=2000)
    approved: ApprovedIncidentInput


class RejectReportInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    expected_version: int = Field(ge=1, strict=True)
    reason: str = Field(min_length=1, max_length=2000)


class ReportReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: UUID
    status: Literal["verified", "rejected"]
    report_version: int = Field(ge=1)

    incident_id: UUID | None = None
    revision_id: UUID | None = None
    incident_version: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_result_references(self) -> Self:
        references = (
            self.incident_id,
            self.revision_id,
            self.incident_version,
        )

        if self.status == "verified":
            if any(value is None for value in references):
                raise ValueError("Verification requires incident and revision references.")
        elif any(value is not None for value in references):
            raise ValueError("Rejection cannot contain incident references.")

        return self
