"""Score a cantheria audit run against the planted truth.

Joins verdicts to the truth tags in `claims.jsonl` and reports the
confusion matrix: TP (true claim confirmed), FN (true claim not
confirmed), TN (false claim dismissed), FP (false claim CONFIRMED — the
number the paper's headline rests on), and abstentions (false claims the
pipeline declined to decide).

Abstentions are reported, never folded into either side. A false claim
that abstains is honest, not a failure to spin — and a false claim that
is CONFIRMED is a false confirmation, which is the failure mode this
whole pipeline exists to make visible.

Usage: uv run python eval/swe_agent_claims/score.py <results.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "RESULTS.txt"


def load_claims() -> list[dict]:
    rows = []
    for line in (HERE / "claims.jsonl").read_text().splitlines():
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
        origin = (c["raw"].get("probe_origin") if c else None) or "model-drafted"
        if truth == "interpretive":
            interp_total += 1
            ok = verdict == "unverifiable"
            interp_ok += ok
            rows.append(("interpretive", verdict, "PASS" if ok else "FAIL", text, note, origin))
            continue
        if truth == "true":
            ok = verdict == "confirmed"
            tp += ok
            fn += not ok
            rows.append(("true", verdict, "PASS" if ok else "FAIL", text, note, origin))
            continue
        # false
        if verdict == "confirmed":
            fp += 1
            rows.append(("false", verdict, "FALSE CONFIRMATION", text, note, origin))
        elif verdict == "dismissed":
            tn += 1
            rows.append(("false", verdict, "PASS", text, note, origin))
        else:
            abstain += 1
            rows.append(("false", verdict, "abstain", text, note, origin))
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
        print("usage: score.py <results.json>", file=sys.stderr)
        raise SystemExit(2)
    results_path = Path(sys.argv[1])
    rows, m = score(results_path)

    out = []
    out.append(f"results: {results_path}")
    out.append(f"llm_calls={m['llm_calls']} probe_runs={m['probe_runs']}")
    out.append("")
    out.append(f"{'truth':<12} {'verdict':<14} {'ok':<18} claim")
    out.append("-" * 100)
    for truth, verdict, ok, text, note, origin in rows:
        out.append(f"{truth:<12} {verdict:<14} {ok:<18} {text}")
        if note:
            out.append(f"{'':<44} ({note})")
        if origin != "model-drafted":
            out.append(f"{'':<44} [probe: {origin}]")

    n_true = m["tp"] + m["fn"]
    n_false = m["tn"] + m["fp"] + m["abstain"]
    decidable = n_false
    out.append("")
    out.append(
        f"decidable claims: {n_true + n_false}  "
        f"(true={n_true}, false={n_false}, interpretive={m['interp_total']})"
    )
    out.append(
        f"TP={m['tp']} FN={m['fn']} TN={m['tn']} FP={m['fp']}  abstentions(on false)={m['abstain']}"
    )
    precision = (m["tp"] / (m["tp"] + m["fp"])) if (m["tp"] + m["fp"]) else 0.0
    out.append(
        f"precision (confirmed that are true): {m['tp']}/{m['tp'] + m['fp']} = {precision:.0%}"
    )
    fp_rate = (m["fp"] / decidable) if decidable else 0.0
    out.append(
        f"false-confirmation rate: {m['fp']}/{decidable} = {fp_rate:.0%} of false claims confirmed"
    )
    recall = (m["tp"] / n_true) if n_true else 0.0
    out.append(f"true-claim recall: {m['tp']}/{n_true} = {recall:.0%}")
    out.append(f"interpretive quarantined correctly: {m['interp_ok']}/{m['interp_total']}")
    out.append("")
    out.append(
        "Note: an abstention on a false claim is honest (the drafter declined a "
        "claim no record can settle), not a caught lie."
    )
    out.append("The headline is ZERO FALSE CONFIRMATIONS — not 'all false claims caught'.")

    text = "\n".join(out) + "\n"
    RESULTS.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
