from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.periods import financial_period_for
from database.repositories import (AccountsRepository, BalanceSnapshotsRepository, BrokerSnapshotsRepository,
                                   ExpensesRepository, IncomesRepository, TransfersRepository)
from services.accounts import AccountsService
from services.events import EventsService
from services.investments import InvestmentsService
from services.transfers import TransfersService


class DemoDataService:
    """Seeds a new user space only; it never merges into or overwrites existing data."""
    def __init__(self, accounts: AccountsRepository, balances: BalanceSnapshotsRepository, incomes: IncomesRepository,
                 expenses: ExpensesRepository, transfers: TransfersRepository, brokers: BrokerSnapshotsRepository):
        self.accounts = accounts
        self.account_service = AccountsService(accounts, balances)
        self.incomes = incomes
        self.expenses = expenses
        self.transfers = transfers
        self.brokers = brokers

    def seed(self, today: date | None = None) -> None:
        if self.accounts.list(include_inactive=True):
            raise ValueError("Demo data lze vytvořit pouze v prázdném účtu. Existující data nebyla změněna.")
        now = today or date.today()
        main = self.account_service.create_account(name="Hlavní účet", institution="Demo banka", account_type="main_current", currency="CZK", is_primary=True)
        savings = self.account_service.create_account(name="Rezerva", institution="Demo banka", account_type="savings", currency="CZK")
        overdraft = self.account_service.create_account(name="Kontokorent", institution="Demo banka", account_type="overdraft", currency="CZK", overdraft_limit=Decimal("30000"))
        broker = self.account_service.create_account(name="Demo broker", institution="Demo broker", account_type="broker", currency="USD")

        period = financial_period_for(now, 13)
        historical = []
        for _ in range(8):
            historical.append(period)
            period = financial_period_for(date.fromordinal(period.start.toordinal() - 1), 13)
        for index, item in enumerate(reversed(historical)):
            snapshot_date = min(item.end, now)
            self.account_service.record_snapshot(account=main, snapshot_date=snapshot_date, balance=Decimal("80000") + Decimal(index * 3500), exchange_rate=Decimal("1"))
            self.account_service.record_snapshot(account=savings, snapshot_date=snapshot_date, balance=Decimal("25000") + Decimal(index * 1200), exchange_rate=Decimal("1"))
            self.account_service.record_snapshot(account=overdraft, snapshot_date=snapshot_date, balance=Decimal("5000"), exchange_rate=Decimal("1"))
            InvestmentsService(self.brokers).record_snapshot(account=broker, snapshot_date=snapshot_date, value=Decimal("4000") + Decimal(index * 250), exchange_rate=Decimal("23"))

        event_start = historical[0].start
        income_service = EventsService(self.accounts, self.incomes)
        expense_service = EventsService(self.accounts, self.expenses)
        income_service.create(description="Mzda", amount=Decimal("50000"), currency="CZK", account=main, due_date=event_start, recurrence="recurring")
        expense_service.create(description="Bydlení", amount=Decimal("18000"), currency="CZK", account=main, due_date=event_start, recurrence="recurring")
        expense_service.create(description="Servis auta", amount=Decimal("7000"), currency="CZK", account=main, due_date=event_start, recurrence="recurring", is_reserve=True)
        TransfersService(self.transfers).create(source=main, target=savings, amount=Decimal("5000"), transfer_date=now, description="Pravidelná rezerva")
