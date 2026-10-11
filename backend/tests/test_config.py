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


def test_production_accepts_debug_disabled() -> None:
    settings = Settings(_env_file=None, environment="production", debug=False)

    assert settings.environment == "production"
    assert settings.debug is False


def test_invalid_debug_value_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RAILCONNECT_DEBUG", "invalid")

    with pytest.raises(ValidationError, match="debug"):
        Settings(_env_file=None)
