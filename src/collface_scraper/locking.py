"""One writer per run directory."""

import fcntl
from contextlib import contextmanager
from pathlib import Path

from .errors import AccessBlocked


@contextmanager
def run_lock(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ".run.lock"
    with path.open("w") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise AccessBlocked("Another process is already writing this run.") from None
        yield
