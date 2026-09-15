import json
from pathlib import Path

from collface_scraper.cli import main


def test_doctor_json_is_safe_without_credentials(capsys, monkeypatch):
    monkeypatch.delenv("COLLFACE_USERNAME", raising=False)
    monkeypatch.delenv("COLLFACE_PASSWORD", raising=False)

    assert main(["--doctor", "--json"]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["ok"] is True
    assert value["credentials"] == {"password": False, "username": False}
    assert "COLLFACE" not in json.dumps(value)


def test_export_only_reaches_saved_state_validation(tmp_path, capsys):
    assert main(["--export-only", "--output-dir", str(tmp_path)]) == 3
    assert "state_mismatch" in capsys.readouterr().err
    assert not (Path(tmp_path) / "full" / "run.sqlite").exists()
