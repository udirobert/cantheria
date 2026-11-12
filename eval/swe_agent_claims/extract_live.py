"""Extract atomic claims from the LIVE agents' own final reports.

The claims are decomposed by the same model that wrote the reports
(gemma-4-31b-it via the configured chat backend) — we do not author or
curate them. One deliberate pipeline choice, recorded here: the extractor
would attach `citations` quoting the report itself, but rule 1 of this
eval keeps the report out of the corpus — a source-document quote is
provenance (the claim's origin), never record evidence, and feeding it
to the oracle's citation leg would dismiss every document-extracted
claim for a reason that is an artifact of that design (measured: the
first live audit dismissed 4/4 true claims exactly this way). So
citations are dropped at extraction; the report files in live_reports/
are the provenance.

Output: claims_live.jsonl — same shape as the planted claims.jsonl, with
truth/note left empty for labeling against the record afterward.

Usage (Gemma 4 as extractor):
    env CANTHERIA_CHAT_BASE_URL=https://router.huggingface.co/v1 \
        CANTHERIA_CHAT_API_KEY=$HF_TOKEN \
        CANTHERIA_CHAT_MODEL=google/gemma-4-31B-it \
        uv run python eval/swe_agent_claims/extract_live.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORTS = HERE / "live_reports"
OUT = HERE / "claims_live.jsonl"


async def main() -> None:
    from cantheria.chat import make_chat
    from cantheria.swarm.extract import extract_claims
    from cantheria.swarm.hunt import SwarmBudget

    sie = make_chat()
    budget = SwarmBudget(max_llm_calls=20, max_probe_runs=0)
    rows: list[dict] = []
    try:
        for report in sorted(REPORTS.glob("tinyhttp-*.md")):
            claims = await extract_claims(
                sie, report.read_text(), report.name, "swe-agent-live", budget
            )
            for c in claims:
                rows.append(
                    {
                        "claim": c.text,
                        "kind": c.kind.value,
                        "subjects": c.subjects,
                        "window": c.window,
                        "source_doc": report.name,
                        "truth": "",  # filled by labeling against the record
                        "note": "",  # receipts: record ids that justify the label
                    }
                )
            print(f"{report.name}: {len(claims)} claims")
    finally:
        await sie.close()
    OUT.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(f"{len(rows)} claims -> {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
