from __future__ import annotations

from typing import Any

from .base import Repository


class AccountsRepository(Repository):
    table = "accounts"

    def list(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        query = self.client.table(self.table).select("*").eq("user_id", self.user_id()).order("name")
        if not include_inactive:
            query = query.eq("is_active", True)
        return self.rows(query.execute())

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.rows(self.client.table(self.table).insert(self.own(payload)).execute())[0]

    def update(self, account_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.client.table(self.table).update(payload).eq("id", account_id).eq("user_id", self.user_id()).execute()
        return self._one(response, "Účet nebyl nalezen nebo k němu nemáte přístup.")

    def deactivate(self, account_id: str) -> dict[str, Any]:
        return self.update(account_id, {"is_active": False, "is_primary": False})

    @staticmethod
    def _one(response: Any, error: str) -> dict[str, Any]:
        rows = list(response.data or [])
        if not rows:
            raise LookupError(error)
        return rows[0]

