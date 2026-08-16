from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .client import create_anonymous_client, create_authenticated_client


SESSION_KEY = "supabase_session"


@dataclass(frozen=True)
class SessionTokens:
    access_token: str
    refresh_token: str
    user_id: str
    email: str | None


class AuthenticationError(RuntimeError):
    pass


def sign_in(secrets: Any, email: str, password: str) -> SessionTokens:
    if not email.strip() or not password:
        raise AuthenticationError("Zadejte e-mail i heslo.")
    try:
        response = create_anonymous_client(secrets).auth.sign_in_with_password(
            {"email": email.strip(), "password": password}
        )
        return _tokens_from_session(response.session)
    except Exception as exc:  # Supabase exception classes differ between compatible releases.
        raise AuthenticationError("Přihlášení se nezdařilo. Zkontrolujte e-mail a heslo.") from exc


def refresh(tokens: SessionTokens, secrets: Any) -> SessionTokens:
    """Refresh an existing session; callers replace their stored tokens atomically."""
    try:
        client = create_authenticated_client(secrets, tokens.access_token, tokens.refresh_token)
        response = client.auth.refresh_session()
        return _tokens_from_session(response.session)
    except Exception as exc:
        raise AuthenticationError("Relaci se nepodařilo obnovit. Přihlaste se znovu.") from exc


def authenticated_client(tokens: SessionTokens, secrets: Any):
    return create_authenticated_client(secrets, tokens.access_token, tokens.refresh_token)


def _tokens_from_session(session: Any) -> SessionTokens:
    if session is None or not session.access_token or not session.refresh_token or session.user is None:
        raise AuthenticationError("Supabase nevrátil platnou relaci.")
    return SessionTokens(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        user_id=str(session.user.id),
        email=getattr(session.user, "email", None),
    )

