import json

import pytest

from collface_scraper.browser_export import BrowserExportAdapter
from collface_scraper.errors import DiscoveryError


def contract():
    return {
        "target": "https://collface.deptcpanel.princeton.edu",
        "source_url": "/",
        "identity_field": "id",
        "api": {
            "status_field": "status",
            "success_value": "OK",
            "records_field": "data",
            "total_field": "total",
        },
        "visible_fields": [
            {"section": "Profile", "label": "Name", "key": "name"},
            {"section": "Profile", "label": "Email", "key": "email"},
        ],
    }


def test_browser_export_filters_to_visible_contract_fields(tmp_path):
    path = tmp_path / "response.json"
    path.write_text(
        json.dumps(
            {
                "status": "OK",
                "total": 1,
                "data": [
                    {
                        "id": 123,
                        "name": "Synthetic Student",
                        "email": "test@example.test",
                        "hidden": "x",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    adapter = BrowserExportAdapter(path, contract())
    page = adapter.list_page(None)
    fields = adapter.profile(page.profiles[0])
    assert fields == {
        "Profile/Name": "Synthetic Student",
        "Profile/Email": "test@example.test",
    }


def test_browser_export_rejects_count_mismatch(tmp_path):
    path = tmp_path / "response.json"
    path.write_text(json.dumps({"status": "OK", "total": 2, "data": []}), encoding="utf-8")
    with pytest.raises(DiscoveryError, match="total"):
        BrowserExportAdapter(path, contract()).list_page(None)
