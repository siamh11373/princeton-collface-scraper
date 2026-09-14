"""Command-line entry point. Features land in independently verified milestones."""

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .errors import CollFaceError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="collface-scraper",
        description="Authorized, resumable Princeton CollFace directory export",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    parser.add_argument("--doctor", action="store_true", help="Check local configuration")
    parser.add_argument(
        "--check-auth", action="store_true", help="Verify fresh CAS login and protected content"
    )
    parser.add_argument(
        "--allow-interactive",
        action="store_true",
        help="Allow human MFA for development inspection only",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    os.umask(0o077)
    try:
        if args.doctor:
            result = {
                "ok": True,
                "version": __version__,
                "python": ".".join(map(str, sys.version_info[:3])),
                "credentials": {
                    "username": bool(os.getenv("COLLFACE_USERNAME")),
                    "password": bool(os.getenv("COLLFACE_PASSWORD")),
                },
                "network_checked": False,
            }
            if args.json:
                print(json.dumps(result, sort_keys=True))
            else:
                print("Local configuration checked; network and authentication were not attempted.")
            return 0
        if args.check_auth:
            from playwright.sync_api import sync_playwright

            from .auth import authenticate
            from .config import load_credentials

            credentials = load_credentials()
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=not args.allow_interactive)
                context = browser.new_context()
                try:
                    authenticate(
                        context.new_page(),
                        credentials,
                        allow_interactive=args.allow_interactive,
                    )
                finally:
                    context.close()
                    browser.close()
            print("Fresh CAS login verified against protected CollFace content.")
            return 0
        build_parser().print_help()
        return 0
    except CollFaceError as error:
        if args.json:
            print(json.dumps({"ok": False, "error": error.code, "message": str(error)}))
        else:
            print(f"{error.code}: {error}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except Exception:
        print("Unexpected failure; no sensitive browser details were printed.", file=sys.stderr)
        return 3

