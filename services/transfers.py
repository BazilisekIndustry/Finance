from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from core.validation import positive_decimal, validate_currency
from database.repositories import TransfersRepository


class TransfersService:
    def __init__(self, repository: TransfersRepository):
        self.repository = repository

    def create(
        self, *, source: dict[str, Any], target: dict[str, Any], amount: Decimal, transfer_date: date,
        description: str | None = None, target_amount: Decimal | None = None,
    ) -> dict[str, Any]:
        if source["id"] == target["id"]:
            raise ValueError("Zdrojový a cílový účet musí být rozdílné.")
        if source.get("account_type") == "broker" or target.get("account_type") == "broker":
            raise ValueError("Broker nelze použít jako účet pro cash-flow převod.")
        positive_decimal(amount, "Částka")
        source_currency = validate_currency(source["currency"])
        cross_currency = source_currency != validate_currency(target["currency"])
        if cross_currency and target_amount is None:
            raise ValueError("Pro převod mezi měnami zadejte připsanou cílovou částku.")
        if target_amount is not None:
            positive_decimal(target_amount, "Cílová částka")
        rate = (target_amount / amount) if target_amount is not None else None
        return self.repository.create({
            "source_account_id": source["id"], "target_account_id": target["id"], "amount": str(amount),
            "target_amount": str(target_amount) if target_amount is not None else None, "currency": source_currency,
            "exchange_rate": str(rate) if rate is not None else None, "transfer_date": transfer_date.isoformat(),
            "description": description.strip() if description else None,
        })
