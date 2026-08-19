"""Vendor-neutral application boundaries for external capabilities."""

from typing import Protocol, TypeVar

_ReceiptInputT = TypeVar("_ReceiptInputT", contravariant=True)
_ReceiptOutputT = TypeVar("_ReceiptOutputT", covariant=True)
_PdfInputT = TypeVar("_PdfInputT", contravariant=True)


class ReceiptParser(Protocol[_ReceiptInputT, _ReceiptOutputT]):
    """Parse one application-owned receipt image into an editable result.

    Milestone 3 supplies the concrete input and output values.
    """

    async def parse(self, image: _ReceiptInputT) -> _ReceiptOutputT:
        """Return an editable extraction result for a normalized image."""
        ...


class PdfRenderer(Protocol[_PdfInputT]):
    """Render one application-owned finalized split as PDF bytes.

    Milestone 4 supplies the concrete finalized-split value.
    """

    def render(self, split: _PdfInputT) -> bytes:
        """Return a PDF representation of a validated split."""
        ...
