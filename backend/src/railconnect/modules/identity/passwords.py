from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

MIN_PASSWORD_LENGTH = 15
MAX_PASSWORD_LENGTH = 128


@lru_cache(maxsize=1)
def get_password_hasher() -> PasswordHasher:
    return PasswordHasher()


def validate_new_password(password: str) -> None:
    if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
        raise ValueError(
            f"Passwords must contain between "
            f"{MIN_PASSWORD_LENGTH} and {MAX_PASSWORD_LENGTH} characters."
        )


def hash_password(password: str) -> str:
    validate_new_password(password)
    return get_password_hasher().hash(password)


def verify_password(encoded_hash: str, password: str) -> bool:
    if not password or len(password) > MAX_PASSWORD_LENGTH:
        return False

    if not encoded_hash or len(encoded_hash) > 512:
        return False

    try:
        return get_password_hasher().verify(encoded_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def password_needs_rehash(encoded_hash: str) -> bool:
    return get_password_hasher().check_needs_rehash(encoded_hash)
