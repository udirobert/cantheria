# SwarmTraces report audit — claims vs. the payload corpus

Audit of the SwarmTraces investigation report's own factual claims against
its published payload dataset — the same "audit the investigators" move as
the collusion.wiki audit, applied to the sprint's headline incident.

## Setup

- Corpus: `swarmtraces.org/data/final/redacted.jsonl.gz` (15 MB gz,
  189,579 rows: 91,037 payloads / 75,534 recovered_text / 23,008 responses;
  **zero timestamps, no agent or thread labels** — parent_id chains only).
- Ingested via `cantheria ingest --source swarmtraces` →
  `runs/swarmtraces/records.db`.
- Claims: `claims.jsonl` — 14 atomic claims distilled from the report's
  findings sections (LOOT, Slack search, inference APIs, evidence
  deletion, link-shortener chains, Kubernetes, CAPTCHA, DNS exfil,
  Docker Hub, >80k payloads, internal-network scanning, worker
  infrastructure, plus one interpretive and one agent-count claim).
- Run: `cantheria audit runs/swarmtraces/records.db --claims
  eval/swarmtraces_claims/claims.jsonl --out runs/swarmtraces/audit1
  --budget 200` → 16 model calls, 7 probe executions.

## Result

| verdict | n | notes |
|---|---|---|
| confirmed | 2 | Kubernetes references (1,525 matching rows corpus-wide), Docker Hub references (4,823 rows) — receipts in REPORT.md |
| unverifiable | 12 | see below |
| dismissed | 0 | |

Ground-truth spot check (direct SQL): every audited keyword exists in the
corpus — LOOT ×4, slack ×10, inference ×56, rm −rf ×207, kubernetes ×1,525,
docker ×4,823, captcha ×123, dns ×590. The report's factual claims are
largely *true of the record*; the pipeline confirmed the two it could
mechanically bind and quarantined the rest rather than bluffing.

## Why coverage collapsed — two honest failure modes

1. **Drafter abstention on unattributed corpora (~8 claims).** With no
   agent_id/timestamp/thread fields, pattern claims about payload content
   gave the probe-drafter nothing to bind; it declined → `unverifiable`.
   Safe, but a recall gap: the evidence exists (keywords match hundreds
   to thousands of rows) and a simpler content-LIKE probe would have
   confirmed most of them.
2. **Projection truncation defeated a committed expectation (LOOT).**
   The model drafted `substr(content,1,400)` for readability; the probe
   matched all 4 LOOT-bearing rows, but `must_contain: ["LOOT"]` was
   evaluated against the truncated projection → leg failed →
   `unverifiable`. The evidence was present; the probe's own SELECT hid
   it. The journal + matched_ids preserve enough for a human to re-run
   with full content — which is the point of receipts — but it is a
   real probe-authoring hazard worth fixing (evaluate must_contain on
   untruncated content, or forbid substr in probe SELECTs).

## What this run establishes

- The pipeline runs end-to-end on the incident's own payload corpus and
  refuses to overclaim: 2 confirmed with receipts, 12 quarantined, 0
  dismissed, 0 false confirmations.
- Claim verification needs corpus *structure* (agents, timestamps,
  threads) that raw payload dumps lack; on structureless corpora expect
  abstention-dominated coverage. Documented limitation, not hidden.
- It also stress-tests the report-audit thesis on the highest-stakes
  dataset: most of the report's checkable claims survive contact with the
  record, and the ones the pipeline could not decide are exactly the ones
  a human should inspect.

Reproduce:

```bash
curl -LO https://swarmtraces.org/data/final/redacted.jsonl.gz
uv run cantheria ingest data/swarmtraces/redacted.jsonl.gz \
  --corpus runs/swarmtraces/records.db --source swarmtraces
uv run cantheria audit runs/swarmtraces/records.db \
  --claims eval/swarmtraces_claims/claims.jsonl \
  --out runs/swarmtraces/audit1 --budget 200
```
