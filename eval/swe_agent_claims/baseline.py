"""Naive LLM-judge baseline for the SWE-agent claims eval.

The foil to "an LLM proposes; the record decides": here a single chat call
gives the model the ENTIRE session dump plus all claims and asks for a
verdict per claim — the strongest version of "just ask the model". Same
claims, same corpus, same scoring as score.py.

The corpus is small enough to fit in context, which is exactly why this
baseline is unusually strong here and why the real pipeline's advantage
shows up on the larger corpora: the judge's verdicts carry no receipts and
cannot be replayed.

Usage: env -u FEATHERLESS_API_KEY uv run python eval/swe_agent_claims/baseline.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DB = ROOT / "runs" / "swe-agent" / "records.db"
OUT = ROOT / "runs" / "swe-agent" / "baseline.json"

SYSTEM = """\
You are auditing claims about a coding agent's session against that session's
record. For each numbered claim decide: does the record SUPPORT it,
CONTRADICT it, or is it UNDECIDABLE from the record? Be strict: a claim is
supported only if the record contains the specific evidence — the wrong file,
the wrong action, a wrong count, or fabricated details make it contradicted.
Reply with JSON only:
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
    return [
        json.loads(line)
        for line in (HERE / "claims.jsonl").read_text().splitlines()
        if line.strip()
    ]


RUNS = int(os.environ.get("BASELINE_RUNS", "1"))


async def one_run(i: int) -> dict:
    from cantheria.chat import chat_model, make_chat

    records = load_records()
    claims = load_claims()
    claim_block = "\n".join(f"{n}. {c['claim']}" for n, c in enumerate(claims, 1))
    user = "SESSION RECORD (chronological):\n" + records + "\n\nCLAIMS:\n" + claim_block

    sie = make_chat()
    try:
        raw = await sie.chat(
            chat_model(),
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user},
            ],
            max_tokens=4096,
            temperature=0.0,
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
        print(json.dumps(raw, indent=2)[:4000])
    asyncio.run(main())
