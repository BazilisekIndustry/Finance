from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .models import Money


def to_czk(amount: Money, rate_to_czk: Money) -> Money:
    """Convert an amount using the explicitly stored CZK rate for its currency."""
    if rate_to_czk <= 0:
        raise ValueError("Kurz musí být kladné číslo.")
    return (amount * rate_to_czk).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def convert(amount: Money, source_rate_to_czk: Money, target_rate_to_czk: Money) -> Money:
    if target_rate_to_czk <= 0:
        raise ValueError("Cílový kurz musí být kladné číslo.")
    return (amount * source_rate_to_czk / target_rate_to_czk).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

