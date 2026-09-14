import pytest

from collface_scraper.errors import DiscoveryError, StateMismatch
from collface_scraper.models import ListingPage, ProfileRef
from collface_scraper.state import RunStore


def identity(limit=None):
    return {
        "target": "https://example.test",
        "account": "synthetic",
        "scope": "full" if limit is None else f"sample-{limit}",
        "limit": limit,
        "contract_sha256": "synthetic",
    }


def test_page_and_ids_commit_together_and_resume(tmp_path):
    path = tmp_path / "run.sqlite"
    store = RunStore(path, identity())
    store.save_page(
        "discovery",
        None,
        ListingPage(
            (ProfileRef("1", "https://example.test/1"),),
            "https://example.test/?page=2",
            2,
            True,
        ),
    )
    store.close()
    resumed = RunStore(path, identity())
    assert resumed.checkpoint("discovery")["cursor"].endswith("page=2")
    assert resumed.counts()["pending"] == 1
    resumed.close()


def test_identity_mismatch_and_cursor_loop_fail(tmp_path):
    path = tmp_path / "run.sqlite"
    store = RunStore(path, identity())
    page = ListingPage((ProfileRef("1", "https://example.test/1"),), None, 1, True)
    store.save_page("discovery", None, page)
    with pytest.raises(DiscoveryError, match="repeated"):
        store.save_page("discovery", None, page)
    store.close()
    with pytest.raises(StateMismatch):
        RunStore(path, identity(limit=1))
