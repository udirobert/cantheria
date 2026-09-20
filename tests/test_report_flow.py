"""The verdict → confidence → report ordering, pinned down.

`reportable` is read while confidence is still 0.0, because triage — the thing
that produces confidence — runs after the scan. This test exists because that
once wasn't true, and the pipeline silently reported zero findings from repos it
had just crashed three times in: every confirmed finding was filtered on its way
out of hunt, before anything had scored it, so nothing ever reached triage to be
scored.
"""

from pathlib import Path

from cantheria.report import write_reports
from cantheria.schemas import Finding, Location, PoC, Verdict, VulnClass


def _confirmed(fid: str = "c1", **kw) -> Finding:
    base = dict(
        id=fid,
        target_repo="planted",
        vuln_class=VulnClass.memory_safety,
        title="Off-by-one in read_record",
        detail="Reads one byte past the record.",
        location=Location(file="planted/reader.py", line=22, symbol="read_record"),
        poc=PoC(files={"poc.py": "raise SystemExit(1)"}, entry="python poc.py"),
        verdict=Verdict.confirmed,
    )
    base.update(kw)
    return Finding(**base)


def test_confirmed_before_triage_is_still_reportable():
    assert _confirmed().confidence == 0.0
    assert _confirmed().reportable


def test_reports_written_for_confirmed_finding(tmp_path: Path):
    paths = write_reports([_confirmed()], tmp_path)
    assert len(paths) == 1
    text = (paths[0] / "REPORT.md").read_text()
    assert "Off-by-one in read_record" in text
    assert "python poc.py" in text
    assert (paths[0] / "poc" / "poc.py").exists()
    assert (tmp_path / "index.json").read_text().count('"c1"') == 1


def test_low_confidence_finding_gets_quarantined_out_of_reports(tmp_path: Path):
    f = _confirmed()
    f.confidence = 0.1
    f.raw["quarantined"] = True
    assert write_reports([f], tmp_path) == []
    assert not (tmp_path / f.id).exists()


def test_flaky_and_dismissed_never_appear_in_reports(tmp_path: Path):
    hidden = [
        _confirmed("f1", verdict=Verdict.flaky),
        _confirmed("f2", verdict=Verdict.dismissed),
        _confirmed("f3", verdict=Verdict.candidate),
    ]
    assert write_reports(hidden, tmp_path) == []
    for f in hidden:
        assert not (tmp_path / f.id).exists()


def test_poc_files_cannot_write_outside_their_report_dir(tmp_path: Path):
    f = _confirmed()
    f.poc = PoC(files={"../../evil.py": "x", "poc.py": "y"}, entry="python poc.py")
    write_reports([f], tmp_path)
    assert not (tmp_path / "evil.py").exists()  # d/poc/../../evil.py lands here
    assert (tmp_path / f.id / "poc" / "poc.py").exists()
