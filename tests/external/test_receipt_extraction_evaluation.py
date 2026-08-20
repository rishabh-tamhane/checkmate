"""Opt-in quality evaluation for the pinned receipt-extraction inputs."""

from __future__ import annotations

import os
from dataclasses import dataclass
from io import BytesIO

import pytest
from PIL import Image, ImageDraw, ImageFont

from checkmate.adapters.receipt_parser import (
    OpenAIReceiptParser,
    PillowReceiptImageNormalizer,
)
from checkmate.application.models import ExtractionResult


@dataclass(frozen=True, slots=True)
class EvaluationReceipt:
    """One generated layout and its exact expected transcription."""

    name: str
    style: str
    restaurant_name: str
    receipt_date: str
    item_names: tuple[str, ...]
    item_totals: tuple[str, ...]
    subtotal: str
    tax: str
    tip: str | None
    total: str


EVALUATION_RECEIPTS = (
    EvaluationReceipt(
        "clean-a",
        "clean",
        "North Star Cafe",
        "2026-08-01",
        ("Soup", "Bread"),
        ("8.00", "4.00"),
        "12.00",
        "0.96",
        "2.40",
        "15.36",
    ),
    EvaluationReceipt(
        "clean-b",
        "clean",
        "Juniper Table",
        "2026-08-02",
        ("Rice Bowl", "Tea"),
        ("14.50", "3.00"),
        "17.50",
        "1.40",
        "3.50",
        "22.40",
    ),
    EvaluationReceipt(
        "rotated-left",
        "rotate-left",
        "Cedar Kitchen",
        "2026-08-03",
        ("Tacos", "Salsa"),
        ("12.00", "4.00"),
        "16.00",
        "1.28",
        "3.20",
        "20.48",
    ),
    EvaluationReceipt(
        "rotated-right",
        "rotate-right",
        "Willow Grill",
        "2026-08-04",
        ("Pasta", "Soda"),
        ("18.00", "3.50"),
        "21.50",
        "1.72",
        "4.30",
        "27.52",
    ),
    EvaluationReceipt(
        "skew-a",
        "skew",
        "Maple Lunch",
        "2026-08-05",
        ("Sandwich", "Chips"),
        ("11.25", "2.75"),
        "14.00",
        "1.12",
        "2.80",
        "17.92",
    ),
    EvaluationReceipt(
        "skew-b",
        "skew",
        "Orchard Room",
        "2026-08-06",
        ("Curry", "Naan"),
        ("15.00", "4.50"),
        "19.50",
        "1.56",
        "3.90",
        "24.96",
    ),
    EvaluationReceipt(
        "long-a",
        "long",
        "Harbor Diner",
        "2026-08-07",
        ("Eggs", "Toast", "Coffee", "Fruit"),
        ("9.00", "3.00", "3.50", "4.50"),
        "20.00",
        "1.60",
        "4.00",
        "25.60",
    ),
    EvaluationReceipt(
        "long-b",
        "long",
        "Meadow Cafe",
        "2026-08-08",
        ("Salad", "Soup", "Juice", "Cake"),
        ("10.00", "7.00", "4.00", "6.00"),
        "27.00",
        "2.16",
        "5.40",
        "34.56",
    ),
    EvaluationReceipt(
        "contrast-a",
        "low-contrast",
        "Birch Bistro",
        "2026-08-09",
        ("Noodles", "Tea"),
        ("13.00", "3.00"),
        "16.00",
        "1.28",
        "3.20",
        "20.48",
    ),
    EvaluationReceipt(
        "contrast-b",
        "low-contrast",
        "Stone Cafe",
        "2026-08-10",
        ("Burger", "Fries"),
        ("12.00", "5.00"),
        "17.00",
        "1.36",
        "3.40",
        "21.76",
    ),
    EvaluationReceipt(
        "no-tip-a",
        "no-tip",
        "Lake Counter",
        "2026-08-11",
        ("Bagel", "Coffee"),
        ("5.00", "3.00"),
        "8.00",
        "0.64",
        None,
        "8.64",
    ),
    EvaluationReceipt(
        "no-tip-b",
        "no-tip",
        "Pine Bakery",
        "2026-08-12",
        ("Pastry", "Milk"),
        ("4.50", "2.50"),
        "7.00",
        "0.56",
        None,
        "7.56",
    ),
)


def generated_receipt_image(receipt: EvaluationReceipt) -> bytes:
    """Render and transform one fictional receipt entirely in memory."""
    height = 1_800 if receipt.style == "long" else 900
    background = 225 if receipt.style == "low-contrast" else 255
    foreground = 150 if receipt.style == "low-contrast" else 0
    image = Image.new("L", (700, height), background)
    draw = ImageDraw.Draw(image)
    lines = [
        receipt.restaurant_name,
        receipt.receipt_date,
        "",
        *(
            f"{name}  {amount}"
            for name, amount in zip(
                receipt.item_names, receipt.item_totals, strict=True
            )
        ),
        "",
        f"SUBTOTAL  {receipt.subtotal}",
        f"TAX  {receipt.tax}",
    ]
    if receipt.tip is not None:
        lines.append(f"TIP  {receipt.tip}")
    lines.append(f"TOTAL  {receipt.total}")
    draw.multiline_text(
        (70, 80),
        "\n\n".join(lines),
        fill=foreground,
        font=ImageFont.load_default(size=24),
        spacing=12,
    )

    if receipt.style == "rotate-left":
        image = image.rotate(90, expand=True)
    elif receipt.style == "rotate-right":
        image = image.rotate(-90, expand=True)
    elif receipt.style == "skew":
        image = image.transform(
            image.size,
            Image.Transform.AFFINE,
            (1, 0.12, -40, 0.04, 1, -10),
            fillcolor=background,
        )

    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def optional_text_score(
    expected: EvaluationReceipt, actual: ExtractionResult
) -> tuple[int, int]:
    """Count exact normalized optional restaurant, date, and item-name values."""
    expected_values = (
        expected.restaurant_name.casefold(),
        expected.receipt_date.casefold(),
        *(name.casefold() for name in expected.item_names),
    )
    actual_values = (
        (actual.restaurant_name or "").strip().casefold(),
        (actual.receipt_date or "").strip().casefold(),
        *(item.name.strip().casefold() for item in actual.items),
    )
    exact = sum(
        left == right
        for left, right in zip(expected_values, actual_values, strict=True)
    )
    return exact, len(expected_values)


@pytest.mark.external
@pytest.mark.asyncio
async def test_pinned_model_meets_the_approved_twelve_receipt_threshold() -> None:
    """Run paid quality evidence only after an explicit local opt-in."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        pytest.fail("OPENAI_API_KEY is required with --run-external")
    parser = OpenAIReceiptParser(api_key)
    normalizer = PillowReceiptImageNormalizer()
    exact_optional = 0
    optional_total = 0

    async def evaluate() -> None:
        nonlocal exact_optional, optional_total
        for fixture in EVALUATION_RECEIPTS:
            image = normalizer.normalize(generated_receipt_image(fixture))
            result = await parser.parse(image)
            assert len(result.items) == len(fixture.item_names), fixture.name
            assert (
                tuple(item.line_total for item in result.items) == fixture.item_totals
            )
            assert result.subtotal == fixture.subtotal
            assert result.tax == fixture.tax
            assert result.tip == (fixture.tip or "0.00")
            assert result.total == fixture.total
            assert len(result.items) <= len(fixture.item_names), fixture.name
            exact, count = optional_text_score(fixture, result)
            exact_optional += exact
            optional_total += count

    await evaluate()

    assert len(EVALUATION_RECEIPTS) == 12
    assert exact_optional / optional_total >= 0.90
    print(
        "external_receipts=12 schema_valid=12 item_money_exact=12 "
        f"optional_text_exact={exact_optional}/{optional_total}"
    )
