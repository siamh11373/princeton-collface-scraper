import pytest

from collface_scraper.adapter import DomAdapter, same_origin_url
from collface_scraper.config import TARGET
from collface_scraper.errors import DiscoveryError


def contract():
    return {
        "target": TARGET,
        "mode": "dom",
        "evidence": "Synthetic test",
        "exhaustive": True,
        "listing": {
            "url": TARGET + "/directory?page=1",
            "cards": ".card",
            "profile_link": "a.profile",
            "id_attribute": "data-source-id",
            "total": ".total",
            "next_link": "a.next",
        },
        "profile": {},
    }


def test_listing_uses_stable_ids_and_same_origin_pagination(browser):
    context = browser.new_context()
    context.route(
        "**/*",
        lambda route: route.fulfill(
            content_type="text/html",
            body="""
            <span class=total>2 students</span>
            <div class=card data-source-id=101><a class=profile href=/students/101>A</a></div>
            <div class=card data-source-id=102><a class=profile href=/students/102>B</a></div>
            <a class=next href='/directory?page=2'>Next</a>
            """,
        ),
    )
    adapter = DomAdapter(context.new_page(), contract())
    page = adapter.list_page(None)
    assert [ref.source_id for ref in page.profiles] == ["101", "102"]
    assert page.next_cursor == TARGET + "/directory?page=2"
    assert page.total == 2
    assert page.exhaustive is True
    context.close()


def test_duplicate_ids_are_rejected(browser):
    context = browser.new_context()
    context.route(
        "**/*",
        lambda route: route.fulfill(
            content_type="text/html",
            body="""
            <div class=card data-source-id=101><a class=profile href=/students/101>A</a></div>
            <div class=card data-source-id=101><a class=profile href=/students/101>B</a></div>
            """,
        ),
    )
    value = contract()
    value["listing"].pop("total")
    with pytest.raises(DiscoveryError, match="duplicate"):
        DomAdapter(context.new_page(), value).list_page(None)
    context.close()


def test_url_identity_uses_named_capture(browser):
    context = browser.new_context()
    context.route(
        "**/*",
        lambda route: route.fulfill(
            content_type="text/html",
            body='<div class=card><a class=profile href="/students/abc-123">A</a></div>',
        ),
    )
    value = contract()
    value["listing"].pop("id_attribute")
    value["listing"].pop("total")
    value["listing"]["id_from_url"] = r"/students/(?P<id>[^/?]+)"
    result = DomAdapter(context.new_page(), value).list_page(None)
    assert result.profiles[0].source_id == "abc-123"
    context.close()


def test_cross_origin_urls_are_rejected():
    with pytest.raises(DiscoveryError, match="outside"):
        same_origin_url("https://unexpected.test/student/1")

