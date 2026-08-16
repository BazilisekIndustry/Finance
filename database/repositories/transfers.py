from __future__ import annotations

from datetime import date
from typing import Any

from .base import Repository


class TransfersRepository(Repository):
    table = "transfers"

    def list_between(self, start: date, end: date) -> list[dict[str, Any]]:
        return self.rows(
            self.client.table(self.table).select("*").eq("user_id", self.user_id()).gte("transfer_date", start.isoformat()).lte("transfer_date", end.isoformat()).order("transfer_date").execute()
        )

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("source_account_id") == payload.get("target_account_id"):
            raise ValueError("Zdrojový a cílový účet převodu musí být rozdílné.")
        return self.rows(self.client.table(self.table).insert(self.own(payload)).execute())[0]

