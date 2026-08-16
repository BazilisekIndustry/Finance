from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from core.calculations import cash_available, investment_available, projection_for_period
from core.currency import to_czk
from core.models import Account, AccountProjection, AccountType, PlannedExpense, PlannedIncome, RecurrenceType, Transfer
from core.periods import FinancialPeriod, financial_period_for
from core.prediction import project_periods


@dataclass(frozen=True)
class DashboardData:
    current_cash_czk: Decimal
    best_case_czk: Decimal | None
    worst_case_czk: Decimal | None
    investment_available_czk: Decimal | None
    purchase_power_czk: Decimal
    total_wealth_czk: Decimal
    projections: dict[str, AccountProjection]
    missing_snapshot_accounts: tuple[str, ...]
    shortages_czk: dict[str, Decimal]
    period: FinancialPeriod


@dataclass(frozen=True)
class CashFlowPoint:
    period: FinancialPeriod
    best_case_czk: Decimal
    worst_case_czk: Decimal


class DashboardService:
    def cash_flow_forecast(
        self, *, accounts: list[dict[str, Any]], latest_snapshots: list[dict[str, Any]], incomes: list[dict[str, Any]],
        expenses: list[dict[str, Any]], transfers: list[dict[str, Any]], payday: int, count: int, today: date | None = None,
    ) -> list[CashFlowPoint]:
        active = [item for item in accounts if item["is_active"] and item["account_type"] != AccountType.BROKER.value]
        snapshots = {item["account_id"]: item for item in latest_snapshots}
        if any(item["id"] not in snapshots for item in active):
            return []
        opening = {item["id"]: Decimal(str(snapshots[item["id"]]["balance"])) for item in active}
        types = {item["id"]: AccountType(item["account_type"]) for item in active}
        period = financial_period_for(today or date.today(), payday)
        projections = project_periods(opening, period, count, payday, self._incomes(incomes), self._expenses(expenses), self._transfers(transfers), account_types=types)
        result = []
        for item_period, projection in projections:
            result.append(CashFlowPoint(
                item_period,
                self._available_total(active, projection, snapshots, "best_case"),
                self._available_total(active, projection, snapshots, "worst_case"),
            ))
        return result

    def build(
        self, *, accounts: list[dict[str, Any]], latest_snapshots: list[dict[str, Any]], incomes: list[dict[str, Any]],
        expenses: list[dict[str, Any]], transfers: list[dict[str, Any]], payday: int, investment_ratio: Decimal,
        today: date | None = None, latest_broker_snapshots: list[dict[str, Any]] | None = None,
    ) -> DashboardData:
        period = financial_period_for(today or date.today(), payday)
        active = [item for item in accounts if item["is_active"]]
        cash_accounts = [item for item in active if item["account_type"] != AccountType.BROKER.value]
        snapshot_by_account = {item["account_id"]: item for item in latest_snapshots}
        missing = tuple(item["name"] for item in cash_accounts if item["id"] not in snapshot_by_account)
        current_cash = self._current_cash(cash_accounts, snapshot_by_account)
        wealth = current_cash + sum(Decimal(str(item["value_czk"])) for item in (latest_broker_snapshots or []))
        if missing:
            return DashboardData(current_cash, None, None, None, current_cash, wealth, {}, missing, {}, period)

        opening = {item["id"]: Decimal(str(snapshot_by_account[item["id"]]["balance"])) for item in cash_accounts}
        types = {item["id"]: AccountType(item["account_type"]) for item in cash_accounts}
        projection = projection_for_period(opening, self._incomes(incomes), self._expenses(expenses), self._transfers(transfers), period, types)
        best = self._available_total(cash_accounts, projection, snapshot_by_account, "best_case")
        worst = self._available_total(cash_accounts, projection, snapshot_by_account, "worst_case")
        primary = next((item for item in cash_accounts if item["is_primary"]), None)
        invest = None
        if primary:
            raw = projection[primary["id"]].worst_case
            available = cash_available(self._account(primary), raw)
            rate = Decimal(str(snapshot_by_account[primary["id"]]["exchange_rate"]))
            invest = investment_available(to_czk(available, rate), investment_ratio)
        shortages = {
            item["name"]: to_czk(-projection[item["id"]].worst_case, Decimal(str(snapshot_by_account[item["id"]]["exchange_rate"])))
            for item in cash_accounts
            if item["account_type"] != AccountType.OVERDRAFT.value and projection[item["id"]].worst_case < 0
        }
        return DashboardData(current_cash, best, worst, invest, current_cash, wealth, projection, (), shortages, period)

    @staticmethod
    def _account(raw: dict[str, Any]) -> Account:
        return Account(raw["id"], raw["name"], raw["currency"], AccountType(raw["account_type"]), raw["is_primary"], Decimal(str(raw["overdraft_limit"])))

    def _current_cash(self, accounts: list[dict[str, Any]], snapshots: dict[str, dict[str, Any]]) -> Decimal:
        total = Decimal("0")
        for raw in accounts:
            snapshot = snapshots.get(raw["id"])
            if snapshot:
                total += to_czk(cash_available(self._account(raw), Decimal(str(snapshot["balance"]))), Decimal(str(snapshot["exchange_rate"])))
        return total

    def _available_total(self, accounts, projection, snapshots, attribute: str) -> Decimal:
        total = Decimal("0")
        for raw in accounts:
            value = getattr(projection[raw["id"]], attribute)
            available = cash_available(self._account(raw), value)
            total += to_czk(available, Decimal(str(snapshots[raw["id"]]["exchange_rate"])))
        return total

    @staticmethod
    def _incomes(rows: list[dict[str, Any]]) -> list[PlannedIncome]:
        return [PlannedIncome(row["account_id"], Decimal(str(row["amount"])), row["currency"], date.fromisoformat(row["due_date"]), RecurrenceType(row["recurrence"]), row["is_active"], date.fromisoformat(row["effective_from"]), date.fromisoformat(row["effective_to"]) if row["effective_to"] else None) for row in rows]

    @staticmethod
    def _expenses(rows: list[dict[str, Any]]) -> list[PlannedExpense]:
        return [PlannedExpense(row["account_id"], Decimal(str(row["amount"])), row["currency"], date.fromisoformat(row["due_date"]), RecurrenceType(row["recurrence"]), row["is_reserve"], row["is_active"], date.fromisoformat(row["effective_from"]), date.fromisoformat(row["effective_to"]) if row["effective_to"] else None) for row in rows]

    @staticmethod
    def _transfers(rows: list[dict[str, Any]]) -> list[Transfer]:
        return [Transfer(row["source_account_id"], row["target_account_id"], Decimal(str(row["amount"])), row["currency"], date.fromisoformat(row["transfer_date"]), Decimal(str(row["target_amount"])) if row["target_amount"] is not None else None, Decimal(str(row["exchange_rate"])) if row["exchange_rate"] is not None else None) for row in rows]
