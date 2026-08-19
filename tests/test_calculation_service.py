"""Application orchestration tests for raw manual-splitting drafts."""

from dataclasses import replace

import pytest

from checkmate.application.models import (
    RawParticipant,
    RawReceipt,
    RawReceiptItem,
    RawSplitDraft,
)
from checkmate.application.services import calculate_draft


def draft(
    *,
    items: tuple[RawReceiptItem, ...] | None = None,
    participants: tuple[RawParticipant, ...] | None = None,
    assignments: tuple[tuple[str, tuple[str, ...]], ...] | None = None,
    subtotal: str = "10.01",
    tax: str = "1.00",
    tip: str = "2.00",
    total: str = "13.01",
) -> RawSplitDraft:
    actual_items = (
        (
            RawReceiptItem(
                id="item-1",
                name="  Synthetic noodles  ",
                quantity="2",
                line_total="10.01",
            ),
        )
        if items is None
        else items
    )
    actual_participants = (
        (
            RawParticipant(id="person-1", name="  Maya  "),
            RawParticipant(id="person-2", name="Alex"),
        )
        if participants is None
        else participants
    )
    actual_assignments = (
        (("item-1", ("person-2", "person-1")),) if assignments is None else assignments
    )
    return RawSplitDraft(
        revision=7,
        receipt=RawReceipt(
            restaurant_name="  Example Cafe  ",
            receipt_date="2026-08-16",
            items=actual_items,
            subtotal=subtotal,
            tax=tax,
            tip=tip,
            total=total,
        ),
        participants=actual_participants,
        assignments=actual_assignments,
    )


def test_calculation_service_normalizes_and_calculates_without_dependencies() -> None:
    output = calculate_draft(draft())

    assert output.revision == 7
    assert output.issues == ()
    assert output.finalized
    assert output.non_zero
    assert output.normalized is not None
    assert output.normalized.receipt.restaurant_name == "Example Cafe"
    assert output.normalized.receipt.items[0].name == "Synthetic noodles"
    assert output.normalized.receipt.items[0].line_total.cents == 1001
    assert output.normalized.assignments.for_item("item-1") == (
        "person-1",
        "person-2",
    )
    assert [total.total.cents for total in output.participant_totals] == [651, 650]
    assert output.reconciliation is not None
    assert output.reconciliation.calculated_total.cents == 1301


def test_quantity_is_display_only_and_does_not_multiply_line_total() -> None:
    output = calculate_draft(draft())
    assert output.normalized is not None
    assert str(output.normalized.receipt.items[0].quantity) == "2"
    assert output.reconciliation is not None
    assert output.reconciliation.calculated_subtotal.cents == 1001


@pytest.mark.parametrize(
    ("receipt_change", "expected_path"),
    [
        ({"subtotal": ""}, "receipt.subtotal"),
        ({"tax": "-1"}, "receipt.tax"),
        ({"tip": "1.234"}, "receipt.tip"),
        ({"total": "$13.01"}, "receipt.total"),
    ],
)
def test_invalid_money_returns_field_issues_without_calculation(
    receipt_change: dict[str, str], expected_path: str
) -> None:
    original = draft()
    output = calculate_draft(
        replace(original, receipt=replace(original.receipt, **receipt_change))
    )
    assert output.normalized is None
    assert output.reconciliation is None
    assert output.item_allocations == ()
    assert {issue.path for issue in output.issues} == {expected_path}
    assert {issue.code for issue in output.issues} == {"invalid_money"}


@pytest.mark.parametrize(
    ("changed", "expected_code"),
    [
        (
            {"items": (RawReceiptItem("item-1", "", "1", "10.01"),)},
            "required_text",
        ),
        (
            {"items": (RawReceiptItem("item-1", "Item", "0", "10.01"),)},
            "invalid_quantity",
        ),
        (
            {"items": (RawReceiptItem("bad id", "Item", "1", "10.01"),)},
            "invalid_id",
        ),
        ({"receipt_date": "2026-02-30"}, "invalid_date"),
        ({"restaurant_name": "Cafe 🙂"}, "unsupported_text"),
    ],
)
def test_invalid_receipt_fields_are_reported(
    changed: dict[str, object], expected_code: str
) -> None:
    original = draft()
    output = calculate_draft(
        replace(original, receipt=replace(original.receipt, **changed))
    )
    assert output.normalized is None
    assert expected_code in {issue.code for issue in output.issues}


def test_duplicate_item_and_participant_identities_are_rejected() -> None:
    output = calculate_draft(
        draft(
            items=(
                RawReceiptItem("same", "One", "1", "5.00"),
                RawReceiptItem("same", "Two", "1", "5.01"),
            ),
            participants=(
                RawParticipant("same-person", "Maya"),
                RawParticipant("same-person", "Alex"),
            ),
            assignments=(),
        )
    )
    assert {issue.code for issue in output.issues} >= {
        "duplicate_item_id",
        "duplicate_participant_id",
    }


def test_participant_names_are_unique_after_trimming_and_casefolding() -> None:
    output = calculate_draft(
        draft(
            participants=(
                RawParticipant("person-1", " Maya"),
                RawParticipant("person-2", "maya "),
            )
        )
    )
    assert output.normalized is None
    assert [issue.code for issue in output.issues].count(
        "duplicate_participant_name"
    ) == 2


@pytest.mark.parametrize(
    ("assignments", "expected_code"),
    [
        (("missing", ("person-1",)), "unknown_item_reference"),
        (("item-1", ("missing",)), "unknown_participant_reference"),
        (
            ("item-1", ("person-1", "person-1")),
            "duplicate_participant_reference",
        ),
    ],
)
def test_invalid_assignment_references_block_conversion(
    assignments: tuple[str, tuple[str, ...]], expected_code: str
) -> None:
    output = calculate_draft(draft(assignments=(assignments,)))
    assert output.normalized is None
    assert expected_code in {issue.code for issue in output.issues}


def test_item_and_participant_count_limits_are_enforced() -> None:
    items = tuple(
        RawReceiptItem(f"item-{index}", "Item", "1", "0") for index in range(101)
    )
    participants = tuple(
        RawParticipant(f"person-{index}", f"Person {index}") for index in range(51)
    )
    output = calculate_draft(
        draft(
            items=items,
            participants=participants,
            assignments=(),
            subtotal="0",
            tax="0",
            tip="0",
            total="0",
        )
    )
    assert {issue.code for issue in output.issues} >= {
        "too_many_items",
        "too_many_participants",
    }


def test_unassigned_item_blocks_allocation_but_keeps_normalized_values() -> None:
    output = calculate_draft(draft(assignments=(("item-1", ()),)))
    assert output.normalized is not None
    assert output.item_allocations == ()
    assert output.reconciliation is not None
    assert output.reconciliation.subtotal_difference_cents == 0
    assert output.reconciliation.total_difference_cents == 0
    assert {issue.code for issue in output.issues} == {"unassigned_item"}


def test_reconciliation_mismatch_returns_safe_provisional_allocations() -> None:
    output = calculate_draft(draft(subtotal="10.00", total="13.00"))
    assert output.normalized is not None
    assert output.item_allocations
    assert output.participant_totals
    assert output.reconciliation is not None
    assert not output.finalized
    assert {issue.code for issue in output.issues} == {
        "subtotal_mismatch",
        "total_mismatch",
        "participant_total_mismatch",
    }


def test_zero_receipt_calculates_but_never_finalizes() -> None:
    output = calculate_draft(
        draft(
            items=(RawReceiptItem("free", "Water", "1", "0"),),
            participants=(RawParticipant("person-1", "Maya"),),
            assignments=(("free", ()),),
            subtotal="0",
            tax="0",
            tip="0",
            total="0",
        )
    )
    assert output.normalized is not None
    assert output.reconciliation is not None
    assert not output.non_zero
    assert not output.finalized
    assert {issue.code for issue in output.issues} == {"zero_receipt"}
