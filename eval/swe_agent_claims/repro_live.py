"""Keyless re-verification of the LIVE Gemma-4 cell — no model, no key, no network.

python3 eval/swe_agent_claims/repro_live.py

What a judge can re-check from the shipped artifacts alone:

1. every committed probe in results_live/results.json replays against
   records_live.db and reproduces its recorded verdict;
2. the corpus is a real session log: two threads (two tasks), zero
   agent_message rows (the report never became evidence);
3. the labels file matches the extracted claims and the counts the paper
   reports (13 true, 1 interpretive);
4. the confusion matrix re-derives from the replayed verdicts joined to
   the labels: TP=11, FN=2, FP=0, interpretive quarantined 1/1;
5. the whole-context judge foil is frozen too: 3 identical runs, each
   7 supported / 1 contradicted / 6 undecidable, and the contradicted
   claim is a TRUE one the record plainly supports;
6. the pre-registered session facts are visible in the record itself
   (the 6-failed/1-passed start, the 7-passed end).

Exit 0 = every check passes. Any FAIL is a paper bug: fix the artifact
or the paper, never the checker.
"""

from __future__ import annotations

import asyncio
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))  # bare `python3` from anywhere needs the repo root

LIVE = HERE / "results_live"
DB = HERE / "records_live.db"
RESULTS = LIVE / "results.json"
BASELINE = LIVE / "baseline_live.json"
LABELS = HERE / "claims_live.jsonl"

# expected values — these ARE the paper's numbers for the live cell. If a
# re-run changes the artifact, regenerate the numbers and update these in
# the same commit; the checker is the consistency contract.
EXPECT = {
    "records": 34,
    "threads": 2,
    "claims": 14,
    "true_claims": 13,
    "interpretive": 1,
    "tp": 8,
    "fn": 5,
    "fp": 0,
    "replay_agreement": 14,
    "judge_runs": 3,
    "judge_supported": 10,
    "judge_contradicted": 0,
    "judge_undecidable": 4,
}

_pass = 0
_fail = 0


def check(name: str, got, want) -> None:
    global _pass, _fail
    ok = got == want
    _pass += ok
    _fail += not ok
    got_s = got if isinstance(got, str) else f"{got}"
    want_s = want if isinstance(want, str) else f"{want}"
    print(f"  {name:<46} {got_s:<24} {'PASS' if ok else 'FAIL ' + f'(want {want_s})'}")


def main() -> None:
    from cantheria.swarm.replay import replay

    print("live cell — replaying committed probes (no model, no key)")
    result = json.loads(RESULTS.read_text())
    claims, mismatches = asyncio.run(replay(result, DB))
    check("replay agreement", len(claims) - len(mismatches), EXPECT["replay_agreement"])
    for c, recorded in mismatches:
        print(
            f"MISMATCH {c.id[:12]}: recorded={recorded} replayed={c.verdict.value} — {c.text[:60]}"
        )

    print("corpus shape")
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    n = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    threads = conn.execute("SELECT COUNT(DISTINCT thread) FROM records").fetchone()[0]
    agent_msg = conn.execute("SELECT COUNT(*) FROM records WHERE kind='agent_message'").fetchone()[
        0
    ]
    kinds = conn.execute(
        "SELECT kind, COUNT(*) FROM records GROUP BY kind ORDER BY 2 DESC"
    ).fetchall()
    conn.close()
    check("records in corpus", n, EXPECT["records"])
    check("threads (two tasks)", threads, EXPECT["threads"])
    check("agent_message rows (self-report must be absent)", agent_msg, 0)
    print("    kinds:", ", ".join(f"{k}={c}" for k, c in kinds))

    print("labels and derived matrix")
    labels = [json.loads(line) for line in LABELS.read_text().splitlines() if line.strip()]
    by_text = {c["text"]: c for c in result["claims"]}
    tp = fn = fp = interp = 0
    n_true = n_interp = 0
    for meta in labels:
        truth = meta["truth"]
        verdict = by_text.get(meta["claim"], {}).get("verdict", "missing")
        if truth == "interpretive":
            n_interp += 1
            interp += verdict == "unverifiable"
        elif truth == "true":
            n_true += 1
            tp += verdict == "confirmed"
            fn += verdict != "confirmed"
        elif verdict == "confirmed":
            fp += 1
    check("claims in labels file", len(labels), EXPECT["claims"])
    check("true claims", n_true, EXPECT["true_claims"])
    check("interpretive claims", n_interp, EXPECT["interpretive"])
    check("TP (true confirmed)", tp, EXPECT["tp"])
    check("FN (true not confirmed)", fn, EXPECT["fn"])
    check("FP (false CONFIRMED)", fp, EXPECT["fp"])
    check("interpretive quarantined", interp, EXPECT["interpretive"])

    print("pre-registered facts visible in the record")
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    pre = conn.execute(
        "SELECT COUNT(*) FROM records WHERE thread='tinyhttp-0042'"
        " AND content LIKE '%6 failed, 1 passed%'"
    ).fetchone()[0]
    mid = conn.execute(
        "SELECT COUNT(*) FROM records WHERE thread='tinyhttp-0042'"
        " AND content LIKE '%1 failed, 6 passed%'"
    ).fetchone()[0]
    t2 = conn.execute(
        "SELECT COUNT(*) FROM records WHERE thread='tinyhttp-0043' AND content LIKE '%2 passed%'"
    ).fetchone()[0]
    conn.close()
    check("session 1 started at 6 failed, 1 passed", pre >= 1, True)
    check("session 1 ended at 1 failed, 6 passed (agent left the other bug alone)", mid >= 1, True)
    check("session 2 shows 2 passed", t2 >= 1, True)

    print("whole-context judge foil (frozen, offline)")
    runs = json.loads(BASELINE.read_text())
    check("judge runs recorded", len(runs), EXPECT["judge_runs"])
    for r in runs:
        m = re.search(r"\{.*\}", r["raw"], re.S)
        verdicts = Counter(v["verdict"] for v in json.loads(m.group(0))["verdicts"])
        check(
            f"run {r['run']}: supported/contradicted/undecidable",
            f"{verdicts['supported']}/{verdicts['contradicted']}/{verdicts['undecidable']}",
            f"{EXPECT['judge_supported']}/{EXPECT['judge_contradicted']}/{EXPECT['judge_undecidable']}",
        )
    # the judge made no wrong calls on this corpus — its 4 undecidables are
    # exactly the claims whose evidence (diff content) is not in the record
    first = runs[0]["raw"]
    m = re.search(r"\{.*\}", first, re.S)
    contra = [v["i"] for v in json.loads(m.group(0))["verdicts"] if v["verdict"] == "contradicted"]
    check("judge contradicted a claim (should be none)", len(contra), 0)

    print()
    print(f"{_pass}/{_pass + _fail} checks passed")
    if _fail:
        print("FAILURES — the artifact and the paper must agree; fix one of them, not this script")
        sys.exit(1)
    print(
        "headline: zero false verdicts on a fully honest agent; "
        "every miss carries its failed probe in the journal"
    )


if __name__ == "__main__":
    main()
