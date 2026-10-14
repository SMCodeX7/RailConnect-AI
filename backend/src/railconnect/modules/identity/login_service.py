from collections.abc import Callable
from datetime import datetime
from functools import lru_cache
from secrets import token_urlsafe

from sqlalchemy.orm import Session

from railconnect.core.clock import utc_now
from railconnect.core.config import Settings
from railconnect.modules.identity.auth_schemas import LoginInput
from railconnect.modules.identity.errors import AuthenticationError, LoginRateLimitError
from railconnect.modules.identity.login_repository import (
    get_credentials,
    get_login_user_for_update,
)
from railconnect.modules.identity.passwords import (
    get_password_hasher,
    password_needs_rehash,
    verify_password,
)
from railconnect.modules.identity.rate_limit_service import consume_login_attempt
from railconnect.modules.identity.session_service import CreatedSession, create_staff_session


@lru_cache(maxsize=1)
def _dummy_password_hash() -> str:
    return get_password_hasher().hash(token_urlsafe(32))


def login_staff(
    session: Session,
    data: LoginInput,
    client_key: str,
    settings: Settings,
    clock: Callable[[], datetime] = utc_now,
) -> CreatedSession:
    if session.in_transaction():
        raise ValueError("Login requires a fresh session without an active transaction.")

    with session.begin():
        decision = consume_login_attempt(
            session,
            client_key,
            data.username,
            settings,
            clock(),
        )

    if not decision.allowed:
        raise LoginRateLimitError(decision.retry_after)

    with session.begin():
        credentials = get_credentials(session, data.username)

    password = data.password.get_secret_value()
    encoded_hash = credentials.password_hash if credentials is not None else _dummy_password_hash()
    verified = verify_password(encoded_hash, password)

    if credentials is None or not credentials.is_active or not verified:
        raise AuthenticationError("Authentication failed.")

    replacement_hash = (
        get_password_hasher().hash(password) if password_needs_rehash(encoded_hash) else None
    )

    with session.begin():
        user = get_login_user_for_update(session, credentials.user_id)

        if (
            user is None
            or not user.is_active
            or user.username != data.username
            or user.auth_version != credentials.auth_version
            or user.password_hash != credentials.password_hash
        ):
            raise AuthenticationError("Authentication failed.")

        if replacement_hash is not None:
            user.password_hash = replacement_hash
            session.flush()

        return create_staff_session(
            session,
            user.id,
            settings,
            clock(),
        )
