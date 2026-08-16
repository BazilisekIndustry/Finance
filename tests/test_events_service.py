from datetime import date
from decimal import Decimal

import pytest

from services.events import EventsService
from services.transfers import TransfersService


class FakeEvents:
    table = "expenses"
    def __init__(self): self.created = []; self.updated = []
    def create(self, payload): self.created.append(payload); return payload
    def update(self, identifier, payload): self.updated.append((identifier, payload)); return payload


def test_recurring_change_creates_a_future_version():
    repository = FakeEvents()
    service = EventsService(None, repository)
    service.replace_recurring_amount({"id": "old", "recurrence": "recurring", "effective_from": "2026-01-01", "account_id": "a", "description": "Nájem", "currency": "CZK", "due_date": "2026-01-15", "is_reserve": False}, Decimal("25000"), date(2026, 9, 13))
    assert repository.updated[0] == ("old", {"effective_to": "2026-09-12"})
    assert repository.created[0]["effective_from"] == "2026-09-13"


def test_cross_currency_transfer_requires_target_amount():
    with pytest.raises(ValueError):
        TransfersService(None).create(source={"id": "a", "currency": "CZK"}, target={"id": "b", "currency": "EUR"}, amount=Decimal("100"), transfer_date=date.today())
