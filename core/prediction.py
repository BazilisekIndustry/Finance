from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from .calculations import projection_for_period
from .models import AccountProjection, AccountType, Money, PlannedExpense, PlannedIncome, Transfer
from .periods import FinancialPeriod, period_after


def project_periods(
    initial_balances: dict[str, Money],
    start_period: FinancialPeriod,
    count: int,
    payday: int,
    incomes: Iterable[PlannedIncome],
    expenses: Iterable[PlannedExpense],
    transfers: Iterable[Transfer],
    actual_snapshots: dict[date, dict[str, Money]] | None = None,
    account_types: dict[str, AccountType] | None = None,
) -> list[tuple[FinancialPeriod, dict[str, AccountProjection]]]:
    """Projects consecutively; a snapshot dated in a period replaces the opening state for that period."""
    if count < 1:
        raise ValueError("Počet období musí být alespoň 1.")
    snapshot_map = actual_snapshots or {}
    current_opening = dict(initial_balances)
    period = start_period
    result = []
    income_list, expense_list, transfer_list = list(incomes), list(expenses), list(transfers)
    for _ in range(count):
        snapshots_in_period = [(d, b) for d, b in snapshot_map.items() if period.contains(d)]
        if snapshots_in_period:
            _, current_opening = max(snapshots_in_period, key=lambda item: item[0])
            current_opening = dict(current_opening)
        projection = projection_for_period(current_opening, income_list, expense_list, transfer_list, period, account_types)
        result.append((period, projection))
        current_opening = {account_id: value.worst_case for account_id, value in projection.items()}
        period = period_after(period, payday)
    return result
