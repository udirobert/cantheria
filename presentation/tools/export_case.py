"""Export one reviewed case from results.json + REPORT.md (Developer-B owned)."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def parse_report_links(report_text: str) -> dict[str, str]:
    links: dict[str, str] = {}
    pat = r"`(aivillage:[0-9a-f-]+)`\s*[-\u2014\u2013]\s*(https?://\S+)"
    for m in re.finditer(pat, report_text):
        links[m.group(1)] = m.group(2).rstrip(").,")
    return links


def leg_status(legs: dict, leg: str) -> tuple[str, str]:
    v = legs.get(leg)
    if v is None:
        return "not-run", f"No recorded {leg} outcome for this claim."
    s = str(v)
    if s.startswith("ok"):
        return "passed", s
    if "not run" in s.lower():
        return "not-run", s
    return "failed", s


CHECKS = [
    ("grounding", "Grounding"),
    ("attribution", "Attribution"),
    ("replication", "Replication"),
    ("control", "Negative control"),
]

LEG_KEY = {
    "grounding": "grounding",
    "attribution": "attribute",
    "replication": "replicate",
    "control": "control",
}


def step_status(pr: dict) -> tuple[str, str]:
    if pr.get("error"):
        return "error", str(pr["error"])
    detail = "; ".join(pr.get("leg_failures") or []) or "No recorded outcome."
    return ("passed" if pr.get("ok") else "failed"), detail


def build_steps(claim: dict) -> list[dict]:
    raw = claim.get("raw") or {}
    history = raw.get("probe_history") or []
    origin = raw.get("probe_origin", "model")
    runs = claim.get("probes_run") or []
    steps: list[dict] = []
    for i, h in enumerate(history):
        pr = runs[i] if i < len(runs) else {}
        status, detail = step_status(pr)
        steps.append(
            {
                "id": f"step-draft-{i + 1}",
                "label": f"Drafted probe — attempt {i + 1}",
                "origin": "model",
                "query": h.get("query"),
                "expect": h.get("expect"),
                "result": {"status": status, "rows": pr.get("rows"), "detail": detail},
                "receiptIds": [],
            }
        )
    probe = claim.get("probe") or {}
    has_control = bool((probe.get("control") or "").strip())
    candidates = runs[:-1] if (has_control and len(runs) >= 2) else runs
    committed = next(
        (r for r in reversed(candidates) if r.get("ok")),
        candidates[-1] if candidates else {},
    )
    status, detail = step_status(committed)
    steps.append(
        {
            "id": "step-committed-probe",
            "label": (
                "Committed probe — mechanical fallback"
                if origin == "mechanical-fallback"
                else "Committed probe — model draft"
            ),
            "origin": "mechanical" if origin == "mechanical-fallback" else "model",
            "query": probe.get("query"),
            "expect": probe.get("expect"),
            "result": {"status": status, "rows": committed.get("rows"), "detail": detail},
            "receiptIds": list(dict.fromkeys(committed.get("matched_ids") or []))[:12],
        }
    )
    if (probe.get("control") or "").strip() and len(runs) >= 2:
        ctrl = runs[-1]
        cstatus, cdetail = step_status(ctrl)
        if not ctrl.get("error") and not ctrl.get("ok"):
            cdetail = "Control window clean — no match. " + cdetail
        steps.append(
            {
                "id": "step-control",
                "label": "Negative control — same probe, disjoint window",
                "origin": "control",
                "query": probe.get("control"),
                "expect": probe.get("expect"),
                "result": {"status": cstatus, "rows": ctrl.get("rows"), "detail": cdetail},
                "receiptIds": [],
            }
        )
    return steps


def build_case(claim, review, links, case_id, run_id, src, corpus):
    raw = claim.get("raw") or {}
    legs = raw.get("legs") or {}
    steps = build_steps(claim)
    committed_ids = []
    for s in steps:
        if s["id"] == "step-committed-probe":
            committed_ids = s["receiptIds"]
    samples = {}
    for pr in claim.get("probes_run") or []:
        for row in pr.get("sample") or []:
            samples.setdefault(str(row.get("record_id")), row)
    receipts = []
    for rid in committed_ids:
        row = samples.get(rid, {})
        receipts.append(
            {
                "id": rid,
                "agent": row.get("agent_id"),
                "timestamp": row.get("ts"),
                "kind": str(row.get("kind") or "record"),
                "excerpt": str(row.get("content") or "")[:2000],
                # links maps record_id -> http URL; corpus-internal refs
                # (collusion-wiki:...) stay null per CONTRACT.md provenance rule
                "sourceUrl": links.get(rid),
                "annotations": [],
            }
        )
    checks = []
    for cid, label in CHECKS:
        status, detail = leg_status(legs, LEG_KEY[cid])
        checks.append({"id": cid, "label": label, "status": status, "detail": detail})
    return {
        "schemaVersion": 1,
        "id": case_id,
        "title": review["title"],
        "question": review["question"],
        "deck": review["deck"],
        "publication": "reviewed",
        "corpus": corpus,
        "run": {
            "id": run_id,
            "sourceArtifact": src,
            "capturedAt": claim.get("created_utc"),
        },
        "claim": {
            "id": claim.get("id"),
            "text": claim.get("text"),
            "sourceLabel": review["sourceLabel"],
            "sourceUrl": review.get("sourceUrl"),
            "sourceExcerpt": review.get("sourceExcerpt"),
        },
        "recordedVerdict": claim.get("verdict"),
        "review": {
            "label": review["label"],
            "supported": review["supported"],
            "unresolved": review["unresolved"],
            "assumptions": review["assumptions"],
        },
        "checks": checks,
        "steps": steps,
        "receipts": receipts,
        "reproduction": review["reproduction"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--claim", required=True)
    ap.add_argument("--review", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--case-id", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--corpus", required=True)
    args = ap.parse_args()
    result = json.loads(Path(args.results).read_text())
    report_text = Path(args.report).read_text()
    found = [c for c in result.get("claims", []) if c.get("id") == args.claim]
    if not found:
        raise SystemExit(f"claim {args.claim} not found in {args.results}")
    review = json.loads(Path(args.review).read_text())
    case = build_case(
        found[0],
        review,
        parse_report_links(report_text),
        args.case_id,
        args.run_id,
        args.results,
        args.corpus,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(case, indent=2) + "\n")
    print(f"wrote {out} — {len(case['receipts'])} receipts, {len(case['steps'])} steps")


if __name__ == "__main__":
    main()
