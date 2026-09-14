import re

import pytest

from collface_scraper.auth import authenticate
from collface_scraper.config import Credentials
from collface_scraper.errors import AuthenticationError, InteractiveAuthenticationRequired

LOGIN = """<form method="post" action="/cas/login">
<input name="username"><input name="password" type="password">
<input name="execution" type="hidden" value="synthetic-state">
<button type="submit">LOGIN</button></form>"""
PROTECTED = "<h1>Residential College</h1><h2>Search for Students</h2>"


def install_routes(context, outcome="success", *, action="/cas/login"):
    submissions = []

    def route(request):
        url = request.request.url
        if url == "https://collface.deptcpanel.princeton.edu/":
            request.fulfill(
                content_type="text/html",
                body='<script>location.replace("https://fed.princeton.edu/cas/login?service='
                'https%3A%2F%2Fcollface.deptcpanel.princeton.edu%2F")</script>',
            )
        elif url.startswith("https://fed.princeton.edu/cas/login"):
            if request.request.method == "POST":
                submissions.append(request.request.post_data)
                body = {
                    "success": '<script>location.replace("https://collface.deptcpanel.princeton.edu/home")</script>',
                    "invalid": "Invalid credentials",
                    "duo": "Check your device to approve your Duo sign-in",
                    "foreign": '<script>location.replace("https://unexpected.test/")</script>',
                }[outcome]
                request.fulfill(content_type="text/html", body=body)
            else:
                request.fulfill(content_type="text/html", body=LOGIN.replace("/cas/login", action))
        elif url == "https://collface.deptcpanel.princeton.edu/home":
            request.fulfill(content_type="text/html", body=PROTECTED)
        elif url == "https://unexpected.test/":
            request.fulfill(content_type="text/html", body="unexpected")
        else:
            request.abort()

    context.route("**/*", route)
    return submissions


def test_programmatic_cas_success_requires_protected_content(browser):
    context = browser.new_context()
    submissions = install_routes(context)
    url = authenticate(context.new_page(), Credentials("synthetic", "test-only"), timeout=3)
    assert url == "https://collface.deptcpanel.princeton.edu/home"
    assert len(submissions) == 1
    assert "execution=synthetic-state" in submissions[0]
    context.close()


@pytest.mark.parametrize(
    ("outcome", "error"),
    [("invalid", AuthenticationError), ("duo", InteractiveAuthenticationRequired)],
)
def test_cas_failure_modes_are_explicit(browser, outcome, error):
    context = browser.new_context()
    install_routes(context, outcome)
    with pytest.raises(error):
        authenticate(context.new_page(), Credentials("synthetic", "test-only"), timeout=3)
    context.close()


def test_credentials_cannot_be_sent_to_another_origin(browser):
    context = browser.new_context()
    install_routes(context, action="https://unexpected.test/collect")
    with pytest.raises(AuthenticationError, match="unexpected origin"):
        authenticate(context.new_page(), Credentials("synthetic", "test-only"), timeout=3)
    context.close()


def test_unexpected_callback_origin_is_rejected(browser):
    context = browser.new_context()
    install_routes(context, outcome="foreign")
    with pytest.raises(AuthenticationError, match="unexpected origin"):
        authenticate(context.new_page(), Credentials("synthetic", "test-only"), timeout=3)
    context.close()


def test_target_page_without_both_markers_is_not_authenticated(browser):
    context = browser.new_context()
    context.route(
        "**/*",
        lambda route: route.fulfill(content_type="text/html", body="Residential College only"),
    )
    with pytest.raises(AuthenticationError, match="could not be verified"):
        authenticate(context.new_page(), Credentials("synthetic", "test-only"), timeout=0.3)
    context.close()


def test_service_parameter_cannot_point_elsewhere(browser):
    context = browser.new_context()
    context.route(
        "**/*",
        lambda route: route.fulfill(
            content_type="text/html",
            body=LOGIN,
        ),
    )
    page = context.new_page()
    page.goto("https://fed.princeton.edu/cas/login?service=https%3A%2F%2Funexpected.test")
    with pytest.raises(AuthenticationError, match="destination"):
        authenticate(page, Credentials("synthetic", "test-only"), timeout=0.3)
    context.close()


def test_invalid_text_pattern_does_not_include_credentials():
    assert re.search("invalid credentials", "Invalid credentials", re.I)
