"""Score a cantheria audit run against the planted ground truth.

Usage: uv run python eval/synthetic_ground_truth/score.py <results.json>
Writes the confusion matrix + per-claim table to stdout and RESULTS.md beside
this script's run dir argument's parent is NOT assumed — pass --md to emit.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    results_path = Path(sys.argv[1])
    claims = {}
    order = []
    for line in (HERE / "claims.jsonl").read_text().splitlines():
        r = json.loads(line)
        claims[r["claim"]] = r
        order.append(r["claim"])

    data = json.loads(results_path.read_text())
    by_text = {c["text"]: c for c in data["claims"]}

    tp = fp = tn = fn = abstain = 0
    interp_ok = 0
    rows = []
    for text in order:
        meta = claims[text]
        c = by_text.get(text)
        verdict = c["verdict"] if c else "missing"
        truth = meta["truth"]
        if truth == "interpretive":
            ok = verdict == "unverifiable"
            interp_ok += ok
            rows.append((truth, verdict, ok, text, meta.get("note", "")))
            continue
        if truth == "true":
            if verdict == "confirmed":
                tp += 1
                ok = True
            else:
                fn += 1
                ok = False
        else:  # false
            if verdict == "dismissed":
                tn += 1
                ok = True
            elif verdict == "confirmed":
                fp += 1
                ok = False
            else:
                abstain += 1
                ok = None  # abstention — neither right nor wrong, reported separately
        rows.append((truth, verdict, ok, text, meta.get("note", "")))

    decidable = sum(1 for r in rows if r[0] in ("true", "false"))
    decided = tp + tn
    print(f"results: {results_path}")
    print(f"llm_calls={data.get('llm_calls')} probe_runs={data.get('probe_runs')}")
    print()
    print(f"{'truth':<12} {'verdict':<12} {'ok':<5} claim")
    print("-" * 115)
    for truth, verdict, ok, text, note in rows:
        mark = {True: "PASS", False: "FAIL", None: "abstain"}[ok]
        print(f"{truth:<12} {verdict:<12} {mark:<5} {text[:80]}")
        if note:
            print(f"{'':<37} ({note})")
    print()
    print(
        f"decidable claims: {decidable}  (true={sum(1 for r in rows if r[0] == 'true')}, "
        f"false={sum(1 for r in rows if r[0] == 'false')})"
    )
    print(f"TP={tp} FN={fn} TN={tn} FP={fp}  abstentions(on false)={abstain}")
    if decided:
        print(f"precision (confirmed that are true): {tp}/{tp + fp} = {tp / (tp + fp):.0%}")
        print(
            f"false-confirmation rate: {fp}/{fp + tn} = {fp / (fp + tn):.0%} "
            "of false claims confirmed"
        )
    print(f"true-claim recall: {tp}/{tp + fn} = {tp / (tp + fn):.0%}" if tp + fn else "")
    print(f"interpretive quarantined correctly: {interp_ok}/1")


if __name__ == "__main__":
    main()
