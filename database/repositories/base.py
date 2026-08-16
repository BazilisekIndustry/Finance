from __future__ import annotations

from typing import Any


class Repository:
    def __init__(self, client: Any):
        self.client = client

    def user_id(self) -> str:
        response = self.client.auth.get_user()
        user = getattr(response, "user", None)
        if user is None or not user.id:
            raise PermissionError("Operace vyžaduje přihlášeného uživatele.")
        return str(user.id)

    def own(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Attach the authenticated identity; callers cannot select a different owner."""
        return {**payload, "user_id": self.user_id()}

    @staticmethod
    def rows(response: Any) -> list[dict[str, Any]]:
        return list(response.data or [])

