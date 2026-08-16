from __future__ import annotations

from datetime import date
from typing import Any

from .base import Repository


class BalanceSnapshotsRepository(Repository):
    table = "balance_snapshots"

    def list_for_account(self, account_id: str) -> list[dict[str, Any]]:
        return self.rows(
            self.client.table(self.table).select("*").eq("account_id", account_id).eq("user_id", self.user_id()).order("snapshot_date", desc=True).execute()
        )

    def latest_by_account(self) -> list[dict[str, Any]]:
        # PostgreSQL grouping is deliberately avoided here; latest snapshot selection stays explicit and testable.
        snapshots = self.rows(self.client.table(self.table).select("*").eq("user_id", self.user_id()).order("snapshot_date", desc=True).execute())
        latest: dict[str, dict[str, Any]] = {}
        for snapshot in snapshots:
            latest.setdefault(snapshot["account_id"], snapshot)
        return list(latest.values())

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        required = {"account_id", "snapshot_date", "balance", "currency", "exchange_rate", "balance_czk"}
        missing = required - payload.keys()
        if missing:
            raise ValueError(f"Snapshotu chybí povinná pole: {', '.join(sorted(missing))}")
        return self.rows(self.client.table(self.table).insert(self.own(payload)).execute())[0]

    def history_between(self, start: date, end: date) -> list[dict[str, Any]]:
        return self.rows(
            self.client.table(self.table).select("*").eq("user_id", self.user_id()).gte("snapshot_date", start.isoformat()).lte("snapshot_date", end.isoformat()).execute()
        )

