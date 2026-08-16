from datetime import date

from core.periods import financial_period_for


def test_payday_period_boundary():
    assert financial_period_for(date(2026, 8, 12)).start == date(2026, 7, 13)
    period = financial_period_for(date(2026, 8, 13))
    assert period.start == date(2026, 8, 13)
    assert period.end == date(2026, 9, 12)

