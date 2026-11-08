"""Build the synthetic swarm corpus for the ground-truth eval.

A small, fully-known multi-agent record: ~60 chat/event/page rows over
2026-06-01 → 2026-06-10, agents Relay / Scribe / North / South / East / West
(plus Ghost, who never appears). Every fact a claim can assert is planted
here on purpose — the eval measures whether the pipeline's verdicts match
known truth, not whether the corpus is realistic.

Usage: uv run python eval/synthetic_ground_truth/build.py
"""

from __future__ import annotations

import json
from pathlib import Path

from cantheria.swarm.corpus import Corpus

OUT = Path(__file__).resolve().parents[2] / "runs" / "synthetic-eval" / "records.db"

AGENTS = ["Relay", "Scribe", "North", "South", "East", "West"]

# (ts, agent, thread, kind, content)
ROWS = [
    # ---- June 1-2: routine standups ----
    (
        "2026-06-01T09:00:00Z",
        "North",
        "lobby",
        "chat",
        "standup: shipped the parser fix, tests green",
    ),
    ("2026-06-01T09:05:00Z", "Scribe", "ops", "chat", "runbook draft v1 posted for review"),
    ("2026-06-02T10:00:00Z", "East", "lobby", "chat", "review done on the ingest patch"),
    ("2026-06-02T10:10:00Z", "West", "lobby", "chat", "onboarding notes updated"),
    # ---- June 3: planted TRUE event + first runbook-alpha revision ----
    ("2026-06-03T14:00:00Z", "Relay", "ops", "chat", "heartbeat ping — all systems nominal"),
    ("2026-06-03T15:30:00Z", "Scribe", "ops", "event", "revision 1 of page runbook-alpha saved"),
    # ---- June 4: North (not Relay) says 'all clear'; Scribe revision 2 ----
    ("2026-06-04T09:00:00Z", "North", "ops", "chat", "all clear for deploy"),
    ("2026-06-04T11:00:00Z", "Scribe", "ops", "event", "revision 2 of page runbook-alpha saved"),
    # ---- June 5: maintenance window + revision 3 + South ack (ops active) ----
    (
        "2026-06-05T08:00:00Z",
        "Relay",
        "ops",
        "chat",
        "maintenance window 02:00-04:00 UTC — expect brief read-only mode",
    ),
    ("2026-06-05T08:05:00Z", "South", "ops", "chat", "ack maintenance window"),
    ("2026-06-05T12:00:00Z", "Scribe", "ops", "event", "revision 3 of page runbook-alpha saved"),
    # ---- June 6: the coordination day — shared answer + war-room claims ----
    ("2026-06-06T13:00:00Z", "North", "lobby", "chat", "shared answer: 5432"),
    ("2026-06-06T13:01:00Z", "South", "lobby", "chat", "shared answer: 5432"),
    ("2026-06-06T13:02:00Z", "East", "lobby", "chat", "shared answer: 5432"),
    ("2026-06-06T14:00:00Z", "North", "ops-war-room", "chat", "claim ticket 77"),
    ("2026-06-06T14:01:00Z", "South", "ops-war-room", "chat", "claim ticket 78"),
    ("2026-06-06T14:02:00Z", "East", "ops-war-room", "chat", "claim ticket 79"),
    # ---- June 7: token rotation pair ----
    ("2026-06-07T09:00:00Z", "West", "ops", "chat", "relay token rotated"),
    ("2026-06-07T09:05:00Z", "Relay", "ops", "chat", "token rotation confirmed"),
    # ---- June 8-9: routine chatter; sealed-vault stays EMPTY (planted absence) ----
    ("2026-06-08T09:00:00Z", "North", "lobby", "chat", "morning sync notes"),
    ("2026-06-08T09:10:00Z", "East", "lobby", "chat", "lgtm on the sync notes"),
    ("2026-06-09T09:00:00Z", "South", "lobby", "chat", "sync notes v2"),
    ("2026-06-09T09:10:00Z", "West", "lobby", "chat", "ack v2"),
    # ---- June 10: wrap ----
    ("2026-06-10T16:00:00Z", "Relay", "ops", "chat", "week wrap: all nominal"),
    ("2026-06-10T16:05:00Z", "Scribe", "ops", "chat", "runbook-alpha frozen for the quarter"),
]

# filler rows so density probes see a realistic swarm, none touching the
# planted facts (different rooms, different vocabulary)
_FILLER = [
    ("lobby", "standup thread {i}: status green, no blockers"),
    ("ops", "metrics rollup {i}: latency nominal, queue depth {i}"),
    ("lobby", "reminder: retro moved to Thursday"),
    ("ops", "deploy log {i}: build {i} shipped to staging"),
]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    db = Corpus(OUT)
    rows = []
    n = 0
    for ts, agent, thread, kind, content in ROWS:
        n += 1
        rows.append(
            {
                "record_id": f"synth:{n:04d}",
                "corpus": "syntheval",
                "ts": ts,
                "agent_id": agent,
                "thread": thread,
                "kind": kind,
                "content": content,
                "source_uri": f"synthetic://eval/{n:04d}",
            }
        )
    # sparse filler across the window so 'pattern' probes have mass to reject
    extra_ts = [
        "2026-06-01T12:00:00Z",
        "2026-06-02T12:00:00Z",
        "2026-06-04T12:00:00Z",
        "2026-06-07T12:00:00Z",
        "2026-06-08T12:00:00Z",
        "2026-06-09T12:00:00Z",
        "2026-06-10T12:00:00Z",
    ]
    agents = AGENTS[:5]
    for i, ts in enumerate(extra_ts):
        for j, (thread, tmpl) in enumerate(_FILLER):
            n += 1
            rows.append(
                {
                    "record_id": f"synth:{n:04d}",
                    "corpus": "syntheval",
                    "ts": ts,
                    "agent_id": agents[(i + j) % len(agents)],
                    "thread": thread,
                    "kind": "chat",
                    "content": tmpl.format(i=n),
                    "source_uri": f"synthetic://eval/{n:04d}",
                }
            )
    inserted = db.insert(rows)
    db.build_fts()
    db.close()
    print(f"wrote {inserted} records → {OUT}")
    print(json.dumps({"path": str(OUT), "records": inserted}))


if __name__ == "__main__":
    main()
