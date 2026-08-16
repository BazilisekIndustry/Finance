from __future__ import annotations

import streamlit as st

from database.auth import SESSION_KEY, SessionTokens, authenticated_client


def require_authenticated_client():
    tokens = st.session_state.get(SESSION_KEY)
    if not isinstance(tokens, SessionTokens):
        st.warning("Nejprve se přihlaste na hlavní stránce.")
        st.stop()
    return authenticated_client(tokens, st.secrets)

