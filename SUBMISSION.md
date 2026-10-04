# Cantheria — swarm claim verification

**An LLM proposes; the record decides.**

Swarm investigation runs on narration: agents write summaries, humans skim
them, and the narrative becomes fact. Cantheria treats every sentence as a
hypothesis — each claim must survive a mechanical evidence chain against
the normalized record, or it goes in the journal as unsupported. Nothing is
taken on faith, *including the verifier's own model*.

## Live demo

https://thunder-timeline-simplified-interpreted.trycloudflare.com/

- **Audit report** — 180 claims extracted from 16 official AI Village daily
  summaries, with evidence receipts deep-linking to the live village UI
- **Hunt report** — 25 agent-day segments, fully autonomous hypothesize→verify
- **Replayable demo corpus** (17MB tarball) — `cantheria replay` re-runs every
  committed probe deterministically: **no model, no API key, 180/180 verdict
  agreement** in ~30 seconds

## The findings (real data, real numbers)

Corpus: HF `aidigestorg/ai-village`, normalized to `records` —
3,646,303 rows (chat, events, memories, sessions, summaries, 2.5M
computer-use turns), 2025-04-02 → 2026-09-19.

| run | claims | confirmed | dismissed | unverifiable |
|---|---|---|---|---|
| audit: 16 daily summaries | 180 | 62 | 97 | 21 |
| hunt: 25 segments | 24 | 1 | 14 | 9 |

**Slop rate: 61%** of decidable daily-summary claims failed verification —
measured, not asserted.

Three findings worth reading the receipts on:

- **The day that wasn't**: `summary:2026-07-03` went **0/12** — every claim
  dismissed on a day with 825 chats / ~2k events / 23k turns in the corpus.
  A whole official summary that evaporates under verification.
- **The thing nobody searched for**: hunt mode autonomously confirmed an
  agent starting a *private* session to roll a d6 to assign its own role —
  hidden randomization found without anyone writing a query for it.
- **The verifier auditing itself**: the Conjecture-843 claim's model-drafted
  probes failed 3× (over-constrained FTS); a mechanical fallback recovered
  17 records and confirmed it. If model probes were the oracle, our own
  slop rate would have been a fabrication. That failure mode — *the
  auditor's model producing false negatives* — is invisible to
  summarizers and dashboards.

## How it works

```
document ─fenced→ claim extraction ─→ atomic claims (event|pattern|
                                      coordination|absence|interpretive)
per claim:  draft probe → SELECT-only execution → repair loop
            → grounding → attribution → replication → control
            → verdict + receipts → append-only journal
```

The legs that matter: **control** runs the same probe on a disjoint
window/agent and requires it *not* to match — an actual false-positive
check on the claim. **Interpretive** claims are quarantined as
`unverifiable` at zero probe cost rather than force-answered. Probes are
SELECT-only, row-capped, watchdog-timed, on read-only handles; source
documents enter the model fenced, never as instructions.

## What this is not

Not a summarizer (it audits summaries), not RAG (claims carry executable
receipts or don't ship), not a trajectory dashboard (verdicts, not plots),
not a chatbot (the model's own probes are falsifiable drafts, and a
mechanical fallback arbitrates when they can't express the test).

## Reproduce

```bash
# keyless — deterministic replay of the committed probes
curl -O https://thunder-timeline-simplified-interpreted.trycloudflare.com/cantheria-demo.tar.gz
tar xzf cantheria-demo.tar.gz
cantheria replay demo/audit5/results.json --corpus demo/audit5/records.db
cantheria replay demo/hunt1/results.json --corpus demo/hunt1/records.db

# full pipeline (needs a chat backend — see .env.example)
cantheria ingest data/aivillage --corpus records.db
cantheria audit records.db --claims summaries.jsonl
cantheria hunt records.db --segments 25
```

Design doc: `SWARM.md`. Demo narrative: `DEMO.md`.
Origin domain (LLM-assisted vuln falsification) intact under `cantheria/`.
