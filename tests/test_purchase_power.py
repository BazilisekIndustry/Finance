from datetime import date
from decimal import Decimal

from services.dashboard import DashboardService


def test_purchase_power_includes_planned_expense_that_has_already_occurred():
    accounts = [{"id": "main", "name": "Hlavní", "currency": "CZK", "account_type": "main_current", "is_active": True, "is_primary": True, "overdraft_limit": "0"}]
    snapshots = [{"account_id": "main", "balance": "3000", "exchange_rate": "1", "snapshot_date": "2026-08-13"}]
    expenses = [{"account_id": "main", "amount": "1000", "currency": "CZK", "due_date": "2026-08-15", "recurrence": "one_off", "is_reserve": False, "is_active": True, "effective_from": "2026-08-15", "effective_to": None}]

    before_expense = DashboardService().build(accounts=accounts, latest_snapshots=snapshots, incomes=[], expenses=expenses, transfers=[], payday=13, investment_ratio=Decimal("0.7"), today=date(2026, 8, 13))
    after_expense = DashboardService().build(accounts=accounts, latest_snapshots=snapshots, incomes=[], expenses=expenses, transfers=[], payday=13, investment_ratio=Decimal("0.7"), today=date(2026, 8, 20))

    assert before_expense.purchase_power_czk == Decimal("3000.00")
    assert after_expense.purchase_power_czk == Decimal("2000.00")
