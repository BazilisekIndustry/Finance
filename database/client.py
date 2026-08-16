from __future__ import annotations

from typing import Any


class ConfigurationError(RuntimeError):
    """Raised when Supabase deployment secrets are unavailable or incomplete."""


def get_supabase_config(secrets: Any) -> tuple[str, str]:
    """Read only the public URL and anon key from Streamlit secrets.

    The service-role key is deliberately unsupported in the application: it would
    bypass Row Level Security and must never be shipped to a browser-facing app.
    """
    try:
        config = secrets["supabase"]
        url = str(config["url"])
        anon_key = str(config["anon_key"])
    except (KeyError, TypeError) as exc:
        raise ConfigurationError(
            "Chybí konfigurace [supabase] s položkami url a anon_key v secrets."
        ) from exc
    if not url.startswith(("https://", "http://")) or not anon_key:
        raise ConfigurationError("Konfigurace Supabase není platná.")
    return url, anon_key


def create_anonymous_client(secrets: Any):
    """Create a fresh client with the Supabase anonymous key and no user token."""
    try:
        from supabase import create_client
    except ImportError as exc:
        raise ConfigurationError("Chybí balíček supabase. Spusťte instalaci requirements.txt.") from exc
    url, anon_key = get_supabase_config(secrets)
    return create_client(url, anon_key)


def create_authenticated_client(secrets: Any, access_token: str, refresh_token: str):
    """Return a client whose requests carry the authenticated user's JWT."""
    client = create_anonymous_client(secrets)
    client.auth.set_session(access_token, refresh_token)
    return client

