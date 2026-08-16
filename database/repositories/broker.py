from __future__ import annotations

from datetime import date
from typing import Any

from .base import Repository


class BrokerSnapshotsRepository(Repository):
    table = "broker_snapshots"

    def list_for_account(self, account_id: str) -> list[dict[str, Any]]:
        return self.rows(self.client.table(self.table).select("*").eq("user_id", self.user_id()).eq("account_id", account_id).order("snapshot_date").execute())

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.rows(self.client.table(self.table).insert(self.own(payload)).execute())[0]

    def latest_by_account(self) -> list[dict[str, Any]]:
        snapshots = self.rows(self.client.table(self.table).select("*").eq("user_id", self.user_id()).order("snapshot_date", desc=True).execute())
        latest: dict[str, dict[str, Any]] = {}
        for snapshot in snapshots:
            latest.setdefault(snapshot["account_id"], snapshot)
        return list(latest.values())

    def history_between(self, start: date, end: date) -> list[dict[str, Any]]:
        return self.rows(self.client.table(self.table).select("*").eq("user_id", self.user_id()).gte("snapshot_date", start.isoformat()).lte("snapshot_date", end.isoformat()).execute())
