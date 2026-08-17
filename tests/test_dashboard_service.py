from datetime import date
from decimal import Decimal

from services.dashboard import DashboardService


def test_dashboard_best_worst_and_investment_availability():
    accounts = [{"id": "main", "name": "Hlavní", "currency": "CZK", "account_type": "main_current", "is_active": True, "is_primary": True, "overdraft_limit": "0"}]
    snapshots = [{"account_id": "main", "balance": "100000", "exchange_rate": "1", "snapshot_date": "2026-08-12"}]
    incomes = [{"account_id": "main", "amount": "50000", "currency": "CZK", "due_date": "2026-08-13", "recurrence": "recurring", "is_active": True, "effective_from": "2026-08-13", "effective_to": None}]
    expenses = [
        {"account_id": "main", "amount": "30000", "currency": "CZK", "due_date": "2026-08-20", "recurrence": "recurring", "is_reserve": False, "is_active": True, "effective_from": "2026-08-20", "effective_to": None},
        {"account_id": "main", "amount": "20000", "currency": "CZK", "due_date": "2026-08-25", "recurrence": "recurring", "is_reserve": True, "is_active": True, "effective_from": "2026-08-25", "effective_to": None},
    ]
    data = DashboardService().build(accounts=accounts, latest_snapshots=snapshots, incomes=incomes, expenses=expenses, transfers=[], payday=13, investment_ratio=Decimal("0.70"), today=date(2026, 8, 16))
    assert data.best_case_czk == Decimal("120000.00")
    assert data.worst_case_czk == Decimal("100000.00")
    assert data.investment_available_czk == Decimal("70000.0000")


def test_cash_flow_forecast_supports_twelve_periods():
    accounts = [{"id": "main", "name": "Hlavní", "currency": "CZK", "account_type": "main_current", "is_active": True, "is_primary": True, "overdraft_limit": "0"}]
    snapshots = [{"account_id": "main", "balance": "100000", "exchange_rate": "1", "snapshot_date": "2026-08-16"}]
    forecast = DashboardService().cash_flow_forecast(accounts=accounts, latest_snapshots=snapshots, incomes=[], expenses=[], transfers=[], payday=13, count=12, today=date(2026, 8, 16))
    assert len(forecast) == 12
    assert forecast[-1].worst_case_czk == Decimal("100000.00")
