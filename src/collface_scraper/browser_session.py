"""Browser lifecycle for headless runs and attended MFA in installed Google Chrome."""

import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .errors import ConfigurationError


def installed_chrome_path(*, platform: str | None = None) -> Path:
    """Return a supported installed Google Chrome executable."""

    selected = platform or sys.platform
    candidates: dict[str, tuple[Path, ...]] = {
        "darwin": (
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ),
        "linux": (
            Path("/usr/bin/google-chrome"),
            Path("/usr/bin/google-chrome-stable"),
        ),
        "win32": (
            Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
            Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
        ),
    }
    for candidate in candidates.get(selected, ()):
        if candidate.is_file():
            return candidate
    raise ConfigurationError("Attended authentication requires an installed Google Chrome browser.")


def _wait_for_debug_port(profile: Path, process, *, timeout: float) -> int:
    active_port = profile / "DevToolsActivePort"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            break
        try:
            port = int(active_port.read_text(encoding="utf-8").splitlines()[0])
        except (OSError, ValueError, IndexError):
            time.sleep(0.05)
            continue
        if 0 < port < 65_536:
            return port
        break
    raise ConfigurationError("Installed Google Chrome did not expose its local control port.")


def _stop_process(process) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


@contextmanager
def browser_context(playwright, *, interactive: bool) -> Iterator[object]:
    """Yield an isolated context, using branded Chrome for attended MFA."""

    if not interactive:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context()
        try:
            yield context
        finally:
            context.close()
            browser.close()
        return

    chrome = installed_chrome_path()
    with tempfile.TemporaryDirectory(prefix="collface-attended-chrome-") as temporary:
        profile = Path(temporary)
        process = subprocess.Popen(
            [
                str(chrome),
                "--remote-debugging-port=0",
                f"--user-data-dir={profile}",
                "--no-first-run",
                "--no-default-browser-check",
                "about:blank",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        browser = None
        try:
            port = _wait_for_debug_port(profile, process, timeout=20)
            browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            if len(browser.contexts) != 1:
                raise ConfigurationError(
                    "Installed Google Chrome did not create an isolated attended context."
                )
            yield browser.contexts[0]
        finally:
            if browser is not None:
                browser.close()
            _stop_process(process)


def context_page(context):
    """Reuse Chrome's initial tab so attended mode opens one predictable window."""

    return context.pages[0] if context.pages else context.new_page()
