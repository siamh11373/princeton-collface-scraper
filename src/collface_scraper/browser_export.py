"""Offline adapter for an authenticated response downloaded in normal Chrome."""

import json
from pathlib import Path

from .adapter import same_origin_url, visible_field_url
from .errors import DiscoveryError, ExtractionError
from .fields import from_pairs, visible_contract_value
from .models import Fields, ListingPage, ProfileRef
from .search_adapter import opaque_source_id


class BrowserExportAdapter:
    """Feed a temporary Chrome download through the normal validated pipeline."""

    def __init__(self, path: Path, contract: dict):
        self.path = path
        self.contract = contract
        self.records: dict[str, dict] = {}

    def list_page(self, cursor: str | None) -> ListingPage:
        if cursor is not None:
            raise DiscoveryError("The observed exhaustive response must terminate in one page.")
        try:
            body = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise DiscoveryError("The Chrome export is not valid UTF-8 JSON.") from None
        api = self.contract["api"]
        if not isinstance(body, dict) or body.get(api["status_field"]) != api["success_value"]:
            raise DiscoveryError("The Chrome export did not report directory success.")
        records = body.get(api["records_field"])
        total = body.get(api["total_field"])
        if not isinstance(records, list) or not isinstance(total, int) or total != len(records):
            raise DiscoveryError("The Chrome export total does not match its records.")
        identity_field = self.contract["identity_field"]
        found: dict[str, dict] = {}
        for record in records:
            if not isinstance(record, dict):
                raise DiscoveryError("A Chrome export record is not an object.")
            identity = record.get(identity_field)
            source_id = opaque_source_id(identity)
            if source_id in found:
                raise DiscoveryError("The Chrome export contains duplicate stable identities.")
            found[source_id] = record
        self.records = found
        source_url = same_origin_url(self.contract["source_url"])
        return ListingPage(
            tuple(ProfileRef(source_id, source_url) for source_id in sorted(found)),
            None,
            total,
            True,
        )

    def profile(self, ref: ProfileRef) -> Fields:
        record = self.records.get(ref.source_id)
        if record is None:
            raise ExtractionError("A Chrome export record disappeared during extraction.")
        pairs = []
        for field in self.contract["visible_fields"]:
            if field["key"] not in record:
                raise ExtractionError("A contract-verified visible field disappeared.")
            value = record[field["key"]]
            if field.get("url") and value:
                value = visible_field_url(field, value, target=self.contract["target"])
            else:
                value = visible_contract_value(field, value)
            pairs.append((field["section"], field["label"], value))
        return from_pairs(pairs)

    def audit(self, ref: ProfileRef, fields: Fields) -> bool:
        # The browser comparison is performed separately in the authenticated Chrome tab.
        return True
