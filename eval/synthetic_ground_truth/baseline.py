"""Naive LLM-judge baseline for the synthetic ground-truth eval.

The foil to "an LLM proposes; the record decides": here a single chat call
gives the model the ENTIRE record dump plus all claims and asks for a
verdict per claim — the strongest version of "just ask the model". Same
claims, same corpus, same scoring as score.py.

Usage: env -u FEATHERLESS_API_KEY uv run python eval/synthetic_ground_truth/baseline.py
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DB = ROOT / "runs" / "synthetic-eval" / "records.db"
OUT = ROOT / "runs" / "synthetic-eval" / "baseline.json"

SYSTEM = """\
You are auditing claims about a group of AI agents against their message/event
record. For each numbered claim decide: does the record SUPPORT it, CONTRADICT
it, or is it UNDECIDABLE from the record? Be strict: a claim is supported only
if the record contains the specific evidence; wrong agent, wrong time, wrong
count, or fabricated details make it contradicted. Reply with JSON only:
{"verdicts": [{"i": <claim number>, "verdict": "supported"|"contradicted"|"undecidable"}]}"""


def load_records() -> str:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    lines = []
    for r in conn.execute("SELECT ts, agent_id, thread, kind, content FROM records ORDER BY ts"):
        lines.append(
            f"[{r['ts']}] {r['agent_id'] or '-'} @{r['thread'] or '-'} "
            f"({r['kind']}): {r['content']}"
        )
    conn.close()
    return "\n".join(lines)


def load_claims() -> list[dict]:
    return [json.loads(line) for line in (HERE / "claims.jsonl").read_text().splitlines()]


RUNS = int(__import__("os").environ.get("BASELINE_RUNS", "1"))


async def one_run(i: int) -> dict:
    from cantheria.chat import chat_model, make_chat

    records = load_records()
    claims = load_claims()
    claim_block = "\n".join(f"{i2}. {c['claim']}" for i2, c in enumerate(claims, 1))
    user = "RECORD (chronological):\n" + records + "\n\nCLAIMS:\n" + claim_block

    sie = make_chat()
    try:
        raw = await sie.chat(
            chat_model(),
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user},
            ],
            max_tokens=4096,
        )
    finally:
        await sie.close()
    return {"run": i, "raw": raw}


async def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    results = await asyncio.gather(*(one_run(i) for i in range(RUNS)))
    OUT.write_text(json.dumps(results if RUNS > 1 else results[0], indent=2))
    for r in results:
        print(f"--- run {r['run']} ---")
        print(r["raw"][:2500])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--parse":
        # offline re-parse of a saved raw response
        raw = json.loads(OUT.read_text())["raw"]
    asyncio.run(main())
