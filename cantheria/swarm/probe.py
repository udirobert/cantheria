"""Probe executor — the record-domain sandbox.

A probe is SELECT-only SQL over `records`, run on a read-only handle with a
row cap and a step budget. No seatbelt needed: `mode=ro` + `PRAGMA
query_only` means the probe structurally cannot write — the worst it does is
return nothing, which is itself a verdict.

`expect` is evaluated mechanically (see schemas.Probe). A probe that
errors or violates SELECT-only is a failed *draft* — fed back to the
drafter for repair, never a verdict on the claim.
"""

from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from cantheria.swarm.schemas import Probe, ProbeResult

ROW_CAP = 50
SAMPLE_ROWS = 5
STEP_BUDGET = 400_000
WALL_S_CAP = 15.0

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|attach|detach|pragma|vacuum|create|"
    r"replace|truncate|grant|revoke|reindex|analyze|savepoint|release|begin|"
    r"commit|rollback)\b",
    re.IGNORECASE,
)
_SELECT_HEAD = re.compile(
    r"^\s*(?:--[^\n]*\n|/\*.*?\*/|\s)*(select|with)\b", re.IGNORECASE | re.DOTALL
)


def _refuse(query: str) -> str:
    if not _SELECT_HEAD.search(query):
        return "not a SELECT/WITH statement"
    if ";" in query.strip().rstrip(";"):
        return "multiple statements"
    m = _FORBIDDEN.search(query)
    if m:
        return f"forbidden keyword: {m.group(1)}"
    return ""


def _eval_expect(rows: list[dict[str, Any]], expect: dict[str, Any]) -> tuple[bool, list[str]]:
    fails: list[str] = []
    n = len(rows)
    if "min_rows" in expect and n < int(expect["min_rows"]):
        fails.append(f"rows {n} < min_rows {expect['min_rows']}")
    if "max_rows" in expect and n > int(expect["max_rows"]):
        fails.append(f"rows {n} > max_rows {expect['max_rows']}")
    if not expect.get("max_rows") and n == 0:
        fails.append("0 rows — no evidence")
    blob = "\n".join(str(v) for r in rows for v in r.values()).lower()
    for needle in expect.get("must_contain", []) or []:
        if str(needle).lower() not in blob:
            fails.append(f"must_contain missing: {str(needle)[:60]}")
    for needle in expect.get("must_not", []) or []:
        if str(needle).lower() in blob:
            fails.append(f"must_not present: {str(needle)[:60]}")
    field = expect.get("distinct_field")
    if field:
        distinct = {str(r.get(field)) for r in rows if r.get(field) is not None}
        need = int(expect.get("min_distinct", 2))
        if len(distinct) < need:
            fails.append(f"distinct({field})={len(distinct)} < {need}")
    return not fails, fails


def run_probe(
    db_path: Path | str,
    probe: Probe | str,
    expect: dict[str, Any] | None = None,
    row_cap: int = ROW_CAP,
    step_budget: int = STEP_BUDGET,
    wall_s_cap: float = WALL_S_CAP,
) -> ProbeResult:
    """Execute one probe against the corpus. Never throws for a bad query —
    a refused/errored probe returns error= so the drafter can repair.
    `expect` overrides probe.expect — the control leg runs the control query
    against the *claim's* expect, not its own."""
    query = probe.query if isinstance(probe, Probe) else str(probe)
    if expect is None:
        expect = probe.expect if isinstance(probe, Probe) else {}
    t0 = time.monotonic()

    if why := _refuse(query):
        return ProbeResult(error=why, detail="probe refused before execution")

    steps = [0]

    def watchdog() -> int:
        steps[0] += 1
        return 1 if steps[0] > step_budget or time.monotonic() - t0 > wall_s_cap else 0

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
        conn.execute("PRAGMA query_only = ON")
        conn.row_factory = sqlite3.Row
        conn.set_progress_handler(watchdog, 1000)
        try:
            cur = conn.execute(query)
            names = [d[0] for d in cur.description or []]
            rows = [dict(zip(names, r, strict=True)) for r in cur.fetchmany(row_cap + 1)]
            truncated = len(rows) > row_cap
            rows = rows[:row_cap]
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return ProbeResult(error=f"sqlite: {exc}", wall_s=time.monotonic() - t0)
    except sqlite3.OperationalError as exc:  # step/wall watchdog interrupt
        return ProbeResult(error=f"budget: {exc}", wall_s=time.monotonic() - t0)

    ok, fails = _eval_expect(rows, expect)
    matched = [str(r["record_id"]) for r in rows if r.get("record_id")]
    detail = ""
    if truncated:
        detail = f"capped at {row_cap} rows"
    supportive = expect.get("supportive") or []
    if supportive and rows:
        blob = "\n".join(str(v) for r in rows for v in r.values()).lower()
        hit = [n for n in supportive if str(n).lower() in blob]
        detail = (detail + " | " if detail else "") + (
            f"supportive needles hit {len(hit)}/{len(supportive)}"
        )
    return ProbeResult(
        ok=ok,
        rows=len(rows),
        matched_ids=matched,
        sample=[{k: str(v)[:300] for k, v in r.items()} for r in rows[:SAMPLE_ROWS]],
        leg_failures=fails,
        detail=detail,
        wall_s=time.monotonic() - t0,
    )
