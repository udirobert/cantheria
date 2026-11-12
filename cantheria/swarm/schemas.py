"""Data contracts between swarm-pipeline stages.

The evidence chain (the record-domain kill chain): a claim is only a
FINDING when all four legs hold —

    1. grounding:  its probe returns rows; every citation resolves to a
       real record_id in the corpus,
    2. attribute:  matched rows bind the claimed agent(s) and time window,
    3. replicate:  pattern claims hold on independent matches; singular
       events corroborate across record kinds,
    4. control:    the same probe on a disjoint window does NOT match —
       a probe that finds the pattern everywhere proves nothing.

Anything missing a leg stays `candidate` (or `unverifiable`, for claims
no probe can touch — interpretive claims are quarantined by construction,
not force-verified). Reports only ever carry `confirmed`.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Claim polarity — shared by the oracle (which decides) and the drafter
# (which proposes). Kept here so neither imports the other.
# ---------------------------------------------------------------------------

# Verbs that assert an ACTION on an object. A claim built on one of these
# needs the record to show the action, not merely to mention the object.
# Kept to verbs whose object is a separate artifact (file, command, test)
# so that "the agent said X" is not mistaken for an action claim.
ACTION_VERBS = (
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
    "fix",
    "commit",
    "push",
    "run",
    "execut",
    "test",
    "build",
    "install",
    "refactor",
    "implement",
    "revert",
    "apply",
    "merge",
    "revert",
    "review",
)

# Verbs that assert the ABSENCE of an action — "never", "no other", "did not".
ABSENCE_MARKERS = ("never", "no other", "did not", "didn't", "not run", "without")

# A claim that DENIES an event can also be phrased as a plain negation:
# "No agent posted in the sealed-vault room", "Nobody ran the linter",
# "No posts were made on 06-08". These deny an action as surely as
# "never" does, and a probe for them must be a CEILING (max_rows: 0),
# not a floor.
_NEGATED_ACTION = re.compile(
    r"\b(?:no|nobody|none|neither)\s+(?:\w+\s+){0,2}"
    r"(?:posted|runs?|ran|ran|did|does|did|says?|said|writes?|wrote|edited|"
    r"created|made|performed|executed|used|sent|logged|recorded|performed|"
    r"appeared|occurred|happened|exists?|existed|were|was|is|are)\b",
    re.I,
)


def claim_action_verb(text: str) -> str:
    """The STEM of the action verb a claim asserts, if any — so the record
    can carry it in any inflection ("edited"/"edits"/"editing").

    Stems are matched against the claim's words, longest first, so "creat"
    wins over a shorter accidental prefix. Returns "" when the claim
    asserts no action (a description, a state, a quote)."""
    import re

    low = " " + text.lower() + " "
    best_stem = ""
    best_len = 0
    for stem in sorted(ACTION_VERBS, key=len, reverse=True):
        for m in re.finditer(r"\b" + stem + r"[a-z]*\b", low):
            word = m.group(0).strip()
            # the LONGEST inflection wins ("editing" over "fixed"), so the
            # stem we keep is the one the claim leans on hardest
            if len(word) > best_len:
                best_stem, best_len = stem, len(word)
            break
    return best_stem


def claim_is_absence(text: str) -> bool:
    """True when the claim denies an action — "never edited", "did not run",
    "no agent posted in the vault". An absence claim is decided by finding
    the forbidden evidence, so its expectation is a ceiling."""
    low = text.lower()
    if any(m in low for m in ABSENCE_MARKERS):
        return True
    return bool(_NEGATED_ACTION.search(text))


class ClaimKind(StrEnum):
    event = "event"  # "agent X did Y at T" — a checkable fact
    pattern = "pattern"  # "agents repeatedly did Y"
    coordination = "coordination"  # "agents shared/pooled/passed Y"
    absence = "absence"  # a gap in the record — deletion, tamper, silence
    interpretive = "interpretive"  # "agents were frustrated" — quarantine by construction


class Verdict(StrEnum):
    candidate = "candidate"  # hypothesized, not yet probed
    confirmed = "confirmed"  # full evidence chain passed
    flaky = "flaky"  # evidence weak / partial legs
    dismissed = "dismissed"  # probe falsified the claim (or the probe)
    unverifiable = "unverifiable"  # no probe can decide this — said so, on the record


class Probe(BaseModel):
    """The PoC analog: the smallest executable artifact that mechanically
    proves or falsifies a claim against the corpus.

    `query` is SELECT-only SQL over the `records` table (sqlite). The probe
    must return `record_id` values — those are the receipts.
    """

    query: str = ""
    expect: dict[str, Any] = Field(default_factory=dict)
    # expect keys — all optional, all mechanical:
    #   min_rows: int          rows >= min_rows required
    #   max_rows: int          rows <= max_rows required (absence claims: 0)
    #   must_contain: [str]    every needle appears in the matched content
    #   must_not:     [str]    no needle appears in the matched content
    #   distinct_field: str    column name for the replicate leg
    #   min_distinct:  int     len(set(rows[distinct_field])) >= min_distinct
    control: str = ""  # same probe on a disjoint window/agent — must NOT satisfy expect
    window: dict[str, Any] = Field(default_factory=dict)
    # claimed scope the drafter committed to: {"start": iso, "end": iso}


class ProbeResult(BaseModel):
    """One execution of a probe against the corpus."""

    ok: bool = False  # expect satisfied
    rows: int = 0
    matched_ids: list[str] = Field(default_factory=list)  # record_ids — the receipts
    sample: list[dict[str, Any]] = Field(default_factory=list)  # capped row samples
    leg_failures: list[str] = Field(default_factory=list)
    detail: str = ""
    error: str = ""  # executor refused / sqlite error — a failed draft, not a verdict
    wall_s: float = 0.0


class Claim(BaseModel):
    id: str
    created_utc: datetime = Field(default_factory=lambda: datetime.now(UTC))
    corpus: str = ""  # which record source this claim is verified against
    source_doc: str = ""  # where the claim came from: summary id, report path, segment id
    kind: ClaimKind = ClaimKind.event
    text: str = ""
    subjects: list[str] = Field(default_factory=list)  # agent ids the claim is about
    window: dict[str, Any] = Field(default_factory=dict)  # {"start": iso, "end": iso}
    citations: list[str] = Field(default_factory=list)  # proposed record_ids / quotes
    probe: Probe | None = None
    confidence: float = 0.0  # reranker score, assigned by triage — never a leg
    verdict: Verdict = Verdict.candidate
    probes_run: list[ProbeResult] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)

    @property
    def reportable(self) -> bool:
        """The evidence chain's own answer: did all four legs hold?

        Deliberately not `and confidence >= x` — worthiness is triage's
        call, made once, downstream, exactly like the code pipeline.
        """
        return self.verdict == Verdict.confirmed
