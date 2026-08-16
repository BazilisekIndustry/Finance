from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.auth import require_authenticated_client
from components.navigation import render_navigation
from database.repositories import AccountsRepository, BalanceSnapshotsRepository, SettingsRepository
from services.statistics import StatisticsService

st.set_page_config(page_title="Statistiky | Family Finance", page_icon="📊", layout="wide")
st.title("📊 Statistiky")
client = require_authenticated_client()
render_navigation()
settings = SettingsRepository(client).get_or_create()
accounts = AccountsRepository(client).list(include_inactive=True)
snapshots = BalanceSnapshotsRepository(client).history_between(date(2000, 1, 1), date(2100, 1, 1))
data = StatisticsService().build(accounts=accounts, snapshots=snapshots, payday=int(settings["payday"]))

def label(period):
    return f"{period.start.strftime('%d. %m. %Y')} – {period.end.strftime('%d. %m. %Y')}"

if data.trend_delta is None:
    st.info("Pro vyhodnocení trendu jsou potřeba alespoň dvě úplná skutečná finanční období.")
else:
    symbol = "🟢" if data.trend_delta > 0 else "🔴" if data.trend_delta < 0 else "⚪"
    st.metric("Trend skutečného cash", f"{symbol} {data.trend_delta:,.0f} Kč".replace(",", " "))

if data.actual:
    actual_frame = pd.DataFrame({"Období": [label(item.period) for item in data.actual], "Cash (CZK)": [float(item.cash_czk) for item in data.actual]})
    chart = go.Figure(go.Scatter(x=actual_frame["Období"], y=actual_frame["Cash (CZK)"], mode="lines+markers", name="Skutečnost"))
    chart.update_layout(title="Historický vývoj cash", yaxis_title="CZK", xaxis_title="Finanční období")
    st.plotly_chart(chart, use_container_width=True)
else:
    st.info("Pro historický graf je třeba pořídit kompletní snapshoty aktivních cash účtů v daných obdobích.")

if data.forecast:
    forecast_frame = pd.DataFrame({"Období": [label(period) for period, _ in data.forecast], "Statistická predikce (CZK)": [float(value) for _, value in data.forecast]})
    chart = go.Figure(go.Scatter(x=forecast_frame["Období"], y=forecast_frame["Statistická predikce (CZK)"], mode="lines+markers", line={"dash": "dash"}, name="Lineární trend"))
    chart.update_layout(title="Budoucí statistická predikce", yaxis_title="CZK", xaxis_title="Finanční období")
    st.plotly_chart(chart, use_container_width=True)
else:
    st.caption("Statistická predikce se zobrazí až po šesti úplných skutečných obdobích.")
