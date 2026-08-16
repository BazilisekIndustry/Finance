import pytest

from database.client import ConfigurationError, get_supabase_config


def test_reads_only_public_supabase_configuration():
    url, key = get_supabase_config({"supabase": {"url": "https://example.supabase.co", "anon_key": "anon"}})
    assert url == "https://example.supabase.co"
    assert key == "anon"


def test_rejects_missing_configuration():
    with pytest.raises(ConfigurationError):
        get_supabase_config({})

