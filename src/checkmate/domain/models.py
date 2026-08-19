"""Immutable values used by deterministic receipt splitting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True, slots=True)
class Money:
    """A non-negative USD amount represented as integer cents."""

    cents: int

    def __post_init__(self) -> None:
        if isinstance(self.cents, bool) or not isinstance(self.cents, int):
            raise TypeError("Money cents must be an integer.")
        if self.cents < 0:
            raise ValueError("Money cannot be negative.")


@dataclass(frozen=True, slots=True)
class ReceiptItem:
    """One validated receipt row whose amount is the complete line total."""

    id: str
    name: str
    quantity: Decimal | None
    line_total: Money


@dataclass(frozen=True, slots=True)
class Receipt:
    """Validated receipt values in original item order."""

    restaurant_name: str | None
    receipt_date: date | None
    items: tuple[ReceiptItem, ...]
    subtotal: Money
    tax: Money
    tip: Money
    total: Money


@dataclass(frozen=True, slots=True)
class Participant:
    """A participant whose position is the deterministic tie-break order."""

    id: str
    name: str


@dataclass(frozen=True, slots=True)
class Assignments:
    """Validated participant IDs assigned to each item in participant order."""

    by_item: tuple[tuple[str, tuple[str, ...]], ...]

    def for_item(self, item_id: str) -> tuple[str, ...]:
        """Return ordered participant IDs assigned to one item."""
        for assigned_item_id, participant_ids in self.by_item:
            if assigned_item_id == item_id:
                return participant_ids
        return ()


@dataclass(frozen=True, slots=True)
class SplitInput:
    """All validated values needed for one deterministic calculation."""

    receipt: Receipt
    participants: tuple[Participant, ...]
    assignments: Assignments


@dataclass(frozen=True, slots=True)
class ParticipantShare:
    """One participant's exact share of an item."""

    participant_id: str
    amount: Money


@dataclass(frozen=True, slots=True)
class ItemAllocation:
    """Cent-exact shares for one receipt item."""

    item_id: str
    shares: tuple[ParticipantShare, ...]


@dataclass(frozen=True, slots=True)
class ParticipantTotal:
    """One participant's item, tax, tip, and final amounts."""

    participant_id: str
    item_subtotal: Money
    tax: Money
    tip: Money
    total: Money


@dataclass(frozen=True, slots=True)
class Reconciliation:
    """Entered and calculated values, including their signed difference."""

    entered_subtotal: Money
    calculated_subtotal: Money
    subtotal_difference_cents: int
    entered_total: Money
    calculated_total: Money
    total_difference_cents: int


@dataclass(frozen=True, slots=True)
class SplitResult:
    """A deterministic calculation that may still fail finalization."""

    item_allocations: tuple[ItemAllocation, ...]
    participant_totals: tuple[ParticipantTotal, ...]
    reconciliation: Reconciliation


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A stable, field-addressable problem or review notice."""

    code: str
    path: str
    message: str
    severity: Literal["error", "warning"] = "error"

    @property
    def blocking(self) -> bool:
        """Return whether this issue prevents finalization."""
        return self.severity == "error"


@dataclass(frozen=True, slots=True)
class FinalizedSplit:
    """A non-zero split proven valid for downstream PDF rendering."""

    split_input: SplitInput
    result: SplitResult
