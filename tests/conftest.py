import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as value:
        yield value


@pytest.fixture
def browser(playwright_instance):
    value = playwright_instance.chromium.launch(headless=True)
    yield value
    value.close()
