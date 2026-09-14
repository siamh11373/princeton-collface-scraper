"""Fail-closed Princeton CAS authentication for CollFace."""

import re
import time
from urllib.parse import parse_qs, urljoin, urlsplit

from playwright.sync_api import Error as PlaywrightError

from .config import CAS_ORIGIN, TARGET, Credentials, origin
from .errors import AuthenticationError, InteractiveAuthenticationRequired

PROTECTED_MARKERS = (
    re.compile(r"Residential\s+College", re.I),
    re.compile(r"Search\s+for\s+Students", re.I),
)
CHALLENGE = re.compile(
    r"verify your identity|check your device|approve.{0,30}(sign.in|duo)|"
    r"enter.{0,20}verification code|use.{0,15}(passkey|security key)|"
    r"two.factor authentication|multi.factor authentication",
    re.I,
)
HUMAN_CHECK = re.compile(r"verify you are human|checking your browser|security verification", re.I)
INVALID = re.compile(
    r"invalid credentials|authentication failed|incorrect password|"
    r"credentials.{0,20}(invalid|incorrect)",
    re.I,
)


def _service_is_valid(url: str) -> bool:
    services = parse_qs(urlsplit(url).query).get("service", [])
    return not services or all(origin(value) == TARGET for value in services)


def _protected(page, text: str) -> bool:
    return (
        origin(page.url) == TARGET
        and not page.locator('input[type="password"]').count()
        and all(marker.search(text) for marker in PROTECTED_MARKERS)
    )


def authenticate(
    page,
    credentials: Credentials,
    *,
    allow_interactive: bool = False,
    timeout: float = 45.0,
    interactive_timeout: float = 300.0,
    progress=print,
) -> str:
    """Authenticate in a fresh context and return verified protected CollFace URL.

    Interactive mode exists for bounded development inspection. It is deliberately not the
    default and is never represented as unattended assessment compliance.
    """

    try:
        page.goto(TARGET + "/", wait_until="domcontentloaded", timeout=30_000)
        submitted = False
        waiting = False
        deadline = time.monotonic() + timeout

        def require_human() -> None:
            nonlocal waiting, deadline
            if not allow_interactive:
                raise InteractiveAuthenticationRequired(
                    "Princeton CAS requires human MFA; unattended authentication is blocked."
                )
            if not waiting:
                waiting = True
                deadline = time.monotonic() + interactive_timeout
                page.bring_to_front()
                progress(
                    "Complete the Princeton MFA prompt in the browser or on your device. "
                    "Do not enter credentials or verification codes in chat."
                )

        while time.monotonic() < deadline:
            frame_hosts = {urlsplit(frame.url).hostname or "" for frame in page.frames}
            if any(host.endswith(".duosecurity.com") for host in frame_hosts):
                require_human()
                page.wait_for_timeout(250)
                continue
            try:
                text = page.locator("body").inner_text(timeout=1_500)
            except PlaywrightError:
                page.wait_for_timeout(250)
                continue
            if CHALLENGE.search(text) or HUMAN_CHECK.search(text):
                require_human()
                page.wait_for_timeout(250)
                continue
            if INVALID.search(text):
                raise AuthenticationError("Princeton CAS rejected the supplied credentials.")
            if _protected(page, text):
                return page.url

            username = page.locator('input[name="username"]')
            password = page.locator('input[name="password"]')
            if not submitted and username.count() and password.count() and username.is_visible():
                if origin(page.url) != CAS_ORIGIN or not _service_is_valid(page.url):
                    raise AuthenticationError("The CAS login destination is not approved.")
                action = password.evaluate("input => input.form ? input.form.action : null")
                method = password.evaluate(
                    "input => input.form ? input.form.method.toLowerCase() : null"
                )
                if not action or origin(urljoin(page.url, action)) != CAS_ORIGIN:
                    raise AuthenticationError("The credential form has an unexpected origin.")
                if method != "post":
                    raise AuthenticationError("The credential form no longer submits by POST.")
                username.fill(credentials.username)
                password.fill(credentials.password)
                page.get_by_role("button", name=re.compile(r"^login$", re.I)).click(timeout=15_000)
                submitted = True
            elif origin(page.url) not in (TARGET, CAS_ORIGIN) and not any(
                host.endswith(".duosecurity.com") for host in frame_hosts
            ):
                raise AuthenticationError("Authentication redirected to an unexpected origin.")
            page.wait_for_timeout(250)

        if waiting:
            raise InteractiveAuthenticationRequired(
                "Manual MFA did not complete within the allowed inspection window."
            )
        raise AuthenticationError("Protected CollFace content could not be verified.")
    except (AuthenticationError, InteractiveAuthenticationRequired):
        raise
    except PlaywrightError:
        raise AuthenticationError("The browser could not complete the verified CAS flow.") from None
