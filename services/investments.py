from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from core.currency import to_czk
from core.models import AccountType
from core.validation import non_negative_decimal, positive_decimal, validate_currency
from database.repositories import BrokerSnapshotsRepository


class InvestmentsService:
    def __init__(self, repository: BrokerSnapshotsRepository):
        self.repository = repository

    def record_snapshot(self, *, account: dict[str, Any], snapshot_date: date, value: Decimal, exchange_rate: Decimal) -> dict[str, Any]:
        if account["account_type"] != AccountType.BROKER.value:
            raise ValueError("Investiční snapshot lze uložit pouze k brokerovému účtu.")
        non_negative_decimal(value, "Hodnota portfolia")
        positive_decimal(exchange_rate, "Kurz")
        currency = validate_currency(account["currency"])
        return self.repository.create({
            "account_id": account["id"], "snapshot_date": snapshot_date.isoformat(), "value": str(value),
            "currency": currency, "exchange_rate": str(exchange_rate), "value_czk": str(to_czk(value, exchange_rate)),
        })
