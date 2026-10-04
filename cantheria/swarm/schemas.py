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

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


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
