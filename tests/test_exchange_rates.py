from datetime import date
from decimal import Decimal

from services.exchange_rates import ExchangeRatesService


class FakeProvider:
    name = "test"
    def rates_to_czk(self, rate_date):
        return {"CZK": Decimal("1"), "EUR": Decimal("25"), "USD": Decimal("23")}


class FakeRepository:
    def __init__(self): self.rows = []
    def create(self, payload): self.rows.append(payload); return payload


def test_provider_is_separate_and_rates_are_saved():
    repository = FakeRepository()
    stored = ExchangeRatesService(repository, FakeProvider()).fetch_and_store(date(2026, 8, 16))
    assert len(stored) == 3
    assert repository.rows[1]["rate_to_czk"] == "25"
