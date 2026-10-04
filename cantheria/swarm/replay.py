"""Keyless re-verification — the thesis made literal.

The LLM drafts probes; the corpus decides. Every verdict in an audit's
results.json is therefore re-checkable without any model: re-run the
committed probe (and its control) through the same oracle legs and the
verdict must reproduce. `replay` does exactly that; `slice_corpus` extracts
just the rows the probes and citations touch into a small db a reviewer
can replay against — no keys, no credits, no model.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from cantheria.swarm.corpus import COLS, FTS_SCHEMA, SCHEMA
from cantheria.swarm.oracle import LocalOracle
from cantheria.swarm.schemas import Claim, ClaimKind, Verdict


async def replay(
    result: dict[str, Any], db_path: Path | str
) -> tuple[list[Claim], list[tuple[Claim, str]]]:
    """Re-validate every claim deterministically.

    Returns (claims, mismatches): each claim carries its replayed verdict;
    mismatches pair the claim with its recorded verdict for the report.
    Claims recorded unverifiable with no executable probe aren't re-run —
    "no probe can decide this" is the verdict, not a measurement gap.
    """
    oracle = LocalOracle()
    claims: list[Claim] = []
    mismatches: list[tuple[Claim, str]] = []
    for raw in result.get("claims") or []:
        claim = Claim(**raw)
        recorded = claim.verdict
        has_probe = claim.probe is not None and bool(claim.probe.query.strip())
        if claim.kind is ClaimKind.interpretive:
            # deterministic quarantine — replayable by construction
            claim = await oracle.validate(claim, db_path)
        elif recorded is Verdict.unverifiable or not has_probe:
            # "no deciding probe exists" IS the verdict — a failed draft in
            # probe history isn't evidence the verdict rests on
            claim.verdict = Verdict.unverifiable
        else:
            claim = await oracle.validate(claim, db_path)
        if claim.verdict != recorded:
            mismatches.append((claim, recorded))
        claims.append(claim)
    return claims, mismatches


def _rid_col(cursor: sqlite3.Cursor) -> int:
    for i, d in enumerate(cursor.description or []):
        if (d[0] or "").lower() == "record_id":
            return i
    return 0


def slice_corpus(
    full_db: Path | str,
    result: dict[str, Any],
    out_db: Path | str,
) -> int:
    """Extract the rows a results.json's verdicts actually depend on —
    every probe's matched rows, every control's matches, every citation's
    resolution — into a standalone db (rowids preserved so probes return
    the identical row sets). FTS rebuilt so MATCH probes replay too."""
    src = sqlite3.connect(f"file:{full_db}?mode=ro", uri=True, timeout=30)
    rowids: set[int] = set()

    def add_rows(query: str) -> None:
        if not query or not query.strip().upper().startswith(("SELECT", "WITH")):
            return
        try:
            cur = src.execute(query)
        except sqlite3.Error:
            return
        idx = _rid_col(cur)
        for row in cur.fetchall():
            rid = src.execute(
                "SELECT rowid FROM records WHERE record_id = ?", (row[idx],)
            ).fetchone()
            if rid:
                rowids.add(rid[0])

    try:
        for raw in result.get("claims") or []:
            probe = raw.get("probe") or {}
            add_rows(str(probe.get("query") or ""))
            add_rows(str(probe.get("control") or ""))
            for p in raw.get("probes_run") or []:
                for rid in p.get("matched_ids") or []:
                    r = src.execute(
                        "SELECT rowid FROM records WHERE record_id = ?", (rid,)
                    ).fetchone()
                    if r:
                        rowids.add(r[0])
            for cite in raw.get("citations") or []:
                for r in src.execute(
                    "SELECT rowid FROM records WHERE record_id = ? OR content LIKE ? LIMIT 3",
                    (str(cite).strip(), f"%{str(cite).strip()[:200]}%"),
                ):
                    rowids.add(r[0])
    finally:
        src.close()

    out_db = Path(out_db)
    out_db.parent.mkdir(parents=True, exist_ok=True)
    dst = sqlite3.connect(out_db)
    try:
        dst.executescript(SCHEMA)
        if rowids:
            cols = ",".join(COLS)
            dst.execute("CREATE TEMP TABLE _ids(rowid INTEGER PRIMARY KEY)")
            dst.executemany("INSERT OR IGNORE INTO _ids VALUES(?)", [(i,) for i in sorted(rowids)])
            # attach-based copy keeps types + rowids intact
            dst.execute("ATTACH DATABASE ? AS src", (str(full_db),))
            dst.execute(
                f"INSERT INTO records(rowid, {cols})"  # noqa: S608 — fixed cols
                f" SELECT rowid, {cols} FROM src.records"
                " WHERE rowid IN (SELECT rowid FROM _ids)"
            )
        dst.commit()
        dst.executescript(FTS_SCHEMA)
        dst.execute("INSERT INTO records_fts(records_fts) VALUES('rebuild')")
        dst.commit()
        n = dst.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    finally:
        dst.close()
    return n
