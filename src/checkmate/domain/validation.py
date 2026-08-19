"""Receipt, participant, assignment, and reconciliation validation."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Final

from checkmate.domain.models import (
    Assignments,
    SplitInput,
    SplitResult,
    ValidationIssue,
)

MAX_TEXT_LENGTH: Final = 200
MAX_ID_LENGTH: Final = 128
MAX_ITEMS: Final = 100
MAX_PARTICIPANTS: Final = 50
ID_PATTERN: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
DATE_PATTERN: Final = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
QUANTITY_PATTERN: Final = re.compile(r"^[0-9]+(?:\.[0-9]{1,3})?$")


def validate_text(
    raw_value: str, *, path: str, required: bool
) -> tuple[str | None, ValidationIssue | None]:
    """Trim and validate a user-visible Windows-1252 string."""
    value = raw_value.strip()
    if not value:
        if required:
            return None, _issue("required_text", path, "Enter a value.")
        return None, None
    if len(value) > MAX_TEXT_LENGTH:
        return None, _issue(
            "text_too_long", path, f"Use {MAX_TEXT_LENGTH} characters or fewer."
        )
    if not all(character.isprintable() for character in value):
        return None, _issue(
            "unsupported_text", path, "Use printable text without control characters."
        )
    try:
        value.encode("windows-1252")
    except UnicodeEncodeError:
        return None, _issue(
            "unsupported_text",
            path,
            "Use characters supported by the current PDF output.",
        )
    return value, None


def validate_id(raw_value: str, *, path: str) -> ValidationIssue | None:
    """Validate a bounded opaque identifier without interpreting its meaning."""
    if len(raw_value) > MAX_ID_LENGTH or not ID_PATTERN.fullmatch(raw_value):
        return _issue("invalid_id", path, "The record identifier is invalid.")
    return None


def validate_date(
    raw_value: str, *, path: str
) -> tuple[date | None, ValidationIssue | None]:
    """Convert a blank or exact ISO calendar date."""
    value = raw_value.strip()
    if not value:
        return None, None
    if not DATE_PATTERN.fullmatch(value):
        return None, _issue("invalid_date", path, "Enter a date as YYYY-MM-DD.")
    try:
        return date.fromisoformat(value), None
    except ValueError:
        return None, _issue("invalid_date", path, "Enter a valid calendar date.")


def validate_quantity(
    raw_value: str, *, path: str
) -> tuple[Decimal | None, ValidationIssue | None]:
    """Convert a blank or positive decimal quantity with up to three places."""
    value = raw_value.strip()
    if not value:
        return None, None
    if not QUANTITY_PATTERN.fullmatch(value):
        return None, _issue(
            "invalid_quantity",
            path,
            "Enter a positive quantity with at most three decimal places.",
        )
    try:
        quantity = Decimal(value)
    except InvalidOperation:
        return None, _issue("invalid_quantity", path, "Enter a valid quantity.")
    if quantity <= 0:
        return None, _issue(
            "invalid_quantity", path, "Quantity must be greater than zero."
        )
    return quantity, None


def normalize_assignments(
    *,
    item_ids: tuple[str, ...],
    participant_ids: tuple[str, ...],
    raw_assignments: tuple[tuple[str, tuple[str, ...]], ...],
) -> tuple[Assignments | None, tuple[ValidationIssue, ...]]:
    """Validate references and normalize valid lists into participant order."""
    issues: list[ValidationIssue] = []
    known_items = set(item_ids)
    known_participants = set(participant_ids)
    seen_assignment_items: set[str] = set()
    raw_by_item: dict[str, tuple[str, ...]] = {}

    for item_id, assigned_ids in raw_assignments:
        path = f"assignments.{item_id}"
        if item_id in seen_assignment_items:
            issues.append(
                _issue(
                    "duplicate_assignment_item",
                    path,
                    "An item may appear only once in assignments.",
                )
            )
        seen_assignment_items.add(item_id)
        if item_id not in known_items:
            issues.append(
                _issue(
                    "unknown_item_reference",
                    path,
                    "The assignment references an item that does not exist.",
                )
            )

        seen_participants: set[str] = set()
        for participant_id in assigned_ids:
            participant_path = f"{path}.{participant_id}"
            if participant_id in seen_participants:
                issues.append(
                    _issue(
                        "duplicate_participant_reference",
                        participant_path,
                        "A participant may be assigned to an item only once.",
                    )
                )
            seen_participants.add(participant_id)
            if participant_id not in known_participants:
                issues.append(
                    _issue(
                        "unknown_participant_reference",
                        participant_path,
                        "The assignment references a participant that does not exist.",
                    )
                )
        raw_by_item[item_id] = assigned_ids

    if issues:
        return None, tuple(issues)

    participant_order = {
        participant_id: index for index, participant_id in enumerate(participant_ids)
    }
    normalized = tuple(
        (
            item_id,
            tuple(
                sorted(
                    raw_by_item.get(item_id, ()),
                    key=participant_order.__getitem__,
                )
            ),
        )
        for item_id in item_ids
    )
    return Assignments(normalized), ()


def validate_business_rules(split_input: SplitInput) -> tuple[ValidationIssue, ...]:
    """Return allocation and reconciliation blockers for valid field values."""
    issues: list[ValidationIssue] = []
    receipt = split_input.receipt
    calculated_subtotal = sum(item.line_total.cents for item in receipt.items)
    calculated_total = calculated_subtotal + receipt.tax.cents + receipt.tip.cents

    for item in receipt.items:
        if item.line_total.cents > 0 and not split_input.assignments.for_item(item.id):
            issues.append(
                _issue(
                    "unassigned_item",
                    f"assignments.{item.id}",
                    "Assign this non-zero item to at least one participant.",
                )
            )

    if receipt.total.cents > 0 and not split_input.participants:
        issues.append(
            _issue(
                "participants_required",
                "participants",
                "Add at least one participant for a non-zero receipt.",
            )
        )

    if calculated_subtotal == 0:
        if receipt.tax.cents > 0:
            issues.append(
                _issue(
                    "zero_subtotal_tax",
                    "receipt.tax",
                    "Tax must be zero when the item subtotal is zero.",
                )
            )
        if receipt.tip.cents > 0:
            issues.append(
                _issue(
                    "zero_subtotal_tip",
                    "receipt.tip",
                    "Tip must be zero when the item subtotal is zero.",
                )
            )

    if receipt.subtotal.cents != calculated_subtotal:
        issues.append(
            _issue(
                "subtotal_mismatch",
                "receipt.subtotal",
                "Entered subtotal must match the sum of item line totals.",
            )
        )
    if receipt.total.cents != calculated_total:
        issues.append(
            _issue(
                "total_mismatch",
                "receipt.total",
                "Entered total must match item subtotal plus tax and tip.",
            )
        )
    if receipt.total.cents == 0 and calculated_total == 0:
        issues.append(
            _issue(
                "zero_receipt",
                "receipt.total",
                "Enter a non-zero receipt before generating a PDF.",
            )
        )
    return tuple(issues)


def validate_participant_total(
    split_input: SplitInput, result: SplitResult
) -> ValidationIssue | None:
    """Ensure calculated participant totals exactly match the entered total."""
    participant_sum = sum(total.total.cents for total in result.participant_totals)
    if participant_sum != split_input.receipt.total.cents:
        return _issue(
            "participant_total_mismatch",
            "participants",
            "Participant totals do not add up to the entered receipt total.",
        )
    return None


def _issue(code: str, path: str, message: str) -> ValidationIssue:
    return ValidationIssue(code=code, path=path, message=message)
