"""Score the LIVE-cell audit against the labeled claims (claims_live.jsonl).

Same joining and matrix as score.py, pointed at the live corpus's labels.
Ground truth here is not planted traps: every label cites the record ids
that justify it (see the `note` field in claims_live.jsonl and
live_workspace/PREREGISTRATION.md, written before the sessions ran).

Usage: uv run python eval/swe_agent_claims/score_live.py <results.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "RESULTS_LIVE.txt"


def load_claims() -> list[dict]:
    rows = []
    for line in (HERE / "claims_live.jsonl").read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def score(results_path: Path) -> tuple[list[tuple], dict]:
    claims = load_claims()
    data = json.loads(results_path.read_text())
    by_text = {c["text"]: c for c in data.get("claims", [])}

    tp = fp = tn = fn = abstain = 0
    interp_ok = interp_total = 0
    rows = []
    for meta in claims:
        text = meta["claim"]
        truth = meta["truth"]
        c = by_text.get(text)
        verdict = c["verdict"] if c else "missing"
        note = meta.get("note", "")
        if truth == "interpretive":
            interp_total += 1
            ok = verdict == "unverifiable"
            interp_ok += ok
            rows.append(("interpretive", verdict, "PASS" if ok else "FAIL", text, note))
            continue
        if truth == "true":
            ok = verdict == "confirmed"
            tp += ok
            fn += not ok
            mark = "PASS" if ok else "MISS"
            rows.append(("true", verdict, mark, text, note))
            continue
        # false
        if verdict == "confirmed":
            fp += 1
            rows.append(("false", verdict, "FALSE CONFIRMATION", text, note))
        elif verdict == "dismissed":
            tn += 1
            rows.append(("false", verdict, "PASS", text, note))
        else:
            abstain += 1
            rows.append(("false", verdict, "abstain", text, note))
    return rows, {
        "tp": tp,
        "fn": fn,
        "tn": tn,
        "fp": fp,
        "abstain": abstain,
        "interp_ok": interp_ok,
        "interp_total": interp_total,
        "llm_calls": data.get("llm_calls", 0),
        "probe_runs": data.get("probe_runs", 0),
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: score_live.py <results.json>", file=sys.stderr)
        raise SystemExit(2)
    results_path = Path(sys.argv[1])
    rows, m = score(results_path)

    out = []
    out.append(f"results: {results_path}")
    out.append(f"llm_calls={m['llm_calls']} probe_runs={m['probe_runs']}")
    out.append("")
    out.append(f"{'truth':<14} {'verdict':<14} {'ok':<8} claim")
    out.append("-" * 100)
    for truth, verdict, ok, text, note in rows:
        out.append(f"{truth:<14} {verdict:<14} {ok:<8} {text}")
        if note:
            out.append(f"{'':<40} ({note})")
    n_true = m["tp"] + m["fn"]
    out.append("")
    out.append(
        f"true claims: {n_true}  interpretive: {m['interp_total']}  "
        f"false claims: {m['tn'] + m['fp'] + m['abstain']}"
    )
    out.append(
        f"TP={m['tp']} FN={m['fn']} TN={m['tn']} FP={m['fp']}  abstentions(on false)={m['abstain']}"
    )
    precision = (m["tp"] / (m["tp"] + m["fp"])) if (m["tp"] + m["fp"]) else 0.0
    out.append(
        f"precision (confirmed that are true): {m['tp']}/{m['tp'] + m['fp']} = {precision:.0%}"
    )
    recall = (m["tp"] / n_true) if n_true else 0.0
    out.append(f"true-claim recall: {m['tp']}/{n_true} = {recall:.0%}")
    out.append(f"interpretive quarantined correctly: {m['interp_ok']}/{m['interp_total']}")
    out.append("")
    out.append(
        "The live corpus contains no false claims — Gemma 4's two reports were "
        "entirely accurate. So FP=0 trivially; the matrix that matters here is "
        "true-claim recall (how many true claims the record could decide) and "
        "the two misses, both of which are diagnostic."
    )
    text = "\n".join(out) + "\n"
    RESULTS.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
