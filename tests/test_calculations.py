from datetime import date
from decimal import Decimal

import pytest

from core.calculations import investment_available, overdraft_available, projection_for_period
from core.models import AccountType, PlannedExpense, PlannedIncome, RecurrenceType, Transfer
from core.periods import financial_period_for

D = Decimal
PERIOD = financial_period_for(date(2026, 8, 13))


def income(amount="50000"):
    return PlannedIncome("main", D(amount), "CZK", date(2026, 8, 13), RecurrenceType.RECURRING)


def expense(amount, reserve=False):
    return PlannedExpense("main", D(amount), "CZK", date(2026, 8, 20), RecurrenceType.RECURRING, reserve)


def test_regular_period():
    result = projection_for_period({"main": D("100000")}, [income()], [expense("30000")], [], PERIOD)
    assert result["main"].best_case == D("120000")
    assert result["main"].worst_case == D("120000")


def test_reserve_is_only_in_worst_case():
    result = projection_for_period({"main": D("100000")}, [income()], [expense("30000"), expense("20000", True)], [], PERIOD)
    assert result["main"].best_case == D("120000")
    assert result["main"].worst_case == D("100000")


def test_transfer_preserves_total_in_same_currency():
    transfer = Transfer("a", "b", D("20000"), "CZK", date(2026, 8, 17))
    result = projection_for_period({"a": D("100000"), "b": D("50000")}, [], [], [transfer], PERIOD)
    assert result["a"].worst_case == D("80000")
    assert result["b"].worst_case == D("70000")
    assert sum(item.worst_case for item in result.values()) == D("150000")


def test_overdraft_available_and_investment_floor():
    assert overdraft_available(D("30000"), D("20000")) == D("10000")
    assert overdraft_available(D("30000"), D("30000")) == D("0")
    assert investment_available(D("100000"), D("0.70")) == D("70000")
    assert investment_available(D("-100"), D("0.70")) == D("0")


def test_overdraft_projection_tracks_draw_not_negative_balance():
    overdraft_expense = PlannedExpense("overdraft", D("5000"), "CZK", date(2026, 8, 20), RecurrenceType.ONE_OFF)
    result = projection_for_period({"overdraft": D("20000")}, [], [overdraft_expense], [], PERIOD, {"overdraft": AccountType.OVERDRAFT})
    assert result["overdraft"].worst_case == D("25000")


def test_unknown_account_is_not_silently_accepted():
    with pytest.raises(ValueError):
        projection_for_period({"main": D("0")}, [PlannedIncome("unknown", D("1"), "CZK", date(2026, 8, 13), RecurrenceType.ONE_OFF)], [], [], PERIOD)


def test_recurring_income_repeats_in_later_financial_periods():
    later_period = financial_period_for(date(2026, 9, 13))
    result = projection_for_period({"main": D("0")}, [income()], [], [], later_period)
    assert result["main"].worst_case == D("50000")
