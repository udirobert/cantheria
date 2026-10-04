"""The record — one normalized table every source lands in.

sqlite, zero deps: probes are SELECT-only SQL over `records`, so the corpus
*is* the sandbox. Ingestion is defensive — gated datasets aren't visible
ahead of access, so loaders pick fields by name and keep the raw row.

The `source_uri` column is the receipt: anything a report cites should
link back to where a human can look at the same record.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS records(
  record_id  TEXT PRIMARY KEY,
  corpus     TEXT NOT NULL,
  ts         TEXT,
  ts_unix    REAL,
  agent_id   TEXT,
  thread     TEXT,
  kind       TEXT NOT NULL,
  content    TEXT,
  parent_id  TEXT,
  source_uri TEXT,
  raw        TEXT
);
CREATE INDEX IF NOT EXISTS idx_records_kind  ON records(kind);
CREATE INDEX IF NOT EXISTS idx_records_agent ON records(agent_id);
CREATE INDEX IF NOT EXISTS idx_records_ts    ON records(ts_unix);
CREATE INDEX IF NOT EXISTS idx_records_corpus_kind ON records(corpus, kind);
"""

# External-content FTS5: indexes records.content + records.thread without
# duplicating the text (the corpus table owns the bytes; the fts table owns
# only the index). thread is indexed because record *names* — wiki page
# titles, room names — carry evidence the body never repeats.
FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS records_fts
USING fts5(content, thread, content='records', content_rowid='rowid');
"""

COLS = (
    "record_id",
    "corpus",
    "ts",
    "ts_unix",
    "agent_id",
    "thread",
    "kind",
    "content",
    "parent_id",
    "source_uri",
    "raw",
)


def ts_unix(ts: str | None) -> float | None:
    """ISO → epoch seconds. Tolerates 'Z' and naive strings; None if unparseable."""
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.timestamp()


def record_id(corpus: str, row: dict[str, Any], content: str) -> str:
    """Stable id: source-native when present, else content hash."""
    for key in (
        "id",
        "record_id",
        "message_id",
        "turn_id",
        "event_id",
        "rev_id",
        "paste_id",
        "uuid",
    ):
        if row.get(key):
            return f"{corpus}:{row[key]}"
    blob = f"{corpus}|{row.get('created_at') or row.get('timestamp')}|{content[:200]}"
    return f"{corpus}:h{hashlib.sha1(blob.encode(), usedforsecurity=False).hexdigest()[:16]}"


class Corpus:
    """A sqlite record store. Open with `Corpus(path)`; insert dicts shaped
    like COLS; probes run against `db_path` in read-only mode."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def insert(self, rows: Iterable[dict[str, Any]], batch_size: int = 2000) -> int:
        """Stream inserts in batches — corpus tables run to hundreds of
        thousands of rows, materializing them all is how you swap to death."""
        cols = ",".join(COLS)
        placeholders = ",".join("?" * len(COLS))
        sql = f"INSERT OR IGNORE INTO records({cols}) VALUES({placeholders})"
        total, batch = 0, []
        for row in rows:
            raw = dict(row.get("raw") or row)
            batch.append(
                tuple(row.get(c) if c != "raw" else json.dumps(raw, default=str) for c in COLS)
            )
            if len(batch) >= batch_size:
                with self._conn:
                    total += self._conn.executemany(sql, batch).rowcount
                batch = []
        if batch:
            with self._conn:
                total += self._conn.executemany(sql, batch).rowcount
        return total

    def build_fts(self) -> None:
        """Build/rebuild the content FTS index after ingest. Index-only —
        no text duplication, but a one-time scan of the corpus."""
        with self._conn:
            self._conn.executescript(FTS_SCHEMA)
            self._conn.execute("INSERT INTO records_fts(records_fts) VALUES('rebuild')")

    def topup_fts(self, where: str = "kind = 'turn'") -> int:
        """Index rows added after the initial build without rescanning the
        whole corpus — external-content FTS supports row-level inserts."""
        with self._conn:
            self._conn.executescript(FTS_SCHEMA)
            cur = self._conn.execute(
                "INSERT INTO records_fts(rowid, content, thread)"  # noqa: S608 — clause arg is internal
                f" SELECT rowid, content, thread FROM records WHERE {where}"
            )
            return cur.rowcount

    def stats(self) -> dict[str, Any]:
        cur = self._conn.execute(
            "SELECT corpus, kind, COUNT(*) FROM records GROUP BY corpus, kind ORDER BY 1, 3 DESC"
        )
        by: dict[str, dict[str, int]] = {}
        for corpus, kind, n in cur.fetchall():
            by.setdefault(corpus, {})[kind] = n
        total = self._conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        span = self._conn.execute(
            "SELECT MIN(ts_unix), MAX(ts_unix) FROM records WHERE ts_unix IS NOT NULL"
        ).fetchone()
        return {
            "total": total,
            "by_corpus": by,
            "span": [datetime.fromtimestamp(t, UTC).isoformat() if t else None for t in span],
        }

    def agents(self) -> list[str]:
        cur = self._conn.execute(
            "SELECT DISTINCT agent_id FROM records WHERE agent_id IS NOT NULL ORDER BY 1"
        )
        return [r[0] for r in cur.fetchall()]

    def close(self) -> None:
        self._conn.close()
