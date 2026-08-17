from __future__ import annotations

from collections.abc import Iterable
from calendar import monthrange
from datetime import date
from decimal import Decimal

from .models import Account, AccountProjection, AccountType, Money, PlannedExpense, PlannedIncome, Transfer
from .periods import FinancialPeriod


def overdraft_used(limit: Money, available: Money) -> Money:
    """Return the amount drawn from an overdraft shown by the bank as available."""
    if limit < 0 or available < 0 or available > limit:
        raise ValueError("Limit i dostupný kontokorent musí být v rozsahu od nuly do limitu.")
    return max(Decimal("0"), limit - available)


def overdraft_available(limit: Money, available: Money) -> Money:
    """Validate and return the bank-facing available overdraft amount."""
    overdraft_used(limit, available)
    return available


def cash_available(account: Account, actual_balance: Money) -> Money:
    """Cash available from one account; overdrafts store the available amount."""
    if account.account_type == AccountType.OVERDRAFT:
        return overdraft_available(account.overdraft_limit, actual_balance)
    return max(Decimal("0"), actual_balance)


def projection_for_period(
    opening_balances: dict[str, Money],
    incomes: Iterable[PlannedIncome],
    expenses: Iterable[PlannedExpense],
    transfers: Iterable[Transfer],
    period: FinancialPeriod,
    account_types: dict[str, AccountType] | None = None,
    snapshot_dates: dict[str, date] | None = None,
    through_date: date | None = None,
) -> dict[str, AccountProjection]:
    best = dict(opening_balances)
    worst = dict(opening_balances)
    for income in incomes:
        occurrence = _event_occurrence(income.active, income.recurrence.value, income.due_date, period, income.effective_from, income.effective_to)
        if occurrence and _within_horizon(occurrence, through_date) and _after_snapshot(occurrence, income.account_id, snapshot_dates):
            _require_account(best, income.account_id)
            _apply_delta(best, income.account_id, income.amount, account_types)
            _apply_delta(worst, income.account_id, income.amount, account_types)
    for expense in expenses:
        occurrence = _event_occurrence(expense.active, expense.recurrence.value, expense.due_date, period, expense.effective_from, expense.effective_to)
        if occurrence and _within_horizon(occurrence, through_date) and _after_snapshot(occurrence, expense.account_id, snapshot_dates):
            _require_account(best, expense.account_id)
            if not expense.is_reserve:
                _apply_delta(best, expense.account_id, -expense.amount, account_types)
            _apply_delta(worst, expense.account_id, -expense.amount, account_types)
    for transfer in transfers:
        if period.contains(transfer.transfer_date) and _within_horizon(transfer.transfer_date, through_date):
            credit = transfer.target_amount if transfer.target_amount is not None else transfer.amount
            for scenario in (best, worst):
                # Each leg has its own actual-state boundary. This prevents a transfer
                # already reflected by either account's snapshot from being replayed.
                if _after_snapshot(transfer.transfer_date, transfer.source_account_id, snapshot_dates):
                    _require_account(scenario, transfer.source_account_id)
                    _apply_delta(scenario, transfer.source_account_id, -transfer.amount, account_types)
                if _after_snapshot(transfer.transfer_date, transfer.target_account_id, snapshot_dates):
                    _require_account(scenario, transfer.target_account_id)
                    _apply_delta(scenario, transfer.target_account_id, credit, account_types)
    return {account_id: AccountProjection(best[account_id], worst[account_id]) for account_id in best}


def investment_available(worst_case_main_account: Money, ratio: Money) -> Money:
    if not Decimal("0") <= ratio <= Decimal("1"):
        raise ValueError("Investiční poměr musí být mezi 0 a 1.")
    return max(Decimal("0"), worst_case_main_account * ratio)


def _require_account(balances: dict[str, Money], account_id: str) -> None:
    if account_id not in balances:
        raise ValueError(f"Událost odkazuje na neznámý účet: {account_id}")


def _apply_delta(balances: dict[str, Money], account_id: str, cash_delta: Money, account_types: dict[str, AccountType] | None) -> None:
    """Apply a cash movement; overdraft balances represent available credit."""
    is_overdraft = account_types is not None and account_types.get(account_id) == AccountType.OVERDRAFT
    if is_overdraft:
        balances[account_id] = max(Decimal("0"), balances[account_id] + cash_delta)
    else:
        balances[account_id] += cash_delta


def _after_snapshot(occurrence: date, account_id: str, snapshot_dates: dict[str, date] | None) -> bool:
    return snapshot_dates is None or account_id not in snapshot_dates or occurrence > snapshot_dates[account_id]


def _within_horizon(occurrence: date, through_date: date | None) -> bool:
    return through_date is None or occurrence <= through_date


def _event_occurrence(active: bool, recurrence: str, due_date: date, period: FinancialPeriod, effective_from=None, effective_to=None) -> date | None:
    """Return the event date in this financial period, if the event occurs there."""
    if not active:
        return None
    start = effective_from or due_date
    if recurrence == "one_off":
        return due_date if period.contains(due_date) else None
    if recurrence == "recurring":
        if period.end < start or (effective_to is not None and period.start > effective_to):
            return None
        for year, month in ((period.start.year, period.start.month), (period.end.year, period.end.month)):
            occurrence = date(year, month, min(due_date.day, monthrange(year, month)[1]))
            if period.contains(occurrence) and occurrence >= start and (effective_to is None or occurrence <= effective_to):
                return occurrence
        return None
    raise ValueError(f"Neznámý typ opakování: {recurrence}")
