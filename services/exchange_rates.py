from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import urlopen

from core.validation import validate_currency
from database.repositories import ExchangeRatesRepository


class ExchangeRateProvider(Protocol):
    name: str
    def rates_to_czk(self, rate_date: date) -> dict[str, Decimal]: ...


@dataclass(frozen=True)
class CnbExchangeRateProvider:
    """Official ČNB daily fixing source, kept outside financial calculation logic."""
    name: str = "cnb"
    endpoint: str = "https://www.cnb.cz/cs/financni-trhy/devizovy-trh/kurzy-devizoveho-trhu/kurzy-devizoveho-trhu/denni_kurz.txt"

    def rates_to_czk(self, rate_date: date) -> dict[str, Decimal]:
        query = urlencode({"date": rate_date.strftime("%d.%m.%Y")})
        try:
            with urlopen(f"{self.endpoint}?{query}", timeout=10) as response:  # nosec B310: fixed HTTPS endpoint
                content = response.read().decode("utf-8-sig")
        except OSError as exc:
            raise RuntimeError("Kurzovní lístek ČNB se nepodařilo načíst.") from exc
        rates = {"CZK": Decimal("1")}
        for line in content.splitlines()[2:]:
            cells = line.split("|")
            if len(cells) != 5:
                continue
            _, _, quantity, code, rate = cells
            if code in {"EUR", "USD"}:
                rates[code] = Decimal(rate.replace(",", ".")) / Decimal(quantity)
        missing = {"EUR", "USD"} - rates.keys()
        if missing:
            raise RuntimeError("Kurzovní lístek ČNB neobsahuje: " + ", ".join(sorted(missing)))
        return rates


class ExchangeRatesService:
    def __init__(self, repository: ExchangeRatesRepository, provider: ExchangeRateProvider):
        self.repository = repository
        self.provider = provider

    def fetch_and_store(self, rate_date: date) -> list[dict]:
        rates = self.provider.rates_to_czk(rate_date)
        return [self.repository.create({"rate_date": rate_date.isoformat(), "currency": currency, "rate_to_czk": str(rate), "source": self.provider.name}) for currency, rate in rates.items()]

    def latest(self, currency: str, before: date):
        return self.repository.latest(validate_currency(currency), before)
