from datetime import date
from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from railconnect.modules.stations.schemas import StationResponse


class JourneySearchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    departure_station_id: UUID
    arrival_station_id: UUID
    travel_date: date
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_stations(self) -> Self:
        if self.departure_station_id == self.arrival_station_id:
            raise ValueError("Departure and arrival stations must be different.")

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
