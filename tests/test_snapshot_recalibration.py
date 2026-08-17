from datetime import date
from decimal import Decimal

from core.prediction import project_periods
from core.periods import financial_period_for
from services.dashboard import DashboardService


def account(identifier: str = "main"):
    return {"id": identifier, "name": identifier, "currency": "CZK", "account_type": "main_current", "is_active": True, "is_primary": identifier == "main", "overdraft_limit": "0"}


def snapshot(identifier: str, value: str, when: str):
    return {"account_id": identifier, "balance": value, "exchange_rate": "1", "snapshot_date": when}


def expense(when: str):
    return {"account_id": "main", "amount": "10000", "currency": "CZK", "due_date": when, "recurrence": "one_off", "is_reserve": False, "is_active": True, "effective_from": when, "effective_to": None}


def income(when: str):
    return {"account_id": "main", "amount": "10000", "currency": "CZK", "due_date": when, "recurrence": "one_off", "is_active": True, "effective_from": when, "effective_to": None}


def build(snapshots, incomes=None, expenses=None, transfers=None, accounts=None):
    return DashboardService().build(accounts=accounts or [account()], latest_snapshots=snapshots, incomes=incomes or [], expenses=expenses or [], transfers=transfers or [], payday=13, investment_ratio=Decimal("0.7"), today=date(2026, 8, 20))


def test_past_expense_is_not_replayed_after_snapshot():
    assert build([snapshot("main", "85000", "2026-08-20")], expenses=[expense("2026-08-18")]).worst_case_czk == Decimal("85000.00")


def test_future_expense_is_included_after_snapshot():
    assert build([snapshot("main", "85000", "2026-08-20")], expenses=[expense("2026-08-25")]).worst_case_czk == Decimal("75000.00")


def test_past_income_is_not_replayed_after_snapshot():
    assert build([snapshot("main", "85000", "2026-08-20")], incomes=[income("2026-08-13")]).worst_case_czk == Decimal("85000.00")


def test_future_income_is_included_after_snapshot():
    assert build([snapshot("main", "85000", "2026-08-20")], incomes=[income("2026-08-25")]).worst_case_czk == Decimal("95000.00")


def test_latest_snapshot_is_the_prediction_opening_balance():
    assert build([snapshot("main", "85000", "2026-08-20")]).worst_case_czk == Decimal("85000.00")


def test_latest_of_multiple_snapshots_in_the_period_is_used():
    period = financial_period_for(date(2026, 8, 20), 13)
    forecast = project_periods(
        {"main": Decimal("100000")}, period, 1, 13, [], [], [],
        actual_snapshots={date(2026, 8, 13): {"main": Decimal("100000")}, date(2026, 8, 20): {"main": Decimal("85000")}},
    )
    assert forecast[0][1]["main"].worst_case == Decimal("85000")


def test_transfer_already_reflected_by_both_snapshots_is_not_replayed():
    accounts = [account("main"), account("savings")]
    accounts[1]["is_primary"] = False
    transfer = {"source_account_id": "main", "target_account_id": "savings", "amount": "10000", "target_amount": None, "exchange_rate": None, "currency": "CZK", "transfer_date": "2026-08-18"}
    data = build([snapshot("main", "85000", "2026-08-20"), snapshot("savings", "200000", "2026-08-20")], transfers=[transfer], accounts=accounts)
    assert data.projections["main"].worst_case == Decimal("85000")
    assert data.projections["savings"].worst_case == Decimal("200000")
