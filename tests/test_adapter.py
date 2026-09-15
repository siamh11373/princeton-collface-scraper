import pytest

from collface_scraper.adapter import DomAdapter, same_origin_url, visible_field_url
from collface_scraper.config import TARGET
from collface_scraper.errors import AccessBlocked, DiscoveryError, FetchError


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
            content_type="text/html; charset=utf-8",
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


def test_visible_field_url_applies_observed_same_origin_prefix():
    field = {"url": True, "url_prefix": "img"}
    assert visible_field_url(field, "synthetic.jpg") == TARGET + "/img/synthetic.jpg"
    with pytest.raises(DiscoveryError, match="outside"):
        visible_field_url({"url": True}, "https://unexpected.test/student.jpg")


def test_expired_session_is_renewed_once(browser):
    context = browser.new_context()
    calls = {"requests": 0, "renewals": 0}

    def route_request(route):
        calls["requests"] += 1
        if calls["requests"] == 1:
            route.fulfill(content_type="text/html", body='<input type="password">')
        else:
            route.fulfill(
                content_type="text/html",
                body=(
                    "<div class=card data-source-id=101>"
                    "<a class=profile href=/students/101>A</a></div>"
                ),
            )

    def renew():
        calls["renewals"] += 1

    context.route("**/*", route_request)
    value = contract()
    value["listing"].pop("total")
    result = DomAdapter(context.new_page(), value, renew=renew).list_page(None)
    assert result.profiles[0].source_id == "101"
    assert calls["renewals"] == 1
    context.close()


def test_rate_limit_honors_retry_after_then_recovers(browser):
    context = browser.new_context()
    calls = {"requests": 0}
    sleeps = []

    def route_request(route):
        calls["requests"] += 1
        if calls["requests"] == 1:
            route.fulfill(status=429, headers={"Retry-After": "2"}, body="slow down")
        else:
            route.fulfill(
                content_type="text/html",
                body=(
                    "<div class=card data-source-id=101>"
                    "<a class=profile href=/students/101>A</a></div>"
                ),
            )

    context.route("**/*", route_request)
    value = contract()
    value["listing"].pop("total")
    result = DomAdapter(context.new_page(), value, sleep=sleeps.append).list_page(None)
    assert result.profiles[0].source_id == "101"
    assert sleeps == [2.0]
    context.close()


@pytest.mark.parametrize("status", [403, 429])
def test_persistent_access_controls_stop_collection(browser, status):
    context = browser.new_context()
    context.route(
        "**/*",
        lambda route: route.fulfill(status=status, headers={"Retry-After": "0"}, body="blocked"),
    )
    value = contract()
    value["listing"].pop("total")
    with pytest.raises(AccessBlocked):
        DomAdapter(context.new_page(), value, sleep=lambda _: None).list_page(None)
    context.close()


def test_network_failures_retry_then_fail_cleanly(browser):
    context = browser.new_context()
    calls = []

    def fail(route):
        calls.append(route.request.url)
        route.abort("connectionfailed")

    context.route("**/*", fail)
    value = contract()
    value["listing"].pop("total")
    with pytest.raises(FetchError, match="bounded retries"):
        DomAdapter(context.new_page(), value, sleep=lambda _: None).list_page(None)
    assert len(calls) == 4
    context.close()


def test_profile_extracts_dynamic_repeated_fields_links_and_photo(browser):
    context = browser.new_context()
    context.route(
        "**/*",
        lambda route: route.fulfill(
            content_type="text/html; charset=utf-8",
            body="""
            <main id=profile>
              <img class=photo src=/media/101.jpg>
              <section><h2>Contact</h2>
                <dl><dt>Unexpected label</dt><dd>東京, "quoted"</dd></dl>
                <dl><dt>Affiliation</dt><dd>First</dd></dl>
                <dl><dt>Affiliation</dt><dd>Second</dd></dl>
                <dl><dt>Links</dt><dd><a href=/about>About</a>
                  <a hidden href=/hidden-backend-value>Hidden</a></dd></dl>
                <dl><dt>Missing</dt><dd></dd></dl>
              </section>
            </main>
            """,
        ),
    )
    value = contract()
    value["profile"] = {
        "root": "#profile",
        "sections": "section",
        "heading": "h2",
        "rows": "dl",
        "label": "dt",
        "value": "dd",
        "photo": {"selector": "img.photo", "label": "Photo URL"},
    }
    value["field_validation_evidence"] = "Synthetic fixture comparison"
    adapter = DomAdapter(context.new_page(), value)
    ref = type("Ref", (), {"source_id": "101", "url": TARGET + "/students/101"})()
    fields = adapter.profile(ref)
    assert fields["Contact/Unexpected label"] == '東京, "quoted"'
    assert fields["Contact/Affiliation"] == ["First", "Second"]
    assert fields["Contact/Links"]["links"] == [TARGET + "/about"]
    assert fields["Contact/Missing"] == ""
    assert fields["Profile/Photo URL"] == TARGET + "/media/101.jpg"
    assert adapter.audit(ref, fields)
    context.close()
