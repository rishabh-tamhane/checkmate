"""Vendor-neutral application boundaries for external capabilities."""

from typing import Protocol

from checkmate.application.models import ExtractionResult, NormalizedReceiptImage
from checkmate.domain.models import FinalizedSplit


class ReceiptParser(Protocol):
    """Parse one application-owned receipt image into editable suggestions."""

    async def parse(self, image: NormalizedReceiptImage) -> ExtractionResult:
        """Return an editable extraction result for a normalized image."""
        ...


class ReceiptImageNormalizer(Protocol):
    """Validate and normalize untrusted encoded receipt-image bytes."""

    def normalize(self, content: bytes) -> NormalizedReceiptImage:
        """Return a safe metadata-free JPEG or raise a safe extraction error."""
        ...


class PdfRenderer(Protocol):
    """Render one application-owned finalized split as PDF bytes."""

    def render(self, split: FinalizedSplit) -> bytes:
        """Return a PDF representation of a validated split."""
        ...
