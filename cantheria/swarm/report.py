"""Investigator-facing audit report — markdown with evidence receipts.

Reads an audit/hunt results.json (claims as plain dicts) and renders:
  - verdict distribution + slop rate
  - confirmed claims with receipts (record ids → deep links via the corpus)
  - dismissed claims with the mechanical reason
  - unverifiable quarantine + flaky backend notes

The report's contract: every confirmed claim lists the record ids its probe
matched, and — when the corpus db is available — each resolves to the
source_uri deep link so a reviewer can open the original record directly.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any


def _receipts(claim: dict, db_path: Path | str | None) -> list[str]:
    """record ids the winning probe matched, enriched with deep links."""
    ids: list[str] = []
    for r in claim.get("probes_run") or []:
        ids.extend(r.get("matched_ids") or [])
    ids = list(dict.fromkeys(ids))[:12]
    if not ids:
        return []
    links: dict[str, str] = {}
    if db_path:
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
            try:
                for rid in ids:
                    row = conn.execute(
                        "SELECT source_uri FROM records WHERE record_id = ?",
                        (rid,),
                    ).fetchone()
                    if row and row[0]:
                        links[rid] = row[0]
            finally:
                conn.close()
        except sqlite3.Error:
            pass
    return [f"`{rid}`" + (f" — {links[rid]}" if rid in links else "") for rid in ids]


def _section(title: str, lines: list[str]) -> str:
    return f"## {title}\n\n" + "\n".join(lines) + "\n" if lines else ""


def _claim_lines(c: dict, db_path: Path | str | None) -> list[str]:
    raw = c.get("raw") or {}
    lines = [f"### {c.get('text', '(no text)')}\n"]
    meta = [
        f"- id `{c.get('id')}` — kind `{c.get('kind')}` — source `{c.get('source_doc')}`",
        f"- probe origin: `{raw.get('probe_origin', 'model')}`"
        + (f", attempt {raw['probe_attempt']}" if raw.get("probe_attempt") else ""),
    ]
    legs = raw.get("legs") or {}
    if legs:
        meta.append("- legs: " + " · ".join(f"**{k}** {v}" for k, v in legs.items()))
    lines.extend(meta)
    if c.get("verdict") == "confirmed":
        receipts = _receipts(c, db_path)
        if receipts:
            lines.append("- receipts:")
            lines.extend(f"  - {r}" for r in receipts)
    reason = raw.get("dismiss_reason") or raw.get("note") or raw.get("backend_error")
    if reason:
        lines.append(f"- reason: {reason}")
    hist = raw.get("probe_history") or []
    if hist:
        lines.append(f"- probe attempts logged: {len(hist)} (see journal.jsonl)")
    lines.append("")
    return lines


def write_audit_report(
    result: dict[str, Any],
    out_path: Path,
    db_path: Path | str | None = None,
) -> Path:
    claims: list[dict] = result.get("claims") or []
    verdicts = Counter(c.get("verdict") for c in claims)
    decided = verdicts.get("confirmed", 0) + verdicts.get("dismissed", 0)
    slop = verdicts.get("dismissed", 0) / decided if decided else 0.0

    parts = [
        "# Swarm audit report\n",
        f"**Corpus:** `{result.get('corpus', '?')}`  ",
        (
            f"**Claims:** {len(claims)} — "
            + ", ".join(f"{k} {v}" for k, v in sorted(verdicts.items()))
        ),
        "",
        f"**Decided:** {decided}  **Slop rate:** {slop:.0%} "
        "(dismissed / decided — claims the record could not support)",
        "",
        (
            f"**Cost:** {result.get('llm_calls', '?')} model calls, "
            f"{result.get('probe_runs', '?')} probe executions"
        ),
        "",
        (
            "> An LLM proposes; the record decides. `unverifiable` claims were "
            "quarantined — they assert something no mechanical probe can check. "
            "`confirmed` claims carry receipts; every row below resolves to a "
            "record in the corpus."
        ),
        "",
    ]

    by_verdict: dict[str, list[dict]] = {}
    for c in claims:
        by_verdict.setdefault(c.get("verdict", "?"), []).append(c)

    for verdict, title in (
        ("confirmed", "Confirmed — record-backed"),
        ("dismissed", "Dismissed — record contradicts or lacks support"),
        ("flaky", "Flaky — probe/backend failures, retest"),
        ("unverifiable", "Unverifiable — quarantined by construction"),
    ):
        items = by_verdict.get(verdict) or []
        if not items:
            continue
        lines: list[str] = []
        for c in items:
            lines.extend(_claim_lines(c, db_path))
        parts.append(_section(f"{title} ({len(items)})", lines))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts))
    return out_path
