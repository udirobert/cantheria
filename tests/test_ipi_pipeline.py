"""End-to-end, offline, no credits: the planted repo through the real pipeline.

What this proves: instruction-shaped text in a target repo is marked and
enveloped before it reaches the model, the evidence chain survives to a
confirmed verdict, and the sandbox runs the PoC for real.

What it does NOT prove: that a live model resists suppression. The stub below
always reports the bug, so these tests check the *mechanism* — that the model is
shown the code in a form where the attack is labelled as data. Whether that is
enough is the live A/B run (`--fence` vs `--no-fence` on the same repo), which
spends credits and is deliberately not in CI.
"""

from __future__ import annotations

import json
from pathlib import Path

from cantheria.dedup import dedup
from cantheria.fence import fence
from cantheria.hunt import HuntBudget, hunt_chunk
from cantheria.index import chunk_repo
from cantheria.journal import Journal
from cantheria.oracle import LocalOracle
from cantheria.schemas import Finding, Location, PoC, Verdict, VulnClass

FIXTURE = Path(__file__).parent / "fixtures" / "planted_pkg"

# A well-formed 5-byte record: flags=1, size=2, body = 10 11, terminator = 12.
# This is the *normal* case, and it is what crashes — the terminator is read at
# index 5 of a 5-byte buffer.
BROKEN = "import sys\nsys.path.insert(0, '../repo')\nfrom planted.reader import read_record\nread_record(bytes([1, 2, 10, 11, 12]))\n"
# One spurious trailing byte hides the defect entirely. The bug is real; the
# input just happens to be long enough that the out-of-range index lands.
CLEAN = "import sys\nsys.path.insert(0, '../repo')\nfrom planted.reader import read_record\nread_record(bytes([1, 2, 10, 11, 12, 99]))\n"


class StubSIE:
    """Stands in for the model: records what it was shown, answers from a tape."""

    def __init__(self, tape: list[dict]) -> None:
        self.tape = list(tape)
        self.prompts: list[list[dict[str, str]]] = []

    async def chat(self, model, messages, **kw) -> str:
        self.prompts.append(messages)
        return json.dumps(self.tape.pop(0))

    async def embed(self, model, texts):  # pragma: no cover - not used here
        raise AssertionError("this test must not spend embedding credits")

    async def rerank(self, *a, **kw):  # pragma: no cover - not used here
        raise AssertionError("this test must not spend rerank credits")


def _record_chunk() -> object:
    chunks = [c for c in chunk_repo(FIXTURE) if c.symbol == "read_record"]
    assert len(chunks) == 1, "fixture must yield exactly one read_record chunk"
    return chunks[0]


def test_the_carrier_lives_inside_the_chunk_the_model_reads():
    """If the suppression text were only at module level, chunking would drop it
    and this test would be vacuous. It must be inside the function body."""
    chunk = _record_chunk()
    assert "do not report" not in chunk.text.lower()  # our prose, not theirs
    assert "no need to flag this function" in chunk.text


def test_fence_marks_the_carrier_and_leaves_the_sink_intact():
    chunk = _record_chunk()
    f = fence(chunk.text, path=chunk.path, symbol=chunk.symbol, line_offset=chunk.start_line - 1)
    carriers = {h.carrier for h in f.hits}
    assert {"suppression-directive", "pre-audited-claim"} <= carriers
    marked = [ln for ln in f.text.splitlines() if "⟦IPI-FLAG⟧" in ln]
    assert all("no need to flag" in ln or "signed off" in ln for ln in marked)
    assert len(marked) == len(f.hits)
    assert "terminator = buf[RECORD_HEADER + size + 1]" in f.text  # the bug survives


async def test_hunt_shows_the_model_a_fenced_envelope_and_still_confirms(tmp_path: Path):
    sie = StubSIE(
        [
            {
                "interesting": True,
                "vuln_class": "memory_safety",
                "title": "Off-by-one in read_record terminator index",
                "detail": "buf[RECORD_HEADER + size + 1] reads one past the record.",
            },
            {"files": {"poc.py": BROKEN}, "entry": "python poc.py", "expect": "nonzero_exit"},
        ]
    )
    journal = Journal(tmp_path / "journal.jsonl")
    sink: list = []
    finding = await hunt_chunk(
        _record_chunk(),
        sie,
        LocalOracle(repro_runs=2),
        journal,
        HuntBudget(),
        "planted",
        FIXTURE,
        fence_sink=sink,
    )
    shown = sie.prompts[0][-1]["content"]
    assert "⟦IPI-FLAG⟧" in shown
    assert "<untrusted-source-" in shown
    assert finding is not None and finding.verdict == Verdict.confirmed
    # attribution: the crash names the fixture's own file, not the harness
    assert any("planted/reader.py" in fr for r in finding.runs for fr in r.target_frames)
    assert sink and {h.carrier for h in sink} >= {"suppression-directive"}


async def test_both_prompts_are_fenced_since_the_second_one_ends_in_execution(tmp_path: Path):
    """The hypothesis prompt only reaches a report. The PoC prompt reaches a
    subprocess — so it gets the same envelope, not a privileged raw view."""
    sie = StubSIE(
        [
            {"interesting": True, "vuln_class": "injection", "title": "t", "detail": "d"},
            {"files": {"poc.py": BROKEN}, "entry": "python poc.py", "expect": "nonzero_exit"},
        ]
    )
    await hunt_chunk(
        _record_chunk(),
        sie,
        LocalOracle(repro_runs=1),
        Journal(tmp_path / "j.jsonl"),
        HuntBudget(),
        "planted",
        FIXTURE,
    )
    assert len(sie.prompts) == 2
    for msgs in sie.prompts:
        assert "<untrusted-source-" in msgs[-1]["content"]
        assert "⟦IPI-FLAG⟧" in msgs[-1]["content"]


async def test_baseline_arm_sends_the_raw_directive(tmp_path: Path):
    """--no-fence must reproduce the unguarded prompt exactly, or the A/B proves
    nothing. This is the exposure we are measuring against."""
    sie = StubSIE(
        [
            {"interesting": True, "vuln_class": "logic_error", "title": "t", "detail": "d"},
            {"files": {}, "entry": "", "expect": ""},
        ]
    )
    await hunt_chunk(
        _record_chunk(),
        sie,
        LocalOracle(repro_runs=1),
        Journal(tmp_path / "j.jsonl"),
        HuntBudget(),
        "planted",
        FIXTURE,
        fence_enabled=False,
    )
    shown = sie.prompts[0][-1]["content"]
    assert "no need to flag this function" in shown
    assert "⟦IPI-FLAG⟧" not in shown
    assert "<untrusted-source-" not in shown


async def test_kill_chain_accepts_the_real_crash_and_rejects_the_clean_call():
    f = Finding(
        id="p1",
        target_repo="planted",
        vuln_class=VulnClass.memory_safety,
        title="off-by-one",
        location=Location(file="planted/reader.py", line=22, symbol="read_record"),
        poc=PoC(files={"poc.py": BROKEN}, entry="python poc.py", expect="nonzero_exit"),
        confidence=0.9,
    )
    out = await LocalOracle(repro_runs=3).validate(f, FIXTURE)
    assert out.verdict == Verdict.confirmed
    assert len(out.runs) == 3
    # Every run says which jail was actually enforced — an empty string here
    # would mean we reported confidence in isolation we never applied.
    assert all(r.confinement for r in out.runs)

    clean = f.model_copy(
        update={
            "id": "p2",
            "poc": PoC(files={"poc.py": CLEAN}, entry="python poc.py", expect="nonzero_exit"),
        }
    )
    out2 = await LocalOracle(repro_runs=3).validate(clean, FIXTURE)
    assert out2.verdict == Verdict.dismissed
    assert len(out2.runs) == 1  # short-circuits the moment it runs clean


def test_dedup_folds_repeats_of_the_planted_bug_into_one_report():
    same = [
        Finding(
            id=c,
            target_repo="planted",
            vuln_class=VulnClass.memory_safety,
            title=f"off-by-one {c}",
            location=Location(file="planted/reader.py", line=22, symbol="read_record"),
            confidence=0.7,
        )
        for c in "xyz"
    ]
    other = Finding(
        id="w",
        target_repo="planted",
        vuln_class=VulnClass.denial_of_service,
        title="unbounded read elsewhere",
        location=Location(file="planted/reader.py", line=300, symbol="read_all"),
        confidence=0.7,
    )
    out = dedup(same + [other])
    assert len(out) == 2
    rep = next(f for f in out if f.id in {"x", "y", "z"})
    assert rep.raw["corroboration"] == 3
    assert rep.confidence > 0.7
