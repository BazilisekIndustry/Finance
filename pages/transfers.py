from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd
import streamlit as st

from components.auth import require_authenticated_client
from components.navigation import render_navigation
from database.repositories import AccountsRepository, TransfersRepository
from services.transfers import TransfersService

st.set_page_config(page_title="Převody | Family Finance", page_icon="🔄", layout="wide")
st.title("🔄 Převody mezi účty")
client = require_authenticated_client()
render_navigation()
accounts = [item for item in AccountsRepository(client).list() if item["account_type"] != "broker"]
repository = TransfersRepository(client)
service = TransfersService(repository)
labels = {f"{item['name']} ({item['currency']})": item for item in accounts}
if len(labels) < 2:
    st.info("Pro převod potřebujete alespoň dva aktivní nebrokerové účty.")
    st.stop()
with st.form("transfer_form", clear_on_submit=True):
    source_label = st.selectbox("Zdrojový účet", list(labels))
    target_label = st.selectbox("Cílový účet", list(labels), index=1)
    amount = st.number_input("Odeslaná částka", min_value=0.01, step=1000.0)
    target_amount_text = st.text_input("Připsaná cílová částka (povinné při jiné měně)")
    transfer_date = st.date_input("Datum", value=date.today())
    description = st.text_input("Popis")
    submit = st.form_submit_button("Uložit převod", type="primary")
if submit:
    try:
        target_amount = Decimal(target_amount_text.replace(",", ".")) if target_amount_text.strip() else None
        service.create(source=labels[source_label], target=labels[target_label], amount=Decimal(str(amount)), target_amount=target_amount, transfer_date=transfer_date, description=description)
        st.success("Převod byl uložen.")
        st.rerun()
    except (ValueError, ArithmeticError) as exc:
        st.error(str(exc))
items = repository.list_between(date(2000, 1, 1), date(2100, 1, 1))
if items:
    st.dataframe(pd.DataFrame(items)[["transfer_date", "amount", "currency", "target_amount", "description"]], hide_index=True, use_container_width=True)
