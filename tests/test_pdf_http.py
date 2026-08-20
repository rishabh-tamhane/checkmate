"""HTTP contract tests for independently finalized PDF downloads."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from checkmate.adapters.pdf_renderer import FakePdfRenderer
from checkmate.application.ports import PdfRenderer
from checkmate.domain.models import FinalizedSplit
from checkmate.web.app import (
    JSON_BODY_LIMIT,
    SAME_ORIGIN_HEADER,
    SAME_ORIGIN_VALUE,
    create_app,
)

REQUEST_HEADERS = {SAME_ORIGIN_HEADER: SAME_ORIGIN_VALUE}


def valid_payload() -> dict[str, object]:
    """Return one complete fictional browser draft."""
    return {
        "revision": 12,
        "receipt": {
            "restaurantName": "Synthetic Cafe",
            "date": "2026-08-16",
            "items": [
                {
                    "id": "item-1",
                    "name": "Noodles",
                    "quantity": "2",
                    "lineTotal": "10.01",
                }
            ],
            "subtotal": "10.01",
            "tax": "1.00",
            "tip": "2.00",
            "total": "13.01",
        },
        "participants": [
            {"id": "person-1", "name": "Maya"},
            {"id": "person-2", "name": "Alex"},
        ],
        "assignments": {"item-1": ["person-2", "person-1"]},
    }


@contextmanager
def pdf_client(renderer: PdfRenderer | None = None) -> Iterator[TestClient]:
    """Yield an isolated application with the selected renderer."""
    with TestClient(create_app(pdf_renderer=renderer)) as client:
        yield client


class FailingPdfRenderer:
    """Raise without exposing sensitive exception content to HTTP clients."""

    def render(self, split: FinalizedSplit) -> bytes:
        assert split.split_input.receipt.restaurant_name is not None
        raise RuntimeError(
            f"sensitive renderer failure: {split.split_input.receipt.restaurant_name}"
        )


def test_pdf_download_has_fixed_private_headers_and_uses_finalized_input() -> None:
    renderer = FakePdfRenderer(b"%PDF synthetic response")

    with pdf_client(renderer) as client:
        response = client.post(
            "/api/splits/pdf", json=valid_payload(), headers=REQUEST_HEADERS
        )

    assert response.status_code == 200
    assert response.content == b"%PDF synthetic response"
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == (
        'attachment; filename="checkmate-split.pdf"'
    )
    assert response.headers["cache-control"] == "no-store"
    assert "Synthetic Cafe" not in response.headers["content-disposition"]
    assert len(renderer.splits) == 1
    assert renderer.splits[0].split_input.assignments.for_item("item-1") == (
        "person-1",
        "person-2",
    )


def test_default_renderer_returns_a_semantically_readable_pdf() -> None:
    with pdf_client() as client:
        response = client.post(
            "/api/splits/pdf", json=valid_payload(), headers=REQUEST_HEADERS
        )

    reader = PdfReader(BytesIO(response.content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert response.status_code == 200
    assert "Checkmate Expense Split" in text
    assert "Synthetic Cafe" in text
    assert "Noodles" in text
    assert "$13.01" in text


def test_invalid_and_zero_drafts_return_422_and_do_not_render() -> None:
    renderer = FakePdfRenderer()
    invalid = valid_payload()
    receipt = invalid["receipt"]
    assert isinstance(receipt, dict)
    receipt["subtotal"] = "9.00"
    zero = valid_payload()
    zero_receipt = zero["receipt"]
    assert isinstance(zero_receipt, dict)
    zero_receipt.update(
        {
            "items": [
                {
                    "id": "free",
                    "name": "Water",
                    "quantity": "1",
                    "lineTotal": "0",
                }
            ],
            "subtotal": "0",
            "tax": "0",
            "tip": "0",
            "total": "0",
        }
    )
    zero["assignments"] = {"free": []}

    with pdf_client(renderer) as client:
        invalid_response = client.post(
            "/api/splits/pdf", json=invalid, headers=REQUEST_HEADERS
        )
        zero_response = client.post(
            "/api/splits/pdf", json=zero, headers=REQUEST_HEADERS
        )

    assert invalid_response.status_code == 422
    assert {issue["code"] for issue in invalid_response.json()["issues"]} >= {
        "subtotal_mismatch"
    }
    assert zero_response.status_code == 422
    assert {issue["code"] for issue in zero_response.json()["issues"]} == {
        "zero_receipt"
    }
    assert renderer.splits == []


def test_pdf_rejects_malformed_oversized_and_cross_origin_requests() -> None:
    with pdf_client(FakePdfRenderer()) as client:
        malformed = client.post(
            "/api/splits/pdf", content=b"not-json", headers=REQUEST_HEADERS
        )
        oversized = client.post(
            "/api/splits/pdf",
            content=b"x" * (JSON_BODY_LIMIT + 1),
            headers=REQUEST_HEADERS,
        )
        missing_header = client.post("/api/splits/pdf", json=valid_payload())
        wrong_origin = client.post(
            "/api/splits/pdf",
            json=valid_payload(),
            headers={**REQUEST_HEADERS, "Origin": "https://example.invalid"},
        )

    assert (malformed.status_code, malformed.json()["error"]["code"]) == (
        422,
        "invalid_request",
    )
    assert (oversized.status_code, oversized.json()["error"]["code"]) == (
        413,
        "request_too_large",
    )
    assert missing_header.status_code == 403
    assert wrong_origin.status_code == 403


def test_renderer_failure_is_sanitized_and_privacy_safe(
    caplog: pytest.LogCaptureFixture,
) -> None:
    payload = valid_payload()
    receipt = payload["receipt"]
    assert isinstance(receipt, dict)
    receipt["restaurantName"] = "Secret Synthetic Cafe"

    with (
        caplog.at_level(logging.ERROR, logger="checkmate.pdf"),
        pdf_client(FailingPdfRenderer()) as client,
    ):
        response = client.post("/api/splits/pdf", json=payload, headers=REQUEST_HEADERS)

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "pdf_generation_failed"
    assert "Secret Synthetic Cafe" not in response.text
    assert "Secret Synthetic Cafe" not in caplog.text
    assert "renderer_failure" in caplog.text
