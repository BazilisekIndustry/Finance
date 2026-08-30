from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from core.models import ExpenseKind, RecurrenceType
from core.validation import positive_decimal, validate_currency
from database.repositories import AccountsRepository, ExpensesRepository, IncomesRepository


class EventsService:
    def __init__(self, accounts: AccountsRepository, repository: IncomesRepository | ExpensesRepository):
        self.accounts = accounts
        self.repository = repository

    def create(
        self, *, description: str, amount: Decimal, currency: str, account: dict[str, Any], due_date: date,
        recurrence: str, is_reserve: bool = False, expense_kind: str = "fixed",
    ) -> dict[str, Any]:
        if not description.strip():
            raise ValueError("Popis je povinný.")
        positive_decimal(amount, "Částka")
        recurrence_type = RecurrenceType(recurrence)
        if self.repository.table == "expenses" and ExpenseKind(expense_kind) == ExpenseKind.CONTINUOUS and recurrence_type != RecurrenceType.RECURRING:
            raise ValueError("Průběžný výdaj musí být pravidelný, protože představuje rozpočet pro finanční období.")
        event_currency = validate_currency(currency)
        if event_currency != account["currency"]:
            raise ValueError("Měna příjmu či výdaje musí odpovídat měně cílového účtu.")
        payload = {
            "account_id": account["id"], "description": description.strip(), "amount": str(amount),
            "currency": event_currency, "due_date": due_date.isoformat(), "recurrence": recurrence_type.value,
            "is_active": True, "effective_from": due_date.isoformat(), "effective_to": None,
        }
        if self.repository.table == "expenses":
            payload["is_reserve"] = is_reserve
            payload["expense_kind"] = ExpenseKind(expense_kind).value
        return self.repository.create(payload)

    def replace_recurring_amount(self, event: dict[str, Any], new_amount: Decimal, effective_from: date) -> dict[str, Any]:
        """Version a recurring item rather than changing the definition used in past periods."""
        if event["recurrence"] != RecurrenceType.RECURRING.value:
            raise ValueError("Verzovat lze pouze pravidelnou položku.")
        positive_decimal(new_amount, "Nová částka")
        current_from = date.fromisoformat(event["effective_from"])
        if effective_from <= current_from:
            raise ValueError("Nová verze musí začít až po začátku původní položky.")
        self.repository.update(event["id"], {"effective_to": (effective_from - timedelta(days=1)).isoformat()})
        clone = {key: event[key] for key in ("account_id", "description", "currency", "due_date", "recurrence")}
        clone.update({"amount": str(new_amount), "is_active": True, "effective_from": effective_from.isoformat(), "effective_to": None})
        if self.repository.table == "expenses":
            clone["is_reserve"] = event["is_reserve"]
            clone["expense_kind"] = event.get("expense_kind", "fixed")
        return self.repository.create(clone)
