"""Atomic, round-trip-validated CSV and completion reports."""

import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path

from .fields import csv_text, sheets_safe
from .state import RunStore, utc_now


def _write_csv(store: RunStore, destination: Path, *, safe: bool) -> dict:
    records = list(store.records())
    keys = sorted(
        {key for _, _, fields in records for key in fields}, key=lambda value: value.casefold()
    )
    headers = ["profile_id", "profile_url", *keys]
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".profiles-", suffix=".tmp", dir=destination.parent)
    render = sheets_safe if safe else csv_text
    sensitive_cells = 0
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            for source_id, url, fields in records:
                raw = [source_id, url, *(fields.get(key) for key in keys)]
                rendered = [render(value) for value in raw]
                sensitive_cells += sum(
                    safe and rendered_value.startswith("'") for rendered_value in rendered
                )
                writer.writerow(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        with open(temporary, encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            if next(reader) != headers:
                raise ValueError("CSV header validation failed.")
            for source_id, url, fields in records:
                expected = [
                    render(source_id),
                    render(url),
                    *(render(fields.get(key)) for key in keys),
                ]
                if next(reader, None) != expected:
                    raise ValueError("CSV record round-trip validation failed.")
            if next(reader, None) is not None:
                raise ValueError("CSV contains unexpected extra rows.")
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    return {
        "file": destination.name,
        "rows": len(records),
        "columns": len(headers),
        "sha256": digest,
        "roundtrip_verified": True,
        "spreadsheet_sensitive_cells": sensitive_cells,
        "sheet_cells_required": (len(records) + 1) * len(headers),
        "fits_google_sheets_10m_cells": (len(records) + 1) * len(headers) <= 10_000_000,
    }


def export_run(store: RunStore, directory: Path) -> dict:
    raw = _write_csv(store, directory / "profiles.raw.csv", safe=False)
    display = _write_csv(store, directory / "profiles.csv", safe=True)
    reasons = []
    identity = store.get("identity")
    if identity["limit"] is not None:
        reasons.append("limited_run")
    for phase in ("discovery", "reconciliation"):
        if not store.checkpoint(phase)["done"]:
            reasons.append(f"{phase}_unfinished")
        if not store.get(f"exhaustive:{phase}", False):
            reasons.append(f"{phase}_coverage_unproven")
        total = store.get(f"total:{phase}")
        if total is not None and total != store.membership_count(phase):
            reasons.append(f"{phase}_count_mismatch")
    if store.membership_changed():
        reasons.append("source_membership_changed")
    counts = store.counts()
    if counts["pending"] or counts["failed"]:
        reasons.append("unresolved_profiles")
    if not counts["discovered"]:
        reasons.append("empty_population")
    if not store.get("field_fidelity_verified", False):
        reasons.append("field_fidelity_unverified")
    if store.get("blocker"):
        reasons.append(store.get("blocker"))
    report = {
        **display,
        "raw_export": raw,
        "status": "complete" if not reasons else "partial",
        "reasons": sorted(set(reasons)),
        "counts": counts,
        "scope": identity["scope"],
        "started_at": store.get("started_at"),
        "exported_at": utc_now(),
        "audited_profiles": store.get("audit_count", 0),
        "benchmark": store.get("benchmark"),
        "snapshot_semantics": "collection_window_not_atomic_source_snapshot",
        "google_sheet_verified": bool(store.get("google_sheet_verified", False)),
    }
    fd, temporary = tempfile.mkstemp(prefix=".report-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, directory / "report.json")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return report
