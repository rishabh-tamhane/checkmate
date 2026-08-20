"""In-memory PDF-renderer adapters."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from html import escape
from io import BytesIO
from typing import Final

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from checkmate.domain.models import FinalizedSplit
from checkmate.domain.money import format_money

PDF_TITLE: Final = "Checkmate Expense Split"
PDF_AUTHOR: Final = "Checkmate"
_MONTH_NAMES: Final = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


class FakePdfRenderer:
    """Deterministic renderer for application and HTTP tests."""

    def __init__(
        self, content: bytes = b"%PDF-1.4\n% Checkmate synthetic PDF\n"
    ) -> None:
        self.content = content
        self.splits: list[FinalizedSplit] = []

    def render(self, split: FinalizedSplit) -> bytes:
        """Record the finalized split and return configured bytes."""
        self.splits.append(split)
        return self.content


class ReportLabPdfRenderer:
    """Lay out one finalized split as a complete in-memory PDF."""

    def render(self, split: FinalizedSplit) -> bytes:
        """Render trusted receipt and allocation values without recalculation."""
        output = BytesIO()
        document = SimpleDocTemplate(
            output,
            pagesize=letter,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.7 * inch,
            bottomMargin=0.7 * inch,
            title=PDF_TITLE,
            author=PDF_AUTHOR,
        )
        document.build(
            _document_flowables(split),
            onFirstPage=_set_document_metadata,
            onLaterPages=_set_document_metadata,
        )
        return output.getvalue()


def _document_flowables(split: FinalizedSplit) -> list[Flowable]:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CheckmateTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        spaceAfter=10,
    )
    body_style = ParagraphStyle(
        "CheckmateBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
    )
    header_style = ParagraphStyle(
        "CheckmateHeader",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )
    money_style = ParagraphStyle(
        "CheckmateMoney",
        parent=body_style,
        alignment=TA_RIGHT,
    )
    section_style = ParagraphStyle(
        "CheckmateSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        spaceBefore=12,
        spaceAfter=6,
    )

    receipt = split.split_input.receipt
    flowables: list[Flowable] = [Paragraph(PDF_TITLE, title_style)]
    if receipt.restaurant_name is not None:
        flowables.append(Paragraph(_safe(receipt.restaurant_name), body_style))
    if receipt.receipt_date is not None:
        flowables.append(Paragraph(_format_date(receipt.receipt_date), body_style))

    flowables.extend(
        [
            Paragraph("Itemized bill", section_style),
            _item_table(split, body_style, header_style, money_style),
            Spacer(1, 8),
            _receipt_totals_table(split, body_style, money_style),
            Paragraph("Split summary", section_style),
            _participant_table(split, body_style, header_style, money_style),
        ]
    )
    return flowables


def _item_table(
    split: FinalizedSplit,
    body_style: ParagraphStyle,
    header_style: ParagraphStyle,
    money_style: ParagraphStyle,
) -> Table:
    participants = {
        participant.id: participant.name
        for participant in split.split_input.participants
    }
    rows: list[list[Flowable]] = [
        [
            Paragraph("Item", header_style),
            Paragraph("Qty", header_style),
            Paragraph("Line total", header_style),
            Paragraph("Shared by", header_style),
        ]
    ]
    for item in split.split_input.receipt.items:
        assigned_names = [
            participants[participant_id]
            for participant_id in split.split_input.assignments.for_item(item.id)
        ]
        rows.append(
            [
                Paragraph(_safe(item.name), body_style),
                Paragraph(_format_quantity(item.quantity), body_style),
                Paragraph(format_money(item.line_total), money_style),
                Paragraph(_safe(", ".join(assigned_names)), body_style),
            ]
        )
    return _styled_table(rows, (2.35 * inch, 0.45 * inch, 0.85 * inch, 3.35 * inch))


def _receipt_totals_table(
    split: FinalizedSplit,
    body_style: ParagraphStyle,
    money_style: ParagraphStyle,
) -> Table:
    receipt = split.split_input.receipt
    rows = [
        [Paragraph(label, body_style), Paragraph(format_money(value), money_style)]
        for label, value in (
            ("Subtotal", receipt.subtotal),
            ("Tax", receipt.tax),
            ("Tip", receipt.tip),
            ("Total", receipt.total),
        )
    ]
    table = Table(rows, colWidths=(5.9 * inch, 1.1 * inch), hAlign="RIGHT")
    table.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, -1), (-1, -1), 0.75, colors.HexColor("#374151")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _participant_table(
    split: FinalizedSplit,
    body_style: ParagraphStyle,
    header_style: ParagraphStyle,
    money_style: ParagraphStyle,
) -> Table:
    participant_names = {
        participant.id: participant.name
        for participant in split.split_input.participants
    }
    rows: list[list[Flowable]] = [
        [
            Paragraph("Person", header_style),
            Paragraph("Items", header_style),
            Paragraph("Tax", header_style),
            Paragraph("Tip", header_style),
            Paragraph("Amount owed", header_style),
        ]
    ]
    for total in split.result.participant_totals:
        rows.append(
            [
                Paragraph(_safe(participant_names[total.participant_id]), body_style),
                Paragraph(format_money(total.item_subtotal), money_style),
                Paragraph(format_money(total.tax), money_style),
                Paragraph(format_money(total.tip), money_style),
                Paragraph(format_money(total.total), money_style),
            ]
        )
    return _styled_table(
        rows,
        (2.2 * inch, 1.1 * inch, 0.9 * inch, 0.9 * inch, 1.9 * inch),
    )


def _styled_table(rows: list[list[Flowable]], widths: tuple[float, ...]) -> Table:
    table = Table(
        rows,
        colWidths=widths,
        repeatRows=1,
        splitByRow=1,
        splitInRow=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#374151")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D1D5DB")),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _safe(value: str) -> str:
    return escape(value, quote=True)


def _format_date(value: date) -> str:
    return f"{_MONTH_NAMES[value.month - 1]} {value.day}, {value.year}"


def _format_quantity(value: Decimal | None) -> str:
    return "" if value is None else format(value, "f")


def _set_document_metadata(canvas: Canvas, _: BaseDocTemplate) -> None:
    canvas.setTitle(PDF_TITLE)
    canvas.setAuthor(PDF_AUTHOR)


__all__ = ["FakePdfRenderer", "ReportLabPdfRenderer"]
