from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd
import streamlit as st

from components.auth import require_authenticated_client
from components.navigation import render_navigation
from database.repositories import AccountsRepository, ExpensesRepository
from services.events import EventsService

st.set_page_config(page_title="Výdaje | Family Finance", page_icon="💸", layout="wide")
st.title("💸 Výdaje")
client = require_authenticated_client()
render_navigation()
accounts = AccountsRepository(client).list()
repository = ExpensesRepository(client)
service = EventsService(AccountsRepository(client), repository)
labels = {f"{item['name']} ({item['currency']})": item for item in accounts if item["account_type"] != "broker"}
if not labels:
    st.info("Nejdříve vytvořte běžný nebo spořicí účet.")
    st.stop()
with st.form("expense_form", clear_on_submit=True):
    description = st.text_input("Popis")
    amount = st.number_input("Částka", min_value=0.01, step=1000.0)
    selected = st.selectbox("Účet", list(labels))
    due_date = st.date_input("Datum splatnosti", value=date.today())
    recurrence = st.radio("Typ", ["one_off", "recurring"], format_func=lambda x: "Jednorázový" if x == "one_off" else "Pravidelný", horizontal=True)
    expense_kind = st.radio("Charakter", ["fixed", "continuous"], format_func=lambda x: "Pevný" if x == "fixed" else "Průběžný (rovnoměrně za období)", horizontal=True)
    reserve = st.checkbox("Rezervní výdaj (pouze Worst Case)")
    submit = st.form_submit_button("Uložit výdaj", type="primary")
if submit:
    try:
        account = labels[selected]
        service.create(description=description, amount=Decimal(str(amount)), currency=account["currency"], account=account, due_date=due_date, recurrence=recurrence, is_reserve=reserve, expense_kind=expense_kind)
        st.success("Výdaj byl uložen.")
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))
items = repository.list()
if items:
    frame = pd.DataFrame(items)
    columns = ["description", "amount", "currency", "due_date", "recurrence", "expense_kind", "is_reserve", "is_active"]
    st.dataframe(frame[[column for column in columns if column in frame]], hide_index=True, use_container_width=True)
    active_items = [item for item in items if item["is_active"]]
    if active_items:
        labels_manage = {f"{item['description']} — {item['amount']} {item['currency']} ({item['due_date']})": item for item in active_items}
        with st.expander("Upravit nebo deaktivovat pravidelný výdaj"):
            chosen_label = st.selectbox("Výdaj", list(labels_manage), key="manage_expense")
            chosen = labels_manage[chosen_label]
            if chosen["recurrence"] == "recurring":
                with st.form("expense_version"):
                    new_amount = st.number_input("Nová částka", min_value=0.01, value=float(chosen["amount"]), step=1000.0)
                    effective_from = st.date_input("Platnost nové částky od", value=date.today())
                    replace = st.form_submit_button("Vytvořit novou verzi")
                if replace:
                    try:
                        service.replace_recurring_amount(chosen, Decimal(str(new_amount)), effective_from)
                        st.success("Nová verze výdaje byla vytvořena; historická verze zůstala zachována.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
            if st.button("Deaktivovat vybraný výdaj", key="deactivate_expense"):
                repository.deactivate(chosen["id"])
                st.success("Výdaj byl deaktivován.")
                st.rerun()
