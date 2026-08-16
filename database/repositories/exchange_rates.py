from __future__ import annotations

from datetime import date
from typing import Any

from .base import Repository


class ExchangeRatesRepository(Repository):
    table = "exchange_rates"

    def latest(self, currency: str, before: date) -> dict[str, Any] | None:
        rows = self.rows(self.client.table(self.table).select("*").eq("user_id", self.user_id()).eq("currency", currency).lte("rate_date", before.isoformat()).order("rate_date", desc=True).limit(1).execute())
        return rows[0] if rows else None

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.rows(self.client.table(self.table).insert(self.own(payload)).execute())[0]

