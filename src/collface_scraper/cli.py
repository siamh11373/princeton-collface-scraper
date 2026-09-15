"""Command-line entry point. Features land in independently verified milestones."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from . import __version__
from .errors import AuthenticationError, CollFaceError


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
        help="Open installed Google Chrome and allow human MFA approval",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--site-contract", type=Path, default=Path("site-contract.json"))
    parser.add_argument("--limit", type=int, help="Collect at most this many profiles")
    parser.add_argument("--inspect", action="store_true", help="Run bounded attended inspection")
    parser.add_argument("--export-only", action="store_true", help="Rebuild CSVs from saved state")
    parser.add_argument(
        "--browser-export",
        type=Path,
        help="Process a temporary authenticated JSON response downloaded in normal Chrome",
    )
    return parser


def _print_result(args, result: dict) -> None:
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))


def _report_exit_code(report: dict) -> int:
    """Treat complete data from an explicitly attended run as command success."""

    non_auth_reasons = set(report.get("reasons", ())) - {"attended_authentication"}
    return 0 if not non_auth_reasons else 2


def _run(args) -> int:
    from .config import TARGET, load_credentials
    from .contract import load_contract
    from .export import export_run
    from .locking import run_lock
    from .state import RunStore

    run_dir = args.output_dir / ("sample" if args.limit is not None else "full")
    state_path = run_dir / "run.sqlite"
    if args.export_only:
        with run_lock(run_dir):
            store = RunStore(state_path)
            try:
                report = export_run(store, run_dir)
            finally:
                store.close()
        _print_result(args, report)
        return _report_exit_code(report)

    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be a positive integer")
    contract_bytes = args.site_contract.read_bytes()
    contract = load_contract(args.site_contract)
    if args.browser_export:
        from .browser_export import BrowserExportAdapter
        from .runner import collect

        run_dir = args.output_dir / (
            "attended-sample" if args.limit is not None else "attended-full"
        )
        state_path = run_dir / "run.sqlite"
        export_hash = hashlib.sha256(args.browser_export.read_bytes()).hexdigest()
        identity = {
            "target": TARGET,
            "account": "normal-chrome-attended",
            "scope": "all-visible-students",
            "limit": args.limit,
            "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            "browser_export_sha256": export_hash,
        }
        with run_lock(run_dir):
            store = RunStore(state_path, identity)
            try:
                collect(
                    BrowserExportAdapter(args.browser_export, contract), store, limit=args.limit
                )
                store.note("blocker", "attended_authentication")
                store.note("browser_export_sha256", export_hash)
                report = export_run(store, run_dir)
            finally:
                store.close()
        _print_result(args, report)
        return _report_exit_code(report)
    credentials = load_credentials(optional=args.allow_interactive)
    attended = args.allow_interactive
    if attended:
        print(
            "Opening a clean Google Chrome window. Complete Princeton login and Duo there; "
            "this command will continue automatically after CollFace loads.",
            file=sys.stderr,
        )
        run_dir = args.output_dir / (
            "attended-sample" if args.limit is not None else "attended-full"
        )
        state_path = run_dir / "run.sqlite"
    from playwright.sync_api import sync_playwright

    from .adapter import DomAdapter
    from .auth import authenticate
    from .browser_session import browser_context, context_page
    from .fetch import Pacer
    from .runner import collect
    from .search_adapter import SearchApiAdapter

    with sync_playwright() as playwright:
        with browser_context(playwright, interactive=args.allow_interactive) as context:
            page = context_page(context)
            authenticate(page, credentials, allow_interactive=args.allow_interactive)
            if credentials is None:
                # Manual credential entry leaves no plaintext username in the process. Hash the
                # already-verified protected surface for stable run separation without storing or
                # logging its account text. CollFace does not expose a reliable semantic <nav>.
                account_basis = " ".join(page.locator("body").inner_text(timeout=5_000).split())
                if not account_basis:
                    raise AuthenticationError(
                        "The authenticated CollFace account marker could not be derived."
                    )
                account_key = hashlib.sha256(account_basis.encode()).hexdigest()
            else:
                account_key = credentials.account_key
            identity = {
                "target": TARGET,
                "account": account_key,
                "scope": "all-visible-students",
                "limit": args.limit,
                "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
            }
            with run_lock(run_dir):
                store = RunStore(state_path, identity)
                try:
                    adapter_type = (
                        SearchApiAdapter if contract["mode"] == "search-api" else DomAdapter
                    )
                    collect(
                        adapter_type(
                            page,
                            contract,
                            pace=Pacer(1).wait,
                            renew=lambda: authenticate(
                                page,
                                credentials,
                                allow_interactive=args.allow_interactive,
                            ),
                        ),
                        store,
                        limit=args.limit,
                    )
                    if attended:
                        store.note("blocker", "attended_authentication")
                    report = export_run(store, run_dir)
                except CollFaceError as error:
                    store.note("blocker", error.code)
                    export_run(store, run_dir)
                    raise
                finally:
                    store.close()
    _print_result(args, report)
    return _report_exit_code(report)


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
            from .browser_session import browser_context, context_page
            from .config import load_credentials

            credentials = load_credentials(optional=args.allow_interactive)
            if args.allow_interactive:
                print(
                    "Opening a clean Google Chrome window. Complete Princeton login and Duo "
                    "there; this check will continue automatically after CollFace loads.",
                    file=sys.stderr,
                )
            with sync_playwright() as playwright:
                with browser_context(playwright, interactive=args.allow_interactive) as context:
                    authenticate(
                        context_page(context),
                        credentials,
                        allow_interactive=args.allow_interactive,
                    )
            print("Fresh CAS login verified against protected CollFace content.")
            return 0
        if args.inspect:
            from playwright.sync_api import sync_playwright

            from .auth import authenticate
            from .browser_session import browser_context, context_page
            from .config import load_credentials
            from .inspection import inspect_surface

            credentials = load_credentials(optional=args.allow_interactive)
            if args.allow_interactive:
                print(
                    "Opening a clean Google Chrome window. Complete Princeton login and Duo "
                    "there; inspection will continue automatically after CollFace loads.",
                    file=sys.stderr,
                )
            with sync_playwright() as playwright:
                with browser_context(playwright, interactive=args.allow_interactive) as context:
                    page = context_page(context)
                    authenticate(page, credentials, allow_interactive=args.allow_interactive)
                    result = inspect_surface(
                        page, args.output_dir / "inspection" / "site-observation.json"
                    )
                    if args.allow_interactive:
                        print(
                            "The authenticated browser will remain open for contract review. "
                            "Press Enter here when the review is finished."
                        )
                        input()
            _print_result(args, result)
            return 0
        return _run(args)
    except CollFaceError as error:
        if args.json:
            print(json.dumps({"ok": False, "error": error.code, "message": str(error)}))
        else:
            print(f"{error.code}: {error}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except (OSError, ValueError) as error:
        print(f"configuration_error: {error}", file=sys.stderr)
        return 3
    except Exception:
        print("Unexpected failure; no sensitive browser details were printed.", file=sys.stderr)
        return 3
