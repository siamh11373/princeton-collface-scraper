"""Transactional, resumable collection state."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from .errors import DiscoveryError, StateMismatch
from .models import Fields, ListingPage, ProfileRef


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class RunStore:
    def __init__(self, path: Path, identity: dict | None = None):
        if identity is None and not path.is_file():
            raise StateMismatch("No saved run exists at this path.")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.db = sqlite3.connect(path, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata(
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS profiles(
                source_id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                fields TEXT,
                error_code TEXT,
                fetched_at TEXT
            );
            CREATE TABLE IF NOT EXISTS page_visits(
                phase TEXT NOT NULL,
                cursor TEXT NOT NULL,
                next_cursor TEXT,
                PRIMARY KEY(phase, cursor)
            );
            CREATE TABLE IF NOT EXISTS membership(
                phase TEXT NOT NULL,
                source_id TEXT NOT NULL REFERENCES profiles(source_id),
                PRIMARY KEY(phase, source_id)
            );
            CREATE INDEX IF NOT EXISTS profiles_status_id
            ON profiles(status, source_id);
            """
        )
        saved = self.get("identity")
        expected = {**identity, "schema": 1} if identity is not None else None
        if saved is None:
            if expected is None:
                self.close()
                raise StateMismatch("Saved run has no identity.")
            with self.db:
                self._set("identity", expected)
                self._set("started_at", utc_now())
        elif expected is not None and saved != expected:
            self.close()
            raise StateMismatch("Saved state belongs to another account, contract, or scope.")
        elif saved.get("schema") != 1:
            self.close()
            raise StateMismatch("Unsupported run-state schema.")

    def close(self) -> None:
        self.db.close()

    def get(self, key: str, default=None):
        row = self.db.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def _set(self, key: str, value) -> None:
        self.db.execute(
            """INSERT INTO metadata(key, value) VALUES(?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
            (key, json.dumps(value, ensure_ascii=False, allow_nan=False)),
        )

    def note(self, key: str, value) -> None:
        with self.db:
            self._set(key, value)

    def checkpoint(self, phase: str) -> dict:
        return self.get(f"checkpoint:{phase}", {"cursor": None, "done": False})

    def save_page(self, phase: str, requested_cursor: str | None, page: ListingPage) -> None:
        token = json.dumps(requested_cursor)
        if self.db.execute(
            "SELECT 1 FROM page_visits WHERE phase=? AND cursor=?", (phase, token)
        ).fetchone():
            raise DiscoveryError("Discovery repeated a committed page cursor.")
        next_token = json.dumps(page.next_cursor) if page.next_cursor is not None else None
        if next_token == token:
            raise DiscoveryError("Discovery returned a self-repeating cursor.")
        refs = {ref.source_id: ref for ref in page.profiles}
        if len(refs) != len(page.profiles) or any(not key for key in refs):
            raise DiscoveryError("Discovery returned duplicate or empty stable IDs.")

        with self.db:
            prior_total = self.get(f"total:{phase}")
            if page.total is not None and prior_total not in (None, page.total):
                raise DiscoveryError("The directory total changed within one discovery pass.")
            if page.total is not None:
                self._set(f"total:{phase}", page.total)
            self._set(f"exhaustive:{phase}", page.exhaustive)
            for ref in refs.values():
                self.db.execute(
                    """INSERT INTO profiles(source_id, url) VALUES(?, ?)
                    ON CONFLICT(source_id) DO UPDATE SET url=excluded.url""",
                    (ref.source_id, ref.url),
                )
                self.db.execute(
                    "INSERT OR IGNORE INTO membership(phase, source_id) VALUES(?, ?)",
                    (phase, ref.source_id),
                )
            self.db.execute(
                "INSERT INTO page_visits(phase, cursor, next_cursor) VALUES(?, ?, ?)",
                (phase, token, next_token),
            )
            self._set(
                f"checkpoint:{phase}",
                {"cursor": page.next_cursor, "done": page.next_cursor is None},
            )

    def retry_failures(self) -> None:
        with self.db:
            self.db.execute(
                "UPDATE profiles SET status='pending', error_code=NULL WHERE status='failed'"
            )

    def pending(self) -> list[ProfileRef]:
        rows = self.db.execute(
            "SELECT source_id, url FROM profiles WHERE status='pending' ORDER BY source_id"
        )
        return [ProfileRef(row["source_id"], row["url"]) for row in rows]

    def attempt(self, source_id: str) -> None:
        with self.db:
            self.db.execute(
                "UPDATE profiles SET attempts=attempts+1 WHERE source_id=?", (source_id,)
            )

    def complete(self, source_id: str, fields: Fields) -> None:
        encoded = json.dumps(fields, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        with self.db:
            self.db.execute(
                """UPDATE profiles SET status='complete', fields=?, error_code=NULL, fetched_at=?
                WHERE source_id=?""",
                (encoded, utc_now(), source_id),
            )

    def fail(self, source_id: str, code: str) -> None:
        with self.db:
            self.db.execute(
                "UPDATE profiles SET status='failed', fields=NULL, error_code=? WHERE source_id=?",
                (code, source_id),
            )

    def counts(self) -> dict[str, int]:
        result = {"discovered": 0, "pending": 0, "complete": 0, "failed": 0}
        status_counts = self.db.execute(
            "SELECT status, COUNT(*) AS count FROM profiles GROUP BY status"
        )
        for row in status_counts:
            result[row["status"]] = row["count"]
            result["discovered"] += row["count"]
        return result

    def records(self):
        rows = self.db.execute(
            """SELECT source_id, url, fields FROM profiles
            WHERE status='complete' ORDER BY source_id"""
        )
        for row in rows:
            yield row["source_id"], row["url"], json.loads(row["fields"])

    def membership_count(self, phase: str) -> int:
        row = self.db.execute(
            "SELECT COUNT(*) AS count FROM membership WHERE phase=?", (phase,)
        ).fetchone()
        return row["count"]

    def membership_changed(self) -> bool:
        first = {
            row[0]
            for row in self.db.execute("SELECT source_id FROM membership WHERE phase='discovery'")
        }
        second = {
            row[0]
            for row in self.db.execute(
                "SELECT source_id FROM membership WHERE phase='reconciliation'"
            )
        }
        return first != second
