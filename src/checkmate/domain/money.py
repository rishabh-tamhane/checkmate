"""Deterministic parsing and formatting of integer-cent USD values."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Final

from checkmate.domain.models import Money

MONEY_PATTERN: Final = re.compile(r"^[0-9]+(?:\.[0-9]{1,2})?$")


class InvalidMoneyError(ValueError):
    """Raised when an editable money string is not canonical USD input."""


def parse_money(raw_value: str) -> Money:
    """Parse a canonical non-negative decimal string into integer cents."""
    value = raw_value.strip()
    if not MONEY_PATTERN.fullmatch(value):
        raise InvalidMoneyError(
            "Enter a non-negative amount using digits and at most two decimal places."
        )

    decimal_value = Decimal(value)
    cents = int(decimal_value * 100)
    return Money(cents)


def format_money(value: Money) -> str:
    """Format an integer-cent amount as USD with two fractional digits."""
    return f"${format_decimal(value)}"


def format_decimal(value: Money) -> str:
    """Format an integer-cent amount as a canonical editable decimal string."""
    dollars, cents = divmod(value.cents, 100)
    return f"{dollars}.{cents:02d}"


def format_signed_cents(cents: int) -> str:
    """Format a signed reconciliation difference as USD."""
    sign = "-" if cents < 0 else ""
    absolute = Money(abs(cents))
    return f"{sign}{format_money(absolute)}"
