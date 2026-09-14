"""Contract-driven browser adapter with no guessed CollFace selectors."""

import re
from urllib.parse import urljoin, urlsplit

from playwright.sync_api import Error as PlaywrightError

from .config import TARGET, origin
from .errors import AccessBlocked, AuthenticationError, DiscoveryError, FetchError
from .models import ListingPage, ProfileRef


def same_origin_url(value: str, base: str = TARGET) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DiscoveryError("The source did not provide a usable URL.")
    result = urljoin(base, value)
    if origin(result) != TARGET:
        raise DiscoveryError("The source supplied a URL outside the approved origin.")
    return urlsplit(result)._replace(fragment="").geturl()


def source_id_from_url(url: str, pattern: str) -> str:
    match = re.search(pattern, url)
    if not match or not match.groupdict().get("id"):
        raise DiscoveryError("A profile URL did not expose the observed stable ID.")
    return match.group("id")


class DomAdapter:
    def __init__(self, page, contract: dict, *, pace=lambda: None):
        self.page = page
        self.contract = contract
        self.pace = pace

    def _navigate(self, url: str) -> None:
        url = same_origin_url(url)
        self.pace()
        try:
            response = self.page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        except PlaywrightError:
            raise FetchError("Browser navigation failed without exposing page details.") from None
        if response is None:
            raise FetchError("Browser navigation returned no response.")
        if origin(self.page.url) != TARGET or self.page.locator('input[type="password"]').count():
            raise AuthenticationError("Protected CollFace access expired or was not established.")
        if response.status == 403:
            raise AccessBlocked("CollFace denied access; collection stopped.")
        if response.status == 429:
            raise AccessBlocked("CollFace rate-limited the browser; collection stopped.")
        if not 200 <= response.status < 300:
            raise FetchError(f"CollFace navigation failed with HTTP {response.status}.")

    def list_page(self, cursor: str | None) -> ListingPage:
        listing = self.contract["listing"]
        url = same_origin_url(cursor or listing["url"])
        self._navigate(url)
        cards = self.page.locator(listing["cards"])
        try:
            cards.first.wait_for(state="visible", timeout=15_000)
        except PlaywrightError:
            raise DiscoveryError("The observed listing structure was not found.") from None
        refs: list[ProfileRef] = []
        for card in cards.all():
            link = card.locator(listing["profile_link"]).first
            href = link.get_attribute("href")
            profile_url = same_origin_url(href or "", url)
            if listing.get("id_attribute"):
                source_id = card.get_attribute(listing["id_attribute"])
                if not source_id:
                    raise DiscoveryError("A listing card omitted its observed stable ID.")
            else:
                source_id = source_id_from_url(profile_url, listing["id_from_url"])
            refs.append(ProfileRef(source_id, profile_url))
        if len({ref.source_id for ref in refs}) != len(refs):
            raise DiscoveryError("A listing page contains duplicate stable IDs.")

        total = None
        if listing.get("total"):
            raw_total = self.page.locator(listing["total"]).first.inner_text()
            try:
                total = int(re.sub(r"[^0-9]", "", raw_total))
            except ValueError:
                raise DiscoveryError("The observed total is not numeric.") from None

        next_cursor = None
        if listing.get("next_link"):
            next_link = self.page.locator(listing["next_link"])
            if next_link.count() and next_link.first.is_visible():
                disabled = next_link.first.get_attribute("aria-disabled") == "true"
                if not disabled:
                    href = next_link.first.get_attribute("href")
                    if not href:
                        raise DiscoveryError("The observed next-page control has no URL.")
                    next_cursor = same_origin_url(href, url)
        return ListingPage(tuple(refs), next_cursor, total, self.contract["exhaustive"])

