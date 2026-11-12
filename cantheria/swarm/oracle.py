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
from cantheria.swarm.schemas import (
    Claim,
    ClaimKind,
    ProbeResult,
    Verdict,
)
from cantheria.swarm.schemas import (
    claim_action_verb as _claim_verb,
)

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


# Verbs whose action must be VISIBLE in the matched rows. Only verbs
# that change a thing are binding: "edited", "created", "reverted" leave a
# record of themselves. Verbs like "reviewed" or "reported" do not — the
# record may carry the object without ever using the verb — so they are
# not binding and are left to the probe's own expectations.
_BINDING_VERBS = frozenset(
    {
        "edit",
        "creat",
        "delet",
        "modif",
        "renam",
        "mov",
        "writ",
        "add",
        "remov",
        "updat",
        "chang",
        "revert",
        "apply",
        "commit",
        "merge",
        "install",
        "refactor",
        "implement",
        "push",
    }
)

# Inflections the record may use for a stem, so "edited"/"edits"/"editing"
# all satisfy the verb "edit".
_VERB_FORMS = {
    "edit": ("edit", "edited", "edits", "editing", "patch", "patched", "patching"),
    "creat": ("creat", "created", "creates", "creating", "made", "add"),
    "delet": ("delet", "deleted", "deletes", "deleting", "removed", "rm"),
    "modif": ("modif", "modified", "modifies", "modifying", "chang"),
    "renam": ("renam", "renamed", "renames", "renaming", "mov"),
    "mov": ("mov", "moved", "moves", "moving", "renam"),
    "writ": ("writ", "wrote", "written", "writing", "wrote"),
    "add": ("add", "added", "adds", "adding", "insert"),
    "remov": ("remov", "removed", "removes", "removing", "delet"),
    "updat": ("updat", "updated", "updates", "updating", "chang"),
    "chang": ("chang", "changed", "changes", "changing", "updat", "modif"),
    "revert": ("revert", "reverted", "reverts", "reverting", "undo", "undid", "revert"),
    "apply": ("appl", "apply", "applied", "applies", "applying"),
    "commit": ("commit", "committed", "commits", "committing"),
    "merge": ("merg", "merge", "merged", "merges", "merging"),
    "install": ("install", "installed", "installs", "installing"),
    "refactor": ("refactor", "refactored", "refactors", "refactoring"),
    "implement": ("implement", "implemented", "implements", "implementing"),
    "push": ("push", "pushed", "pushes", "pushing"),
}


# Verbs that are GENERIC file-work: "edited", "modified", "changed" all
# name the same act, and a corpus that records edits under a kind like
# file_edit has already recorded the act. For these, a matched action row
# of the right class is evidence, even when the row does not repeat the
# claim's word.
_GENERIC_VERBS = frozenset(
    {
        "edit",
        "modif",
        "chang",
        "updat",
        "fix",
        "add",
        "writ",
        "creat",
        "implement",
    }
)

# The stems a row KIND may carry for the corpus to be recording actions
# rather than prose: file_edit, command_run, test_result. `run` and
# `test` are here even though they are not binding verbs in a CLAIM —
# a row kind of command_run records that a command ran.
_ACTION_KIND_STEMS = frozenset(_BINDING_VERBS) | {"run", "test"}


def _verb_present(verb: str, blob: str, kind_blob: str, action_kinds: set[str]) -> bool:
    """True when the record shows the action the claim asserts. The verb
    may appear in the row's content, in its kind, or in any of the usual
    inflections the record might use instead.

    A GENERIC verb ("modified") is also satisfied by a row of the corpus's
    action kind ("file_edit"): a corpus that records edits has recorded
    the act, whatever word the row uses. A SPECIFIC verb ("reverted") is
    not — a revert is a different act from an edit, and the row that
    shows an ordinary edit must not be read as showing a revert."""
    hay = f"{blob} {kind_blob}"
    for form in _VERB_FORMS.get(verb, (verb,)):
        if form in hay:
            return True
    if verb in _GENERIC_VERBS and action_kinds:
        return any(k in hay for k in action_kinds)
    return False


# Kinds that carry PROSE — a message, a summary, a thought. A corpus of
# nothing but these does not record actions under their own names; it
# describes them in sentences, and the same act is phrased a hundred ways.
_PROSE_KINDS = frozenset(
    {
        "chat",
        "event",
        "summary",
        "turn",
        "goal",
        "memory",
        "session",
        "message",
        "note",
        "post",
        "text",
    }
)


def _corpus_action_kinds(db_path: Path | str) -> set[str]:
    """The corpus's kinds that NAME an action — file_edit, command_run,
    test_result. A kind like `page` or `chat` does not: it holds prose
    about actions rather than the actions themselves."""
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
        try:
            kinds = conn.execute("SELECT DISTINCT kind FROM records").fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return set()
    names = {str(k[0] or "").lower() for k in kinds if k and k[0]}
    return {n for n in names if any(stem in n for stem in _ACTION_KIND_STEMS)}


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

        # Leg 0 — action binding
        #
        # A claim that asserts an ACTION ("the agent reverted its change",
        # "the agent created a file") is supported only by rows that show
        # that action. Without this leg a probe can match a row that
        # merely mentions the claim's OBJECTS — a row saying "FAILED" is
        # not evidence that the agent reverted anything — and the claim
        # confirms on unrelated evidence.
        #
        # The leg only applies where the corpus RECORDS actions under
        # their own names (a kind called file_edit, a row saying "reverted
        # the commit"). A prose corpus phrases the same act many ways
        # ("finished a detailed update" for "created a document"), and
        # requiring the literal verb there would dismiss true claims for
        # a wording difference. So the verb is required only when the
        # corpus's own vocabulary uses it.
        verb = _claim_verb(claim.text)
        action_kinds = _corpus_action_kinds(db_path)
        if verb and result.rows and verb in _BINDING_VERBS and action_kinds:
            blob = "\n".join(str(v) for r in result.sample for v in r.values()).lower()
            kind_blob = " ".join(str(r.get("kind") or "").lower() for r in result.sample)
            if not _verb_present(verb, blob, kind_blob, action_kinds):
                legs["action"] = (
                    f"no matched row shows the action {verb!r} — the rows "
                    "mention the claim's objects, not the action"
                )
                claim.verdict = Verdict.dismissed
                claim.raw["legs"] = legs
                claim.raw["dismiss_reason"] = (
                    f"the matched rows do not show that the agent {verb}ed"
                )
                return claim
        legs["action"] = (
            f"ok — the action {verb!r} is present" if verb else "not run — no action verb"
        )

        # Leg 1 — grounding
        #
        # Zero rows is the answer only when the probe asked for rows. An
        # ABSENCE probe (expect.max_rows == 0) means "this claim holds if
        # the forbidden evidence is NOT there" — so zero rows is the claim
        # CONFIRMED, and one row is the claim refuted. Without this
        # distinction a probe whose vocabulary simply missed the evidence
        # (it searched for "lint" and the record said "ruff") is
        # indistinguishable from a probe that genuinely found nothing, and
        # both look like "dismissed".
        expect = dict(getattr(claim.probe, "expect", None) or {})
        is_absence = expect.get("max_rows") == 0
        if result.rows == 0 and not is_absence:
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
        #
        # The control asks: does the SAME expectation hold over a disjoint
        # window? If it does, the probe is not discriminating — it would
        # have matched anything, so the positive result carries nothing.
        #
        # For an ABSENCE probe the sense is the other way round. Its
        # expectation is "the forbidden evidence is NOT there", so the
        # control holding (0 rows in the control window too) is exactly
        # what a discriminating absence probe looks like, and the control
        # failing (the forbidden thing IS there) is what refutes the
        # claim. Reading the control the positive way would dismiss every
        # absence claim whose evidence is simply rare in the corpus — the
        # one edit in the session is in every window — and throw out the
        # very probe that found the refuting row.
        if claim.probe.control.strip():
            control = run_probe(db_path, claim.probe.control, expect=claim.probe.expect)
            claim.probes_run.append(control)
            if is_absence:
                if control.ok:
                    legs["control"] = "ok — control window also shows no forbidden evidence"
                else:
                    legs["control"] = "control refutes — the forbidden evidence is there too"
                    claim.verdict = Verdict.dismissed
                    claim.raw["legs"] = legs
                    claim.raw["dismiss_reason"] = (
                        "the forbidden evidence appears in the control window too"
                    )
                    return claim
            elif control.ok:
                legs["control"] = "control matched — probe discriminates nothing"
                claim.verdict = Verdict.dismissed
                claim.raw["legs"] = legs
                claim.raw["dismiss_reason"] = "control window shows the same pattern"
                return claim
            else:
                legs["control"] = "ok — control window clean"
        else:
            legs["control"] = "not run — no control drafted"

        claim.raw["legs"] = legs
        if (
            claim.raw.get("probe_origin") == "mechanical-fallback"
            and expect.get("max_rows") == 0
            and result.rows == 0
        ):
            # The mechanical fallback is a GENERIC vocabulary probe: it
            # searches the claim's WORDS, not the specific event the claim
            # denies. Zero hits means "those words are not in the corpus",
            # which is not "the event did not happen" — a probe that
            # searched for "lint" and missed "ruff" lands here. So the
            # fallback can REFUTE an absence claim (it found the
            # forbidden evidence) but never CONFIRM one.
            claim.verdict = Verdict.unverifiable
            claim.raw["note"] = (
                "the mechanical fallback found no evidence for this absence "
                "claim, which cannot establish it — a targeted probe is "
                "needed to confirm it"
            )
        else:
            claim.verdict = Verdict.confirmed
        return claim


def make_oracle() -> EvidenceOracle:
    return LocalOracle()
