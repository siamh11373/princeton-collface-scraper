import json
from urllib.parse import unquote

import pytest

from collface_scraper.config import TARGET
from collface_scraper.errors import DiscoveryError
from collface_scraper.search_adapter import SearchApiAdapter

RECORDS = [
    {
        "id": 991,
        "name": "Alpha Example",
        "year": 2029,
        "class_yr": "29",
        "email": "alpha@princeton.edu",
        "acad_plan_descr": "Hidden description",
        "program": "BSE - Engineering",
        "college": "Hidden college",
        "img": "/photos/alpha.jpg",
    },
    {
        "id": 992,
        "name": "Beta Example",
        "year": 2028,
        "class_yr": "28",
        "email": "beta@princeton.edu",
        "acad_plan_descr": "Hidden description",
        "program": "AB - History",
        "college": "Hidden college",
        "img": "/photos/beta.jpg",
    },
]


def contract():
    return {
        "target": TARGET,
        "mode": "search-api",
        "exhaustive": True,
        "source_url": TARGET + "/",
        "identity_field": "id",
        "api": {
            "url": TARGET + "/search/term/all/college/all",
            "status_field": "status",
            "success_value": "OK",
            "total_field": "total",
            "records_field": "data",
        },
        "visible_fields": [
            {"section": "Profile", "label": "Name", "key": "name"},
            {
                "section": "Academic",
                "label": "Class Year",
                "key": "class_yr",
                "display_prefix": "'",
            },
            {"section": "Contact", "label": "Email", "key": "email"},
            {"section": "Academic", "label": "Program", "key": "program"},
            {"section": "Profile", "label": "Photo URL", "key": "img", "url": True},
        ],
        "audit": {
            "search_key": "email",
            "search_input": "input[placeholder='Search for...']",
            "search_button_name": "Search",
            "card": "li.student",
            "photo": "img",
        },
    }


def install(context, records=RECORDS, *, total=None):
    page_html = """
    <input placeholder='Search for...'><button>Search</button><ul></ul>
    <script>
      document.querySelector('button').onclick = async () => {
        const term = document.querySelector('input').value;
        const result = await fetch('/search/term/' + encodeURIComponent(term) + '/college/all');
        const body = await result.json();
        document.querySelector('ul').innerHTML = body.data.map(item =>
          `<li class=student><img src="${item.img}"><b>${item.name}</b> ` +
          `'${item.class_yr} ${item.email} ${item.program}</li>`).join('');
      };
    </script>
    """

    def route_request(route):
        url = route.request.url
        if "/search/term/" not in url:
            route.fulfill(content_type="text/html", body=page_html)
            return
        term = unquote(url.split("/search/term/", 1)[1].split("/college/", 1)[0])
        selected = records if term == "all" else [r for r in records if r["email"] == term]
        route.fulfill(
            content_type="application/json",
            body=json.dumps(
                {
                    "status": "OK",
                    "total": len(selected) if total is None else total,
                    "data": selected,
                }
            ),
        )

    context.route("**/*", route_request)


def test_whole_directory_discovery_extracts_only_visible_contract_fields(browser):
    context = browser.new_context()
    install(context)
    page = context.new_page()
    page.goto(TARGET)
    adapter = SearchApiAdapter(page, contract())
    listing = adapter.list_page(None)
    assert listing.total == 2
    assert listing.next_cursor is None
    assert listing.exhaustive is True
    assert all(ref.source_id.startswith("cf_") for ref in listing.profiles)
    assert len({ref.source_id for ref in listing.profiles}) == 2
    ref = next(ref for ref in listing.profiles if adapter.records[ref.source_id]["id"] == 991)
    fields = adapter.profile(ref)
    assert fields["Profile/Name"] == "Alpha Example"
    assert fields["Academic/Class Year"] == "'29"
    assert fields["Profile/Photo URL"] == TARGET + "/photos/alpha.jpg"
    assert "Hidden description" not in json.dumps(fields)
    assert "Hidden college" not in json.dumps(fields)
    assert adapter.audit(ref, fields) is True
    context.close()


def test_authoritative_total_mismatch_is_rejected(browser):
    context = browser.new_context()
    install(context, total=99)
    page = context.new_page()
    page.goto(TARGET)
    with pytest.raises(DiscoveryError, match="total"):
        SearchApiAdapter(page, contract()).list_page(None)
    context.close()


def test_duplicate_visible_identity_is_rejected(browser):
    context = browser.new_context()
    install(context, records=[RECORDS[0], RECORDS[0]])
    page = context.new_page()
    page.goto(TARGET)
    with pytest.raises(DiscoveryError, match="duplicate"):
        SearchApiAdapter(page, contract()).list_page(None)
    context.close()
