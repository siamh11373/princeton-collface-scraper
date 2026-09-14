import json

from collface_scraper.cli import main


def test_doctor_json_is_safe_without_credentials(capsys, monkeypatch):
    monkeypatch.delenv("COLLFACE_USERNAME", raising=False)
    monkeypatch.delenv("COLLFACE_PASSWORD", raising=False)

    assert main(["--doctor", "--json"]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["ok"] is True
    assert value["credentials"] == {"password": False, "username": False}
    assert "COLLFACE" not in json.dumps(value)

