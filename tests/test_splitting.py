"""Deterministic allocation, reconciliation, and finalization tests."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from checkmate.domain.models import (
    Assignments,
    Money,
    Participant,
    ParticipantTotal,
    Receipt,
    ReceiptItem,
    SplitInput,
)
from checkmate.domain.splitting import (
    allocate_component,
    allocate_item,
    calculate_split,
    finalize_split,
)
from checkmate.domain.validation import validate_business_rules


def make_split(
    *,
    items: tuple[ReceiptItem, ...],
    participants: tuple[Participant, ...],
    assignments: tuple[tuple[str, tuple[str, ...]], ...],
    subtotal: int,
    tax: int,
    tip: int,
    total: int,
) -> SplitInput:
    return SplitInput(
        receipt=Receipt(
            restaurant_name="Example Cafe",
            receipt_date=date(2026, 8, 16),
            items=items,
            subtotal=Money(subtotal),
            tax=Money(tax),
            tip=Money(tip),
            total=Money(total),
        ),
        participants=participants,
        assignments=Assignments(assignments),
    )


def item(item_id: str, cents: int, quantity: str = "1") -> ReceiptItem:
    return ReceiptItem(
        id=item_id,
        name=f"Synthetic {item_id}",
        quantity=Decimal(quantity),
        line_total=Money(cents),
    )


def person(person_id: str) -> Participant:
    return Participant(id=person_id, name=f"Person {person_id}")


def test_equal_item_sharing_distributes_indivisible_cents_by_input_order() -> None:
    shares = allocate_item(Money(1001), ("alice", "bob"))
    assert [(share.participant_id, share.amount.cents) for share in shares] == [
        ("alice", 501),
        ("bob", 500),
    ]
    assert sum(share.amount.cents for share in shares) == 1001


def test_zero_item_may_be_unassigned_but_non_zero_item_may_not() -> None:
    assert allocate_item(Money(0), ()) == ()
    with pytest.raises(ValueError, match="requires"):
        allocate_item(Money(1), ())


def test_largest_remainder_uses_participant_order_for_exact_ties() -> None:
    allocated = allocate_component(
        Money(1),
        {"alice": Money(1), "bob": Money(1)},
        ("alice", "bob"),
    )
    assert allocated == {"alice": Money(1), "bob": Money(0)}


def test_zero_component_and_subtotal_allocate_zero_to_every_participant() -> None:
    assert allocate_component(Money(0), {"alice": Money(0)}, ("alice",)) == {
        "alice": Money(0)
    }
    with pytest.raises(ValueError, match="non-zero component"):
        allocate_component(Money(1), {"alice": Money(0)}, ("alice",))


def test_complete_domain_design_example_is_cent_exact_and_finalized() -> None:
    split_input = make_split(
        items=(item("pizza", 1001), item("salad", 700)),
        participants=(person("alice"), person("bob")),
        assignments=(
            ("pizza", ("alice", "bob")),
            ("salad", ("bob",)),
        ),
        subtotal=1701,
        tax=137,
        tip=255,
        total=2093,
    )

    result = calculate_split(split_input)
    finalized, issues = finalize_split(split_input, result)

    assert issues == ()
    assert finalized is not None
    assert [
        (
            participant.participant_id,
            participant.item_subtotal.cents,
            participant.tax.cents,
            participant.tip.cents,
            participant.total.cents,
        )
        for participant in result.participant_totals
    ] == [
        ("alice", 501, 40, 75, 616),
        ("bob", 1200, 97, 180, 1477),
    ]
    assert result.reconciliation.subtotal_difference_cents == 0
    assert result.reconciliation.total_difference_cents == 0

    assert all(
        sum(share.amount.cents for share in allocation.shares)
        == next(
            receipt_item.line_total.cents
            for receipt_item in split_input.receipt.items
            if receipt_item.id == allocation.item_id
        )
        for allocation in result.item_allocations
    )
    assert sum(total.item_subtotal.cents for total in result.participant_totals) == 1701
    assert sum(total.tax.cents for total in result.participant_totals) == 137
    assert sum(total.tip.cents for total in result.participant_totals) == 255
    assert sum(total.total.cents for total in result.participant_totals) == 2093


@pytest.mark.parametrize(
    ("change", "expected_code"),
    [
        ({"assignments": Assignments((("pizza", ()),))}, "unassigned_item"),
        ({"participants": ()}, "participants_required"),
    ],
)
def test_business_rules_block_unassigned_items_and_missing_participants(
    change: dict[str, object], expected_code: str
) -> None:
    split_input = make_split(
        items=(item("pizza", 100),),
        participants=(person("alice"),),
        assignments=(("pizza", ("alice",)),),
        subtotal=100,
        tax=0,
        tip=0,
        total=100,
    )
    invalid = replace(split_input, **change)
    assert expected_code in {issue.code for issue in validate_business_rules(invalid)}


def test_reconciliation_reports_both_subtotal_and_total_mismatches() -> None:
    split_input = make_split(
        items=(item("item-1", 100),),
        participants=(person("person-1"),),
        assignments=(("item-1", ("person-1",)),),
        subtotal=99,
        tax=10,
        tip=20,
        total=128,
    )
    result = calculate_split(split_input)
    finalized, issues = finalize_split(split_input, result)

    assert finalized is None
    assert {issue.code for issue in issues} == {
        "subtotal_mismatch",
        "total_mismatch",
        "participant_total_mismatch",
    }
    assert result.reconciliation.subtotal_difference_cents == -1
    assert result.reconciliation.total_difference_cents == -2


@pytest.mark.parametrize(
    ("tax", "tip", "expected_codes"),
    [
        (1, 0, {"zero_subtotal_tax", "total_mismatch"}),
        (0, 1, {"zero_subtotal_tip", "total_mismatch"}),
        (0, 0, {"zero_receipt"}),
    ],
)
def test_zero_subtotal_rules_and_zero_receipt_finalization_blocker(
    tax: int, tip: int, expected_codes: set[str]
) -> None:
    split_input = make_split(
        items=(item("free", 0),),
        participants=(person("alice"),),
        assignments=(("free", ()),),
        subtotal=0,
        tax=tax,
        tip=tip,
        total=0,
    )
    assert expected_codes <= {
        issue.code for issue in validate_business_rules(split_input)
    }
    if tax == 0 and tip == 0:
        result = calculate_split(split_input)
        finalized, issues = finalize_split(split_input, result)
        assert finalized is None
        assert {issue.code for issue in issues} == {"zero_receipt"}


def test_tampered_participant_total_cannot_be_finalized() -> None:
    split_input = make_split(
        items=(item("item-1", 100),),
        participants=(person("person-1"),),
        assignments=(("item-1", ("person-1",)),),
        subtotal=100,
        tax=0,
        tip=0,
        total=100,
    )
    result = calculate_split(split_input)
    tampered = replace(
        result,
        participant_totals=(
            ParticipantTotal(
                participant_id="person-1",
                item_subtotal=Money(100),
                tax=Money(0),
                tip=Money(0),
                total=Money(99),
            ),
        ),
    )
    finalized, issues = finalize_split(split_input, tampered)
    assert finalized is None
    assert "participant_total_mismatch" in {issue.code for issue in issues}
