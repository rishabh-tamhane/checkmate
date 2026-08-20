"""Semantic tests for complete in-memory ReportLab PDF output."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import BytesIO

from pypdf import PdfReader

from checkmate.adapters.pdf_renderer import ReportLabPdfRenderer
from checkmate.domain.models import (
    Assignments,
    FinalizedSplit,
    Money,
    Participant,
    Receipt,
    ReceiptItem,
    SplitInput,
)
from checkmate.domain.splitting import calculate_split, finalize_split


def finalized_split(
    *,
    restaurant_name: str | None = "A&B <Kitchen>",
    receipt_date: date | None = date(2026, 8, 16),
    item_count: int = 2,
    long_text: bool = False,
) -> FinalizedSplit:
    """Build a deterministic finalized split without raw boundary parsing."""
    participants = (
        Participant("person-1", "Maya & Alex" if long_text else "Maya"),
        Participant("person-2", "Sam <Taylor>" if long_text else "Alex"),
    )
    items = tuple(
        ReceiptItem(
            id=f"item-{index}",
            name=(
                f"Item {index:03d} " + "wrapped synthetic description " * 5
                if long_text
                else f"Item {index:03d}"
            ),
            quantity=Decimal("1.5") if index == 0 else None,
            line_total=Money(100),
        )
        for index in range(item_count)
    )
    subtotal = Money(item_count * 100)
    split_input = SplitInput(
        receipt=Receipt(
            restaurant_name=restaurant_name,
            receipt_date=receipt_date,
            items=items,
            subtotal=subtotal,
            tax=Money(0),
            tip=Money(0),
            total=subtotal,
        ),
        participants=participants,
        assignments=Assignments(
            tuple((item.id, ("person-1", "person-2")) for item in items)
        ),
    )
    result = calculate_split(split_input)
    finalized, issues = finalize_split(split_input, result)
    assert issues == ()
    assert finalized is not None
    return finalized


def extracted_text(content: bytes) -> tuple[PdfReader, str]:
    """Return the parsed document and all semantic page text."""
    reader = PdfReader(BytesIO(content))
    return reader, "\n".join(page.extract_text() or "" for page in reader.pages)


def test_pdf_contains_ordered_sections_metadata_dates_money_and_escaped_text() -> None:
    content = ReportLabPdfRenderer().render(finalized_split())

    reader, text = extracted_text(content)

    assert text.index("Checkmate Expense Split") < text.index("Itemized bill")
    assert text.index("Itemized bill") < text.index("Split summary")
    assert "A&B <Kitchen>" in text
    assert "August 16, 2026" in text
    assert text.index("Item 000") < text.index("Item 001")
    assert text.index("Maya") < text.index("Alex")
    assert "1.5" in text
    assert "$1.00" in text
    assert "$2.00" in text
    assert reader.metadata is not None
    assert reader.metadata.title == "Checkmate Expense Split"
    assert reader.metadata.author == "Checkmate"


def test_optional_receipt_metadata_is_omitted() -> None:
    _, text = extracted_text(
        ReportLabPdfRenderer().render(
            finalized_split(restaurant_name=None, receipt_date=None)
        )
    )

    assert "August 16, 2026" not in text
    assert "A&B <Kitchen>" not in text
    assert "Itemized bill" in text


def test_long_multi_page_pdf_wraps_and_preserves_every_required_row() -> None:
    split = finalized_split(item_count=75, long_text=True)
    reader, text = extracted_text(ReportLabPdfRenderer().render(split))
    compact_text = "".join(text.split())

    assert len(reader.pages) > 1
    assert text.count("Line total") >= 2
    for item in split.split_input.receipt.items:
        assert "".join(item.name.split()) in compact_text
    assert "Maya & Alex" in text
    assert "Sam <Taylor>" in text
    assert "$75.00" in text
