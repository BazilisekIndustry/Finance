from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional


Money = Decimal


class AccountType(str, Enum):
    MAIN_CURRENT = "main_current"
    CURRENT = "current"
    SAVINGS = "savings"
    OVERDRAFT = "overdraft"
    BROKER = "broker"


class RecurrenceType(str, Enum):
    ONE_OFF = "one_off"
    RECURRING = "recurring"


@dataclass(frozen=True)
class Account:
    id: str
    name: str
    currency: str
    account_type: AccountType
    is_primary: bool = False
    overdraft_limit: Money = Decimal("0")


@dataclass(frozen=True)
class BalanceSnapshot:
    account_id: str
    snapshot_date: date
    balance: Money
    currency: str
    exchange_rate: Money
    overdraft_available: Optional[Money] = None


@dataclass(frozen=True)
class PlannedIncome:
    account_id: str
    amount: Money
    currency: str
    due_date: date
    recurrence: RecurrenceType
    active: bool = True
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


@dataclass(frozen=True)
class PlannedExpense:
    account_id: str
    amount: Money
    currency: str
    due_date: date
    recurrence: RecurrenceType
    is_reserve: bool = False
    active: bool = True
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


@dataclass(frozen=True)
class Transfer:
    source_account_id: str
    target_account_id: str
    amount: Money
    currency: str
    transfer_date: date
    target_amount: Optional[Money] = None
    exchange_rate: Optional[Money] = None


@dataclass(frozen=True)
class AccountProjection:
    best_case: Money
    worst_case: Money
