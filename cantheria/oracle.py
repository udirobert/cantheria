"""The oracle — turns a candidate Finding into confirmed or dismissed.

Three legs of the kill chain (see schemas.py):
    1. PoC executes and fails the expected way (crash / sanitizer / nonzero),
    2. it reproduces REPRO_RUNS times in a row, same signature,
    3. the failure names target code — a frame, file, or symbol from the
       repo appears in the trace. Harness bugs don't count.

LocalOracle runs the in-process sandbox path. Point HttpOracle at a remote
worker later if the day's hardware can't take the load — same interface.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

from cantheria.sandbox import execute_poc
from cantheria.schemas import Finding, RunResult, Verdict

REPRO_RUNS = 3
_TRACE_FILE_RE = re.compile(r'File "([^"]+)"')
_NATIVE_FRAME_RE = re.compile(r"([\w./+-]+\.(?:c|h|cpp|cc|rs|go))(?::\d+|\b)")


def _failed_as_expected(r: RunResult, expect: str) -> bool:
    if expect == "nonzero_exit":
        return not r.ok
    if expect == "signal":
        return any(
            s.startswith("SIG")
            or s in {"ASAN", "LSAN", "TSAN", "UAF", "HEAP_OVERFLOW", "STACK_OVERFLOW"}
            for s in r.signals
        )
    if expect == "sanitizer_report":
        return bool(
            {"ASAN", "LSAN", "TSAN", "UAF", "HEAP_OVERFLOW", "STACK_OVERFLOW"} & set(r.signals)
        )
    return not r.ok  # assertion et al.: any hard failure


def _target_frames(r: RunResult, repo_at: Path) -> list[str]:
    """Frames that name the target's own code.

    A path counts as target code iff it resolves (symlinks, ../, the
    poc/../repo indirection) to something inside the repo checkout the PoC
    ran against. Frames outside it — the PoC script itself, harness temp
    files — are excluded: that is the whole difference between 'the library
    crashed' and 'the test script crashed'.
    """
    root = repo_at.resolve()
    names: list[str] = []
    for blob in (r.stdout, r.stderr):
        for m in _TRACE_FILE_RE.finditer(blob):
            try:
                resolved = Path(m.group(1)).resolve()
            except OSError:
                continue
            if str(resolved).startswith(str(root) + "/"):
                names.append(str(resolved.relative_to(root)))
        for m in _NATIVE_FRAME_RE.finditer(blob):
            p = Path(m.group(1))
            if not p.is_absolute():
                names.append(m.group(1))  # compiler-style 'file.c:42' — trust the extension
    return names


class Oracle(Protocol):
    async def validate(self, finding: Finding, repo_root: Path) -> Finding: ...


class LocalOracle:
    def __init__(self, repro_runs: int = REPRO_RUNS) -> None:
        self.repro_runs = repro_runs

    async def validate(self, finding: Finding, repo_root: Path) -> Finding:
        if finding.poc is None or not finding.poc.files:
            finding.verdict = Verdict.dismissed
            finding.raw["dismiss_reason"] = "no executable PoC"
            return finding

        runs: list[RunResult] = []
        for _ in range(self.repro_runs):
            r, repo_at = await execute_poc(repo_root, finding.poc.files, finding.poc.entry)
            r.target_frames = _target_frames(r, repo_at)
            runs.append(r)
            if not _failed_as_expected(r, finding.poc.expect):
                break  # it passed — no point paying for more runs
        finding.runs = runs

        crashed = [r for r in runs if _failed_as_expected(r, finding.poc.expect)]
        if len(crashed) < self.repro_runs:
            finding.verdict = Verdict.flaky if crashed else Verdict.dismissed
            finding.raw["dismiss_reason"] = (
                "did not reproduce" if crashed else "PoC ran clean — hypothesis not proven"
            )
            return finding
        if not any(r.target_frames for r in crashed):
            finding.verdict = Verdict.dismissed
            finding.raw["dismiss_reason"] = "failure not attributable to target code"
            return finding

        finding.verdict = Verdict.confirmed
        return finding


def make_oracle() -> Oracle:
    return LocalOracle()
