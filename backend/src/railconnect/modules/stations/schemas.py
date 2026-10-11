from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DemoStation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: str = Field(pattern=r"^DEMO_[A-Z0-9_]{1,15}$")
    name: str = Field(min_length=1, max_length=120)


class DemoStationDataset(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: Literal["demonstration"]
    source_ref: str = Field(min_length=1, max_length=200)
    stations: list[DemoStation] = Field(min_length=1, max_length=1000)
