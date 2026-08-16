from __future__ import annotations

import streamlit as st

from database.auth import SESSION_KEY


def render_navigation() -> None:
    """Consistent Czech navigation for the Streamlit multipage app."""
    with st.sidebar:
        st.page_link("app.py", label="Dashboard", icon="🏠")
        st.page_link("pages/accounts.py", label="Účty", icon="💳")
        st.page_link("pages/incomes.py", label="Příjmy", icon="💰")
        st.page_link("pages/expenses.py", label="Výdaje", icon="💸")
        st.page_link("pages/transfers.py", label="Převody", icon="🔄")
        st.page_link("pages/investments.py", label="Investice", icon="📈")
        st.page_link("pages/statistics.py", label="Statistiky", icon="📊")
        st.page_link("pages/settings.py", label="Nastavení", icon="⚙️")
        st.divider()
        if st.button("Odhlásit se", use_container_width=True):
            st.session_state.pop(SESSION_KEY, None)
            st.switch_page("app.py")
