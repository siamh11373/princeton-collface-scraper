import pytest

from collface_scraper.config import load_credentials
from collface_scraper.errors import ConfigurationError


def test_credentials_require_both_values(monkeypatch):
    monkeypatch.setenv("COLLFACE_USERNAME", "synthetic")
    monkeypatch.delenv("COLLFACE_PASSWORD", raising=False)
    with pytest.raises(ConfigurationError):
        load_credentials()


def test_credentials_are_not_exposed_by_repr(monkeypatch):
    monkeypatch.setenv("COLLFACE_USERNAME", "synthetic")
    monkeypatch.setenv("COLLFACE_PASSWORD", "secret-test-value")
    value = load_credentials()
    assert "synthetic" not in repr(value)
    assert "secret-test-value" not in repr(value)
