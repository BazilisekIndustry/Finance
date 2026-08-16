from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

import numpy as np

from core.calculations import cash_available
from core.currency import to_czk
from core.models import Account, AccountType
from core.periods import FinancialPeriod, financial_period_for


@dataclass(frozen=True)
class HistoricalPoint:
    period: FinancialPeriod
    cash_czk: Decimal


@dataclass(frozen=True)
class StatisticsData:
    actual: tuple[HistoricalPoint, ...]
    forecast: tuple[tuple[FinancialPeriod, Decimal], ...]
    trend_delta: Decimal | None


class StatisticsService:
    def build(self, *, accounts: list[dict[str, Any]], snapshots: list[dict[str, Any]], payday: int, today: date | None = None) -> StatisticsData:
        active_cash_accounts = [item for item in accounts if item["is_active"] and item["account_type"] != "broker"]
        if not active_cash_accounts:
            return StatisticsData((), (), None)
        periods = self._recent_periods(today or date.today(), payday, 12)
        actual = self._actual_points(periods, active_cash_accounts, snapshots, payday)
        trend_delta = actual[-1].cash_czk - actual[-2].cash_czk if len(actual) >= 2 else None
        forecast = self._linear_forecast(actual, payday, 6)
        return StatisticsData(tuple(actual), tuple(forecast), trend_delta)

    @staticmethod
    def _recent_periods(today: date, payday: int, count: int) -> list[FinancialPeriod]:
        result = []
        current = financial_period_for(today, payday)
        for _ in range(count):
            result.append(current)
            current = financial_period_for(date.fromordinal(current.start.toordinal() - 1), payday)
        return list(reversed(result))

    def _actual_points(self, periods, accounts, snapshots, payday) -> list[HistoricalPoint]:
        points = []
        for period in periods:
            latest = {}
            for snapshot in snapshots:
                snapshot_date = date.fromisoformat(snapshot["snapshot_date"])
                if period.contains(snapshot_date):
                    existing = latest.get(snapshot["account_id"])
                    if existing is None or snapshot_date > date.fromisoformat(existing["snapshot_date"]):
                        latest[snapshot["account_id"]] = snapshot
            if any(account["id"] not in latest for account in accounts):
                continue
            total = Decimal("0")
            for raw in accounts:
                snapshot = latest[raw["id"]]
                account = Account(raw["id"], raw["name"], raw["currency"], AccountType(raw["account_type"]), raw["is_primary"], Decimal(str(raw["overdraft_limit"])))
                total += to_czk(cash_available(account, Decimal(str(snapshot["balance"]))), Decimal(str(snapshot["exchange_rate"])))
            points.append(HistoricalPoint(period, total))
        return points

    @staticmethod
    def _linear_forecast(actual: list[HistoricalPoint], payday: int, count: int) -> list[tuple[FinancialPeriod, Decimal]]:
        if len(actual) < 6:
            return []
        source = actual[-6:]
        x = np.arange(len(source), dtype=float)
        y = np.array([float(point.cash_czk) for point in source], dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        period = financial_period_for(date.fromordinal(source[-1].period.end.toordinal() + 1), payday)
        result = []
        for index in range(count):
            result.append((period, Decimal(str(round(slope * (len(source) + index) + intercept, 2)))))
            period = financial_period_for(date.fromordinal(period.end.toordinal() + 1), payday)
        return result
