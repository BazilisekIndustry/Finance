from types import SimpleNamespace

import pytest

from database.repositories.base import Repository


class FakeClient:
    def __init__(self, user_id: str | None):
        self.auth = SimpleNamespace(get_user=lambda: SimpleNamespace(user=SimpleNamespace(id=user_id) if user_id else None))


def test_repository_uses_authenticated_identity_not_caller_identity():
    repository = Repository(FakeClient("user-from-jwt"))
    payload = repository.own({"name": "Účet", "user_id": "attacker"})
    assert payload["user_id"] == "user-from-jwt"


def test_repository_rejects_anonymous_access():
    with pytest.raises(PermissionError):
        Repository(FakeClient(None)).user_id()

