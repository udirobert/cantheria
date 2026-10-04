import copy
from pathlib import Path

from cantheria.swarm.corpus import Corpus
from cantheria.swarm.report import _public_source_uri, write_audit_report
from cantheria.swarm.report_html import write_audit_html


def _claim(verdict: str, i: int, raw: dict | None = None) -> dict:
    return {
        "id": f"c{i}",
        "kind": "presence",
        "text": f"claim {i} text",
        "source_doc": "chat",
        "verdict": verdict,
        "raw": raw or {},
        "probes_run": [],
    }


def _result(claims: list[dict]) -> dict:
    return {
        "corpus": "test",
        "claims": claims,
        "llm_calls": 0,
        "probe_runs": 0,
    }


def _render_md(tmp_path: Path, result: dict, db: Path | None = None) -> str:
    out = write_audit_report(result, tmp_path / "REPORT.md", db_path=db)
    return out.read_text()


def _render_html(tmp_path: Path, result: dict, db: Path | None = None) -> str:
    out = write_audit_html(result, tmp_path / "index.html", db_path=db)
    return out.read_text()


def test_failing_fraction_both_outputs(tmp_path: Path) -> None:
    result = _result(
        [
            _claim("confirmed", 1),
            _claim("confirmed", 2),
            _claim("dismissed", 3),
            _claim("unverifiable", 4),
            _claim("flaky", 5),
        ]
    )
    md = _render_md(tmp_path, result)
    html = _render_html(tmp_path, result)
    for body in (md, html):
        assert "33%" in body
        assert "1/3" in body
        assert "Slop rate" not in body
        assert "slop rate" not in body


def test_zero_decidable_is_na(tmp_path: Path) -> None:
    result = _result([_claim("unverifiable", i) for i in range(4)])
    md = _render_md(tmp_path, result)
    html = _render_html(tmp_path, result)
    for body in (md, html):
        assert "N/A (0 decidable claims)" in body
        assert "0%" not in body


def test_confirmed_ignores_stale_fields(tmp_path: Path) -> None:
    raw = {
        "dismiss_reason": "stale legacy reason",
        "backend_error": "stale backend timeout",
        "note": "fallback recovered a matching record",
    }
    claim = _claim("confirmed", 1, raw=raw)
    before = copy.deepcopy(raw)
    md = _render_md(tmp_path, _result([claim]))
    html = _render_html(tmp_path, _result([claim]))
    assert raw == before
    for body in (md, html):
        assert "stale legacy reason" not in body
        assert "stale backend timeout" not in body
        assert "fallback recovered a matching record" in body


def test_dismissed_keeps_reason(tmp_path: Path) -> None:
    claim = _claim("dismissed", 1, raw={"dismiss_reason": "no matching record"})
    md = _render_md(tmp_path, _result([claim]))
    html = _render_html(tmp_path, _result([claim]))
    assert "no matching record" in md
    assert "no matching record" in html


class TestPublicSourceUri:
    def test_valid_https(self) -> None:
        assert _public_source_uri("https://example.com/x")

    def test_valid_http(self) -> None:
        assert _public_source_uri("http://example.com")

    def test_malformed(self) -> None:
        assert not _public_source_uri("http://")
        assert not _public_source_uri("not a url")

    def test_javascript(self) -> None:
        assert not _public_source_uri("javascript:alert(1)")

    def test_internal_scheme(self) -> None:
        assert not _public_source_uri("collusion-wiki:dse/x")

    def test_embedded_credentials(self) -> None:
        assert not _public_source_uri("https://user@example.com/x")

    def test_non_string(self) -> None:
        assert not _public_source_uri(None)
        assert not _public_source_uri(42)


def _corpus_with_source(tmp_path: Path, source_uri: str | None) -> Path:
    db = Corpus(tmp_path / "records.db")
    db.insert(
        [
            {
                "record_id": "rec:1",
                "corpus": "test",
                "ts": "2026-07-08T00:00:00Z",
                "ts_unix": 0.0,
                "agent_id": "a",
                "thread": "t",
                "kind": "chat",
                "content": "hello",
                "parent_id": None,
                "source_uri": source_uri,
                "raw": {},
            }
        ]
    )
    db.close()
    return tmp_path / "records.db"


def _confirmed_with_receipt() -> dict:
    c = _claim("confirmed", 1)
    c["probes_run"] = [{"matched_ids": ["rec:1"]}]
    return c


def test_internal_source_renders_reference_not_link(tmp_path: Path) -> None:
    db = _corpus_with_source(tmp_path, "collusion-wiki:dse/SharedAnswers")
    html = _render_html(tmp_path, _result([_confirmed_with_receipt()]), db)
    assert "corpus-internal reference" in html
    assert "collusion-wiki" not in html
    assert "<a href" not in html.split("receipts")[1]

    md = _render_md(tmp_path, _result([_confirmed_with_receipt()]), db)
    assert "corpus-internal reference" in md
    assert "collusion-wiki" not in md


def test_public_source_remains_link(tmp_path: Path) -> None:
    db = _corpus_with_source(tmp_path, "https://theaidigest.org/article/x")
    html = _render_html(tmp_path, _result([_confirmed_with_receipt()]), db)
    assert 'href="https://theaidigest.org/article/x"' in html
    md = _render_md(tmp_path, _result([_confirmed_with_receipt()]), db)
    assert "https://theaidigest.org/article/x" in md


def test_null_source_keeps_record_id(tmp_path: Path) -> None:
    db = _corpus_with_source(tmp_path, None)
    html = _render_html(tmp_path, _result([_confirmed_with_receipt()]), db)
    assert "rec:1" in html
    assert "no public source link supplied" in html
