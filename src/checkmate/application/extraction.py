"""Receipt-extraction orchestration independent of web and provider SDKs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Protocol

from checkmate.application.models import ExtractionOutput
from checkmate.application.ports import ReceiptImageNormalizer, ReceiptParser

MAX_UPLOAD_BYTES: Final = 10 * 1024 * 1024


class ReceiptUpload(Protocol):
    """The minimal asynchronous upload behavior used by the application."""

    async def read(self, size: int = -1) -> bytes:
        """Read at most ``size`` bytes from the upload."""
        ...

    async def close(self) -> None:
        """Release framework-owned upload resources."""
        ...


class ReceiptExtractionError(Exception):
    """A categorized extraction failure safe to translate at the HTTP edge."""

    def __init__(self, *, code: str, message: str, category: str) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message
        self.category = category


@dataclass(frozen=True, slots=True)
class ReceiptExtractionService:
    """Bound upload reading, normalization, parsing, and cleanup in one path."""

    parser: ReceiptParser
    normalizer: ReceiptImageNormalizer

    async def extract(self, upload: ReceiptUpload) -> ExtractionOutput:
        """Extract one upload while always closing its framework resource."""
        try:
            content = await upload.read(MAX_UPLOAD_BYTES + 1)
            if len(content) > MAX_UPLOAD_BYTES:
                raise ReceiptExtractionError(
                    code="receipt_too_large",
                    message="Choose a receipt image that is 10 MiB or smaller.",
                    category="upload_too_large",
                )
            if not content:
                raise ReceiptExtractionError(
                    code="invalid_receipt_image",
                    message="Choose a valid JPEG, PNG, or WebP receipt image.",
                    category="invalid_image",
                )

            image = self.normalizer.normalize(content)
            result = await self.parser.parse(image)
            return ExtractionOutput(
                result=result,
                upload_byte_count=len(content),
                normalized_width=image.width,
                normalized_height=image.height,
            )
        finally:
            await upload.close()


__all__ = [
    "MAX_UPLOAD_BYTES",
    "ReceiptExtractionError",
    "ReceiptExtractionService",
    "ReceiptUpload",
]
