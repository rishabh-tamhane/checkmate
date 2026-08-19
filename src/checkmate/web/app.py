"""FastAPI composition root and executable Checkmate web process."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Final
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from checkmate import __version__
from checkmate.application.models import (
    CalculationOutput,
    RawParticipant,
    RawReceipt,
    RawReceiptItem,
    RawSplitDraft,
)
from checkmate.application.services import calculate_draft
from checkmate.config import ConfigurationError, Settings
from checkmate.domain.money import format_decimal, format_money, format_signed_cents
from checkmate.web.schemas import (
    CalculationRequest,
    CalculationResponse,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    ItemAllocationResponse,
    NormalizedDraftResponse,
    NormalizedParticipantResponse,
    NormalizedReceiptItemResponse,
    NormalizedReceiptResponse,
    ParticipantShareResponse,
    ParticipantTotalResponse,
    ReconciliationComponentResponse,
    ReconciliationResponse,
    ValidationIssueResponse,
)

PACKAGE_DIRECTORY: Final = Path(__file__).parent
TEMPLATE_DIRECTORY: Final = PACKAGE_DIRECTORY / "templates"
STATIC_DIRECTORY: Final = PACKAGE_DIRECTORY / "static"
HTTP_LOGGER: Final = logging.getLogger("checkmate.http")
INTERNAL_ERROR_MESSAGE: Final = "Checkmate could not complete this request."
JSON_BODY_LIMIT: Final = 256 * 1024
SAME_ORIGIN_HEADER: Final = "X-Checkmate-Request"
SAME_ORIGIN_VALUE: Final = "1"
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
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
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

    @app.post(
        "/api/splits/calculate",
        response_model=CalculationResponse,
        response_model_by_alias=True,
        summary="Calculate the current manual split draft",
    )
    async def calculate(request: Request) -> Response:
        origin_error = _same_origin_error(request)
        if origin_error is not None:
            return origin_error

        body = await _read_limited_body(request, JSON_BODY_LIMIT)
        if body is None:
            return _safe_error_response(
                request,
                status_code=413,
                code="request_too_large",
                message="The calculation request must be 256 KiB or smaller.",
            )
        try:
            calculation_request = CalculationRequest.model_validate_json(body)
        except ValidationError:
            return _safe_error_response(
                request,
                status_code=422,
                code="invalid_request",
                message=(
                    "The calculation request does not match the required structure."
                ),
            )

        output = calculate_draft(_to_raw_draft(calculation_request))
        response = _to_calculation_response(output)
        return JSONResponse(
            content=response.model_dump(mode="json", by_alias=True),
            status_code=200,
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


async def _read_limited_body(request: Request, limit: int) -> bytes | None:
    """Read at most limit bytes without passing an oversized body to Pydantic."""
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > limit:
                return None
        except ValueError:
            return None

    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > limit:
            return None
        body.extend(chunk)
    return bytes(body)


def _same_origin_error(request: Request) -> JSONResponse | None:
    """Require the private browser header and validate Origin when supplied."""
    if request.headers.get(SAME_ORIGIN_HEADER) != SAME_ORIGIN_VALUE:
        return _safe_error_response(
            request,
            status_code=403,
            code="same_origin_required",
            message="This request must come from the Checkmate application.",
        )
    origin = request.headers.get("origin")
    expected_origin = str(request.base_url).rstrip("/")
    if origin is not None and origin.rstrip("/") != expected_origin:
        return _safe_error_response(
            request,
            status_code=403,
            code="origin_not_allowed",
            message="This request origin is not allowed.",
        )
    return None


def _safe_error_response(
    request: Request, *, status_code: int, code: str, message: str
) -> JSONResponse:
    """Build a stable safe error envelope using the current request ID."""
    error = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            request_id=str(request.state.request_id),
        )
    )
    return JSONResponse(status_code=status_code, content=error.model_dump())


def _to_raw_draft(request: CalculationRequest) -> RawSplitDraft:
    """Translate Pydantic-owned HTTP values into application-owned values."""
    return RawSplitDraft(
        revision=request.revision,
        receipt=RawReceipt(
            restaurant_name=request.receipt.restaurant_name,
            receipt_date=request.receipt.date,
            items=tuple(
                RawReceiptItem(
                    id=item.id,
                    name=item.name,
                    quantity=item.quantity,
                    line_total=item.line_total,
                )
                for item in request.receipt.items
            ),
            subtotal=request.receipt.subtotal,
            tax=request.receipt.tax,
            tip=request.receipt.tip,
            total=request.receipt.total,
        ),
        participants=tuple(
            RawParticipant(id=participant.id, name=participant.name)
            for participant in request.participants
        ),
        assignments=tuple(
            (item_id, tuple(participant_ids))
            for item_id, participant_ids in request.assignments.items()
        ),
    )


def _to_calculation_response(output: CalculationOutput) -> CalculationResponse:
    """Translate application output into formatted browser response values."""
    normalized: NormalizedDraftResponse | None = None
    participant_names: dict[str, str] = {}
    if output.normalized is not None:
        participant_names = {
            participant.id: participant.name
            for participant in output.normalized.participants
        }
        normalized = NormalizedDraftResponse(
            receipt=NormalizedReceiptResponse(
                restaurantName=output.normalized.receipt.restaurant_name,
                date=(
                    output.normalized.receipt.receipt_date.isoformat()
                    if output.normalized.receipt.receipt_date is not None
                    else None
                ),
                items=[
                    NormalizedReceiptItemResponse(
                        id=item.id,
                        name=item.name,
                        quantity=_format_quantity(item.quantity),
                        lineTotal=format_decimal(item.line_total),
                    )
                    for item in output.normalized.receipt.items
                ],
                subtotal=format_decimal(output.normalized.receipt.subtotal),
                tax=format_decimal(output.normalized.receipt.tax),
                tip=format_decimal(output.normalized.receipt.tip),
                total=format_decimal(output.normalized.receipt.total),
            ),
            participants=[
                NormalizedParticipantResponse(id=participant.id, name=participant.name)
                for participant in output.normalized.participants
            ],
            assignments={
                item_id: list(participant_ids)
                for item_id, participant_ids in output.normalized.assignments.by_item
            },
        )

    reconciliation: ReconciliationResponse | None = None
    if output.reconciliation is not None:
        reconciliation = ReconciliationResponse(
            subtotal=ReconciliationComponentResponse(
                entered=format_money(output.reconciliation.entered_subtotal),
                calculated=format_money(output.reconciliation.calculated_subtotal),
                difference=format_signed_cents(
                    output.reconciliation.subtotal_difference_cents
                ),
            ),
            total=ReconciliationComponentResponse(
                entered=format_money(output.reconciliation.entered_total),
                calculated=format_money(output.reconciliation.calculated_total),
                difference=format_signed_cents(
                    output.reconciliation.total_difference_cents
                ),
            ),
        )

    return CalculationResponse(
        revision=output.revision,
        normalized=normalized,
        issues=[
            ValidationIssueResponse(
                code=issue.code,
                path=issue.path,
                message=issue.message,
                severity=issue.severity,
            )
            for issue in output.issues
        ],
        itemAllocations=[
            ItemAllocationResponse(
                itemId=allocation.item_id,
                shares=[
                    ParticipantShareResponse(
                        participantId=share.participant_id,
                        amount=format_money(share.amount),
                    )
                    for share in allocation.shares
                ],
            )
            for allocation in output.item_allocations
        ],
        participantTotals=[
            ParticipantTotalResponse(
                participantId=total.participant_id,
                name=participant_names[total.participant_id],
                itemSubtotal=format_money(total.item_subtotal),
                tax=format_money(total.tax),
                tip=format_money(total.tip),
                total=format_money(total.total),
            )
            for total in output.participant_totals
        ],
        reconciliation=reconciliation,
        finalized=output.finalized,
        nonZero=output.non_zero,
    )


def _format_quantity(quantity: Decimal | None) -> str | None:
    return format(quantity, "f") if quantity is not None else None
