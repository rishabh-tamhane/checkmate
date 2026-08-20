"""Tests for validated Checkmate process configuration."""

import pytest

from checkmate.config import ConfigurationError, Settings


def test_settings_use_approved_defaults() -> None:
    """An empty environment produces the portable runtime defaults."""
    assert Settings.from_environment({}) == Settings(
        host="0.0.0.0",
        port=8000,
        log_level="info",
        public_origin=None,
        request_concurrency_limit=32,
        openai_api_key=None,
    )


def test_settings_accept_valid_overrides() -> None:
    """Supported environment overrides become typed settings."""
    settings = Settings.from_environment(
        {
            "HOST": "127.0.0.1",
            "PORT": "9123",
            "LOG_LEVEL": "DEBUG",
            "PUBLIC_ORIGIN": "https://checkmate.example.test:8443",
            "REQUEST_CONCURRENCY_LIMIT": "64",
            "OPENAI_API_KEY": "test-secret-value",
        }
    )

    assert settings.host == "127.0.0.1"
    assert settings.port == 9123
    assert settings.log_level == "debug"
    assert settings.public_origin == "https://checkmate.example.test:8443"
    assert settings.request_concurrency_limit == 64
    assert settings.openai_api_key == "test-secret-value"


@pytest.mark.parametrize("invalid_port", ["", "not-a-port", "0", "65536"])
def test_settings_reject_invalid_ports(invalid_port: str) -> None:
    """Invalid ports fail before the web process starts."""
    with pytest.raises(ConfigurationError, match="PORT must be an integer"):
        Settings.from_environment({"PORT": invalid_port})


def test_settings_reject_an_invalid_log_level() -> None:
    """Uvicorn receives only an explicitly supported log level."""
    with pytest.raises(ConfigurationError, match="LOG_LEVEL must be one of"):
        Settings.from_environment({"LOG_LEVEL": "verbose"})


def test_settings_reject_an_empty_host() -> None:
    """A process cannot start without a listening interface value."""
    with pytest.raises(ConfigurationError, match="HOST must not be empty"):
        Settings.from_environment({"HOST": "  "})


@pytest.mark.parametrize(
    "invalid_origin",
    [
        "",
        "checkmate.example.test",
        "ftp://checkmate.example.test",
        "https://user@checkmate.example.test",
        "https://checkmate.example.test/",
        "https://checkmate.example.test/path",
        "https://checkmate.example.test?query=1",
        "https://checkmate.example.test#fragment",
        " https://checkmate.example.test",
        "https://checkmate.example.test:70000",
    ],
)
def test_settings_reject_an_invalid_public_origin(invalid_origin: str) -> None:
    """The canonical browser origin must not contain ambiguous URL parts."""
    with pytest.raises(ConfigurationError, match="PUBLIC_ORIGIN must be"):
        Settings.from_environment({"PUBLIC_ORIGIN": invalid_origin})


@pytest.mark.parametrize("invalid_limit", ["", "many", "0", "1001"])
def test_settings_reject_an_invalid_concurrency_limit(invalid_limit: str) -> None:
    """The production server always receives a bounded concurrency value."""
    with pytest.raises(
        ConfigurationError,
        match="REQUEST_CONCURRENCY_LIMIT must be an integer from 1 to 1000",
    ):
        Settings.from_environment({"REQUEST_CONCURRENCY_LIMIT": invalid_limit})


def test_settings_repr_does_not_expose_the_api_key() -> None:
    """Routine settings diagnostics cannot print the configured secret."""
    secret = "test-secret-value"
    settings = Settings.from_environment({"OPENAI_API_KEY": secret})

    assert secret not in repr(settings)
