"""HTTP integration tests for bounded, private receipt extraction."""

from __future__ import annotations

import logging
import re
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import checkmate.adapters.receipt_parser as receipt_adapter
from checkmate.adapters.receipt_parser import FakeReceiptParser
from checkmate.application.extraction import MAX_UPLOAD_BYTES, ReceiptExtractionError
from checkmate.application.models import ExtractionItemDraft, ExtractionResult
from checkmate.config import Settings
from checkmate.web.app import SAME_ORIGIN_HEADER, SAME_ORIGIN_VALUE, create_app

REQUEST_HEADERS = {SAME_ORIGIN_HEADER: SAME_ORIGIN_VALUE}


def synthetic_image(
    image_format: str = "PNG", *, size: tuple[int, int] = (80, 40)
) -> bytes:
    image = Image.new("RGB", size, "white")
    output = BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def extraction_result() -> ExtractionResult:
    return ExtractionResult(
        restaurant_name="Synthetic Cafe",
        receipt_date="2026-08-16",
        items=(
            ExtractionItemDraft("Piza", "1", "10.01"),
            ExtractionItemDraft("Salad", None, "7.00"),
        ),
        subtotal="17.01",
        tax="1.37",
        tip="2.55",
        total="20.93",
        notices=("Review every extracted value.",),
    )


def extraction_client(
    parser: FakeReceiptParser | None = None,
) -> TestClient:
    return TestClient(
        create_app(receipt_parser=parser or FakeReceiptParser(extraction_result()))
    )


def test_supported_content_returns_stable_editable_schema_and_no_store() -> None:
    parser = FakeReceiptParser(extraction_result())
    with extraction_client(parser) as client:
        response = client.post(
            "/api/receipts/extract",
            headers=REQUEST_HEADERS,
            files={"receipt": ("misleading.jpg", synthetic_image("PNG"), "text/plain")},
        )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert len(response.headers["x-request-id"]) == 32
    body = response.json()
    assert body["receipt"] == {
        "restaurantName": "Synthetic Cafe",
        "date": "2026-08-16",
        "items": body["receipt"]["items"],
        "subtotal": "17.01",
        "tax": "1.37",
        "tip": "2.55",
        "total": "20.93",
    }
    assert [item["name"] for item in body["receipt"]["items"]] == [
        "Piza",
        "Salad",
    ]
    assert body["receipt"]["items"][1]["quantity"] == ""
    assert all(
        re.fullmatch(r"item-[0-9a-f-]{36}", item["id"])
        for item in body["receipt"]["items"]
    )
    assert body["notices"] == ["Review every extracted value."]
    assert len(parser.images) == 1
    assert parser.images[0].media_type == "image/jpeg"


@pytest.mark.parametrize(
    "files",
    [
        {},
        {"wrong": ("receipt.png", b"content", "image/png")},
        [
            ("receipt", ("one.png", b"one", "image/png")),
            ("receipt", ("two.png", b"two", "image/png")),
        ],
    ],
)
def test_missing_wrong_and_duplicate_upload_fields_are_rejected(
    files: object,
) -> None:
    with extraction_client() as client:
        response = client.post(
            "/api/receipts/extract", headers=REQUEST_HEADERS, files=files
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_receipt_upload"
    assert response.headers["cache-control"] == "no-store"


def test_non_multipart_and_structurally_invalid_multipart_are_rejected() -> None:
    with extraction_client() as client:
        non_multipart = client.post(
            "/api/receipts/extract", headers=REQUEST_HEADERS, content=b"not multipart"
        )
        malformed = client.post(
            "/api/receipts/extract",
            headers={
                **REQUEST_HEADERS,
                "Content-Type": "multipart/form-data; boundary=missing",
            },
            content=b"not a valid multipart body",
        )

    assert non_multipart.status_code == 400
    assert malformed.status_code == 400
    assert malformed.json()["error"]["code"] == "invalid_receipt_upload"


def test_encoded_size_limit_is_enforced_at_exact_boundary() -> None:
    parser = FakeReceiptParser(extraction_result())
    with extraction_client(parser) as client:
        at_limit = client.post(
            "/api/receipts/extract",
            headers=REQUEST_HEADERS,
            files={"receipt": ("receipt.png", b"x" * MAX_UPLOAD_BYTES, "image/png")},
        )
        over_limit = client.post(
            "/api/receipts/extract",
            headers=REQUEST_HEADERS,
            files={
                "receipt": (
                    "receipt.png",
                    b"x" * (MAX_UPLOAD_BYTES + 1),
                    "image/png",
                )
            },
        )

    assert at_limit.status_code == 400
    assert at_limit.json()["error"]["code"] == "invalid_receipt_image"
    assert over_limit.status_code == 413
    assert over_limit.json()["error"]["code"] == "receipt_too_large"
    assert parser.images == []


def test_invalid_unsupported_animation_and_pixel_limit_map_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = Image.new("RGB", (20, 20), "white")
    second = Image.new("RGB", (20, 20), "black")
    animation = BytesIO()
    first.save(animation, format="PNG", save_all=True, append_images=[second])

    with extraction_client() as client:
        invalid = client.post(
            "/api/receipts/extract",
            headers=REQUEST_HEADERS,
            files={"receipt": ("receipt.jpg", b"invalid", "image/jpeg")},
        )
        unsupported = client.post(
            "/api/receipts/extract",
            headers=REQUEST_HEADERS,
            files={"receipt": ("receipt.gif", b"GIF89a synthetic", "image/gif")},
        )
        animated = client.post(
            "/api/receipts/extract",
            headers=REQUEST_HEADERS,
            files={"receipt": ("receipt.png", animation.getvalue(), "image/png")},
        )
        monkeypatch.setattr(receipt_adapter, "MAX_IMAGE_PIXELS", 99)
        too_many_pixels = client.post(
            "/api/receipts/extract",
            headers=REQUEST_HEADERS,
            files={
                "receipt": ("receipt.png", synthetic_image(size=(10, 10)), "image/png")
            },
        )

    assert (invalid.status_code, invalid.json()["error"]["code"]) == (
        400,
        "invalid_receipt_image",
    )
    assert (unsupported.status_code, unsupported.json()["error"]["code"]) == (
        415,
        "unsupported_receipt_format",
    )
    assert animated.status_code == 400
    assert too_many_pixels.status_code == 400


@pytest.mark.parametrize(
    ("category", "expected_status"),
    [
        ("provider_timeout", 504),
        ("provider_refusal", 502),
        ("provider_unavailable", 502),
        ("invalid_provider_response", 502),
    ],
)
def test_provider_failures_map_to_safe_transport_errors(
    category: str, expected_status: int
) -> None:
    parser = FakeReceiptParser(
        error=ReceiptExtractionError(
            code="safe_extraction_failure",
            message="Retry or enter the receipt manually.",
            category=category,
        )
    )
    with extraction_client(parser) as client:
        response = client.post(
            "/api/receipts/extract",
            headers=REQUEST_HEADERS,
            files={"receipt": ("receipt.png", synthetic_image(), "image/png")},
        )

    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == "safe_extraction_failure"
    assert response.headers["cache-control"] == "no-store"


def test_same_origin_policy_is_required_for_extraction() -> None:
    image = synthetic_image()
    with extraction_client() as client:
        missing_header = client.post(
            "/api/receipts/extract",
            files={"receipt": ("receipt.png", image, "image/png")},
        )
        foreign_origin = client.post(
            "/api/receipts/extract",
            headers={**REQUEST_HEADERS, "Origin": "https://foreign.invalid"},
            files={"receipt": ("receipt.png", image, "image/png")},
        )

    assert missing_header.status_code == 403
    assert foreign_origin.status_code == 403


def test_no_key_mode_stays_healthy_and_declines_extraction() -> None:
    with TestClient(create_app(Settings(openai_api_key=None))) as client:
        page = client.get("/")
        health = client.get("/health")
        response = client.post(
            "/api/receipts/extract",
            headers=REQUEST_HEADERS,
            files={"receipt": ("receipt.png", synthetic_image(), "image/png")},
        )

    assert health.json() == {"status": "ok", "version": "0.1.0"}
    assert "Continue with manual entry" in page.text
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "automatic_extraction_unavailable"


def test_logs_exclude_filename_image_and_extracted_receipt_values(
    caplog: pytest.LogCaptureFixture,
) -> None:
    filename = "private-original-name.png"
    image = synthetic_image()
    caplog.set_level(logging.INFO)
    with extraction_client() as client:
        response = client.post(
            "/api/receipts/extract",
            headers=REQUEST_HEADERS,
            files={"receipt": (filename, image, "image/png")},
        )

    assert response.status_code == 200
    assert "extraction_complete" in caplog.text
    assert "upload_bytes=" in caplog.text
    assert "normalized_width=80" in caplog.text
    for private_value in (
        filename,
        "Synthetic Cafe",
        "Piza",
        "17.01",
        image.hex(),
    ):
        assert private_value not in caplog.text
