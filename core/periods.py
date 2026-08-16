from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date


def _date_with_day(year: int, month: int, payday: int) -> date:
    return date(year, month, min(payday, monthrange(year, month)[1]))


@dataclass(frozen=True)
class FinancialPeriod:
    start: date
    end: date

    def contains(self, value: date) -> bool:
        return self.start <= value <= self.end


def financial_period_for(value: date, payday: int = 13) -> FinancialPeriod:
    if not 1 <= payday <= 31:
        raise ValueError("Den výplaty musí být mezi 1 a 31.")
    candidate = _date_with_day(value.year, value.month, payday)
    if value >= candidate:
        start = candidate
    elif value.month == 1:
        start = _date_with_day(value.year - 1, 12, payday)
    else:
        start = _date_with_day(value.year, value.month - 1, payday)
    if start.month == 12:
        next_start = _date_with_day(start.year + 1, 1, payday)
    else:
        next_start = _date_with_day(start.year, start.month + 1, payday)
    from datetime import timedelta
    return FinancialPeriod(start=start, end=next_start - timedelta(days=1))


def period_after(period: FinancialPeriod, payday: int = 13) -> FinancialPeriod:
    return financial_period_for(period.end.fromordinal(period.end.toordinal() + 1), payday)

