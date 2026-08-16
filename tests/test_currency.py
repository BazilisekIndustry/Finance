from decimal import Decimal

from core.currency import convert, to_czk


def test_currency_conversion_to_czk_and_between_currencies():
    assert to_czk(Decimal("100"), Decimal("25.50")) == Decimal("2550.00")
    assert convert(Decimal("100"), Decimal("25.50"), Decimal("30.00")) == Decimal("85.00")

