"""Dedup tests. The merge rule is deliberately tight, so half of these assert
that two findings *survive* being looked at — folding two real bugs into one
report loses a point that was already won."""

from cantheria.dedup import CORROBORATION_BUMP, cluster, dedup
from cantheria.schemas import Finding, Location, PoC, VulnClass


def _f(
    fid: str,
    *,
    file="pkg/io.py",
    line=100,
    symbol="read",
    cls=VulnClass.memory_safety,
    conf=0.6,
    poc=None,
):
    return Finding(
        id=fid,
        target_repo="planted",
        vuln_class=cls,
        title=f"finding {fid}",
        location=Location(file=file, line=line, symbol=symbol),
        confidence=conf,
        poc=PoC(files={"poc.py": "x"}, entry="python poc.py") if poc else None,
    )


def test_merges_same_symbol_and_class():
    out = dedup([_f("a"), _f("b", line=104)])
    assert [f.id for f in out] == ["a"]
    assert out[0].raw["corroboration"] == 2
    assert [d["id"] for d in out[0].raw["merged_from"]] == ["b"]


def test_highest_confidence_is_the_representative():
    out = dedup([_f("weak", conf=0.55), _f("strong", conf=0.9, line=101)])
    assert out[0].id == "strong"
    assert out[0].raw["merged_from"][0]["id"] == "weak"


def test_does_not_merge_different_classes_in_the_same_function():
    """An off-by-one and a crypto misuse sharing `read_record` are two bugs."""
    out = dedup(
        [
            _f("mem"),
            _f("crypto", cls=VulnClass.crypto_misuse),
        ]
    )
    assert {f.id for f in out} == {"mem", "crypto"}


def test_does_not_merge_distant_lines_in_one_file():
    out = dedup([_f("a", line=10, symbol=None), _f("b", line=900, symbol=None)])
    assert {f.id for f in out} == {"a", "b"}


def test_merges_nearby_lines_when_symbol_is_unknown():
    """Fallback chunking yields `<file>` symbols; the line window carries it."""
    out = dedup([_f("a", line=200, symbol=None), _f("b", line=207, symbol=None)])
    assert len(out) == 1


def test_does_not_merge_across_files():
    out = dedup([_f("a", file="x.py"), _f("b", file="y.py")])
    assert len(out) == 2


def test_corroboration_raises_confidence_a_little():
    rep = dedup([_f("a", conf=0.7), _f("b", conf=0.6, line=101)])[0]
    assert rep.confidence == 0.7 + CORROBORATION_BUMP


def test_corroboration_never_overstates():
    rep = dedup([_f("a", conf=0.99), _f("b", conf=0.99, line=101)])[0]
    assert rep.confidence <= 1.0


def test_inherits_a_poc_the_representative_lacks():
    """A weaker-scoring twin that actually produced a runnable PoC is the one
    the maintainer needs, regardless of which title ranked higher."""
    rep = dedup([_f("a", conf=0.9), _f("b", conf=0.6, line=101, poc=True)])[0]
    assert rep.id == "a"
    assert rep.poc is not None and rep.poc.files


def test_clean_findings_cluster_into_themselves():
    groups = cluster([_f("a"), _f("b", cls=VulnClass.injection), _f("c", line=102)])
    assert [len(g) for g in groups] == [2, 1]
