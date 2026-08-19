"""FastAPI composition root and executable Checkmate web process."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from time import perf_counter
from typing import Final
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from checkmate import __version__
from checkmate.config import ConfigurationError, Settings
from checkmate.web.schemas import ErrorDetail, ErrorResponse, HealthResponse

PACKAGE_DIRECTORY: Final = Path(__file__).parent
TEMPLATE_DIRECTORY: Final = PACKAGE_DIRECTORY / "templates"
STATIC_DIRECTORY: Final = PACKAGE_DIRECTORY / "static"
HTTP_LOGGER: Final = logging.getLogger("checkmate.http")
INTERNAL_ERROR_MESSAGE: Final = "Checkmate could not complete this request."
SECURITY_HEADERS: Final[Mapping[str, str]] = {
    "Content-Security-Policy": (
        "default-src 'self'; base-uri 'none'; form-action 'self'; "
        "frame-ancestors 'none'; object-src 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
}

RequestHandler = Callable[[Request], Awaitable[Response]]


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construct an isolated FastAPI application from validated settings."""
    if settings is None:
        settings = Settings.from_environment()

    app = FastAPI(
        title="Checkmate",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    templates = Jinja2Templates(directory=TEMPLATE_DIRECTORY)

    @app.middleware("http")
    async def request_context(request: Request, call_next: RequestHandler) -> Response:
        request_id = uuid4().hex
        request.state.request_id = request_id
        started_at = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((perf_counter() - started_at) * 1000)
            HTTP_LOGGER.error(
                "request_failed request_id=%s route=%s status=500 "
                "duration_ms=%s error_category=unexpected_error",
                request_id,
                _route_label(request.scope),
                duration_ms,
            )
            error = ErrorResponse(
                error=ErrorDetail(
                    code="internal_error",
                    message=INTERNAL_ERROR_MESSAGE,
                    request_id=request_id,
                )
            )
            response = JSONResponse(status_code=500, content=error.model_dump())
        else:
            duration_ms = round((perf_counter() - started_at) * 1000)
            HTTP_LOGGER.info(
                "request_complete request_id=%s route=%s status=%s duration_ms=%s",
                request_id,
                _route_label(request.scope),
                response.status_code,
                duration_ms,
            )

        response.headers["X-Request-ID"] = request_id
        for name, value in SECURITY_HEADERS.items():
            response.headers[name] = value
        return response

    @app.get(
        "/health",
        response_model=HealthResponse,
        response_model_exclude_none=True,
        summary="Report process health",
    )
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__)

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def index(request: Request) -> Response:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "application_version": __version__,
                "automatic_extraction_available": False,
                "api_key_configured": settings.openai_api_key is not None,
            },
        )

    app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")
    return app


def main() -> None:
    """Validate configuration and run one production-style Uvicorn process."""
    try:
        settings = Settings.from_environment()
    except ConfigurationError as error:
        raise SystemExit(f"Configuration error: {error}") from None

    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        access_log=False,
        proxy_headers=False,
        reload=False,
        server_header=False,
        workers=1,
    )


def _route_label(scope: Mapping[str, object]) -> str:
    """Return a matched route template without logging a user-supplied URL."""
    route = scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) else "<unmatched>"
