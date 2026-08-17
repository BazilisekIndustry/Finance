from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd
import streamlit as st

from components.auth import require_authenticated_client
from components.navigation import render_navigation
from core.models import AccountType
from database.repositories import AccountsRepository, BalanceSnapshotsRepository
from services.accounts import AccountsService


st.set_page_config(page_title="Účty | Family Finance", page_icon="💳", layout="wide")
st.title("💳 Účty a skutečné zůstatky")

client = require_authenticated_client()
render_navigation()
accounts_repository = AccountsRepository(client)
snapshots_repository = BalanceSnapshotsRepository(client)
service = AccountsService(accounts_repository, snapshots_repository)

try:
    accounts = accounts_repository.list(include_inactive=True)
except Exception:
    st.error("Účty se nepodařilo načíst. Ověřte Supabase konfiguraci a spuštění migrace.")
    st.stop()

with st.expander("Přidat účet", expanded=not accounts):
    with st.form("create_account", clear_on_submit=True):
        name = st.text_input("Název účtu")
        institution = st.text_input("Instituce")
        account_type = st.selectbox(
            "Typ", options=[item.value for item in AccountType],
            format_func=lambda value: {
                "main_current": "Hlavní běžný", "current": "Běžný", "savings": "Spořicí",
                "overdraft": "Kontokorent", "broker": "Broker",
            }[value],
        )
        currency = st.selectbox("Měna", ["CZK", "EUR", "USD"])
        primary = st.checkbox("Hlavní účet")
        limit = st.number_input("Limit kontokorentu", min_value=0.0, step=1000.0)
        create = st.form_submit_button("Vytvořit účet", type="primary")
    if create:
        try:
            service.create_account(
                name=name, institution=institution, account_type=account_type, currency=currency,
                is_primary=primary, overdraft_limit=Decimal(str(limit)),
            )
            st.success("Účet byl vytvořen.")
            st.rerun()
        except (ValueError, LookupError) as exc:
            st.error(str(exc))
        except Exception:
            st.error("Účet se nepodařilo uložit.")

if accounts:
    edit_labels = {f"{item['name']} ({item['currency']})": item for item in accounts}
    with st.expander("Upravit nebo deaktivovat účet"):
        edit_label = st.selectbox("Vybraný účet", list(edit_labels), key="edit_account")
        edit_account = edit_labels[edit_label]
        with st.form("edit_account_form"):
            edit_name = st.text_input("Název", value=edit_account["name"])
            edit_institution = st.text_input("Instituce", value=edit_account["institution"] or "")
            edit_primary = st.checkbox("Hlavní účet", value=edit_account["is_primary"])
            edit_limit = st.number_input("Limit kontokorentu", min_value=0.0, value=float(edit_account["overdraft_limit"]), step=1000.0)
            update = st.form_submit_button("Uložit změny")
        if update:
            try:
                service.update_account(edit_account, name=edit_name, institution=edit_institution, is_primary=edit_primary, overdraft_limit=Decimal(str(edit_limit)))
                st.success("Účet byl upraven.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
        if edit_account["is_active"] and st.button("Deaktivovat vybraný účet", key="deactivate_account"):
            try:
                service.deactivate_account(edit_account["id"])
                st.success("Účet byl deaktivován; historické snapshoty zůstaly zachovány.")
                st.rerun()
            except Exception:
                st.error("Účet se nepodařilo deaktivovat.")

active_accounts = [account for account in accounts if account["is_active"]]
if not active_accounts:
    st.info("Zatím nemáte žádný aktivní účet.")
    st.stop()

latest = {item["account_id"]: item for item in snapshots_repository.latest_by_account()}
table_rows = []
for account in active_accounts:
    snapshot = latest.get(account["id"])
    displayed_balance = snapshot["balance"] if snapshot else "—"
    if account["account_type"] == AccountType.OVERDRAFT.value and snapshot:
        displayed_balance = f"dostupné {snapshot.get('overdraft_available', displayed_balance)} {account['currency']}"
    table_rows.append({
        "Účet": account["name"], "Typ": account["account_type"], "Měna": account["currency"],
        "Aktuální stav": displayed_balance, "Hlavní": "Ano" if account["is_primary"] else "",
    })
st.dataframe(pd.DataFrame(table_rows), hide_index=True, use_container_width=True)

st.subheader("Zapsat skutečný zůstatek")
labels = {f"{account['name']} ({account['currency']})": account for account in active_accounts}
selected_label = st.selectbox("Účet", list(labels))
selected = labels[selected_label]
balance_label = "Dostupný kontokorent" if selected["account_type"] == AccountType.OVERDRAFT.value else "Aktuální zůstatek"
with st.form("record_snapshot", clear_on_submit=True):
    snapshot_date = st.date_input("Datum snapshotu", value=date.today())
    balance = st.number_input(balance_label, min_value=0.0, step=1000.0)
    default_rate = 1.0 if selected["currency"] == "CZK" else 25.0
    rate = st.number_input("Kurz do CZK", min_value=0.000001, value=default_rate, format="%.6f")
    save_snapshot = st.form_submit_button("Uložit snapshot", type="primary")
if save_snapshot:
    try:
        service.record_snapshot(
            account=selected, snapshot_date=snapshot_date, balance=Decimal(str(balance)),
            exchange_rate=Decimal(str(rate)),
        )
        st.success("Skutečný zůstatek byl uložen jako nový historický snapshot.")
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))
    except Exception:
        st.error("Snapshot se nepodařilo uložit.")
