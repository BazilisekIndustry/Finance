from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from database.auth import AuthenticationError, SESSION_KEY, SessionTokens, authenticated_client, refresh, sign_in
from database.client import ConfigurationError
from database.repositories import (AccountsRepository, BalanceSnapshotsRepository, BrokerSnapshotsRepository,
                                   ExpensesRepository, IncomesRepository, SettingsRepository, TransfersRepository)
from components.navigation import render_navigation
from services.dashboard import DashboardService


st.set_page_config(page_title="Family Finance Planner", page_icon="💰", layout="wide")


def _logout() -> None:
    st.session_state.pop(SESSION_KEY, None)
    st.rerun()


def _login_screen() -> None:
    st.title("💰 Family Finance Planner")
    st.caption("Přihlaste se ke svým finančním datům.")
    with st.form("login"):
        email = st.text_input("E-mail", type="default", autocomplete="email")
        password = st.text_input("Heslo", type="password", autocomplete="current-password")
        submitted = st.form_submit_button("Přihlásit se", type="primary")
    if submitted:
        try:
            st.session_state[SESSION_KEY] = sign_in(st.secrets, email, password)
            st.rerun()
        except (AuthenticationError, ConfigurationError) as exc:
            st.error(str(exc))


def _app_shell(tokens: SessionTokens) -> None:
    with st.sidebar:
        st.title("Family Finance")
        st.caption(tokens.email or "Přihlášený uživatel")
        if st.button("Obnovit relaci"):
            try:
                st.session_state[SESSION_KEY] = refresh(tokens, st.secrets)
                st.success("Relace byla obnovena.")
            except (AuthenticationError, ConfigurationError) as exc:
                st.error(str(exc))
                _logout()
    render_navigation()
    st.title("🏠 Dashboard")
    try:
        client = authenticated_client(tokens, st.secrets)
        accounts = AccountsRepository(client).list(include_inactive=True)
        balance_repository = BalanceSnapshotsRepository(client)
        snapshots = balance_repository.latest_by_account()
        snapshot_history = balance_repository.history_between(date(2000, 1, 1), date(2100, 1, 1))
        broker_snapshots = BrokerSnapshotsRepository(client).latest_by_account()
        settings = SettingsRepository(client).get_or_create()
        data = DashboardService().build(
            accounts=accounts, latest_snapshots=snapshots, latest_broker_snapshots=broker_snapshots,
            incomes=IncomesRepository(client).list(), expenses=ExpensesRepository(client).list(),
            transfers=TransfersRepository(client).list_between(date(2000, 1, 1), date(2100, 1, 1)),
            payday=int(settings["payday"]), investment_ratio=Decimal(str(settings["investment_ratio"])),
            snapshot_history=snapshot_history,
        )
    except Exception:
        st.error("Dashboard se nepodařilo načíst. Ověřte Supabase konfiguraci a spuštění migrace.")
        return
    def czk(value):
        return "—" if value is None else f"{value:,.0f} Kč".replace(",", " ")
    cards = st.columns(6)
    cards[0].metric("Aktuální cash", czk(data.current_cash_czk))
    cards[1].metric("Best Case", czk(data.best_case_czk))
    cards[2].metric("Worst Case", czk(data.worst_case_czk))
    cards[3].metric("Pro investice", czk(data.investment_available_czk))
    cards[4].metric("Kupní síla", czk(data.purchase_power_czk))
    cards[5].metric("Celkové bohatství", czk(data.total_wealth_czk))
    analytic_cards = st.columns(4)
    analytic_cards[0].metric("Broker", czk(data.broker_value_czk))
    analytic_cards[1].metric("Odchylka od plánu", czk(data.plan_variance_czk), delta=czk(data.plan_variance_czk) if data.plan_variance_czk is not None else None, delta_color="normal")
    analytic_cards[2].metric("Oproti minulému období", czk(data.previous_period_delta_czk), delta=czk(data.previous_period_delta_czk) if data.previous_period_delta_czk is not None else None, delta_color="normal")
    analytic_cards[3].metric("Trend (další období)", czk(data.forecast_trend_czk), delta=czk(data.forecast_trend_czk) if data.forecast_trend_czk is not None else None, delta_color="normal")
    if data.missing_snapshot_accounts:
        st.warning("Chybí skutečný snapshot pro: " + ", ".join(data.missing_snapshot_accounts) + ". Predikce proto není zobrazena.")
    if not any(item["is_primary"] and item["is_active"] for item in accounts):
        st.warning("Chybí hlavní účet; investiční disponibilitu nelze určit.")
    for account, shortage in data.shortages_czk.items():
        st.error(f"🔴 V období {data.period.start.strftime('%d. %m.')}–{data.period.end.strftime('%d. %m.')} může na účtu {account} chybět {czk(shortage)}.")
    if data.projections:
        rows = []
        latest = {item["account_id"]: item for item in snapshots}
        for account in accounts:
            if account["id"] not in data.projections:
                continue
            projection = data.projections[account["id"]]
            current = latest[account["id"]]
            current_balance = current.get("overdraft_available", current["balance"]) if account["account_type"] == "overdraft" else current["balance"]
            rows.append({"Účet": account["name"], "Aktuálně": current_balance, "Best": projection.best_case, "Worst": projection.worst_case, "Měna": account["currency"]})
        st.subheader("Účty")
        st.dataframe(rows, hide_index=True, use_container_width=True)
        snapshot_labels = [
            f"{account['name']} – aktualizováno {date.fromisoformat(latest[account['id']]['snapshot_date']).day}. {date.fromisoformat(latest[account['id']]['snapshot_date']).month}. {date.fromisoformat(latest[account['id']]['snapshot_date']).year}"
            for account in accounts if account["id"] in data.projections and latest[account["id"]].get("snapshot_date")
        ]
        if snapshot_labels:
            st.info("Predikce aktualizována podle skutečných zůstatků: " + "; ".join(snapshot_labels))
            stale = [f"{account['name']} ({(date.today() - date.fromisoformat(latest[account['id']]['snapshot_date'])).days} dní)" for account in accounts if account["id"] in data.projections and (date.today() - date.fromisoformat(latest[account['id']]['snapshot_date'])).days > 0]
            if stale:
                st.caption("Stáří posledního snapshotu: " + ", ".join(stale))
        horizon = st.select_slider("Horizont cash-flow predikce", options=[1, 2, 3, 6, 12], value=3, format_func=lambda item: f"{item} období")
        forecast = DashboardService().cash_flow_forecast(
            accounts=accounts, latest_snapshots=snapshots, incomes=IncomesRepository(client).list(),
            expenses=ExpensesRepository(client).list(), transfers=TransfersRepository(client).list_between(date(2000, 1, 1), date(2100, 1, 1)),
            payday=int(settings["payday"]), count=horizon,
        )
        if forecast:
            labels = [f"{item.period.start.strftime('%d. %m.')}–{item.period.end.strftime('%d. %m.')}" for item in forecast]
            chart = go.Figure()
            chart.add_trace(go.Scatter(x=labels, y=[float(item.best_case_czk) for item in forecast], name="Best Case", mode="lines+markers"))
            chart.add_trace(go.Scatter(x=labels, y=[float(item.worst_case_czk) for item in forecast], name="Worst Case", mode="lines+markers", line={"dash": "dash"}))
            chart.update_layout(title="Budoucí cash-flow predikce", yaxis_title="CZK", xaxis_title="Finanční období")
            st.plotly_chart(chart, use_container_width=True)
            st.dataframe(pd.DataFrame({"Období": labels, "Best Case (CZK)": [item.best_case_czk for item in forecast], "Worst Case (CZK)": [item.worst_case_czk for item in forecast]}), hide_index=True, use_container_width=True)


tokens = st.session_state.get(SESSION_KEY)
if isinstance(tokens, SessionTokens):
    _app_shell(tokens)
else:
    _login_screen()
