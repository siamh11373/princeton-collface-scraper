import json

import pytest

from collface_scraper.config import TARGET
from collface_scraper.contract import load_contract
from collface_scraper.errors import ConfigurationError


def valid_contract():
    return {
        "target": TARGET,
        "mode": "dom",
        "evidence": "Synthetic test contract",
        "exhaustive": True,
        "enumeration_evidence": "Synthetic fixture has an authoritative total",
        "listing": {
            "url": TARGET + "/",
            "cards": ".card",
            "profile_link": "a.profile",
            "id_attribute": "data-source-id",
        },
        "profile": {
            "root": "main",
            "sections": "section",
            "heading": "h2",
            "rows": "dl",
            "label": "dt",
            "value": "dd",
        },
    }


def test_contract_requires_evidence_and_stable_identity(tmp_path):
    path = tmp_path / "contract.json"
    value = valid_contract()
    del value["evidence"]
    path.write_text(json.dumps(value))
    with pytest.raises(ConfigurationError, match="evidence"):
        load_contract(path)
    value = valid_contract()
    del value["listing"]["id_attribute"]
    path.write_text(json.dumps(value))
    with pytest.raises(ConfigurationError, match="stable identity"):
        load_contract(path)


def test_exhaustive_claim_requires_enumeration_evidence(tmp_path):
    path = tmp_path / "contract.json"
    value = valid_contract()
    del value["enumeration_evidence"]
    path.write_text(json.dumps(value))
    with pytest.raises(ConfigurationError, match="enumeration evidence"):
        load_contract(path)

