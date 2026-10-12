from datetime import date, time
from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from railconnect.modules.stations.schemas import StationResponse


class JourneySearchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    departure_station_id: UUID
    arrival_station_id: UUID
    travel_date: date
    arrive_before: time | None = None
    arrival_date: date | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_search(self) -> Self:
        if self.departure_station_id == self.arrival_station_id:
            raise ValueError("Departure and arrival stations must be different.")

        if self.arrival_date is not None:
            if self.arrive_before is None:
                raise ValueError("An arrival date requires an arrival deadline.")

            if self.arrival_date < self.travel_date:
                raise ValueError("The arrival date cannot precede the boarding date.")

        if self.arrive_before is not None and self.arrive_before.tzinfo is not None:
            raise ValueError("Supply a local arrival time without a timezone offset.")

        return self


class JourneyResponse(BaseModel):
    run_id: UUID
    service_date: date
    run_version: int = Field(gt=0)
    run_status: Literal["scheduled", "restricted"]
    departure_stop_sequence: int = Field(gt=0)
    arrival_stop_sequence: int = Field(gt=0)
    service_id: UUID
    service_code: str
    service_name: str
    source_ref: str
    departure_station: StationResponse
    arrival_station: StationResponse
    departure_at: AwareDatetime
    arrival_at: AwareDatetime
    duration_minutes: int = Field(gt=0)


class JourneyListResponse(BaseModel):
    data_kind: Literal["demonstration"] = "demonstration"
    timezone: Literal["Asia/Colombo"] = "Asia/Colombo"
    departure_station_id: UUID
    arrival_station_id: UUID
    travel_date: date
    items: list[JourneyResponse]
    total: int
    limit: int
    offset: int


class JourneyDetailQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    departure_stop_sequence: int | None = Field(default=None, gt=0)
    arrival_stop_sequence: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_segment(self) -> Self:
        departure = self.departure_stop_sequence
        arrival = self.arrival_stop_sequence

        if (departure is None) != (arrival is None):
            raise ValueError("Supply both segment stop sequences or neither.")

        if departure is not None and arrival is not None and departure >= arrival:
            raise ValueError("Departure must precede arrival.")

        return self


class JourneyStopResponse(BaseModel):
    stop_sequence: int = Field(gt=0)
    station: StationResponse
    scheduled_arrival_at: AwareDatetime | None
    scheduled_departure_at: AwareDatetime | None
    pickup_allowed: bool
    dropoff_allowed: bool


class JourneySegmentResponse(BaseModel):
    departure_stop_sequence: int = Field(gt=0)
    arrival_stop_sequence: int = Field(gt=0)
    departure_station: StationResponse
    arrival_station: StationResponse
    scheduled_departure_at: AwareDatetime
    scheduled_arrival_at: AwareDatetime
    duration_minutes: int = Field(gt=0)


class JourneyDetailResponse(BaseModel):
    data_kind: Literal["demonstration"] = "demonstration"
    timezone: Literal["Asia/Colombo"] = "Asia/Colombo"
    run_id: UUID
    service_id: UUID
    service_code: str
    service_name: str
    service_date: date
    run_version: int = Field(gt=0)
    run_status: Literal["scheduled", "cancelled", "restricted"]
    source_ref: str
    stops: list[JourneyStopResponse] = Field(min_length=2)
    selected_segment: JourneySegmentResponse | None
