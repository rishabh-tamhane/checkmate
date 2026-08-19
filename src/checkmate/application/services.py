"""Application use cases assembled by the web composition root."""

from __future__ import annotations

from collections import Counter

from checkmate.application.models import CalculationOutput, RawSplitDraft
from checkmate.domain.models import (
    Assignments,
    Money,
    Participant,
    Receipt,
    ReceiptItem,
    SplitInput,
    ValidationIssue,
)
from checkmate.domain.money import InvalidMoneyError, parse_money
from checkmate.domain.splitting import (
    calculate_split,
    finalize_split,
    reconcile_receipt,
)
from checkmate.domain.validation import (
    MAX_ITEMS,
    MAX_PARTICIPANTS,
    normalize_assignments,
    validate_business_rules,
    validate_date,
    validate_id,
    validate_quantity,
    validate_text,
)

ALLOCATION_BLOCKING_CODES = frozenset(
    {
        "unassigned_item",
        "participants_required",
        "zero_subtotal_tax",
        "zero_subtotal_tip",
    }
)


def calculate_draft(draft: RawSplitDraft) -> CalculationOutput:
    """Convert and calculate one raw draft without external dependencies."""
    split_input, conversion_issues = _convert_draft(draft)
    if split_input is None:
        return CalculationOutput(
            revision=draft.revision,
            normalized=None,
            issues=conversion_issues,
            item_allocations=(),
            participant_totals=(),
            reconciliation=None,
            finalized_split=None,
        )

    business_issues = validate_business_rules(split_input)
    if any(issue.code in ALLOCATION_BLOCKING_CODES for issue in business_issues):
        return CalculationOutput(
            revision=draft.revision,
            normalized=split_input,
            issues=business_issues,
            item_allocations=(),
            participant_totals=(),
            reconciliation=reconcile_receipt(split_input),
            finalized_split=None,
        )

    result = calculate_split(split_input)
    finalized, final_issues = finalize_split(
        split_input, result, issues=business_issues
    )
    return CalculationOutput(
        revision=draft.revision,
        normalized=split_input,
        issues=final_issues,
        item_allocations=result.item_allocations,
        participant_totals=result.participant_totals,
        reconciliation=result.reconciliation,
        finalized_split=finalized,
    )


def _convert_draft(
    draft: RawSplitDraft,
) -> tuple[SplitInput | None, tuple[ValidationIssue, ...]]:
    issues: list[ValidationIssue] = []
    if len(draft.receipt.items) > MAX_ITEMS:
        issues.append(
            ValidationIssue(
                code="too_many_items",
                path="receipt.items",
                message=f"Use at most {MAX_ITEMS} receipt items.",
            )
        )
    if len(draft.participants) > MAX_PARTICIPANTS:
        issues.append(
            ValidationIssue(
                code="too_many_participants",
                path="participants",
                message=f"Use at most {MAX_PARTICIPANTS} participants.",
            )
        )

    restaurant_name, issue = validate_text(
        draft.receipt.restaurant_name,
        path="receipt.restaurant_name",
        required=False,
    )
    _append_issue(issues, issue)
    receipt_date, issue = validate_date(draft.receipt.receipt_date, path="receipt.date")
    _append_issue(issues, issue)

    item_id_counts = Counter(item.id for item in draft.receipt.items)
    items: list[ReceiptItem] = []
    for index, raw_item in enumerate(draft.receipt.items):
        item_path = f"receipt.items.{raw_item.id or index}"
        id_issue = validate_id(raw_item.id, path=f"receipt.items.{index}.id")
        _append_issue(issues, id_issue)
        if item_id_counts[raw_item.id] > 1:
            issues.append(
                ValidationIssue(
                    code="duplicate_item_id",
                    path=f"receipt.items.{index}.id",
                    message="Each receipt item must have a unique identifier.",
                )
            )
        name, name_issue = validate_text(
            raw_item.name, path=f"{item_path}.name", required=True
        )
        _append_issue(issues, name_issue)
        quantity, quantity_issue = validate_quantity(
            raw_item.quantity, path=f"{item_path}.quantity"
        )
        _append_issue(issues, quantity_issue)
        line_total, money_issue = _parse_money_field(
            raw_item.line_total, path=f"{item_path}.line_total"
        )
        _append_issue(issues, money_issue)
        if (
            id_issue is None
            and item_id_counts[raw_item.id] == 1
            and name is not None
            and quantity_issue is None
            and line_total is not None
        ):
            items.append(
                ReceiptItem(
                    id=raw_item.id,
                    name=name,
                    quantity=quantity,
                    line_total=line_total,
                )
            )

    participant_id_counts = Counter(
        participant.id for participant in draft.participants
    )
    participants: list[Participant] = []
    normalized_names: list[tuple[int, str]] = []
    for index, raw_participant in enumerate(draft.participants):
        path = f"participants.{raw_participant.id or index}"
        id_issue = validate_id(raw_participant.id, path=f"participants.{index}.id")
        _append_issue(issues, id_issue)
        if participant_id_counts[raw_participant.id] > 1:
            issues.append(
                ValidationIssue(
                    code="duplicate_participant_id",
                    path=f"participants.{index}.id",
                    message="Each participant must have a unique identifier.",
                )
            )
        name, name_issue = validate_text(
            raw_participant.name, path=f"{path}.name", required=True
        )
        _append_issue(issues, name_issue)
        if name is not None:
            normalized_names.append((index, name.casefold()))
        if (
            id_issue is None
            and participant_id_counts[raw_participant.id] == 1
            and name is not None
        ):
            participants.append(Participant(id=raw_participant.id, name=name))

    name_counts = Counter(name for _, name in normalized_names)
    for index, name in normalized_names:
        if name_counts[name] > 1:
            participant_id = draft.participants[index].id or str(index)
            issues.append(
                ValidationIssue(
                    code="duplicate_participant_name",
                    path=f"participants.{participant_id}.name",
                    message="Participant names must be unique.",
                )
            )

    subtotal, subtotal_issue = _parse_money_field(
        draft.receipt.subtotal, path="receipt.subtotal"
    )
    tax, tax_issue = _parse_money_field(draft.receipt.tax, path="receipt.tax")
    tip, tip_issue = _parse_money_field(draft.receipt.tip, path="receipt.tip")
    total, total_issue = _parse_money_field(draft.receipt.total, path="receipt.total")
    for money_issue in (subtotal_issue, tax_issue, tip_issue, total_issue):
        _append_issue(issues, money_issue)

    valid_record_shapes = len(items) == len(draft.receipt.items) and len(
        participants
    ) == len(draft.participants)
    assignments: Assignments | None = None
    if valid_record_shapes:
        assignments, assignment_issues = normalize_assignments(
            item_ids=tuple(item.id for item in items),
            participant_ids=tuple(participant.id for participant in participants),
            raw_assignments=draft.assignments,
        )
        issues.extend(assignment_issues)

    if (
        issues
        or assignments is None
        or subtotal is None
        or tax is None
        or tip is None
        or total is None
    ):
        return None, tuple(issues)

    return (
        SplitInput(
            receipt=Receipt(
                restaurant_name=restaurant_name,
                receipt_date=receipt_date,
                items=tuple(items),
                subtotal=subtotal,
                tax=tax,
                tip=tip,
                total=total,
            ),
            participants=tuple(participants),
            assignments=assignments,
        ),
        (),
    )


def _parse_money_field(
    raw_value: str, *, path: str
) -> tuple[Money | None, ValidationIssue | None]:
    try:
        return parse_money(raw_value), None
    except InvalidMoneyError:
        return None, ValidationIssue(
            code="invalid_money",
            path=path,
            message="Enter a non-negative amount with at most two decimal places.",
        )


def _append_issue(issues: list[ValidationIssue], issue: ValidationIssue | None) -> None:
    if issue is not None:
        issues.append(issue)


__all__ = [
    "CalculationOutput",
    "RawSplitDraft",
    "calculate_draft",
]
