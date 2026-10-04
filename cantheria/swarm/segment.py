"""Segmentation — cut the record into slices a hypothesis can be formed over.

Deliberately simple for now: agent-days (agent_id × UTC date), ordered by
record count descending so `--segments N` hunts the busiest slices first —
the same best-first discipline as the vuln pipeline's chunk ranking.
Threads and sliding windows are the obvious next cuts; the interface
(seg_id, agent, day, text) already carries what hunt needs.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Segment:
    seg_id: str
    agent_id: str
    day: str
    n_records: int
    text: str  # concatenated, capped — untrusted downstream, gets fenced


def agent_day_segments(
    db_path: Path | str,
    limit: int = 40,
    chars_per_segment: int = 9000,
    chars_per_record: int = 600,
) -> list[Segment]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
    try:
        days = conn.execute(
            "SELECT agent_id, substr(ts,1,10) d, COUNT(*) c FROM records "
            "WHERE agent_id IS NOT NULL AND ts IS NOT NULL "
            "GROUP BY agent_id, d ORDER BY c DESC LIMIT ?",
            (limit,),
        ).fetchall()
        out: list[Segment] = []
        for agent, day, count in days:
            rows = conn.execute(
                "SELECT record_id, kind, ts, content FROM records "
                "WHERE agent_id = ? AND substr(ts,1,10) = ? ORDER BY ts_unix",
                (agent, day),
            ).fetchall()
            blob, used = [], 0
            for rid, kind, ts, content in rows:
                piece = f"[{ts} {kind} {rid}] {str(content)[:chars_per_record]}"
                if used + len(piece) > chars_per_segment:
                    break
                blob.append(piece)
                used += len(piece)
            out.append(
                Segment(
                    seg_id=f"{agent}:{day}",
                    agent_id=agent,
                    day=day,
                    n_records=count,
                    text="\n".join(blob),
                )
            )
        return out
    finally:
        conn.close()
