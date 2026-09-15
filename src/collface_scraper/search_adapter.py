"""Adapter for CollFace's observed whole-directory Vue search response."""

import hashlib
import time
from urllib.parse import urljoin

from playwright.sync_api import Error as PlaywrightError

from .adapter import same_origin_url
from .errors import AccessBlocked, AuthenticationError, DiscoveryError, ExtractionError, FetchError
from .fetch import backoff, retry_after
from .fields import from_pairs, visible_contract_value
from .models import Fields, ListingPage, ProfileRef


def opaque_source_id(value: object) -> str:
    """Keep the stable backend key useful without exporting its hidden raw value."""

    rendered = str(value).strip()
    if not rendered:
        raise DiscoveryError("A directory record omitted its stable source identity.")
    return "cf_" + hashlib.sha256(("collface:" + rendered).encode()).hexdigest()[:24]


class SearchApiAdapter:
    def __init__(
        self,
        page,
        contract: dict,
        *,
        pace=lambda: None,
        sleep=time.sleep,
        renew=None,
    ):
        self.page = page
        self.contract = contract
        self.pace = pace
        self.sleep = sleep
        self.renew = renew
        self.records: dict[str, dict] = {}

    def _request(self) -> tuple[list[dict], int]:
        api = self.contract["api"]
        url = same_origin_url(api["url"])
        renewed = False
        for attempt in range(4):
            self.pace()
            try:
                result = self.page.evaluate(
                    """async url => {
                      const response = await fetch(url, {
                        credentials: 'same-origin',
                        headers: {Accept: 'application/json'}
                      });
                      const type = response.headers.get('content-type') || '';
                      const body = type.includes('json') ? await response.json() : null;
                      return {
                        status: response.status,
                        url: response.url,
                        retryAfter: response.headers.get('retry-after'),
                        body
                      };
                    }""",
                    url,
                )
            except PlaywrightError:
                if self.renew is not None and not renewed:
                    renewed = True
                    self.renew()
                    continue
                if attempt == 3:
                    raise FetchError("Directory request failed after bounded retries.") from None
                self.sleep(backoff(attempt))
                continue
            status = result["status"]
            if status in (401, 419):
                if self.renew is not None and not renewed:
                    renewed = True
                    self.renew()
                    continue
                raise AuthenticationError("The CollFace directory session expired.")
            if status == 403:
                raise AccessBlocked("CollFace denied directory access; collection stopped.")
            if status == 429:
                if attempt == 3:
                    raise AccessBlocked("Persistent CollFace rate limiting stopped collection.")
                delay = retry_after(result["retryAfter"])
                self.sleep(delay if delay is not None else backoff(attempt))
                continue
            if status >= 500:
                if attempt == 3:
                    raise FetchError(f"CollFace remained unavailable with HTTP {status}.")
                self.sleep(backoff(attempt))
                continue
            if status != 200 or not isinstance(result["body"], dict):
                raise FetchError(f"CollFace directory request failed with HTTP {status}.")
            body = result["body"]
            if body.get(api["status_field"]) != api["success_value"]:
                raise DiscoveryError("The directory response did not report success.")
            records = body.get(api["records_field"])
            total = body.get(api["total_field"])
            if not isinstance(records, list) or not isinstance(total, int):
                raise DiscoveryError("The directory response changed structure.")
            if total != len(records):
                raise DiscoveryError("The authoritative directory total does not match its data.")
            return records, total
        raise FetchError("Directory request exhausted its retry budget.")

    def list_page(self, cursor: str | None) -> ListingPage:
        if cursor is not None:
            raise DiscoveryError("The observed exhaustive response must terminate in one page.")
        records, total = self._request()
        identity_field = self.contract["identity_field"]
        found: dict[str, dict] = {}
        for record in records:
            if not isinstance(record, dict):
                raise DiscoveryError("A directory record is not an object.")
            raw_identity = record.get(identity_field)
            source_id = opaque_source_id(raw_identity)
            if source_id in found:
                raise DiscoveryError("The directory returned duplicate stable identities.")
            found[source_id] = record
        self.records = found
        source_url = same_origin_url(self.contract["source_url"])
        refs = tuple(ProfileRef(source_id, source_url) for source_id in sorted(found))
        return ListingPage(refs, None, total, True)

    def profile(self, ref: ProfileRef) -> Fields:
        if ref.source_id not in self.records:
            self.list_page(None)
        record = self.records.get(ref.source_id)
        if record is None:
            raise ExtractionError("A discovered record disappeared before extraction.")
        pairs = []
        for field in self.contract["visible_fields"]:
            if field["key"] not in record:
                raise ExtractionError("A contract-verified visible field disappeared.")
            value = record[field["key"]]
            if field.get("url") and value:
                value = urljoin(self.contract["target"] + "/", str(value))
            else:
                value = visible_contract_value(field, value)
            pairs.append((field["section"], field["label"], value))
        return from_pairs(pairs)

    def audit(self, ref: ProfileRef, fields: Fields) -> bool:
        audit = self.contract["audit"]
        record = self.records.get(ref.source_id)
        if record is None:
            return False
        self.pace()
        search = self.page.locator(audit["search_input"])
        search_value = record.get(audit["search_key"])
        if not isinstance(search_value, str) or not search_value.strip():
            return False
        search.fill(search_value)
        self.page.get_by_role("button", name=audit["search_button_name"], exact=True).click()
        card = self.page.locator(audit["card"])
        try:
            card.first.wait_for(state="visible", timeout=15_000)
        except PlaywrightError:
            return False
        if card.count() != 1:
            return False
        visible_text = card.first.inner_text()
        for field in self.contract["visible_fields"]:
            value = visible_contract_value(field, record[field["key"]])
            if value in (None, "") or field.get("url"):
                continue
            if str(value) not in visible_text:
                return False
        photo_fields = [field for field in self.contract["visible_fields"] if field.get("url")]
        if photo_fields:
            photo = card.first.locator(audit["photo"])
            if not photo.count() or not photo.first.is_visible():
                return False
            expected = urljoin(self.contract["target"] + "/", str(record[photo_fields[0]["key"]]))
            actual = urljoin(self.page.url, photo.first.get_attribute("src") or "")
            if actual != expected:
                return False
        return True
