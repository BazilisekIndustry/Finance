from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from .models import Account, AccountProjection, AccountType, Money, PlannedExpense, PlannedIncome, Transfer
from .periods import FinancialPeriod


def overdraft_available(limit: Money, drawn: Money) -> Money:
    if limit < 0 or drawn < 0:
        raise ValueError("Limit i čerpání kontokorentu musí být nezáporné.")
    return max(Decimal("0"), limit - drawn)


def cash_available(account: Account, actual_balance: Money) -> Money:
    """Cash available from one account. Overdraft balance stores current draw, not a negative balance."""
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
) -> dict[str, AccountProjection]:
    best = dict(opening_balances)
    worst = dict(opening_balances)
    for income in incomes:
        if _event_applies(income.active, income.recurrence.value, income.due_date, period, income.effective_from, income.effective_to):
            _require_account(best, income.account_id)
            _apply_delta(best, income.account_id, income.amount, account_types)
            _apply_delta(worst, income.account_id, income.amount, account_types)
    for expense in expenses:
        if _event_applies(expense.active, expense.recurrence.value, expense.due_date, period, expense.effective_from, expense.effective_to):
            _require_account(best, expense.account_id)
            if not expense.is_reserve:
                _apply_delta(best, expense.account_id, -expense.amount, account_types)
            _apply_delta(worst, expense.account_id, -expense.amount, account_types)
    for transfer in transfers:
        if period.contains(transfer.transfer_date):
            _require_account(best, transfer.source_account_id)
            _require_account(best, transfer.target_account_id)
            credit = transfer.target_amount if transfer.target_amount is not None else transfer.amount
            for scenario in (best, worst):
                _apply_delta(scenario, transfer.source_account_id, -transfer.amount, account_types)
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
    """Apply cash movement; overdraft balances represent draw, so their direction is reversed."""
    is_overdraft = account_types is not None and account_types.get(account_id) == AccountType.OVERDRAFT
    if is_overdraft:
        balances[account_id] = max(Decimal("0"), balances[account_id] - cash_delta)
    else:
        balances[account_id] += cash_delta


def _event_applies(active: bool, recurrence: str, due_date, period: FinancialPeriod, effective_from=None, effective_to=None) -> bool:
    """A regular event occurs once in every financial period from its first due date."""
    if not active:
        return False
    start = effective_from or due_date
    if recurrence == "one_off":
        return period.contains(due_date)
    if recurrence == "recurring":
        return period.end >= start and (effective_to is None or period.start <= effective_to)
    raise ValueError(f"Neznámý typ opakování: {recurrence}")
