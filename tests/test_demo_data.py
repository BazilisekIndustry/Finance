import pytest

from services.demo_data import DemoDataService


class NonEmptyAccounts:
    def list(self, include_inactive=False):
        return [{"id": "existing"}]


def test_demo_seed_refuses_nonempty_user_space():
    service = DemoDataService(NonEmptyAccounts(), None, None, None, None, None)
    with pytest.raises(ValueError):
        service.seed()
