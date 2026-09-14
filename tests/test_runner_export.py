import csv
import json

import pytest

from collface_scraper.errors import AuthenticationError, ExtractionError
from collface_scraper.export import export_run
from collface_scraper.models import ListingPage, ProfileRef
from collface_scraper.runner import collect
from collface_scraper.state import RunStore


class SyntheticAdapter:
    def __init__(self, fail=None):
        self.fail = fail
        self.fetched = []
        self.phase_pages = 0

    def list_page(self, cursor):
        self.phase_pages += 1
        if cursor is None:
            ids = ["1", "2"]
            next_cursor = "https://example.test/page-2"
        else:
            ids = ["2", "3"]
            next_cursor = None
        return ListingPage(
            tuple(ProfileRef(value, f"https://example.test/{value}") for value in ids),
            next_cursor,
            3,
            True,
        )

    def profile(self, ref):
        self.fetched.append(ref.source_id)
        if self.fail and ref.source_id == "2":
            raise self.fail
        return {
            "Profile/Name": "Same display name",
            "Contact/Code": "00123" if ref.source_id == "1" else ref.source_id,
            "Activities/Group": ["東京", ref.source_id],
        }

    def audit(self, ref, fields):
        return fields == self.profile(ref)


def new_store(path, limit=None):
    return RunStore(
        path,
        {
            "target": "https://example.test",
            "account": "synthetic",
            "scope": "full" if limit is None else f"sample-{limit}",
            "limit": limit,
            "contract_sha256": "synthetic",
        },
    )


def test_full_run_reconciles_and_exports_roundtrip(tmp_path):
    store = new_store(tmp_path / "run.sqlite")
    collect(SyntheticAdapter(), store, progress=lambda _: None)
    report = export_run(store, tmp_path / "out")
    assert report["status"] == "complete"
    assert report["rows"] == 3
    assert report["roundtrip_verified"] is True
    assert report["spreadsheet_sensitive_cells"] == 1
    with (tmp_path / "out" / "profiles.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["Contact/Code"] == "'00123"
    assert "東京" in rows[0]["Activities/Group"]
    assert json.loads((tmp_path / "out" / "report.json").read_text())["rows"] == 3
    store.close()


def test_interrupted_run_resumes_without_refetching_complete_record(tmp_path):
    path = tmp_path / "run.sqlite"
    store = new_store(path)
    with pytest.raises(KeyboardInterrupt):
        collect(SyntheticAdapter(KeyboardInterrupt()), store, progress=lambda _: None)
    assert store.counts()["complete"] == 1
    store.close()
    resumed = new_store(path)
    adapter = SyntheticAdapter()
    collect(adapter, resumed, progress=lambda _: None)
    assert adapter.fetched.count("1") == 0
    assert export_run(resumed, tmp_path / "out")["status"] == "complete"
    resumed.close()


def test_profile_failure_is_partial_and_retried(tmp_path):
    store = new_store(tmp_path / "run.sqlite")
    collect(SyntheticAdapter(ExtractionError("synthetic")), store, progress=lambda _: None)
    report = export_run(store, tmp_path / "out")
    assert report["status"] == "partial"
    assert "unresolved_profiles" in report["reasons"]
    collect(SyntheticAdapter(), store, progress=lambda _: None)
    assert store.counts()["complete"] == 3
    store.close()


def test_authentication_failure_preserves_pending_record(tmp_path):
    store = new_store(tmp_path / "run.sqlite")
    with pytest.raises(AuthenticationError):
        collect(SyntheticAdapter(AuthenticationError("synthetic")), store, progress=lambda _: None)
    assert store.counts()["pending"] >= 1
    store.close()


def test_limited_run_never_claims_complete(tmp_path):
    store = new_store(tmp_path / "run.sqlite", limit=1)
    collect(SyntheticAdapter(), store, limit=1, progress=lambda _: None)
    report = export_run(store, tmp_path / "out")
    assert report["status"] == "partial"
    assert "limited_run" in report["reasons"]
    store.close()
