import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from railconnect.core.config import Settings


@pytest.fixture(autouse=True)
def clear_settings_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in tuple(os.environ):
        if name.startswith("RAILCONNECT_"):
            monkeypatch.delenv(name)


def test_environment_overrides_dotenv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        'RAILCONNECT_APP_NAME="File API"\nRAILCONNECT_ENVIRONMENT=test\nRAILCONNECT_DEBUG=false\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("RAILCONNECT_APP_NAME", "Environment API")

    settings = Settings(_env_file=env_file)

    assert settings.app_name == "Environment API"
    assert settings.environment == "test"
    assert settings.debug is False


def test_production_rejects_debug_mode() -> None:
    with pytest.raises(
        ValidationError,
        match="Debug mode must be disabled in production",
    ):
        Settings(_env_file=None, environment="production", debug=True)


def test_production_accepts_secure_configuration() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        debug=False,
        session_cookie_secure=True,
        trusted_origins=["https://railconnect.example"],
    )

    assert settings.environment == "production"
    assert settings.debug is False
    assert settings.session_cookie_secure is True


def test_invalid_debug_value_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RAILCONNECT_DEBUG", "invalid")

    with pytest.raises(ValidationError, match="debug"):
        Settings(_env_file=None)


def test_production_rejects_insecure_cookies() -> None:
    with pytest.raises(ValidationError, match="must use Secure"):
        Settings(
            _env_file=None,
            environment="production",
            session_cookie_secure=False,
            trusted_origins=["https://railconnect.example"],
        )


def test_production_rejects_http_origins() -> None:
    with pytest.raises(ValidationError, match="must use HTTPS"):
        Settings(
            _env_file=None,
            environment="production",
            trusted_origins=["http://localhost:5173"],
        )


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "https://*.example.com",
        "https://example.com/login",
        "https://user:password@example.com",
        "https://example.com?query=value",
        "https://example.com#fragment",
        "http://example.com",
    ],
)
def test_invalid_origins_are_rejected(origin: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, trusted_origins=[origin])


def test_origins_are_normalized_and_deduplicated() -> None:
    settings = Settings(
        _env_file=None,
        trusted_origins=[
            "https://Example.COM:443",
            "https://example.com",
        ],
    )

    assert settings.trusted_origins == ["https://example.com"]


def test_idle_timeout_cannot_exceed_session_lifetime() -> None:
    with pytest.raises(ValidationError, match="cannot exceed"):
        Settings(
            _env_file=None,
            session_ttl_seconds=300,
            session_idle_timeout_seconds=600,
        )


def test_prefixed_cookies_require_secure() -> None:
    with pytest.raises(ValidationError, match="require Secure"):
        Settings(
            _env_file=None,
            session_cookie_name="__Host-railconnect",
            session_cookie_secure=False,
        )


def test_session_lifetime_has_an_upper_bound() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, session_ttl_seconds=86401)


def test_origins_can_be_loaded_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "RAILCONNECT_TRUSTED_ORIGINS",
        '["https://railconnect.example"]',
    )

    settings = Settings(_env_file=None)

    assert settings.trusted_origins == ["https://railconnect.example"]
