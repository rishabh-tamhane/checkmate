"""Validated process configuration for Checkmate."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Final
from urllib.parse import urlsplit

DEFAULT_HOST: Final = "0.0.0.0"
DEFAULT_PORT: Final = 8000
DEFAULT_LOG_LEVEL: Final = "info"
DEFAULT_REQUEST_CONCURRENCY_LIMIT: Final = 32
MAX_REQUEST_CONCURRENCY_LIMIT: Final = 1_000
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
    public_origin: str | None = None
    request_concurrency_limit: int = DEFAULT_REQUEST_CONCURRENCY_LIMIT
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

        public_origin = _parse_public_origin(values.get("PUBLIC_ORIGIN"))
        request_concurrency_limit = _parse_request_concurrency_limit(
            values.get(
                "REQUEST_CONCURRENCY_LIMIT",
                str(DEFAULT_REQUEST_CONCURRENCY_LIMIT),
            )
        )

        raw_api_key = values.get("OPENAI_API_KEY")
        api_key = raw_api_key if raw_api_key else None
        return cls(
            host=host,
            port=port,
            log_level=log_level,
            public_origin=public_origin,
            request_concurrency_limit=request_concurrency_limit,
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


def _parse_public_origin(raw_origin: str | None) -> str | None:
    """Validate one exact browser origin without accepting proxy-derived data."""
    if raw_origin is None:
        return None
    if not raw_origin or raw_origin != raw_origin.strip():
        raise ConfigurationError(
            "PUBLIC_ORIGIN must be an absolute HTTP(S) origin without a path"
        )

    try:
        parsed = urlsplit(raw_origin)
        port = parsed.port
    except ValueError:
        parsed = None
        port = None

    if (
        parsed is None
        or parsed.scheme not in {"http", "https"}
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
        or any(character.isspace() for character in raw_origin)
    ):
        raise ConfigurationError(
            "PUBLIC_ORIGIN must be an absolute HTTP(S) origin without a path"
        )

    # Accessing parsed.port above validates malformed and out-of-range ports.
    del port
    return raw_origin


def _parse_request_concurrency_limit(raw_limit: str) -> int:
    """Parse the bounded per-process request concurrency setting."""
    try:
        limit = int(raw_limit)
    except ValueError:
        raise ConfigurationError(
            "REQUEST_CONCURRENCY_LIMIT must be an integer from 1 to 1000"
        ) from None
    if not 1 <= limit <= MAX_REQUEST_CONCURRENCY_LIMIT:
        raise ConfigurationError(
            "REQUEST_CONCURRENCY_LIMIT must be an integer from 1 to 1000"
        )
    return limit
