"""Equal item splitting and proportional tax and tip allocation."""

from __future__ import annotations

from collections.abc import Mapping

from checkmate.domain.models import (
    FinalizedSplit,
    ItemAllocation,
    Money,
    ParticipantShare,
    ParticipantTotal,
    Reconciliation,
    SplitInput,
    SplitResult,
    ValidationIssue,
)
from checkmate.domain.validation import (
    validate_business_rules,
    validate_participant_total,
)


def allocate_item(
    line_total: Money, assigned_participant_ids: tuple[str, ...]
) -> tuple[ParticipantShare, ...]:
    """Divide one line total equally, assigning remainder cents by order."""
    if not assigned_participant_ids:
        if line_total.cents == 0:
            return ()
        raise ValueError("A non-zero item requires at least one participant.")

    base, remainder = divmod(line_total.cents, len(assigned_participant_ids))
    return tuple(
        ParticipantShare(
            participant_id=participant_id,
            amount=Money(base + (1 if index < remainder else 0)),
        )
        for index, participant_id in enumerate(assigned_participant_ids)
    )


def allocate_component(
    component: Money,
    participant_subtotals: Mapping[str, Money],
    participant_order: tuple[str, ...],
) -> dict[str, Money]:
    """Allocate tax or tip with the deterministic largest-remainder method."""
    subtotal_cents = sum(value.cents for value in participant_subtotals.values())
    if subtotal_cents == 0:
        if component.cents != 0:
            raise ValueError("A non-zero component requires a non-zero item subtotal.")
        return {participant_id: Money(0) for participant_id in participant_order}

    allocated: dict[str, int] = {}
    remainders: dict[str, int] = {}
    for participant_id in participant_order:
        numerator = component.cents * participant_subtotals[participant_id].cents
        base, remainder = divmod(numerator, subtotal_cents)
        allocated[participant_id] = base
        remainders[participant_id] = remainder

    remaining = component.cents - sum(allocated.values())
    order_index = {
        participant_id: index for index, participant_id in enumerate(participant_order)
    }
    ranked = sorted(
        participant_order,
        key=lambda participant_id: (
            -remainders[participant_id],
            order_index[participant_id],
        ),
    )
    for participant_id in ranked[:remaining]:
        allocated[participant_id] += 1

    return {
        participant_id: Money(allocated[participant_id])
        for participant_id in participant_order
    }


def calculate_split(split_input: SplitInput) -> SplitResult:
    """Calculate cent-exact allocations for an allocation-safe split input."""
    participant_order = tuple(
        participant.id for participant in split_input.participants
    )
    participant_subtotals = {
        participant_id: Money(0) for participant_id in participant_order
    }
    item_allocations: list[ItemAllocation] = []

    for item in split_input.receipt.items:
        shares = allocate_item(
            item.line_total, split_input.assignments.for_item(item.id)
        )
        item_allocations.append(ItemAllocation(item_id=item.id, shares=shares))
        for share in shares:
            current = participant_subtotals[share.participant_id]
            participant_subtotals[share.participant_id] = Money(
                current.cents + share.amount.cents
            )

    tax_shares = allocate_component(
        split_input.receipt.tax, participant_subtotals, participant_order
    )
    tip_shares = allocate_component(
        split_input.receipt.tip, participant_subtotals, participant_order
    )
    participant_totals = tuple(
        ParticipantTotal(
            participant_id=participant_id,
            item_subtotal=participant_subtotals[participant_id],
            tax=tax_shares[participant_id],
            tip=tip_shares[participant_id],
            total=Money(
                participant_subtotals[participant_id].cents
                + tax_shares[participant_id].cents
                + tip_shares[participant_id].cents
            ),
        )
        for participant_id in participant_order
    )

    return SplitResult(
        item_allocations=tuple(item_allocations),
        participant_totals=participant_totals,
        reconciliation=reconcile_receipt(split_input),
    )


def reconcile_receipt(split_input: SplitInput) -> Reconciliation:
    """Compare entered receipt amounts with independently calculated values."""
    calculated_subtotal = Money(
        sum(item.line_total.cents for item in split_input.receipt.items)
    )
    calculated_total = Money(
        calculated_subtotal.cents
        + split_input.receipt.tax.cents
        + split_input.receipt.tip.cents
    )
    return Reconciliation(
        entered_subtotal=split_input.receipt.subtotal,
        calculated_subtotal=calculated_subtotal,
        subtotal_difference_cents=(
            split_input.receipt.subtotal.cents - calculated_subtotal.cents
        ),
        entered_total=split_input.receipt.total,
        calculated_total=calculated_total,
        total_difference_cents=(
            split_input.receipt.total.cents - calculated_total.cents
        ),
    )


def finalize_split(
    split_input: SplitInput,
    result: SplitResult,
    issues: tuple[ValidationIssue, ...] | None = None,
) -> tuple[FinalizedSplit | None, tuple[ValidationIssue, ...]]:
    """Create a finalized split only after every invariant passes."""
    final_issues = list(
        validate_business_rules(split_input) if issues is None else issues
    )
    total_issue = validate_participant_total(split_input, result)
    if total_issue is not None:
        final_issues.append(total_issue)
    if any(issue.blocking for issue in final_issues):
        return None, tuple(final_issues)
    return FinalizedSplit(split_input=split_input, result=result), tuple(final_issues)
