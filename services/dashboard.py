from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from core.calculations import cash_available, investment_available, projection_for_period
from core.currency import to_czk
from core.models import Account, AccountProjection, AccountType, ExpenseKind, PlannedExpense, PlannedIncome, RecurrenceType, Transfer
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
    broker_value_czk: Decimal = Decimal("0")
    plan_variance_czk: Decimal | None = None
    previous_period_delta_czk: Decimal | None = None
    forecast_trend_czk: Decimal | None = None
    snapshot_dates: dict[str, date] | None = None


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
        as_of = today or date.today()
        period = financial_period_for(as_of, payday)
        snapshot_dates = {account_id: date.fromisoformat(item["snapshot_date"]) for account_id, item in snapshots.items()}
        projections = project_periods(opening, period, count, payday, self._incomes(incomes), self._expenses(expenses), self._transfers(transfers), account_types=types, snapshot_dates=snapshot_dates)
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
        snapshot_history: list[dict[str, Any]] | None = None,
    ) -> DashboardData:
        as_of = today or date.today()
        period = financial_period_for(as_of, payday)
        active = [item for item in accounts if item["is_active"]]
        cash_accounts = [item for item in active if item["account_type"] != AccountType.BROKER.value]
        snapshot_by_account = {item["account_id"]: item for item in latest_snapshots}
        missing = tuple(item["name"] for item in cash_accounts if item["id"] not in snapshot_by_account)
        current_cash = self._own_cash(cash_accounts, snapshot_by_account)
        broker_value = sum(Decimal(str(item["value_czk"])) for item in (latest_broker_snapshots or []))
        wealth = self._total_wealth(cash_accounts, snapshot_by_account, latest_broker_snapshots or [])
        if missing:
            return DashboardData(current_cash, None, None, None, current_cash, wealth, {}, missing, {}, period, broker_value=broker_value)

        opening = {item["id"]: Decimal(str(snapshot_by_account[item["id"]]["balance"])) for item in cash_accounts}
        types = {item["id"]: AccountType(item["account_type"]) for item in cash_accounts}
        snapshot_dates = {account_id: date.fromisoformat(item["snapshot_date"]) for account_id, item in snapshot_by_account.items()}
        projection = projection_for_period(opening, self._incomes(incomes), self._expenses(expenses), self._transfers(transfers), period, types, snapshot_dates)
        realized_projection = projection_for_period(
            opening, self._incomes(incomes), self._expenses(expenses), self._transfers(transfers),
            period, types, snapshot_dates, through_date=as_of,
        )
        best = self._available_total(cash_accounts, projection, snapshot_by_account, "best_case")
        worst = self._available_total(cash_accounts, projection, snapshot_by_account, "worst_case")
        # Purchase power is the planned baseline as of today; contingent reserves
        # deliberately stay out of it just as they stay out of plan variance.
        purchase_power = self._available_total(cash_accounts, realized_projection, snapshot_by_account, "best_case")
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
        history = snapshot_history or []
        variance = self._plan_variance(cash_accounts, snapshot_by_account, history, period, types, incomes, expenses, transfers)
        previous_delta = self._previous_period_delta(cash_accounts, history, period)
        forecast = self.cash_flow_forecast(accounts=accounts, latest_snapshots=latest_snapshots, incomes=incomes, expenses=expenses, transfers=transfers, payday=payday, count=2, today=as_of)
        trend = forecast[1].worst_case_czk - forecast[0].worst_case_czk if len(forecast) == 2 else None
        return DashboardData(current_cash, best, worst, invest, purchase_power, wealth, projection, (), shortages, period, broker_value, variance, previous_delta, trend, snapshot_dates)

    @staticmethod
    def _account(raw: dict[str, Any]) -> Account:
        return Account(raw["id"], raw["name"], raw["currency"], AccountType(raw["account_type"]), raw["is_primary"], Decimal(str(raw["overdraft_limit"])))

    def _own_cash(self, accounts: list[dict[str, Any]], snapshots: dict[str, dict[str, Any]]) -> Decimal:
        """Actual own balances only; available overdraft is credit, not cash."""
        total = Decimal("0")
        for raw in accounts:
            snapshot = snapshots.get(raw["id"])
            if snapshot and raw["account_type"] != AccountType.OVERDRAFT.value:
                total += to_czk(max(Decimal("0"), Decimal(str(snapshot["balance"]))), Decimal(str(snapshot["exchange_rate"])))
        return total

    def _total_wealth(self, accounts: list[dict[str, Any]], snapshots: dict[str, dict[str, Any]], broker_snapshots: list[dict[str, Any]]) -> Decimal:
        wealth = self._own_cash(accounts, snapshots)
        wealth += sum(Decimal(str(item["value_czk"])) for item in broker_snapshots)
        for raw in accounts:
            if raw["account_type"] != AccountType.OVERDRAFT.value or raw["id"] not in snapshots:
                continue
            available = Decimal(str(snapshots[raw["id"]]["balance"]))
            used = max(Decimal("0"), Decimal(str(raw["overdraft_limit"])) - available)
            wealth -= to_czk(used, Decimal(str(snapshots[raw["id"]]["exchange_rate"])))
        return wealth

    def _available_total(self, accounts, projection, snapshots, attribute: str) -> Decimal:
        total = Decimal("0")
        for raw in accounts:
            value = getattr(projection[raw["id"]], attribute)
            available = cash_available(self._account(raw), value)
            total += to_czk(available, Decimal(str(snapshots[raw["id"]]["exchange_rate"])))
        return total

    def _plan_variance(self, accounts, latest, history, period, types, incomes, expenses, transfers) -> Decimal | None:
        """Compare every latest actual balance with the baseline from its prior actual point."""
        if not history:
            return None
        total = Decimal("0")
        comparable = False
        for raw in accounts:
            current = latest[raw["id"]]
            current_date = date.fromisoformat(current["snapshot_date"])
            previous = [item for item in history if item["account_id"] == raw["id"] and date.fromisoformat(item["snapshot_date"]) < current_date]
            if not previous:
                continue
            opening_snapshot = max(previous, key=lambda item: (item["snapshot_date"], item.get("created_at", "")))
            opening = {item["id"]: Decimal(str(latest[item["id"]]["balance"])) for item in accounts}
            opening[raw["id"]] = Decimal(str(opening_snapshot["balance"]))
            boundaries = {item["id"]: date.fromisoformat(latest[item["id"]]["snapshot_date"]) for item in accounts}
            boundaries[raw["id"]] = date.fromisoformat(opening_snapshot["snapshot_date"])
            planned = projection_for_period(opening, self._incomes(incomes), self._expenses(expenses), self._transfers(transfers), period, types, boundaries, through_date=current_date)
            total += Decimal(str(current["balance"])) - planned[raw["id"]].worst_case
            comparable = True
        return total if comparable else None

    def _previous_period_delta(self, accounts, history, current_period: FinancialPeriod) -> Decimal | None:
        if not history:
            return None
        from core.periods import period_after
        previous_end = current_period.start.fromordinal(current_period.start.toordinal() - 1)
        previous = financial_period_for(previous_end, current_period.start.day)
        before = financial_period_for(previous.start.fromordinal(previous.start.toordinal() - 1), current_period.start.day)
        def total_for(period):
            latest = {}
            for item in history:
                item_date = date.fromisoformat(item["snapshot_date"])
                if period.contains(item_date):
                    existing = latest.get(item["account_id"])
                    if existing is None or (item["snapshot_date"], item.get("created_at", "")) > (existing["snapshot_date"], existing.get("created_at", "")):
                        latest[item["account_id"]] = item
            # An aggregate remains meaningful when a newly created account is absent.
            return sum((to_czk(max(Decimal("0"), Decimal(str(item["balance"]))), Decimal(str(item["exchange_rate"]))) for raw in accounts if raw["account_type"] != "overdraft" and (item := latest.get(raw["id"]))), Decimal("0"))
        previous_total, before_total = total_for(previous), total_for(before)
        return previous_total - before_total if previous_total or before_total else None

    @staticmethod
    def _incomes(rows: list[dict[str, Any]]) -> list[PlannedIncome]:
        return [PlannedIncome(row["account_id"], Decimal(str(row["amount"])), row["currency"], date.fromisoformat(row["due_date"]), RecurrenceType(row["recurrence"]), row["is_active"], date.fromisoformat(row["effective_from"]), date.fromisoformat(row["effective_to"]) if row["effective_to"] else None) for row in rows]

    @staticmethod
    def _expenses(rows: list[dict[str, Any]]) -> list[PlannedExpense]:
        return [PlannedExpense(row["account_id"], Decimal(str(row["amount"])), row["currency"], date.fromisoformat(row["due_date"]), RecurrenceType(row["recurrence"]), row["is_reserve"], row["is_active"], date.fromisoformat(row["effective_from"]), date.fromisoformat(row["effective_to"]) if row["effective_to"] else None, ExpenseKind(row.get("expense_kind", "fixed"))) for row in rows]

    @staticmethod
    def _transfers(rows: list[dict[str, Any]]) -> list[Transfer]:
        return [Transfer(row["source_account_id"], row["target_account_id"], Decimal(str(row["amount"])), row["currency"], date.fromisoformat(row["transfer_date"]), Decimal(str(row["target_amount"])) if row["target_amount"] is not None else None, Decimal(str(row["exchange_rate"])) if row["exchange_rate"] is not None else None) for row in rows]
