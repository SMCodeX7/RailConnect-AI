from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RAILCONNECT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        str_strip_whitespace=True,
    )

    app_name: str = Field(default="RailConnect AI", min_length=1, max_length=100)
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False

    @model_validator(mode="after")
    def validate_debug_mode(self) -> Self:
        if self.environment == "production" and self.debug:
            raise ValueError("Debug mode must be disabled in production.")
        return self
