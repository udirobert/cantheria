"""Whole-context judge foil for the external cell — the "just ask the model" baseline.

One call gets the entire session record plus all extracted claims and returns
a verdict per claim. Same corpus, same claims, same scoring as score_ext.py.

Usage (Gemma 4 as judge, 3 runs):
    env CANTHERIA_CHAT_BASE_URL=https://router.huggingface.co/v1 \
        CANTHERIA_CHAT_API_KEY=$HF_TOKEN \
        CANTHERIA_CHAT_MODEL=google/gemma-4-31B-it \
        BASELINE_RUNS=3 uv run python eval/swe_agent_external/baseline_ext.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DB = ROOT / "runs" / "swe-agent-ext" / "records.db"
OUT = HERE / "results_ext" / "baseline_ext.json"

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
        for line in (HERE / "claims_ext.jsonl").read_text().splitlines()
        if line.strip()
    ]


RUNS = int(os.environ.get("BASELINE_RUNS", "1"))


async def one_run(i: int) -> dict:
    from cantheria.chat import make_chat

    records = load_records()
    claims = load_claims()
    claim_block = "\n".join(f"{n}. {c['claim']}" for n, c in enumerate(claims, 1))
    user = "SESSION RECORD (chronological):\n" + records + "\n\nCLAIMS:\n" + claim_block

    sie = make_chat()
    try:
        raw = await sie.chat(
            "google/gemma-4-31B-it",
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
    asyncio.run(main())
