"""Application-owned extraction, raw-draft, and calculation values."""

from __future__ import annotations

from dataclasses import dataclass

from checkmate.domain.models import (
    FinalizedSplit,
    ItemAllocation,
    ParticipantTotal,
    Reconciliation,
    SplitInput,
    ValidationIssue,
)


@dataclass(frozen=True, slots=True)
class NormalizedReceiptImage:
    """One metadata-free JPEG prepared for a receipt parser."""

    content: bytes
    width: int
    height: int
    media_type: str = "image/jpeg"


@dataclass(frozen=True, slots=True)
class ExtractionItemDraft:
    """One provider-suggested editable receipt item."""

    name: str
    quantity: str | None
    line_total: str


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    """Vendor-neutral editable suggestions produced from one receipt image."""

    restaurant_name: str | None
    receipt_date: str | None
    items: tuple[ExtractionItemDraft, ...]
    subtotal: str | None
    tax: str | None
    tip: str | None
    total: str | None
    notices: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExtractionOutput:
    """Extraction result plus non-sensitive operational measurements."""

    result: ExtractionResult
    upload_byte_count: int
    normalized_width: int
    normalized_height: int


@dataclass(frozen=True, slots=True)
class RawReceiptItem:
    """One editable item exactly as supplied by the browser."""

    id: str
    name: str
    quantity: str
    line_total: str


@dataclass(frozen=True, slots=True)
class RawReceipt:
    """Editable receipt values before domain conversion."""

    restaurant_name: str
    receipt_date: str
    items: tuple[RawReceiptItem, ...]
    subtotal: str
    tax: str
    tip: str
    total: str


@dataclass(frozen=True, slots=True)
class RawParticipant:
    """One editable participant before domain conversion."""

    id: str
    name: str


@dataclass(frozen=True, slots=True)
class RawSplitDraft:
    """One complete stateless browser draft submitted for calculation."""

    revision: int
    receipt: RawReceipt
    participants: tuple[RawParticipant, ...]
    assignments: tuple[tuple[str, tuple[str, ...]], ...]


@dataclass(frozen=True, slots=True)
class CalculationOutput:
    """Application result for one client revision."""

    revision: int
    normalized: SplitInput | None
    issues: tuple[ValidationIssue, ...]
    item_allocations: tuple[ItemAllocation, ...]
    participant_totals: tuple[ParticipantTotal, ...]
    reconciliation: Reconciliation | None
    finalized_split: FinalizedSplit | None

    @property
    def finalized(self) -> bool:
        """Return whether this response can be exported."""
        return self.finalized_split is not None

    @property
    def non_zero(self) -> bool:
        """Return whether the entered receipt has a non-zero total."""
        return self.normalized is not None and self.normalized.receipt.total.cents > 0
