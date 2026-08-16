from __future__ import annotations

from decimal import Decimal


SUPPORTED_CURRENCIES = frozenset({"CZK", "EUR", "USD"})


def validate_currency(currency: str) -> str:
    normalized = currency.upper().strip()
    if normalized not in SUPPORTED_CURRENCIES:
        raise ValueError("Podporované měny jsou CZK, EUR a USD.")
    return normalized


def positive_decimal(value: Decimal, label: str) -> Decimal:
    if value <= 0:
        raise ValueError(f"{label} musí být větší než nula.")
    return value


def non_negative_decimal(value: Decimal, label: str) -> Decimal:
    if value < 0:
        raise ValueError(f"{label} nesmí být záporné.")
    return value

