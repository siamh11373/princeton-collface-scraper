from contextlib import contextmanager
from pathlib import Path

import pytest

from collface_scraper import browser_session
from collface_scraper.errors import ConfigurationError


class FakeProcess:
    def __init__(self):
        self.running = True
        self.terminated = False

    def poll(self):
        return None if self.running else 0

    def terminate(self):
        self.terminated = True
        self.running = False

    def wait(self, timeout):
        self.running = False

    def kill(self):
        self.running = False


class FakeBrowser:
    def __init__(self, contexts):
        self.contexts = contexts
        self.closed = False

    def close(self):
        self.closed = True


def test_debug_port_file_is_validated(tmp_path):
    process = FakeProcess()
    (tmp_path / "DevToolsActivePort").write_text("9222\n/devtools/browser/test\n")
    assert browser_session._wait_for_debug_port(tmp_path, process, timeout=0.1) == 9222

    (tmp_path / "DevToolsActivePort").write_text("not-a-port\n")
    with pytest.raises(ConfigurationError, match="control port"):
        browser_session._wait_for_debug_port(tmp_path, process, timeout=0)


def test_attended_context_uses_isolated_installed_chrome(monkeypatch, tmp_path):
    process = FakeProcess()
    launched = {}
    context = object()
    browser = FakeBrowser([context])

    @contextmanager
    def temporary_directory(**_kwargs):
        yield str(tmp_path)

    def popen(command, **kwargs):
        launched["command"] = command
        launched["kwargs"] = kwargs
        (tmp_path / "DevToolsActivePort").write_text("9333\n/devtools/browser/test\n")
        return process

    class Chromium:
        def connect_over_cdp(self, endpoint):
            launched["endpoint"] = endpoint
            return browser

    class Playwright:
        chromium = Chromium()

    monkeypatch.setattr(browser_session, "installed_chrome_path", lambda: Path("/chrome"))
    monkeypatch.setattr(browser_session.tempfile, "TemporaryDirectory", temporary_directory)
    monkeypatch.setattr(browser_session.subprocess, "Popen", popen)

    with browser_session.browser_context(Playwright(), interactive=True) as value:
        assert value is context

    assert launched["command"][0] == "/chrome"
    assert "--remote-debugging-port=0" in launched["command"]
    assert f"--user-data-dir={tmp_path}" in launched["command"]
    assert launched["endpoint"] == "http://127.0.0.1:9333"
    assert browser.closed is True
    assert process.terminated is True


def test_context_page_reuses_chromes_initial_tab():
    first = object()

    class Context:
        pages = [first]

    assert browser_session.context_page(Context()) is first
