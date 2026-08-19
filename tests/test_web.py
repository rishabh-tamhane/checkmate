"""HTTP integration tests for the Checkmate application foundation."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from checkmate.config import Settings
from checkmate.web.app import SECURITY_HEADERS, create_app, main


@contextmanager
def application_client(settings: Settings | None = None) -> Iterator[TestClient]:
    """Provide a closed ASGI test client for one isolated application."""
    with TestClient(create_app(settings)) as client:
        yield client


def test_health_has_the_exact_contract_and_security_headers() -> None:
    """Health reports process state without consulting an external service."""
    with application_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok", "version": "0.1.0"}
    assert len(response.headers["x-request-id"]) == 32
    for name, value in SECURITY_HEADERS.items():
        assert response.headers[name] == value


def test_application_shell_links_to_local_assets() -> None:
    """The semantic shell and both versioned package assets are served."""
    with application_client() as client:
        page = client.get("/")
        stylesheet = client.get("/static/checkmate.v1.css")
        script = client.get("/static/checkmate.v1.js")

    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    assert "<main" in page.text
    assert 'id="page-title"' in page.text
    assert 'href="http://testserver/static/checkmate.v1.css"' in page.text
    assert 'src="http://testserver/static/checkmate.v1.js"' in page.text
    assert stylesheet.status_code == 200
    assert stylesheet.headers["content-type"].startswith("text/css")
    assert script.status_code == 200
    assert "javascript" in script.headers["content-type"]


def test_application_starts_without_an_openai_key() -> None:
    """Missing extraction configuration leaves manual entry healthy."""
    with application_client(Settings(openai_api_key=None)) as client:
        page = client.get("/")
        health = client.get("/health")

    assert page.status_code == 200
    assert "Manual entry below is fully available" in " ".join(page.text.split())
    assert health.json()["status"] == "ok"


def test_foundation_does_not_enable_extraction_when_a_key_exists() -> None:
    """A configured secret does not enable a milestone 3 capability early."""
    secret = "test-secret-value"
    with application_client(Settings(openai_api_key=secret)) as client:
        page = client.get("/")

    assert page.status_code == 200
    assert "Automatic extraction arrives in milestone 3" in page.text
    assert secret not in page.text


def test_unexpected_error_is_safe_and_logging_is_allowlisted(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Internal failures return a stable envelope without sensitive details."""
    app = create_app(Settings(openai_api_key="test-secret-value"))

    @app.get("/test-error")
    async def test_error() -> None:
        raise RuntimeError("Example Bistro paid $38.40 with test-secret-value")

    caplog.set_level(logging.INFO, logger="checkmate.http")
    with TestClient(app) as client:
        response = client.get("/test-error?participant=FictionalName")

    request_id = response.headers["x-request-id"]
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "Checkmate could not complete this request.",
            "request_id": request_id,
        }
    }
    assert "route=/test-error" in caplog.text
    for sensitive_value in (
        "Example Bistro",
        "$38.40",
        "test-secret-value",
        "FictionalName",
        "participant=",
    ):
        assert sensitive_value not in caplog.text
        assert sensitive_value not in response.text


def test_main_runs_one_uvicorn_process_without_proxy_trust(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The console entry point uses validated settings and production defaults."""
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "9123")
    monkeypatch.setenv("LOG_LEVEL", "warning")

    with patch("checkmate.web.app.uvicorn.run") as run:
        main()

    app = run.call_args.args[0]
    assert isinstance(app, FastAPI)
    assert run.call_args.kwargs == {
        "host": "127.0.0.1",
        "port": 9123,
        "log_level": "warning",
        "access_log": False,
        "proxy_headers": False,
        "reload": False,
        "server_header": False,
        "workers": 1,
    }


def test_main_fails_safely_for_invalid_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An invalid startup value produces a direct error without a traceback."""
    monkeypatch.setenv("PORT", "invalid")
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-value")

    with pytest.raises(SystemExit, match="Configuration error: PORT must be") as raised:
        main()

    assert "test-secret-value" not in str(raised.value)
