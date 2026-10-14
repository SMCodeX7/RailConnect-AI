from pydantic import BaseModel, ConfigDict

from railconnect.modules.identity.permissions import Permission


class Actor(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: str
    username: str
    display_name: str
    roles: tuple[str, ...]
    permissions: frozenset[Permission]
