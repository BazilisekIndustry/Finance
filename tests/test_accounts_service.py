from datetime import date
from decimal import Decimal

import pytest

from services.accounts import AccountsService


class FakeAccounts:
    def create(self, payload):
        return {"id": "account-1", **payload}


class FakeSnapshots:
    def __init__(self):
        self.payload = None

    def create(self, payload):
        self.payload = payload
        return payload


def test_snapshot_stores_fixed_czk_conversion():
    snapshots = FakeSnapshots()
    service = AccountsService(FakeAccounts(), snapshots)
    service.record_snapshot(
        account={"id": "a", "account_type": "current", "currency": "EUR", "overdraft_limit": "0"},
        snapshot_date=date(2026, 8, 16), balance=Decimal("100"), exchange_rate=Decimal("24.75"),
    )
    assert snapshots.payload["balance_czk"] == "2475.00"


def test_overdraft_draw_cannot_exceed_limit():
    service = AccountsService(FakeAccounts(), FakeSnapshots())
    with pytest.raises(ValueError):
        service.record_snapshot(
            account={"id": "a", "account_type": "overdraft", "currency": "CZK", "overdraft_limit": "30000"},
            snapshot_date=date(2026, 8, 16), balance=Decimal("30001"), exchange_rate=Decimal("1"),
        )
