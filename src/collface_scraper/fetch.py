"""Global pacing and bounded retry helpers."""

import email.utils
import random
import time
from datetime import UTC, datetime


class Pacer:
    def __init__(self, requests_per_second: float = 1.0, *, clock=time.monotonic, sleep=time.sleep):
        if requests_per_second <= 0:
            raise ValueError("Request rate must be positive.")
        self.interval = 1.0 / requests_per_second
        self.clock = clock
        self.sleep = sleep
        self.next_start = 0.0

    def wait(self) -> None:
        now = self.clock()
        if now < self.next_start:
            self.sleep(self.next_start - now)
            now = self.clock()
        self.next_start = max(self.next_start, now) + self.interval


def retry_after(value: str | None, *, now: datetime | None = None) -> float | None:
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return max(0.0, (parsed - (now or datetime.now(UTC))).total_seconds())


def backoff(attempt: int) -> float:
    return min(30.0, 2**attempt + random.random())
