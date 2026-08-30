from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from core.currency import to_czk
from core.models import AccountType
from core.validation import non_negative_decimal, positive_decimal, validate_currency
from database.repositories import AccountsRepository, BalanceSnapshotsRepository


class AccountsService:
    def __init__(self, accounts: AccountsRepository, snapshots: BalanceSnapshotsRepository):
        self.accounts = accounts
        self.snapshots = snapshots

    def create_account(
        self, *, name: str, institution: str | None, account_type: str, currency: str,
        is_primary: bool = False, overdraft_limit: Decimal = Decimal("0"),
    ) -> dict[str, Any]:
        if not name.strip():
            raise ValueError("Název účtu je povinný.")
        try:
            type_value = AccountType(account_type)
        except ValueError as exc:
            raise ValueError("Neplatný typ účtu.") from exc
        limit = non_negative_decimal(overdraft_limit, "Limit kontokorentu")
        if type_value != AccountType.OVERDRAFT and limit != 0:
            raise ValueError("Limit lze zadat pouze pro kontokorent.")
        return self.accounts.create({
            "name": name.strip(), "institution": institution.strip() if institution else None,
            "account_type": type_value.value, "currency": validate_currency(currency),
            "is_primary": is_primary, "overdraft_limit": str(limit),
        })

    def record_snapshot(
        self, *, account: dict[str, Any], snapshot_date: date, balance: Decimal,
        exchange_rate: Decimal,
    ) -> dict[str, Any]:
        """Append an actual balance. Existing snapshots are never updated."""
        non_negative_decimal(balance, "Zůstatek")
        positive_decimal(exchange_rate, "Kurz")
        account_type = AccountType(account["account_type"])
        if account_type == AccountType.OVERDRAFT:
            limit = Decimal(str(account["overdraft_limit"]))
            if balance > limit:
                raise ValueError("Dostupný kontokorent nesmí překročit jeho limit.")
        currency = validate_currency(account["currency"])
        return self.snapshots.create({
            "account_id": account["id"], "snapshot_date": snapshot_date.isoformat(),
            # `balance` remains the common prediction value. For an overdraft it is
            # explicitly the bank-facing available amount, never the drawn amount.
            "balance": str(balance), "overdraft_available": str(balance) if account_type == AccountType.OVERDRAFT else None,
            "currency": currency, "exchange_rate": str(exchange_rate),
            "balance_czk": str(to_czk(balance, exchange_rate)),
        })

    def update_snapshot(
        self, *, snapshot: dict[str, Any], account: dict[str, Any], snapshot_date: date, balance: Decimal, exchange_rate: Decimal,
    ) -> dict[str, Any]:
        """Correct a historical actual balance without changing its account."""
        if snapshot["account_id"] != account["id"]:
            raise ValueError("Účet snapshotu nelze změnit.")
        non_negative_decimal(balance, "Zůstatek")
        positive_decimal(exchange_rate, "Kurz")
        account_type = AccountType(account["account_type"])
        if account_type == AccountType.OVERDRAFT and balance > Decimal(str(account["overdraft_limit"])):
            raise ValueError("Dostupný kontokorent nesmí překročit jeho limit.")
        payload = {
            "snapshot_date": snapshot_date.isoformat(), "balance": str(balance),
            "overdraft_available": str(balance) if account_type == AccountType.OVERDRAFT else None,
            "exchange_rate": str(exchange_rate), "balance_czk": str(to_czk(balance, exchange_rate)),
        }
        return self.snapshots.update(snapshot["id"], payload)

    def delete_snapshot(self, snapshot_id: str) -> None:
        self.snapshots.delete(snapshot_id)

    def update_account(self, account: dict[str, Any], *, name: str, institution: str | None, is_primary: bool, overdraft_limit: Decimal) -> dict[str, Any]:
        if not name.strip():
            raise ValueError("Název účtu je povinný.")
        limit = non_negative_decimal(overdraft_limit, "Limit kontokorentu")
        if account["account_type"] != AccountType.OVERDRAFT.value and limit != 0:
            raise ValueError("Limit lze zadat pouze pro kontokorent.")
        return self.accounts.update(account["id"], {
            "name": name.strip(), "institution": institution.strip() if institution else None,
            "is_primary": is_primary, "overdraft_limit": str(limit),
        })

    def deactivate_account(self, account_id: str) -> dict[str, Any]:
        return self.accounts.deactivate(account_id)
