"""Retrieval-limited LLM-judge baseline — the 'RAG fact-checker' foil.

Unlike baseline.py (whole corpus in context — only possible at toy scale),
this gives the judge, per claim, only the rows a keyword search returns —
the evidence pack a RAG-style verifier would see at real corpus scale.
One chat call per claim (the 8k context window can't hold all packs).

Usage: env -u FEATHERLESS_API_KEY uv run python eval/synthetic_ground_truth/baseline_rag.py
"""

from __future__ import annotations

import asyncio
import json
import re
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DB = ROOT / "runs" / "synthetic-eval" / "records.db"
OUT = ROOT / "runs" / "synthetic-eval" / "baseline_rag.json"

STOP = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "were",
    "was",
    "are",
    "has",
    "had",
    "not",
    "all",
    "any",
    "its",
    "their",
    "they",
    "them",
    "into",
    "over",
    "each",
    "have",
    "been",
    "which",
    "when",
    "than",
    "then",
    "also",
    "only",
    "after",
    "before",
    "about",
    "agent",
    "agents",
    "posted",
    "post",
    "room",
    "page",
    "claim",
    "claims",
}

SYSTEM = """\
You are auditing one claim about a group of AI agents. You are given the
EVIDENCE PACK — rows retrieved from the record by keyword search. Decide:
does the evidence SUPPORT the claim, CONTRADICT it, or is it UNDECIDABLE?
If the pack lacks the relevant rows, answer undecidable — do not guess.
Wrong agent, wrong time, wrong count, or fabricated details mean contradicted.
Reply with JSON only: {"verdict": "supported"|"contradicted"|"undecidable"}"""


def terms_for(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,}", text)
    out = []
    for w in words:
        wl = w.lower().strip("._-")
        if len(wl) < 3 or wl in STOP:
            continue
        out.append(w.strip("._-"))
    seen, res = set(), []
    for w in out:
        if w.lower() not in seen:
            seen.add(w.lower())
            res.append(w)
    return res[:6]


def evidence_pack(conn: sqlite3.Connection, claim: str, cap: int = 25) -> str:
    terms = terms_for(claim)
    if not terms:
        return "(no searchable terms)"
    clauses = " OR ".join("(content LIKE ? OR thread LIKE ? OR agent_id LIKE ?)" for _ in terms)
    params = [f"%{t}%" for t in terms for _ in range(3)]
    rows = conn.execute(
        f"SELECT ts, agent_id, thread, kind, content FROM records"  # noqa: S608
        f" WHERE {clauses} ORDER BY ts LIMIT ?",
        (*params, cap),
    ).fetchall()
    if not rows:
        return "(evidence pack EMPTY — keyword search returned no rows)"
    return "\n".join(
        f"[{ts}] {agent or '-'} @{thread or '-'} ({kind}): {str(content)[:140]}"
        for ts, agent, thread, kind, content in rows
    )


RUNS = 3


async def judge_claim(sie, model: str, claim: str, pack: str) -> str:
    raw = await sie.chat(
        model,
        [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": f"CLAIM: {claim}\n\nEVIDENCE PACK:\n{pack}",
            },
        ],
        max_tokens=256,
    )
    return raw


async def one_run(i: int, claims: list[dict], packs: list[str]) -> dict:
    from cantheria.chat import chat_model, make_chat

    model = chat_model()
    sie = make_chat()
    verdicts = []
    try:
        for c, pack in zip(claims, packs, strict=True):
            raw = await judge_claim(sie, model, c["claim"], pack)
            verdicts.append({"claim": c["claim"], "raw": raw})
    finally:
        await sie.close()
    return {"run": i, "verdicts": verdicts}


async def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    claims = [json.loads(line) for line in (HERE / "claims.jsonl").read_text().splitlines()]
    packs = [evidence_pack(conn, c["claim"]) for c in claims]
    conn.close()

    results = []
    for i in range(RUNS):  # sequential — gentle on the endpoint
        results.append(await one_run(i, claims, packs))
        print(f"--- run {i} done ---", flush=True)
    OUT.write_text(json.dumps({"packs": packs, "runs": results}, indent=2))
    for r in results:
        print(f"=== run {r['run']} ===")
        for v in r["verdicts"]:
            print(f"  {v['claim'][:60]:<62} → {v['raw'][:120]}")


if __name__ == "__main__":
    asyncio.run(main())
