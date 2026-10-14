from pydantic import BaseModel, ConfigDict, Field, field_validator

from railconnect.modules.identity.permissions import RoleCode


class ProvisionStaffInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    username: str = Field(pattern=r"^[a-z][a-z0-9_.-]{2,63}$")
    display_name: str = Field(min_length=1, max_length=100)
    role: RoleCode

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value
