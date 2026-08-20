"""Application tests for bounded extraction orchestration and cleanup."""

from __future__ import annotations

import pytest

from checkmate.adapters.receipt_parser import FakeReceiptParser
from checkmate.application.extraction import (
    MAX_UPLOAD_BYTES,
    ReceiptExtractionError,
    ReceiptExtractionService,
)
from checkmate.application.models import NormalizedReceiptImage


class SyntheticUpload:
    """In-memory upload that records the requested read and cleanup."""

    def __init__(self, content: bytes) -> None:
        self.content = content
        self.read_sizes: list[int] = []
        self.closed = False

    async def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return self.content[:size]

    async def close(self) -> None:
        self.closed = True


class StubNormalizer:
    """Record bytes while returning a predictable normalized image."""

    def __init__(self, error: ReceiptExtractionError | None = None) -> None:
        self.error = error
        self.contents: list[bytes] = []

    def normalize(self, content: bytes) -> NormalizedReceiptImage:
        self.contents.append(content)
        if self.error is not None:
            raise self.error
        return NormalizedReceiptImage(b"normalized", 20, 40)


@pytest.mark.asyncio
async def test_service_reads_only_the_bound_invokes_parser_and_closes() -> None:
    upload = SyntheticUpload(b"synthetic image")
    normalizer = StubNormalizer()
    parser = FakeReceiptParser()
    service = ReceiptExtractionService(parser=parser, normalizer=normalizer)

    output = await service.extract(upload)

    assert upload.read_sizes == [MAX_UPLOAD_BYTES + 1]
    assert upload.closed is True
    assert normalizer.contents == [b"synthetic image"]
    assert parser.images == [NormalizedReceiptImage(b"normalized", 20, 40)]
    assert output.upload_byte_count == len(b"synthetic image")
    assert output.normalized_width == 20
    assert output.result == parser.result


@pytest.mark.asyncio
async def test_service_rejects_empty_and_oversized_uploads_before_parsing() -> None:
    for content, expected_code in (
        (b"", "invalid_receipt_image"),
        (b"x" * (MAX_UPLOAD_BYTES + 1), "receipt_too_large"),
    ):
        upload = SyntheticUpload(content)
        parser = FakeReceiptParser()
        service = ReceiptExtractionService(parser=parser, normalizer=StubNormalizer())

        with pytest.raises(ReceiptExtractionError) as raised:
            await service.extract(upload)

        assert raised.value.code == expected_code
        assert upload.closed is True
        assert parser.images == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "category",
    [
        "invalid_image",
        "provider_timeout",
        "provider_refusal",
        "provider_unavailable",
        "invalid_provider_response",
    ],
)
async def test_service_preserves_every_failure_category_and_closes_upload(
    category: str,
) -> None:
    upload = SyntheticUpload(b"synthetic")
    error = ReceiptExtractionError(
        code="synthetic_failure",
        message="safe",
        category=category,
    )
    normalizer = StubNormalizer(error if category == "invalid_image" else None)
    parser_error = None if category == "invalid_image" else error
    service = ReceiptExtractionService(
        parser=FakeReceiptParser(error=parser_error),
        normalizer=normalizer,
    )

    with pytest.raises(ReceiptExtractionError) as raised:
        await service.extract(upload)

    assert raised.value.category == category
    assert upload.closed is True
