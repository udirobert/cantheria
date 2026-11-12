"""Extract atomic claims from the external agent's own final report.

Same model that wrote the report (gemma-4-31B-it via the HF router).
Citations are dropped at extraction for the same rule-1 reason as the
live cell: the report is the source document, never record evidence.

Output: claims_ext.jsonl with truth/note empty for labeling against the
record afterward.

Usage:
    env CANTHERIA_CHAT_BASE_URL=https://router.huggingface.co/v1 \
        CANTHERIA_CHAT_API_KEY=$HF_TOKEN \
        CANTHERIA_CHAT_MODEL=google/gemma-4-31B-it \
        uv run python eval/swe_agent_external/extract_ext.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORTS = HERE / "ext_reports"
OUT = HERE / "claims_ext.jsonl"


async def main() -> None:
    from cantheria.chat import make_chat
    from cantheria.swarm.extract import extract_claims
    from cantheria.swarm.hunt import SwarmBudget

    sie = make_chat()
    budget = SwarmBudget(max_llm_calls=20, max_probe_runs=0)
    rows: list[dict] = []
    try:
        for report in sorted(REPORTS.glob("requests-*.md")):
            claims = await extract_claims(
                sie, report.read_text(), report.name, "swe-agent-ext", budget
            )
            for c in claims:
                rows.append(
                    {
                        "claim": c.text,
                        "kind": c.kind.value,
                        "subjects": c.subjects,
                        "window": c.window,
                        "source_doc": report.name,
                        "truth": "",
                        "note": "",
                    }
                )
            print(f"{report.name}: {len(claims)} claims")
    finally:
        await sie.close()
    OUT.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(f"{len(rows)} claims -> {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
