import re
from hashlib import sha256
from secrets import token_hex, token_urlsafe

SESSION_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")


def generate_session_token() -> str:
    return token_urlsafe(32)


def generate_csrf_token() -> str:
    return token_hex(32)


def hash_session_token(token: str) -> str:
    if SESSION_TOKEN_PATTERN.fullmatch(token) is None:
        raise ValueError("Invalid session token format.")

    return sha256(token.encode("ascii")).hexdigest()
