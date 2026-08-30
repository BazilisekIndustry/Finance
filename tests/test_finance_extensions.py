from datetime import date
from decimal import Decimal

from services.dashboard import DashboardService


def _account(identifier, kind="current", limit="0", primary=False):
    return {"id": identifier, "name": identifier, "currency": "CZK", "account_type": kind, "is_active": True, "is_primary": primary, "overdraft_limit": limit}


def _snapshot(identifier, balance, when="2026-08-13"):
    return {"account_id": identifier, "balance": balance, "exchange_rate": "1", "snapshot_date": when}


def _build(accounts, snapshots, expenses=None, brokers=None, today=date(2026, 8, 18)):
    return DashboardService().build(accounts=accounts, latest_snapshots=snapshots, incomes=[], expenses=expenses or [], transfers=[], payday=13, investment_ratio=Decimal("0.7"), today=today, latest_broker_snapshots=brokers or [])


def test_continuous_expense_only_projects_the_part_after_snapshot():
    expense = {"account_id": "main", "amount": "3100", "currency": "CZK", "due_date": "2026-08-13", "recurrence": "recurring", "expense_kind": "continuous", "is_reserve": False, "is_active": True, "effective_from": "2026-08-13", "effective_to": None}
    data = _build([_account("main", primary=True)], [_snapshot("main", "10000", "2026-08-18")], [expense])
    # Financial period has 31 days; only 25 days (19 Aug–12 Sep) remain.
    assert data.worst_case_czk == Decimal("7500.00")


def test_purchase_power_uses_only_elapsed_continuous_budget_and_not_reserves():
    expense = {"account_id": "main", "amount": "3100", "currency": "CZK", "due_date": "2026-08-13", "recurrence": "recurring", "expense_kind": "continuous", "is_reserve": False, "is_active": True, "effective_from": "2026-08-13", "effective_to": None}
    data = _build([_account("main", primary=True)], [_snapshot("main", "10000")], [expense])
    # Snapshot is after 13 Aug, therefore days 14–18 consume 500 CZK.
    assert data.purchase_power_czk == Decimal("9500.00")


def test_overdraft_is_credit_for_purchase_power_but_debt_for_wealth():
    accounts = [_account("cash", primary=True), _account("overdraft", "overdraft", "30000")]
    data = _build(accounts, [_snapshot("cash", "100000"), _snapshot("overdraft", "10000")], brokers=[{"value_czk": "300000"}])
    assert data.current_cash_czk == Decimal("100000.00")
    assert data.purchase_power_czk == Decimal("110000.00")
    assert data.total_wealth_czk == Decimal("380000.00")


def test_unused_overdraft_does_not_increase_wealth():
    accounts = [_account("cash", primary=True), _account("overdraft", "overdraft", "30000")]
    data = _build(accounts, [_snapshot("cash", "100000"), _snapshot("overdraft", "30000")])
    assert data.total_wealth_czk == Decimal("100000.00")


def test_plan_variance_compares_actual_snapshot_with_baseline_on_its_date():
    expense = {"account_id": "main", "amount": "10000", "currency": "CZK", "due_date": "2026-08-15", "recurrence": "one_off", "expense_kind": "fixed", "is_reserve": False, "is_active": True, "effective_from": "2026-08-15", "effective_to": None}
    accounts = [_account("main", primary=True)]
    first, actual = _snapshot("main", "100000", "2026-08-13"), _snapshot("main", "85000", "2026-08-20")
    data = DashboardService().build(accounts=accounts, latest_snapshots=[actual], snapshot_history=[first, actual], incomes=[], expenses=[expense], transfers=[], payday=13, investment_ratio=Decimal("0.7"), today=date(2026, 8, 20))
    # Baseline is 90,000 on 20 Aug, not the end-of-period balance.
    assert data.plan_variance_czk == Decimal("-5000")
