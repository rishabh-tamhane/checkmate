"""Contract tests for the private OpenAI receipt-parser adapter boundary."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import httpx2
import openai
import pytest
from pydantic import ValidationError

import checkmate.adapters.receipt_parser as receipt_adapter
from checkmate.adapters.receipt_parser import (
    EXTRACTION_PROMPT_VERSION,
    OPENAI_EXTRACTION_MODEL,
    REVIEW_NOTICE,
    OpenAIReceiptParser,
)
from checkmate.application.extraction import ReceiptExtractionError
from checkmate.application.models import NormalizedReceiptImage


class FakeResponses:
    """Synthetic Responses resource that records the adapter request."""

    def __init__(self, response: object = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []
        self.active = 0
        self.maximum_active = 0

    async def parse(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        self.active += 1
        self.maximum_active = max(self.maximum_active, self.active)
        try:
            await asyncio.sleep(0)
            if self.error is not None:
                raise self.error
            return self.response
        finally:
            self.active -= 1


class FakeClient:
    def __init__(self, responses: FakeResponses) -> None:
        self.responses = responses


def provider_receipt(**overrides: object) -> object:
    values: dict[str, object] = {
        "restaurant_name": " Example Restaurant ",
        "receipt_date": " 2026-08-16 ",
        "items": [
            {
                "name": " Noodles ",
                "quantity": " 1 ",
                "line_total": " $1,234.5 ",
            }
        ],
        "subtotal": "1234.50",
        "tax": "about 10.00",
        "tip": None,
        "total": "9.00",
    }
    values.update(overrides)
    return receipt_adapter._ProviderReceipt.model_validate(values)


def parsed_response(parsed: object) -> object:
    return SimpleNamespace(output_parsed=parsed, output=[])


def test_sdk_client_has_one_retry_and_thirty_second_timeout() -> None:
    parser = OpenAIReceiptParser("test-secret")

    assert parser._client.max_retries == 1
    assert parser._client.timeout == 30.0


@pytest.mark.asyncio
async def test_success_uses_the_pinned_private_request_and_returns_owned_values() -> (
    None
):
    responses = FakeResponses(parsed_response(provider_receipt()))
    parser = OpenAIReceiptParser("test-secret", client=FakeClient(responses))
    image = NormalizedReceiptImage(b"synthetic-jpeg", 80, 40)

    result = await parser.parse(image)

    call = responses.calls[0]
    assert call["model"] == OPENAI_EXTRACTION_MODEL
    assert call["store"] is False
    assert call["tools"] == []
    assert call["text_format"] is receipt_adapter._ProviderReceipt
    assert "untrusted receipt content" in str(call["instructions"])
    assert "synthetic-jpeg" not in str(call)
    assert "data:image/jpeg;base64," in str(call["input"])
    assert result.restaurant_name == "Example Restaurant"
    assert result.receipt_date == "2026-08-16"
    assert result.items[0].name == "Noodles"
    assert result.items[0].quantity == "1"
    assert result.items[0].line_total == "1234.50"
    assert result.tax == "about 10.00"
    assert result.tip == "0.00"
    assert result.total == "9.00"
    assert result.notices == (REVIEW_NOTICE,)
    assert EXTRACTION_PROMPT_VERSION != OPENAI_EXTRACTION_MODEL


@pytest.mark.asyncio
async def test_missing_values_remain_blankable_without_arithmetic_repair() -> None:
    parsed = provider_receipt(
        restaurant_name=None,
        receipt_date=None,
        items=[{"name": "Unreadable", "quantity": None, "line_total": ""}],
        subtotal=None,
        tax=None,
        tip=None,
        total=None,
    )
    parser = OpenAIReceiptParser(
        "test-secret",
        client=FakeClient(FakeResponses(parsed_response(parsed))),
    )

    result = await parser.parse(NormalizedReceiptImage(b"jpeg", 1, 1))

    assert result.restaurant_name is None
    assert result.receipt_date is None
    assert result.items[0].line_total == ""
    assert result.subtotal is None
    assert result.tax is None
    assert result.tip == "0.00"
    assert result.total is None


def test_provider_schema_rejects_unknown_keys_lengths_and_item_overflow() -> None:
    base = {
        "restaurant_name": None,
        "receipt_date": None,
        "items": [],
        "subtotal": None,
        "tax": None,
        "tip": None,
        "total": None,
    }
    with pytest.raises(ValidationError):
        receipt_adapter._ProviderReceipt.model_validate({**base, "unknown": "x"})
    with pytest.raises(ValidationError):
        receipt_adapter._ProviderReceipt.model_validate(
            {**base, "restaurant_name": "x" * 201}
        )
    with pytest.raises(ValidationError):
        receipt_adapter._ProviderReceipt.model_validate(
            {
                **base,
                "items": [{"name": "Item", "quantity": None, "line_total": "1.00"}]
                * 101,
            }
        )
    with pytest.raises(ValidationError):
        receipt_adapter._ProviderReceipt.model_validate(
            {
                **base,
                "items": [
                    {
                        "name": "Item",
                        "quantity": None,
                        "line_total": "1.00",
                        "provider_id": "forbidden",
                    }
                ],
            }
        )


@pytest.mark.parametrize(
    ("error", "expected_code"),
    [
        (TimeoutError(), "receipt_extraction_timed_out"),
        (
            openai.RateLimitError(
                "synthetic rate limit",
                response=httpx2.Response(
                    429, request=httpx2.Request("POST", "https://example.invalid")
                ),
                body=None,
            ),
            "receipt_extraction_unavailable",
        ),
        (
            openai.InternalServerError(
                "synthetic server error",
                response=httpx2.Response(
                    500, request=httpx2.Request("POST", "https://example.invalid")
                ),
                body=None,
            ),
            "receipt_extraction_unavailable",
        ),
    ],
)
@pytest.mark.asyncio
async def test_provider_failures_are_sanitized(
    error: Exception, expected_code: str
) -> None:
    parser = OpenAIReceiptParser(
        "test-secret", client=FakeClient(FakeResponses(error=error))
    )

    with pytest.raises(ReceiptExtractionError) as raised:
        await parser.parse(NormalizedReceiptImage(b"jpeg", 1, 1))

    assert raised.value.code == expected_code
    assert "synthetic" not in raised.value.safe_message


@pytest.mark.asyncio
async def test_refusal_and_invalid_structured_output_are_sanitized() -> None:
    refusal = SimpleNamespace(
        output_parsed=None,
        output=[
            SimpleNamespace(content=[SimpleNamespace(type="refusal", refusal="no")])
        ],
    )
    invalid = SimpleNamespace(output_parsed={"not": "validated"}, output=[])

    for response, expected_category in (
        (refusal, "provider_refusal"),
        (invalid, "invalid_provider_response"),
    ):
        parser = OpenAIReceiptParser(
            "test-secret", client=FakeClient(FakeResponses(response))
        )
        with pytest.raises(ReceiptExtractionError) as raised:
            await parser.parse(NormalizedReceiptImage(b"jpeg", 1, 1))
        assert raised.value.category == expected_category


@pytest.mark.asyncio
async def test_injected_semaphore_bounds_concurrent_provider_calls() -> None:
    responses = FakeResponses(parsed_response(provider_receipt()))
    parser = OpenAIReceiptParser(
        "test-secret",
        client=FakeClient(responses),
        semaphore=asyncio.Semaphore(4),
    )

    async def run_calls() -> None:
        await asyncio.gather(
            *(parser.parse(NormalizedReceiptImage(b"jpeg", 1, 1)) for _ in range(9))
        )

    await run_calls()

    assert responses.maximum_active == 4
