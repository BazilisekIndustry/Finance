from __future__ import annotations

from typing import Any

from .base import Repository


class SettingsRepository(Repository):
    table = "settings"

    def get_or_create(self) -> dict[str, Any]:
        user_id = self.user_id()
        rows = self.rows(self.client.table(self.table).select("*").eq("user_id", user_id).execute())
        if rows:
            return rows[0]
        response = self.client.table(self.table).insert({"user_id": user_id}).execute()
        return self.rows(response)[0]

    def update(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.client.table(self.table).update(payload).eq("user_id", self.user_id()).execute()
        rows = self.rows(response)
        if not rows:
            raise LookupError("Nastavení nebylo nalezeno.")
        return rows[0]
