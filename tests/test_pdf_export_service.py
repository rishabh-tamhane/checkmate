"""Application tests for independent PDF finalization and rendering."""

from checkmate.adapters.pdf_renderer import FakePdfRenderer
from checkmate.application.models import (
    RawParticipant,
    RawReceipt,
    RawReceiptItem,
    RawSplitDraft,
)
from checkmate.application.services import PdfExportService


def draft(*, subtotal: str = "10.00", total: str = "13.00") -> RawSplitDraft:
    """Return one complete raw export draft."""
    return RawSplitDraft(
        revision=4,
        receipt=RawReceipt(
            restaurant_name="Synthetic Cafe",
            receipt_date="2026-08-16",
            items=(RawReceiptItem("item-1", "Noodles", "1", "10.00"),),
            subtotal=subtotal,
            tax="1.00",
            tip="2.00",
            total=total,
        ),
        participants=(RawParticipant("person-1", "Maya"),),
        assignments=(("item-1", ("person-1",)),),
    )


def test_valid_draft_calls_renderer_once_with_finalized_split() -> None:
    renderer = FakePdfRenderer(b"synthetic pdf")

    output = PdfExportService(renderer).export(draft())

    assert output.content == b"synthetic pdf"
    assert output.calculation.finalized
    assert len(renderer.splits) == 1
    assert renderer.splits[0] is output.calculation.finalized_split


def test_invalid_draft_returns_calculation_issues_without_rendering() -> None:
    renderer = FakePdfRenderer()

    output = PdfExportService(renderer).export(draft(subtotal="9.00"))

    assert output.content is None
    assert {issue.code for issue in output.calculation.issues} >= {"subtotal_mismatch"}
    assert renderer.splits == []


def test_zero_draft_never_calls_renderer() -> None:
    renderer = FakePdfRenderer()
    zero = RawSplitDraft(
        revision=5,
        receipt=RawReceipt(
            restaurant_name="",
            receipt_date="",
            items=(RawReceiptItem("free", "Water", "1", "0"),),
            subtotal="0",
            tax="0",
            tip="0",
            total="0",
        ),
        participants=(RawParticipant("person-1", "Maya"),),
        assignments=(("free", ()),),
    )

    output = PdfExportService(renderer).export(zero)

    assert output.content is None
    assert {issue.code for issue in output.calculation.issues} == {"zero_receipt"}
    assert renderer.splits == []
