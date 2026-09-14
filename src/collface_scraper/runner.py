"""Exhaustive discovery, collection, and reconciliation orchestration."""

import time
from typing import Protocol

from .errors import AccessBlocked, AuthenticationError, ExtractionError, FetchError
from .fields import validate_fields
from .models import Fields, ListingPage, ProfileRef
from .state import RunStore


class Adapter(Protocol):
    def list_page(self, cursor: str | None) -> ListingPage: ...

    def profile(self, ref: ProfileRef) -> Fields: ...

    def audit(self, ref: ProfileRef, fields: Fields) -> bool: ...


def collect(adapter: Adapter, store: RunStore, *, limit: int | None = None, progress=print) -> None:
    store.note("blocker", None)
    store.retry_failures()
    started = time.monotonic()
    completed_at_start = store.counts()["complete"]

    def process_pending() -> None:
        for ref in store.pending():
            counts = store.counts()
            if limit is not None and counts["complete"] >= limit:
                return
            store.attempt(ref.source_id)
            try:
                fields = validate_fields(adapter.profile(ref))
                audit_count = store.get("audit_count", 0)
                if audit_count < 3 or counts["complete"] % 500 == 0:
                    if not adapter.audit(ref, fields):
                        raise ExtractionError("Browser field-fidelity audit failed.")
                    store.note("audit_count", audit_count + 1)
                store.complete(ref.source_id, fields)
            except (AuthenticationError, AccessBlocked):
                raise
            except (FetchError, ExtractionError) as error:
                store.fail(ref.source_id, error.code)
            counts = store.counts()
            if counts["complete"] <= 25 or counts["complete"] % 100 == 0 or counts["failed"]:
                elapsed = max(time.monotonic() - started, 0.001)
                rate = (counts["complete"] - completed_at_start) / elapsed
                progress(
                    f"Discovered {counts['discovered']}; completed {counts['complete']}; "
                    f"failed {counts['failed']}; {rate:.2f} profiles/s"
                )

    phases = ("discovery", "reconciliation")
    for phase in phases:
        if limit is not None and store.counts()["complete"] >= limit:
            break
        while not store.checkpoint(phase)["done"]:
            checkpoint = store.checkpoint(phase)
            page = adapter.list_page(checkpoint["cursor"])
            store.save_page(phase, checkpoint["cursor"], page)
            if limit is not None:
                process_pending()
                if store.counts()["complete"] >= limit:
                    break
        if limit is None:
            process_pending()
    process_pending()
    store.note(
        "benchmark",
        {
            "new_profiles": store.counts()["complete"] - completed_at_start,
            "elapsed_seconds": time.monotonic() - started,
        },
    )
    store.note("field_fidelity_verified", store.get("audit_count", 0) >= 3)
