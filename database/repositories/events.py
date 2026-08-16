from __future__ import annotations

from typing import Any

from .base import Repository


class _EventsRepository(Repository):
    table: str

    def list(self, active_only: bool = False) -> list[dict[str, Any]]:
        query = self.client.table(self.table).select("*").eq("user_id", self.user_id()).order("due_date")
        if active_only:
            query = query.eq("is_active", True)
        return self.rows(query.execute())

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.rows(self.client.table(self.table).insert(self.own(payload)).execute())[0]

    def update(self, event_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.client.table(self.table).update(payload).eq("id", event_id).eq("user_id", self.user_id()).execute()
        rows = self.rows(response)
        if not rows:
            raise LookupError("Položka nebyla nalezena nebo k ní nemáte přístup.")
        return rows[0]

    def deactivate(self, event_id: str) -> dict[str, Any]:
        return self.update(event_id, {"is_active": False})


class IncomesRepository(_EventsRepository):
    table = "incomes"


class ExpensesRepository(_EventsRepository):
    table = "expenses"

