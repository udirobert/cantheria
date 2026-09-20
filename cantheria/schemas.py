"""Data contracts between pipeline stages.

The kill chain (borrowed from redteam's bypass validation, re-aimed):
a candidate is only a FINDING when all three legs hold —

    1. a PoC exists and is machine-checkable (crash / sanitizer / assertion),
    2. it reproduces: N consecutive sandbox runs fail the same way,
    3. the failure is attributable to target code (a real frame from the
       target in the trace, not harness or environment noise).

Anything missing a leg stays `candidate` in the journal. Judges (and the
hackathon's manual reviewers) only ever see `confirmed`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Location(BaseModel):
    file: str
    line: int | None = None
    symbol: str | None = None  # function / method name if known


class VulnClass(StrEnum):
    memory_safety = "memory_safety"
    injection = "injection"  # sql/command/template into library API
    input_validation = "input_validation"
    crypto_misuse = "crypto_misuse"
    denial_of_service = "denial_of_service"
    logic_error = "logic_error"
    authz_bypass = "authz_bypass"
    other = "other"


class Verdict(StrEnum):
    candidate = "candidate"  # hypothesis logged, not yet proven
    confirmed = "confirmed"  # full kill chain passed
    flaky = "flaky"  # passed once, failed to reproduce
    dismissed = "dismissed"  # harness artifact / not target code


class RunResult(BaseModel):
    """One sandbox execution of a PoC."""

    ok: bool  # False == the canary died == interesting
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    signals: list[str] = Field(
        default_factory=list
    )  # e.g. ["SIGSEGV", "ASAN:heap-buffer-overflow"]
    target_frames: list[str] = Field(default_factory=list)  # trace lines naming target files
    wall_s: float = 0.0
    confinement: str = ""  # what the jail actually enforced, e.g. "seatbelt: deny network*"


class PoC(BaseModel):
    """Self-contained reproduction: files + how to run them.

    `entry` is a shell command run inside the repo checkout with the PoC
    files written to its working directory, e.g. "python poc.py".
    """

    language: str = "python"
    files: dict[str, str] = Field(default_factory=dict)
    entry: str = "python poc.py"
    expect: str = "nonzero_exit"  # nonzero_exit | signal | sanitizer_report | assertion
    # Control leg: a command that MUST exit 0 — same harness, benign input.
    # If the control fails, the crash was the harness being broken, not the bug.
    # OSS-Fuzz-Gen/AIxCC lesson: negative tests are what separate a finding
    # from a failing build. Empty = no control leg run.
    control: str = ""


class Finding(BaseModel):
    id: str
    created_utc: datetime = Field(default_factory=lambda: datetime.now(UTC))
    target_repo: str
    vuln_class: VulnClass = VulnClass.other
    title: str
    detail: str = ""  # root-cause explanation, not just symptom
    location: Location | None = None
    poc: PoC | None = None
    confidence: float = 0.0  # reranker/validator score, 0..1
    verdict: Verdict = Verdict.candidate
    runs: list[RunResult] = Field(default_factory=list)
    severity: str | None = None  # assigned after confirmation
    patch_hint: str | None = None  # suggested fix for the maintainer report
    raw: dict[str, Any] = Field(default_factory=dict)

    @property
    def reportable(self) -> bool:
        """The kill chain's own answer: did this bug reproduce and attribute?

        Deliberately *not* `and confidence >= x`. Confidence is assigned later,
        by triage, and this property is consulted by hunt — which runs first.
        Requiring it here means every confirmed finding is filtered out before
        anything could score it, and the pipeline reports zero findings from a
        repo it just crashed three times in. Worthiness is triage's call, and it
        is made once, in one place: report.py quarantines on confidence.
        """
        return self.verdict == Verdict.confirmed
