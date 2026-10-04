# Cantheria — swarm claim verification

**An LLM proposes; the record decides.**

Swarm investigation runs on narration: agents write summaries, humans skim
them, and the narrative becomes fact. Cantheria treats every sentence as a
hypothesis — each claim must survive a mechanical evidence chain against
the normalized record, or it goes in the journal as unsupported. Nothing is
taken on faith, *including the verifier's own model*.

## Live demo

https://udirobert.github.io/cantheria/

- **Audit report** — 180 claims extracted from 16 official AI Village daily
  summaries, with evidence receipts deep-linking to the live village UI
- **Hunt report** — 25 agent-day segments, fully autonomous hypothesize→verify
- **Corpus 2** — the collusion.wiki incident report audited against its own
  underlying record (42k German-wiki edits/events/pastes): 108 claims,
  10 confirmed, receipts included
- **Replayable demo corpus** (18MB tarball) — `cantheria replay` re-runs every
  committed probe deterministically: **no model, no API key — 180/180 and
  108/108 verdict agreement** in seconds

## The findings (real data, real numbers)

Corpus 1: HF `aidigestorg/ai-village`, normalized to `records` —
3,646,303 rows (chat, events, memories, sessions, summaries, 2.5M
computer-use turns), 2025-04-02 → 2026-09-19.

Corpus 2: HF `leonidas1712/public-agent-coordination-artifacts` — the
collusion.wiki incident data (42,373 records: wiki revisions, save/delete
events, author labels, paste bodies), May–Sep 2026.

| run | corpus | claims | confirmed | dismissed | unverifiable |
|---|---|---|---|---|---|
| audit: 16 daily summaries | aivillage | 180 | 62 | 97 | 21 |
| hunt: 25 segments | aivillage | 24 | 1 | 14 | 9 |
| audit: collusion.wiki report | collusion | 108 | 10 | 81 | 16+1 flaky |
| hunt: 20 segments | collusion | 20 | 0 | 15 | 5 |

**Slop rate: 61%** of decidable daily-summary claims failed verification —
measured, not asserted. On the second corpus the pipeline inverts the lens:
it audits the *investigators' own incident report* — 10 of its claims
verified end-to-end (the Playwright `route.fulfill` bypass, SSH tunnels via
Pinggy/Serveo/localtunnel, the six-week moderator cleanup), while 89% of
its decidable claims could not be mechanically established against the
underlying record. Slop is not unique to agent-generated summaries —
human-written investigation reports fail verification too, which is exactly
why receipts must ship with the narrative.

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
curl -LO https://github.com/udirobert/cantheria/releases/download/v1.0.0/cantheria-demo.tar.gz
tar xzf cantheria-demo.tar.gz
cantheria replay demo/audit5/results.json --corpus demo/audit5/records.db
cantheria replay demo/hunt1/results.json --corpus demo/hunt1/records.db
cantheria replay demo/collusion-audit2/results.json --corpus demo/collusion-audit2/records.db

# full pipeline (needs a chat backend — see .env.example)
cantheria ingest data/aivillage --corpus records.db
cantheria audit records.db --claims summaries.jsonl
cantheria hunt records.db --segments 25
```

Design doc: `SWARM.md`. Demo narrative: `DEMO.md`.
Origin domain (LLM-assisted vuln falsification) intact under `cantheria/`.
