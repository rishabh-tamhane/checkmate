"""Table-driven coverage for domain boundary values and references."""

from datetime import date
from decimal import Decimal

import pytest

from checkmate.domain.models import Money
from checkmate.domain.money import (
    InvalidMoneyError,
    format_money,
    format_signed_cents,
    parse_money,
)
from checkmate.domain.validation import (
    normalize_assignments,
    validate_date,
    validate_id,
    validate_quantity,
    validate_text,
)


@pytest.mark.parametrize(
    ("raw_value", "expected_cents"),
    [("0", 0), ("12", 1200), ("12.5", 1250), ("12.50", 1250), (" 1.25 ", 125)],
)
def test_parse_money_accepts_only_canonical_decimal_values(
    raw_value: str, expected_cents: int
) -> None:
    assert parse_money(raw_value) == Money(expected_cents)


@pytest.mark.parametrize(
    "raw_value",
    ["", " ", "$12.50", "1,000.00", "-1.00", "+1", "1e2", ".50", "12.", "12.345"],
)
def test_parse_money_rejects_ambiguous_or_invalid_values(raw_value: str) -> None:
    with pytest.raises(InvalidMoneyError):
        parse_money(raw_value)


def test_money_prohibits_negative_non_integer_and_boolean_cents() -> None:
    with pytest.raises(ValueError, match="negative"):
        Money(-1)
    with pytest.raises(TypeError, match="integer"):
        Money(1.5)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="integer"):
        Money(True)


def test_money_formatting_is_exact_and_never_uses_floats() -> None:
    assert format_money(Money(0)) == "$0.00"
    assert format_money(Money(10421)) == "$104.21"
    assert format_signed_cents(50) == "$0.50"
    assert format_signed_cents(-50) == "-$0.50"


@pytest.mark.parametrize(
    ("raw_value", "required", "expected", "issue_code"),
    [
        ("  Maya  ", True, "Maya", None),
        ("", False, None, None),
        ("   ", True, None, "required_text"),
        ("x" * 201, True, None, "text_too_long"),
        ("line\nbreak", True, None, "unsupported_text"),
        ("Dinner 🙂", True, None, "unsupported_text"),
    ],
)
def test_validate_text_enforces_required_length_and_pdf_character_rules(
    raw_value: str,
    required: bool,
    expected: str | None,
    issue_code: str | None,
) -> None:
    value, issue = validate_text(raw_value, path="field", required=required)
    assert value == expected
    assert (None if issue is None else issue.code) == issue_code


@pytest.mark.parametrize(
    ("raw_value", "valid"),
    [
        ("item-1", True),
        ("9f0d5c6a-5821-45ac-974b-2e2fe70be210", True),
        ("", False),
        ("has space", False),
        ("/path", False),
        ("a" * 129, False),
    ],
)
def test_validate_id_accepts_bounded_opaque_ascii_identifiers(
    raw_value: str, valid: bool
) -> None:
    assert (validate_id(raw_value, path="id") is None) is valid


@pytest.mark.parametrize(
    ("raw_value", "expected", "issue_code"),
    [
        ("", None, None),
        ("2026-08-16", date(2026, 8, 16), None),
        ("2026-02-29", None, "invalid_date"),
        ("20260816", None, "invalid_date"),
        ("16-08-2026", None, "invalid_date"),
    ],
)
def test_validate_date_requires_an_exact_iso_calendar_date(
    raw_value: str, expected: date | None, issue_code: str | None
) -> None:
    value, issue = validate_date(raw_value, path="receipt.date")
    assert value == expected
    assert (None if issue is None else issue.code) == issue_code


@pytest.mark.parametrize(
    ("raw_value", "expected", "issue_code"),
    [
        ("", None, None),
        ("1", Decimal("1"), None),
        ("0.125", Decimal("0.125"), None),
        (" 2.5 ", Decimal("2.5"), None),
        ("0", None, "invalid_quantity"),
        ("-1", None, "invalid_quantity"),
        (".5", None, "invalid_quantity"),
        ("1.", None, "invalid_quantity"),
        ("1.2345", None, "invalid_quantity"),
    ],
)
def test_validate_quantity_is_optional_positive_and_bounded(
    raw_value: str, expected: Decimal | None, issue_code: str | None
) -> None:
    value, issue = validate_quantity(raw_value, path="item.quantity")
    assert value == expected
    assert (None if issue is None else issue.code) == issue_code


def test_assignments_are_normalized_into_participant_order() -> None:
    assignments, issues = normalize_assignments(
        item_ids=("item-1", "item-2"),
        participant_ids=("person-b", "person-a"),
        raw_assignments=(("item-1", ("person-a", "person-b")),),
    )

    assert issues == ()
    assert assignments is not None
    assert assignments.by_item == (
        ("item-1", ("person-b", "person-a")),
        ("item-2", ()),
    )
    assert assignments.for_item("missing") == ()


@pytest.mark.parametrize(
    ("raw_assignments", "expected_code"),
    [
        ((("missing", ("person-1",)),), "unknown_item_reference"),
        ((("item-1", ("missing",)),), "unknown_participant_reference"),
        (
            (("item-1", ("person-1", "person-1")),),
            "duplicate_participant_reference",
        ),
        (
            (("item-1", ("person-1",)), ("item-1", ("person-1",))),
            "duplicate_assignment_item",
        ),
    ],
)
def test_assignments_preserve_invalid_references_as_blocking_issues(
    raw_assignments: tuple[tuple[str, tuple[str, ...]], ...], expected_code: str
) -> None:
    assignments, issues = normalize_assignments(
        item_ids=("item-1",),
        participant_ids=("person-1",),
        raw_assignments=raw_assignments,
    )

    assert assignments is None
    assert expected_code in {issue.code for issue in issues}
