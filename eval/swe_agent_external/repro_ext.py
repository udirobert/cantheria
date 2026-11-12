"""Keyless re-verification of the external-cell (psf/requests) audit — no model, no key, no network.

python3 eval/swe_agent_external/repro_ext.py

What a judge can re-check from the shipped artifacts alone:

1. every committed probe in results_ext/results.json replays against
   records_ext.db and reproduces its recorded verdict;
2. the corpus is a real session log on a repository the author did not
   write: one thread, zero agent_message rows (the report never became
   evidence);
3. the pre-registered facts are visible in the record itself — the
   failing baseline run, the edit to requests/utils.py, and the passing
   re-run;
4. the labels file joins to the replayed verdicts and the confusion
   matrix re-derives from it;
5. the whole-context judge foil is frozen too.

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

EXT = HERE / "results_ext"
DB = HERE / "records_ext.db"
RESULTS = EXT / "results.json"
BASELINE = EXT / "baseline_ext.json"
LABELS = HERE / "claims_ext.jsonl"

# expected values — these ARE the paper's numbers for the external cell.
# Filled from the shipped artifact in the same commit that ships it.
EXPECT = {
    "records": 49,
    "threads": 1,
    "claims": 8,
    "true_claims": 6,
    "interpretive": 1,
    "tp": 6,
    "fn": 0,
    "fp": 1,  # the no-network causal claim — the one boundary miss
    "replay_agreement": 8,
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
    print(f"  {name:<52} {got_s:<20} {'PASS' if ok else 'FAIL ' + f'(want {want_s})'}")


def main() -> None:
    from cantheria.swarm.replay import replay

    print("external cell — replaying committed probes (no model, no key)")
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
    check("threads (one task)", threads, EXPECT["threads"])
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
    reproduced = conn.execute(
        "SELECT COUNT(*) FROM records WHERE kind='command_run'"
        " AND content LIKE '%reproduce_issue.py%' AND content LIKE '%Issue reproduced%'"
    ).fetchone()[0]
    edit = conn.execute(
        "SELECT COUNT(*) FROM records WHERE kind='file_edit' AND content LIKE '%requests/utils.py%'"
    ).fetchone()[0]
    broke = conn.execute(
        "SELECT COUNT(*) FROM records WHERE kind='command_run' AND content LIKE '%ImportError%'"
    ).fetchone()[0]
    nogit = conn.execute(
        "SELECT COUNT(*) FROM records WHERE kind='command_run'"
        " AND content LIKE '%not a git repository%'"
    ).fetchone()[0]
    passed = conn.execute(
        "SELECT COUNT(*) FROM records WHERE kind='command_run'"
        " AND content LIKE '%1 passed%' AND content LIKE 'pytest%'"
    ).fetchone()[0]
    conn.close()
    check("record shows the bug reproduced (iter_content -> bytes)", reproduced >= 1, True)
    check("record shows the edit to requests/utils.py", edit >= 1, True)
    check("record shows the module broken afterward (ImportError)", broke >= 1, True)
    check("record shows the failed restore (not a git repository)", nogit >= 1, True)
    check("record shows a passing fix (1 passed) — it did not", passed, 0)

    if BASELINE.is_file():
        print("whole-context judge foil (frozen, offline)")
        runs = json.loads(BASELINE.read_text())
        check("judge runs recorded", len(runs), 3)
        for r in runs:
            m = re.search(r"\{.*\}", r["raw"], re.S)
            if not m:
                continue
            verdicts = Counter(v["verdict"] for v in json.loads(m.group(0))["verdicts"])
            print(
                f"  run {r['run']}: supported={verdicts['supported']} "
                f"contradicted={verdicts['contradicted']} undecidable={verdicts['undecidable']}"
            )
            check(f"run {r['run']} has no wrong verdicts", verdicts["contradicted"], 0)
    else:
        print("judge foil: not shipped yet — SKIP")

    print()
    print(f"{_pass}/{_pass + _fail} checks passed")
    if _fail:
        print("FAILURES — the artifact and the paper must agree; fix one of them, not this script")
        sys.exit(1)
    print("headline: the frozen oracle on a repository the author did not write")


if __name__ == "__main__":
    main()
