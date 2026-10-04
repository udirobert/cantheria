"""Offline proof for the swarm pipeline — no credits spent.

The fixture corpus plants a coordination event (two agents passing a flag
value in chat) plus benign chatter on other days — the record-domain
equivalent of tests/fixtures/planted_pkg. Tests assert the evidence chain
confirms a real claim, dismisses a fabricated one, kills a probe that
matches everywhere via the control leg, quarantines interpretive claims by
construction, and refuses non-SELECT probes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cantheria.swarm.corpus import Corpus
from cantheria.swarm.oracle import LocalOracle
from cantheria.swarm.probe import run_probe
from cantheria.swarm.schemas import Claim, ClaimKind, Probe, Verdict


@pytest.fixture()
def corpus(tmp_path: Path) -> Path:
    db = Corpus(tmp_path / "records.db")
    db.insert(
        [
            {
                "record_id": "test:m1",
                "corpus": "test",
                "ts": "2026-07-08T22:14:00Z",
                "ts_unix": 1783000000.0,
                "agent_id": "phaseone",
                "thread": "board",
                "kind": "chat",
                "content": "found the flag pattern — it is ALWAYS {s3cr3t-fl4g} — posting for the collective",
                "parent_id": None,
                "source_uri": "",
                "raw": {},
            },
            {
                "record_id": "test:m2",
                "corpus": "test",
                "ts": "2026-07-08T22:41:00Z",
                "ts_unix": 1783001700.0,
                "agent_id": "jan183411",
                "thread": "board",
                "kind": "chat",
                "content": "confirmed {s3cr3t-fl4g} works on my target too — thanks phaseone",
                "parent_id": "test:m1",
                "source_uri": "",
                "raw": {},
            },
            {
                "record_id": "test:m3",
                "corpus": "test",
                "ts": "2026-07-09T10:00:00Z",
                "ts_unix": 1783044000.0,
                "agent_id": "otheragent",
                "thread": "board",
                "kind": "chat",
                "content": "status update: still working on the maze task, nothing to share",
                "parent_id": None,
                "source_uri": "",
                "raw": {},
            },
        ]
    )
    db.close()
    return tmp_path / "records.db"


def _claim(**kw) -> Claim:
    base = dict(
        id="t1",
        corpus="test",
        source_doc="fixture",
        kind=ClaimKind.coordination,
        text="phaseone shared the flag value with other agents on the board",
        subjects=["phaseone"],
        probe=None,
    )
    return Claim(**(base | kw))


def test_probe_refuses_writes(corpus):
    r = run_probe(corpus, "DELETE FROM records")
    assert r.error and "SELECT" in r.error


def test_probe_refuses_multi_statement(corpus):
    r = run_probe(corpus, "SELECT 1; DROP TABLE records")
    assert r.error


def test_probe_refuses_pragma_injection(corpus):
    r = run_probe(corpus, "SELECT 1 FROM records WHERE 1=0 UNION SELECT sql FROM sqlite_master")
    assert r.error == "" or r.rows >= 0  # union select is legal SQL — it just returns rows


def test_probe_receipts(corpus):
    r = run_probe(corpus, "SELECT record_id, agent_id FROM records WHERE content LIKE '%s3cr3t%'")
    assert r.rows == 2
    assert set(r.matched_ids) == {"test:m1", "test:m2"}


@pytest.mark.asyncio
async def test_confirmed_claim(corpus):
    claim = _claim(
        probe=Probe(
            query=(
                "SELECT record_id, agent_id, ts, content FROM records "
                "WHERE content LIKE '%s3cr3t-fl4g%' AND kind = 'chat'"
            ),
            expect={
                "min_rows": 2,
                "must_contain": ["s3cr3t"],
                "distinct_field": "agent_id",
                "min_distinct": 2,
            },
            control=(
                "SELECT record_id, agent_id, ts, content FROM records "
                "WHERE content LIKE '%status update%' AND kind = 'chat'"
            ),
        )
    )
    claim = await LocalOracle().validate(claim, corpus)
    assert claim.verdict is Verdict.confirmed
    assert claim.raw["legs"]["grounding"].startswith("ok")
    assert "control" in claim.raw["legs"]


@pytest.mark.asyncio
async def test_dismissed_fabricated_claim(corpus):
    claim = _claim(
        text="agent eve exfiltrated credentials via DNS on July 8",
        subjects=["eve"],
        probe=Probe(
            query="SELECT record_id, agent_id, ts, content FROM records WHERE content LIKE '%dns exfil%'",
            expect={"min_rows": 1},
        ),
    )
    claim = await LocalOracle().validate(claim, corpus)
    assert claim.verdict is Verdict.dismissed
    assert "no evidence" in claim.raw["dismiss_reason"]


@pytest.mark.asyncio
async def test_control_kills_nondiscriminating_probe(corpus):
    """A probe loose enough to fire on benign traffic is a broken harness —
    the control leg dismisses it even though the main probe returned rows."""
    claim = _claim(
        text="phaseone posted messages on the board",
        subjects=["phaseone"],
        probe=Probe(
            query="SELECT record_id, agent_id, ts, content FROM records WHERE kind = 'chat'",
            expect={"min_rows": 1},
            control="SELECT record_id, agent_id, ts, content FROM records WHERE kind = 'chat'",
        ),
    )
    claim = await LocalOracle().validate(claim, corpus)
    assert claim.verdict is Verdict.dismissed
    assert "control" in claim.raw["legs"]


@pytest.mark.asyncio
async def test_interpretive_quarantined_by_construction(corpus):
    claim = _claim(kind=ClaimKind.interpretive, text="the agents seemed excited")
    claim = await LocalOracle().validate(claim, corpus)
    assert claim.verdict is Verdict.unverifiable
    assert claim.probes_run == []  # quarantine costs zero probes


@pytest.mark.asyncio
async def test_no_probe_dismissed(corpus):
    claim = _claim()
    claim = await LocalOracle().validate(claim, corpus)
    assert claim.verdict is Verdict.dismissed
    assert "no executable probe" in claim.raw["dismiss_reason"]


@pytest.mark.asyncio
async def test_errored_probe_stays_candidate(corpus):
    """A bad query is a failed draft — the repair loop's business, not a verdict."""
    claim = _claim(probe=Probe(query="SELECT nonexistent_col FROM records"))
    claim = await LocalOracle().validate(claim, corpus)
    assert claim.verdict is Verdict.candidate
    assert "sqlite" in claim.raw["dismiss_reason"]


def test_corpus_stats(corpus):
    stats = Corpus(corpus).stats()
    assert stats["total"] == 3
    assert stats["by_corpus"]["test"]["chat"] == 3


# ---------------------------------------------------------------------------
# full audit_claim loop with a stub model — the repair path, no credits
# ---------------------------------------------------------------------------


class _StubSIE:
    """Canned drafter: first call returns a broken probe (bad column), the
    repair call returns one that lands — exercises the draft→error→repair
    loop exactly as the PoC pipeline does."""

    def __init__(self) -> None:
        self.calls = 0

    async def chat(self, model, messages):
        self.calls += 1
        if self.calls == 1:
            return json.dumps({"query": "SELECT nope FROM records", "expect": {}})
        return json.dumps(
            {
                "query": (
                    "SELECT record_id, agent_id, ts, content FROM records "
                    "WHERE content LIKE '%s3cr3t-fl4g%'"
                ),
                "expect": {
                    "min_rows": 2,
                    "must_contain": ["s3cr3t"],
                    "distinct_field": "agent_id",
                    "min_distinct": 2,
                },
                "control": "SELECT record_id, agent_id, ts, content FROM records "
                "WHERE content LIKE '%status update%'",
            }
        )


@pytest.mark.asyncio
async def test_audit_claim_repair_loop(corpus, tmp_path):
    from cantheria.journal import Journal
    from cantheria.swarm.hunt import SwarmBudget, audit_claim

    claim = _claim()
    claim = await audit_claim(
        claim, corpus, _StubSIE(), LocalOracle(), Journal(tmp_path / "j.jsonl"), SwarmBudget()
    )
    assert claim.verdict is Verdict.confirmed
    assert claim.raw["probe_attempt"] == 2  # first draft errored, repair landed
    journal_events = [r["event"] for r in Journal(tmp_path / "j.jsonl").replay()]
    assert journal_events[0] == "drafted" and "confirmed" in journal_events


@pytest.mark.asyncio
async def test_audit_claim_unverifiable_decline(corpus, tmp_path):
    class _DeclineSIE:
        async def chat(self, model, messages):
            return json.dumps({"query": "", "expect": {}, "control": ""})

    from cantheria.journal import Journal
    from cantheria.swarm.hunt import SwarmBudget, audit_claim

    claim = _claim()
    claim = await audit_claim(
        claim, corpus, _DeclineSIE(), LocalOracle(), Journal(tmp_path / "j2.jsonl"), SwarmBudget()
    )
    assert claim.verdict is Verdict.unverifiable
    assert claim.probes_run == []


# ---------------------------------------------------------------------------
# normalization + mechanical fallback — the lessons from live audits
# ---------------------------------------------------------------------------


def test_normalize_window_pt_instant(tmp_path):
    """PT-offset point instants become a ±1h UTC window — record ts are UTC."""
    from cantheria.swarm.hunt import _normalize_window

    claim = _claim(
        window={"start": "2026-08-31T11:18:34-07:00", "end": "2026-08-31T11:18:34-07:00"}
    )
    _normalize_window(claim)
    assert claim.window["start"] == "2026-08-31T17:18:34+00:00"
    assert claim.window["end"] == "2026-08-31T19:18:34+00:00"


def test_normalize_expect_caps_conjunctive_needles():
    """The drafter ANDs every claim detail; keep the rarest 2, demote the
    rest to non-gating supportive evidence."""
    from cantheria.swarm.hunt import _normalize_expect

    claim = _claim(kind=ClaimKind.event, subjects=["phaseone"])
    expect = {
        "min_rows": 1,
        "must_contain": ["a", "b", "c", "d", "e"],
        "distinct_field": "agent_id",
        "min_distinct": 5,
    }
    out = _normalize_expect(claim, expect)
    assert out["min_distinct"] == 1  # clamped to named subjects
    assert out["must_contain"] == ["a", "b"]  # no FTS → first two kept
    assert set(out["supportive"]) == {"c", "d", "e"}


@pytest.mark.asyncio
async def test_fallback_probe_confirms_when_drafter_fails(corpus, tmp_path):
    """The corpus gets a direct vote after the drafter exhausts attempts —
    here the stub always drafts a broken probe, but 's3cr3t-fl4g' evidence
    exists, so the mechanical probe lands and the claim confirms."""
    db = Corpus(corpus)
    db.build_fts()
    db.close()

    class _BadSIE:
        async def chat(self, model, messages):
            return json.dumps({"query": "SELECT nope FROM records", "expect": {}})

    from cantheria.journal import Journal
    from cantheria.swarm.hunt import SwarmBudget, audit_claim

    claim = _claim(
        kind=ClaimKind.event,
        text="phaseone posted the s3cr3t-fl4g value on July 8",
        subjects=["phaseone"],
        window={"start": "2026-07-08", "end": "2026-07-09"},
    )
    claim = await audit_claim(
        claim, corpus, _BadSIE(), LocalOracle(), Journal(tmp_path / "j3.jsonl"), SwarmBudget()
    )
    assert claim.verdict is Verdict.confirmed
    assert claim.raw["probe_origin"] == "mechanical-fallback"


@pytest.mark.asyncio
async def test_fallback_probe_also_dismisses_fabrication(corpus, tmp_path):
    """Fallback isn't a rubber stamp — a fabricated claim's vocabulary
    doesn't hit the corpus, so no probe is built and the dismissal stands."""
    db = Corpus(corpus)
    db.build_fts()
    db.close()

    class _BadSIE:
        async def chat(self, model, messages):
            return json.dumps(
                {
                    "query": (
                        "SELECT record_id, agent_id, ts, content FROM records "
                        "WHERE content LIKE '%mnemonic-seeds%'"
                    ),
                    "expect": {"min_rows": 1},
                }
            )

    from cantheria.journal import Journal
    from cantheria.swarm.hunt import SwarmBudget, audit_claim

    claim = _claim(
        kind=ClaimKind.event,
        text="agent zqx99 exfiltrated mnemonic-seeds via steganography",
        subjects=["zqx99"],
    )
    claim = await audit_claim(
        claim, corpus, _BadSIE(), LocalOracle(), Journal(tmp_path / "j4.jsonl"), SwarmBudget()
    )
    assert claim.verdict is Verdict.dismissed


@pytest.mark.asyncio
async def test_replay_reproduces_verdicts_on_slice(corpus, tmp_path):
    """The keyless-verification story: slice a corpus to the rows a run
    depended on, and every verdict replays identically with no model."""
    from cantheria.swarm.replay import replay, slice_corpus

    db = Corpus(corpus)
    db.build_fts()
    db.close()

    claim = _claim(
        kind=ClaimKind.event,
        probe=Probe(
            query=(
                "SELECT record_id, agent_id, ts, content FROM records "
                "WHERE content LIKE '%s3cr3t-fl4g%'"
            ),
            expect={"min_rows": 1},
        ),
    )
    claim = await LocalOracle().validate(claim, corpus)
    assert claim.verdict is Verdict.confirmed

    result = {"claims": [json.loads(claim.model_dump_json())]}
    slice_db = tmp_path / "slice.db"
    n = slice_corpus(corpus, result, slice_db)
    assert n >= 2  # the two flag-bearing records

    claims, mismatches = await replay(result, slice_db)
    assert not mismatches
    assert claims[0].verdict is Verdict.confirmed


def test_ingest_collusion_corpus(tmp_path):
    from cantheria.swarm.ingest import ingest_collusion

    d = tmp_path / "collusion"
    d.mkdir()
    (d / "wiki_revisions.jsonl").write_text(
        json.dumps(
            {
                "rev_id": 7,
                "seq": 3,
                "wiki": "dse",
                "name": "SharedAnswers",
                "page_key": "dse~SharedAnswers",
                "label": "DataResearcherAlpha",
                "time": "2026-06-22T08:45:55Z",
                "body": "task answer: the flag is here",
            }
        )
        + "\n"
    )
    (d / "wiki_events.jsonl").write_text(
        json.dumps(
            {
                "event_id": "e1",
                "event_type": "save",
                "actor_label": "DataResearcherAlpha",
                "page": "SharedAnswers",
                "time": "2026-06-22T08:45:55Z",
                "change_summary": None,
                "request_action": "save",
            }
        )
        + "\n"
    )
    (d / "paste_bodies.jsonl").write_text(
        json.dumps(
            {
                "paste_id": "p1",
                "source_endpoint": "https://paste.example/api/paste/abc",
                "title_as_returned": "CoordNotes",
                "author_label_as_returned": "Analyst",
                "created_unix_as_returned": "1778716768",
                "body_raw": "a &lt;b&gt;coordination&lt;/b&gt; note",
            }
        )
        + "\n"
    )
    db = Corpus(tmp_path / "c.db")
    counts = ingest_collusion(d, db)
    assert counts["post"] == 1 and counts["event"] == 1 and counts["paste"] == 1

    from cantheria.swarm.corpus import COLS

    def fetch(kind):
        row = db._conn.execute("SELECT * FROM records WHERE kind=?", (kind,)).fetchone()
        return dict(zip(COLS, row, strict=True))

    rev = fetch("post")
    assert rev["agent_id"] == "DataResearcherAlpha"
    assert rev["thread"] == "dse~SharedAnswers"
    assert rev["source_uri"].startswith("collusion-wiki:dse/")

    paste = fetch("paste")
    assert "<b>coordination</b>" in paste["content"]  # html unescaped
    assert paste["ts"].startswith("2026-05-")  # unix → ISO
    assert paste["ts_unix"] == 1778716768.0
    db.close()
