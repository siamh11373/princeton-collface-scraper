import pytest

from collface_scraper.config import load_credentials, origin
from collface_scraper.errors import ConfigurationError


def test_credentials_require_both_values(monkeypatch):
    monkeypatch.setenv("COLLFACE_USERNAME", "synthetic")
    monkeypatch.delenv("COLLFACE_PASSWORD", raising=False)
    with pytest.raises(ConfigurationError):
        load_credentials()


def test_missing_credentials_are_allowed_only_when_explicit(monkeypatch):
    monkeypatch.delenv("COLLFACE_USERNAME", raising=False)
    monkeypatch.delenv("COLLFACE_PASSWORD", raising=False)
    assert load_credentials(optional=True) is None


def test_origin_normalizes_only_default_ports():
    assert origin("https://fed.princeton.edu:443/cas") == "https://fed.princeton.edu"
    assert origin("http://fed.princeton.edu:80/cas") == "http://fed.princeton.edu"
    assert origin("https://fed.princeton.edu:444/cas") == "https://fed.princeton.edu:444"


def test_credentials_are_not_exposed_by_repr(monkeypatch):
    monkeypatch.setenv("COLLFACE_USERNAME", "synthetic")
    monkeypatch.setenv("COLLFACE_PASSWORD", "secret-test-value")
    value = load_credentials()
    assert "synthetic" not in repr(value)
    assert "secret-test-value" not in repr(value)
