"""The evidence oracle — turns a candidate Claim into confirmed or dismissed.

Four legs (see swarm/schemas.py):
    1. grounding: probe returns rows and any citations resolve to real
       record_ids,
    2. attribute: matched rows bind the claimed subjects and window,
    3. replicate: enforced by expect (distinct_field/min_distinct or
       corroborating kinds the drafter committed to),
    4. control:   the control probe must NOT satisfy expect — a probe that
       fires on a disjoint window is measuring noise, not the claim.

Legs are recorded in claim.raw["legs"] so the report can show *which* leg
killed a claim — the audit trail is the deliverable, not just the verdict.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Protocol

from cantheria.swarm.probe import run_probe
from cantheria.swarm.schemas import Claim, ClaimKind, ProbeResult, Verdict

REPRO_HINT: dict[ClaimKind, int] = {
    ClaimKind.pattern: 3,
    ClaimKind.coordination: 2,
}

# Subjects that name no one — "an agent", "they", "the swarm" — must not
# gate attribution: requiring a row to literally contain the word "agent"
# kills true claims on corpora where agents have opaque handles.
GENERIC_SUBJECTS = frozenset(
    {
        "agent",
        "agents",
        "an agent",
        "the agent",
        "the agents",
        "ai",
        "ais",
        "ai agent",
        "ai agents",
        "model",
        "models",
        "system",
        "systems",
        "swarm",
        "the swarm",
        "they",
        "them",
        "it",
        "one",
        "another agent",
        "someone",
    }
)


def meaningful_subjects(claim: Claim) -> list[str]:
    return [s for s in claim.subjects if s and s.strip().lower() not in GENERIC_SUBJECTS]


def _citations_resolve(db_path: Path | str, citations: list[str]) -> tuple[int, int]:
    """How many proposed citations point at real records. Citations may be
    record_ids or verbatim quotes — resolve either."""
    if not citations:
        return 0, 0
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
    found = 0
    try:
        for c in citations:
            c = c.strip()
            if not c:
                continue
            hit = conn.execute(
                "SELECT 1 FROM records WHERE record_id = ? OR content LIKE ? LIMIT 1",
                (c, f"%{c[:200]}%"),
            ).fetchone()
            if hit:
                found += 1
    finally:
        conn.close()
    return found, len(citations)


def _attribute(claim: Claim, result: ProbeResult) -> list[str]:
    """Leg 2: do matched rows belong to the claimed subjects and window?
    Checks the sampled rows — the receipts the probe already returned.
    A row binds a subject when the subject authored it OR the row's
    content names the subject — corroboration usually lives in other
    agents' records about them, not the subject's own."""
    fails: list[str] = []
    subjects = {s.lower() for s in meaningful_subjects(claim)}
    if subjects and result.sample:
        bound = {str(r.get("agent_id") or "").lower() for r in result.sample if r.get("agent_id")}
        if bound and not (subjects & bound):
            mentioned = any(
                any(s in str(r.get("content") or "").lower() for s in subjects)
                for r in result.sample
            )
            if not mentioned:
                fails.append(
                    f"no matched row names a claimed subject {sorted(subjects)}"
                    " (by author or by content)"
                )
    win = claim.window or {}
    lo, hi = win.get("start"), win.get("end")
    if (lo or hi) and result.sample:
        in_window = 0
        for r in result.sample:
            ts = str(r.get("ts") or r.get("ts_unix") or "")
            if (not lo or ts >= str(lo)) and (not hi or ts <= str(hi)):
                in_window += 1
        if in_window == 0:
            fails.append(f"no matched row inside claimed window {lo}..{hi}")
    return fails


class EvidenceOracle(Protocol):
    async def validate(self, claim: Claim, db_path: Path | str) -> Claim: ...


class LocalOracle:
    """Runs probes synchronously — sqlite is local, the I/O is the model's."""

    async def validate(self, claim: Claim, db_path: Path | str) -> Claim:
        if claim.kind is ClaimKind.interpretive:
            claim.verdict = Verdict.unverifiable
            return claim
        if claim.probe is None or not claim.probe.query.strip():
            claim.verdict = Verdict.dismissed
            claim.raw["dismiss_reason"] = "no executable probe"
            return claim

        legs: dict[str, str] = {}
        result = run_probe(db_path, claim.probe)
        claim.probes_run.append(result)
        if result.error:
            # a failed draft, not a verdict — the repair loop's business
            claim.verdict = Verdict.candidate
            claim.raw["dismiss_reason"] = f"probe error: {result.error}"
            return claim

        # Leg 1 — grounding
        if result.rows == 0:
            legs["grounding"] = "; ".join(result.leg_failures) or "0 rows"
            claim.verdict = Verdict.dismissed
            claim.raw["legs"] = legs
            claim.raw["dismiss_reason"] = "record contains no evidence for the claim"
            return claim
        if not result.ok:
            # rows exist but fail the drafter's own committed test — the
            # evidence contradicts the claim as specified, not "missing"
            legs["expect"] = "; ".join(result.leg_failures)
            claim.verdict = Verdict.dismissed
            claim.raw["legs"] = legs
            claim.raw["dismiss_reason"] = (
                "evidence found but fails the probe's committed expectations"
            )
            return claim
        found, total = _citations_resolve(db_path, claim.citations)
        if claim.citations and found == 0:
            legs["grounding"] = f"0/{total} citations resolve to records"
            claim.verdict = Verdict.dismissed
            claim.raw["legs"] = legs
            claim.raw["dismiss_reason"] = "cited evidence does not exist in the record"
            return claim
        legs["grounding"] = f"ok — {result.rows} rows" + (
            f", {found}/{total} citations resolve" if claim.citations else ""
        )

        # Leg 2 — attribute
        if fails := _attribute(claim, result):
            legs["attribute"] = "; ".join(fails)
            claim.verdict = Verdict.dismissed
            claim.raw["legs"] = legs
            claim.raw["dismiss_reason"] = "evidence does not bind the claimed subject/window"
            return claim
        legs["attribute"] = "ok"

        # Leg 3 — replicate (encoded in expect by the drafter; recorded here)
        need = REPRO_HINT.get(claim.kind)
        if need and result.rows < need:
            legs["replicate"] = f"{result.rows} independent matches < {need}"
            claim.verdict = Verdict.flaky
            claim.raw["legs"] = legs
            claim.raw["dismiss_reason"] = "pattern too thin to call"
            return claim
        legs["replicate"] = "ok"

        # Leg 4 — control
        if claim.probe.control.strip():
            control = run_probe(db_path, claim.probe.control, expect=claim.probe.expect)
            claim.probes_run.append(control)
            if control.ok:
                legs["control"] = "control matched — probe discriminates nothing"
                claim.verdict = Verdict.dismissed
                claim.raw["legs"] = legs
                claim.raw["dismiss_reason"] = "control window shows the same pattern"
                return claim
            legs["control"] = "ok — control window clean"
        else:
            legs["control"] = "not run — no control drafted"

        claim.raw["legs"] = legs
        claim.verdict = Verdict.confirmed
        return claim


def make_oracle() -> EvidenceOracle:
    return LocalOracle()
