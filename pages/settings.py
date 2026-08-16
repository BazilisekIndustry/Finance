from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd
import streamlit as st

from components.auth import require_authenticated_client
from components.navigation import render_navigation
from database.repositories import (AccountsRepository, BalanceSnapshotsRepository, BrokerSnapshotsRepository,
                                   ExchangeRatesRepository, ExpensesRepository, IncomesRepository, SettingsRepository,
                                   TransfersRepository)
from services.demo_data import DemoDataService
from services.exchange_rates import CnbExchangeRateProvider, ExchangeRatesService

st.set_page_config(page_title="Nastavení | Family Finance", page_icon="⚙️", layout="wide")
st.title("⚙️ Nastavení")
client = require_authenticated_client()
render_navigation()
settings_repository = SettingsRepository(client)
settings = settings_repository.get_or_create()
with st.form("settings_form"):
    st.selectbox("Základní měna", ["CZK"], index=0, disabled=True, help="První verze používá CZK jako pevně definovanou základní měnu.")
    payday = st.number_input("Den výplaty", min_value=1, max_value=31, value=int(settings["payday"]), step=1)
    ratio_percent = st.slider("Investiční poměr (%)", min_value=0, max_value=100, value=round(float(settings["investment_ratio"]) * 100), step=1)
    source = st.selectbox("Kurzovní zdroj", ["cnb"], index=0, format_func=lambda _: "Česká národní banka")
    submit = st.form_submit_button("Uložit nastavení", type="primary")
if submit:
    try:
        settings_repository.update({"base_currency": "CZK", "payday": int(payday), "investment_ratio": str(Decimal(ratio_percent) / Decimal("100")), "exchange_rate_source": source})
        st.success("Nastavení bylo uloženo.")
        st.rerun()
    except Exception:
        st.error("Nastavení se nepodařilo uložit.")

st.subheader("Kurzovní data")
st.caption("ČNB zveřejňuje devizové kurzy v pracovní dny. Historické snapshoty vždy uchovávají vlastní použitý kurz.")
rate_date = st.date_input("Datum kurzu", value=date.today())
if st.button("Načíst a uložit kurzy ČNB"):
    try:
        stored = ExchangeRatesService(ExchangeRatesRepository(client), CnbExchangeRateProvider()).fetch_and_store(rate_date)
        st.success(f"Uloženo {len(stored)} kurzů.")
    except RuntimeError as exc:
        st.error(str(exc))
    except Exception:
        st.error("Kurz se nepodařilo uložit.")
rates = []
for currency in ("CZK", "EUR", "USD"):
    item = ExchangeRatesRepository(client).latest(currency, date.today())
    if item:
        rates.append(item)
if rates:
    st.dataframe(pd.DataFrame(rates)[["rate_date", "currency", "rate_to_czk", "source"]], hide_index=True, use_container_width=True)

st.subheader("Demo data")
st.caption("Vytvoří ukázkové účty, osm období snapshotů, pravidelné položky, převod a broker. Funguje pouze v úplně prázdném účtu a nic nepřepisuje.")
confirmed = st.checkbox("Rozumím, že demo data jsou určena jen pro prázdný účet.")
if st.button("Inicializovat demo data", disabled=not confirmed):
    try:
        DemoDataService(
            AccountsRepository(client), BalanceSnapshotsRepository(client), IncomesRepository(client),
            ExpensesRepository(client), TransfersRepository(client), BrokerSnapshotsRepository(client),
        ).seed()
        st.success("Demo data byla vytvořena.")
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))
    except Exception:
        st.error("Demo data se nepodařilo vytvořit. Žádná existující data nebyla přepsána.")
