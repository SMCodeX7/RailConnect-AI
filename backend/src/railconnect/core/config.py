from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
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
    database_url: SecretStr | None = None

    session_cookie_name: str = Field(
        default="railconnect_session",
        pattern=r"^[A-Za-z0-9_-]{1,64}$",
    )
    session_cookie_secure: bool = True
    session_ttl_seconds: int = Field(default=28800, ge=300, le=86400)
    session_idle_timeout_seconds: int = Field(default=1800, ge=60, le=86400)

    trusted_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        min_length=1,
        max_length=10,
    )

    login_rate_window_seconds: int = Field(default=300, ge=60, le=3600)
    login_client_max_attempts: int = Field(default=30, ge=1, le=1000)
    login_account_max_attempts: int = Field(default=5, ge=1, le=100)
    report_rate_window_seconds: int = Field(default=3600, ge=60, le=86400)
    report_client_max_attempts: int = Field(default=5, ge=1, le=100)

    @field_validator("trusted_origins")
    @classmethod
    def validate_origins(cls, values: list[str]) -> list[str]:
        origins: list[str] = []

        for value in values:
            parsed = urlsplit(value.strip())

            if (
                parsed.scheme not in {"http", "https"}
                or parsed.hostname is None
                or "*" in parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(
                    "Trusted origins must be explicit HTTP(S) origins without paths or credentials."
                )

            host = parsed.hostname.lower()
            port = parsed.port

            if parsed.scheme == "http" and host not in {
                "localhost",
                "127.0.0.1",
                "::1",
            }:
                raise ValueError("HTTP trusted origins are limited to local development.")

            authority = f"[{host}]" if ":" in host else host
            default_port = 443 if parsed.scheme == "https" else 80

            if port is not None and port != default_port:
                authority = f"{authority}:{port}"

            origin = f"{parsed.scheme}://{authority}"
            if origin not in origins:
                origins.append(origin)

        return origins

    @model_validator(mode="after")
    def validate_security_settings(self) -> Self:
        if self.environment == "production" and self.debug:
            raise ValueError("Debug mode must be disabled in production.")

        if self.session_idle_timeout_seconds > self.session_ttl_seconds:
            raise ValueError("Session idle timeout cannot exceed its absolute lifetime.")

        if self.session_cookie_name.startswith(("__Host-", "__Secure-")):
            if not self.session_cookie_secure:
                raise ValueError("Prefixed session cookies require Secure.")

        if self.environment == "production":
            if not self.session_cookie_secure:
                raise ValueError("Production session cookies must use Secure.")

            if any(not origin.startswith("https://") for origin in self.trusted_origins):
                raise ValueError("Production trusted origins must use HTTPS.")

        return self
