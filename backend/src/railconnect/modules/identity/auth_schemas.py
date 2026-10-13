from typing import Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from railconnect.modules.identity.schemas import Actor


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(pattern=r"^[a-z][a-z0-9_.-]{2,63}$")
    password: SecretStr

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @model_validator(mode="after")
    def validate_password_size(self) -> Self:
        if not 1 <= len(self.password.get_secret_value()) <= 128:
            raise ValueError("Password length is invalid.")
        return self


class StaffSessionResponse(BaseModel):
    actor: Actor
    csrf_token: str
    expires_at: AwareDatetime
