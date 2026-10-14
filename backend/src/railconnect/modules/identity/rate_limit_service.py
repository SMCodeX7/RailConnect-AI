from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from math import ceil

from sqlalchemy.orm import Session

from railconnect.core.config import Settings
from railconnect.modules.identity.rate_limit_repository import consume_login_window


@dataclass(frozen=True)
class LoginRateDecision:
    allowed: bool
    retry_after: int


def login_limit_key(scope: str, value: str) -> str:
    return sha256(f"railconnect:login:{scope}:{value}".encode()).hexdigest()


def consume_login_attempt(
    session: Session,
    client_key: str,
    username: str,
    settings: Settings,
    now: datetime,
) -> LoginRateDecision:
    if not session.in_transaction():
        raise ValueError("Login limiting requires a caller-owned transaction.")

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Login limiting requires a timezone-aware clock.")

    client = client_key.strip()
    account = username.strip().lower()

    if not client or len(client) > 128:
        raise ValueError("A bounded client identifier is required.")

    if not account or len(account) > 64:
        raise ValueError("A bounded account identifier is required.")

    timestamp = now.astimezone(UTC)

    client_count, client_expiry = consume_login_window(
        session,
        scope="client",
        key_hash=login_limit_key("client", client),
        now=timestamp,
        window_seconds=settings.login_rate_window_seconds,
        maximum_attempts=settings.login_client_max_attempts,
    )

    if client_count > settings.login_client_max_attempts:
        return LoginRateDecision(
            allowed=False,
            retry_after=max(
                1,
                ceil((client_expiry - timestamp).total_seconds()),
            ),
        )

    account_count, account_expiry = consume_login_window(
        session,
        scope="account",
        key_hash=login_limit_key("account", account),
        now=timestamp,
        window_seconds=settings.login_rate_window_seconds,
        maximum_attempts=settings.login_account_max_attempts,
    )

    if account_count > settings.login_account_max_attempts:
        return LoginRateDecision(
            allowed=False,
            retry_after=max(
                1,
                ceil((account_expiry - timestamp).total_seconds()),
            ),
        )

    return LoginRateDecision(allowed=True, retry_after=0)
