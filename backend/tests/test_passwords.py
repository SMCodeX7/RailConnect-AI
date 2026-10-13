import pytest

from railconnect.modules.identity.passwords import (
    hash_password,
    password_needs_rehash,
    verify_password,
)


def test_hashes_use_argon2id_and_random_salts() -> None:
    password = "A long fictional staff passphrase"
    first = hash_password(password)
    second = hash_password(password)

    assert first.startswith("$argon2id$")
    assert second.startswith("$argon2id$")
    assert first != second
    assert password not in first
    assert verify_password(first, password) is True
    assert verify_password(second, password) is True


def test_incorrect_password_is_rejected() -> None:
    encoded = hash_password("A long fictional staff passphrase")

    assert verify_password(encoded, "A different staff passphrase") is False


def test_password_whitespace_is_preserved() -> None:
    password = "  A staff passphrase with spaces  "
    encoded = hash_password(password)

    assert verify_password(encoded, password) is True
    assert verify_password(encoded, password.strip()) is False


@pytest.mark.parametrize("password", ["", "x" * 14, "x" * 129])
def test_provisioning_rejects_invalid_lengths(password: str) -> None:
    with pytest.raises(ValueError, match="between 15 and 128"):
        hash_password(password)


@pytest.mark.parametrize("password", ["x" * 15, "x" * 128])
def test_provisioning_accepts_length_boundaries(password: str) -> None:
    encoded = hash_password(password)

    assert verify_password(encoded, password) is True


def test_login_rejects_empty_and_oversized_passwords() -> None:
    encoded = hash_password("A long fictional staff passphrase")

    assert verify_password(encoded, "") is False
    assert verify_password(encoded, "x" * 129) is False


def test_invalid_encoded_hash_is_rejected() -> None:
    assert verify_password("not-an-encoded-hash", "A staff passphrase") is False


def test_current_hash_does_not_require_upgrade() -> None:
    encoded = hash_password("A long fictional staff passphrase")

    assert password_needs_rehash(encoded) is False
