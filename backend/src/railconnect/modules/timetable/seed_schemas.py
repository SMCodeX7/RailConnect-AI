from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DemoModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class DemoStop(DemoModel):
    station_code: str = Field(pattern=r"^DEMO_[A-Z0-9_]{1,15}$")
    arrival_minutes: int | None = Field(
        default=None,
        ge=0,
        le=4319,
        strict=True,
    )
    departure_minutes: int | None = Field(
        default=None,
        ge=0,
        le=4319,
        strict=True,
    )
    pickup_allowed: bool = Field(default=False, strict=True)
    dropoff_allowed: bool = Field(default=False, strict=True)

    @model_validator(mode="before")
    @classmethod
    def apply_demo_permission_defaults(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value

        values = dict(value)
        values.setdefault(
            "pickup_allowed",
            values.get("departure_minutes") is not None,
        )
        values.setdefault(
            "dropoff_allowed",
            values.get("arrival_minutes") is not None,
        )
        return values

    @model_validator(mode="after")
    def validate_times_and_permissions(self) -> Self:
        if self.arrival_minutes is None and self.departure_minutes is None:
            raise ValueError("A stop must have an arrival or departure time.")

        if (
            self.arrival_minutes is not None
            and self.departure_minutes is not None
            and self.departure_minutes < self.arrival_minutes
        ):
            raise ValueError("Departure cannot occur before arrival.")

        if self.pickup_allowed and self.departure_minutes is None:
            raise ValueError("Boarding requires a departure time.")

        if self.dropoff_allowed and self.arrival_minutes is None:
            raise ValueError("Alighting requires an arrival time.")

        return self


class DemoService(DemoModel):
    code: str = Field(pattern=r"^DEMO_[A-Z0-9_]{1,35}$")
    name: str = Field(min_length=1, max_length=120)
    operating_days: int = Field(ge=1, le=127, strict=True)
    stops: list[DemoStop] = Field(min_length=2, max_length=100)

    @model_validator(mode="after")
    def validate_stops(self) -> Self:
        codes = [stop.station_code for stop in self.stops]
        if len(codes) != len(set(codes)):
            raise ValueError("Demonstration services cannot repeat a station.")

        first = self.stops[0]
        last = self.stops[-1]

        if first.arrival_minutes is not None or first.departure_minutes is None:
            raise ValueError("The first stop must have only a departure time.")

        if first.departure_minutes >= 1440:
            raise ValueError("The service must start on its starting date.")

        if last.arrival_minutes is None or last.departure_minutes is not None:
            raise ValueError("The final stop must have only an arrival time.")

        for stop in self.stops[1:-1]:
            if stop.arrival_minutes is None or stop.departure_minutes is None:
                raise ValueError("Intermediate stops require both times.")

        previous_departure = first.departure_minutes

        for stop in self.stops[1:]:
            if stop.arrival_minutes is None:
                raise ValueError("Subsequent stops require an arrival time.")

            if stop.arrival_minutes <= previous_departure:
                raise ValueError("Each arrival must follow the previous departure.")

            if stop.departure_minutes is not None:
                previous_departure = stop.departure_minutes

        return self


class DemoTimetableDataset(DemoModel):
    kind: Literal["demonstration"]
    timezone: Literal["Asia/Colombo"]
    source_ref: str = Field(min_length=1, max_length=200)
    valid_from: date
    valid_until: date
    services: list[DemoService] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_dataset(self) -> Self:
        if self.valid_until < self.valid_from:
            raise ValueError("The validity end date cannot precede its start date.")

        codes = [service.code for service in self.services]
        if len(codes) != len(set(codes)):
            raise ValueError("Service codes must be unique.")

        return self
