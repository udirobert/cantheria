"""Offline kill-chain tests — real sandbox, no SIE calls."""

from pathlib import Path

from cantheria.oracle import LocalOracle
from cantheria.schemas import Finding, Location, PoC, Verdict, VulnClass


def _finding(poc_files: dict[str, str], expect: str, repo: str) -> Finding:
    return Finding(
        id="t001",
        target_repo=repo,
        vuln_class=VulnClass.memory_safety,
        title="test",
        location=Location(file="lib.py", symbol="boom"),
        poc=PoC(files=poc_files, entry="python poc.py", expect=expect),
    )


async def test_confirms_reproducible_crash_in_target_code(tmp_path: Path) -> None:
    (tmp_path / "lib.py").write_text(
        "def boom(data):\n    raise ValueError('unhandled: ' + data)\n"
    )
    poc = {
        "poc.py": (
            "import sys\nsys.path.insert(0, '../repo')\nfrom lib import boom\nboom('x' * 10)\n"
        )
    }
    f = await LocalOracle(repro_runs=2).validate(_finding(poc, "nonzero_exit", "proj"), tmp_path)
    assert f.verdict == Verdict.confirmed
    assert len(f.runs) == 2
    assert all(not r.ok for r in f.runs)


async def test_dismisses_clean_poc(tmp_path: Path) -> None:
    (tmp_path / "lib.py").write_text("def ok():\n    return 1\n")
    poc = {"poc.py": "import sys\nsys.path.insert(0, '../repo')\nfrom lib import ok\nok()\n"}
    f = await LocalOracle(repro_runs=2).validate(_finding(poc, "nonzero_exit", "proj"), tmp_path)
    assert f.verdict == Verdict.dismissed
    assert len(f.runs) == 1  # short-circuits the moment it runs clean


async def test_dismisses_crash_without_target_frames(tmp_path: Path) -> None:
    poc = {"poc.py": "raise RuntimeError('harness on fire')\n"}
    f = await LocalOracle(repro_runs=1).validate(_finding(poc, "nonzero_exit", "proj"), tmp_path)
    assert f.verdict == Verdict.dismissed
    assert "not attributable" in f.raw.get("dismiss_reason", "")
