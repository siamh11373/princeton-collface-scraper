"""Command-line entry point. Features land in independently verified milestones."""

import argparse
import json
import os
import sys

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="collface-scraper",
        description="Authorized, resumable Princeton CollFace directory export",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    parser.add_argument("--doctor", action="store_true", help="Check local configuration")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
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
    build_parser().print_help()
    return 0

