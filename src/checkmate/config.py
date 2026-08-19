"""Validated process configuration for Checkmate."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Final

DEFAULT_HOST: Final = "0.0.0.0"
DEFAULT_PORT: Final = 8000
DEFAULT_LOG_LEVEL: Final = "info"
SUPPORTED_LOG_LEVELS: Final = frozenset(
    {"critical", "error", "warning", "info", "debug", "trace"}
)


class ConfigurationError(ValueError):
    """Report invalid startup configuration without exposing secret values."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Typed settings read once while constructing the web process."""

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    log_level: str = DEFAULT_LOG_LEVEL
    openai_api_key: str | None = field(default=None, repr=False)

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> Settings:
        """Build and validate settings from a supplied or process environment."""
        values = os.environ if environment is None else environment
        host = values.get("HOST", DEFAULT_HOST).strip()
        if not host:
            raise ConfigurationError("HOST must not be empty")

        port = _parse_port(values.get("PORT", str(DEFAULT_PORT)))
        log_level = values.get("LOG_LEVEL", DEFAULT_LOG_LEVEL).strip().lower()
        if log_level not in SUPPORTED_LOG_LEVELS:
            supported = ", ".join(sorted(SUPPORTED_LOG_LEVELS))
            raise ConfigurationError(f"LOG_LEVEL must be one of: {supported}")

        raw_api_key = values.get("OPENAI_API_KEY")
        api_key = raw_api_key if raw_api_key else None
        return cls(
            host=host,
            port=port,
            log_level=log_level,
            openai_api_key=api_key,
        )


def _parse_port(raw_port: str) -> int:
    """Parse a TCP port while returning only safe configuration errors."""
    try:
        port = int(raw_port)
    except ValueError:
        raise ConfigurationError("PORT must be an integer from 1 to 65535") from None
    if not 1 <= port <= 65535:
        raise ConfigurationError("PORT must be an integer from 1 to 65535")
    return port
