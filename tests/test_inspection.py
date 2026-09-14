import json

from collface_scraper.config import TARGET
from collface_scraper.inspection import inspect_surface


def test_inspection_records_structure_without_visible_values(browser, tmp_path):
    context = browser.new_context()
    context.route(
        "**/*",
        lambda route: route.fulfill(
            content_type="text/html",
            body="""
            <title>Directory</title>
            <form action=/search method=get><input value='Private Name'><button>Go</button></form>
            <div class='card person'>Private Name</div><div class='card person'>Other</div>
            <a href=/student/private-id>Profile</a><a href=https://princeton.edu>Princeton</a>
            """,
        ),
    )
    page = context.new_page()
    page.goto(TARGET)
    path = tmp_path / "observation.json"
    value = inspect_surface(page, path)
    serialized = json.dumps(value)
    assert "Private Name" not in serialized
    assert "private-id" not in serialized
    assert value["surface"]["visible_class_counts"]["card"] == 2
    assert path.is_file()
    context.close()
