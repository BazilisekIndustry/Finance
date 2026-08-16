from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd
import plotly.express as px
import streamlit as st

from components.auth import require_authenticated_client
from components.navigation import render_navigation
from database.repositories import AccountsRepository, BrokerSnapshotsRepository
from services.investments import InvestmentsService

st.set_page_config(page_title="Investice | Family Finance", page_icon="📈", layout="wide")
st.title("📈 Investiční portfolio")
client = require_authenticated_client()
render_navigation()
accounts = [item for item in AccountsRepository(client).list() if item["account_type"] == "broker"]
repository = BrokerSnapshotsRepository(client)
service = InvestmentsService(repository)
if not accounts:
    st.info("Nejdříve vytvořte účet typu Broker.")
    st.stop()
labels = {f"{item['name']} ({item['currency']})": item for item in accounts}
with st.form("broker_snapshot", clear_on_submit=True):
    selected = st.selectbox("Broker", list(labels))
    snapshot_date = st.date_input("Datum", value=date.today())
    value = st.number_input("Hodnota portfolia", min_value=0.0, step=1000.0)
    rate = st.number_input("Kurz do CZK", min_value=0.000001, value=1.0 if labels[selected]["currency"] == "CZK" else 25.0, format="%.6f")
    submit = st.form_submit_button("Uložit hodnotu", type="primary")
if submit:
    try:
        service.record_snapshot(account=labels[selected], snapshot_date=snapshot_date, value=Decimal(str(value)), exchange_rate=Decimal(str(rate)))
        st.success("Historická hodnota brokeru byla uložena.")
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))
history = []
for account in accounts:
    history.extend(repository.list_for_account(account["id"]))
if history:
    dataframe = pd.DataFrame(history)
    dataframe["snapshot_date"] = pd.to_datetime(dataframe["snapshot_date"])
    st.plotly_chart(px.line(dataframe, x="snapshot_date", y="value_czk", color="account_id", markers=True, labels={"snapshot_date": "Datum", "value_czk": "Hodnota v CZK", "account_id": "Broker"}), use_container_width=True)
    st.dataframe(dataframe[["snapshot_date", "value", "currency", "exchange_rate", "value_czk"]], hide_index=True, use_container_width=True)
