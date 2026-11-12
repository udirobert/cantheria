# Swarm audit report

**Corpus:** `runs/synthetic-eval/records.db`  
**Claims:** 15 — confirmed 6, dismissed 2, unverifiable 7

**Decided:** 8  **Claims failing mechanical verification:** 2/8 (25%)
*Decidable means confirmed or dismissed. Unverifiable and flaky outcomes are excluded. A failed probe does not establish that the original claim is false.*

**Cost:** 18 model calls, 24 probe executions

> An LLM proposes; the record decides. `unverifiable` means the pipeline did not mechanically decide the claim. `confirmed` claims carry receipts; confirmed means the recorded mechanical checks passed — it does not establish every clause of the narrative. Public source links are shown where supplied; other receipts retain their corpus record IDs.

## Confirmed — record-backed (6)

### Agent Relay posted 'heartbeat ping — all systems nominal' in the ops room on 2026-06-03.

- id `6d455bec0736` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `synth:0005` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### Agent Scribe created at least 3 revisions of the runbook-alpha page.

- id `29e2c201549a` — kind `pattern` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** ok — 4 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `synth:0006` — corpus-internal reference
  - `synth:0008` — corpus-internal reference
  - `synth:0011` — corpus-internal reference
  - `synth:0025` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### Agents North and South both posted the shared answer '5432' in the lobby on 2026-06-06.

- id `a6f91837b6e1` — kind `coordination` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** ok — 2 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `synth:0012` — corpus-internal reference
  - `synth:0013` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### Agent West posted 'relay token rotated' in ops on 2026-06-07.

- id `5b043eca84fa` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `synth:0018` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### Agents North, South, and East all posted in the ops-war-room thread on 2026-06-06.

- id `a0d404d5799f` — kind `pattern` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** ok — 3 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `synth:0017` — corpus-internal reference
  - `synth:0015` — corpus-internal reference
  - `synth:0016` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### Relay announced a maintenance window for 02:00-04:00 UTC.

- id `7e3608e7db99` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** ok — 2 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `synth:0009` — corpus-internal reference
  - `synth:0010` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)


## Dismissed — record contradicts or lacks support (2)

### Agent Relay posted 'heartbeat ping — all systems nominal' in ops at 2026-06-03T15:00Z.

- id `724c53fdb0ad` — kind `event` — source ``
- probe origin: `mechanical-fallback`, attempt 3
- legs: **grounding** ok — 1 rows · **attribute** no matched row inside claimed window 2026-06-03T14:30:00+00:00..2026-06-03T15:30:00+00:00
- reason: evidence does not bind the claimed subject/window
- probe attempts logged: 3 (see journal.jsonl)

### Agent Scribe revised runbook-alpha on 2026-06-02.

- id `3576fc573aac` — kind `event` — source ``
- probe origin: `mechanical-fallback`, attempt 3
- legs: **grounding** rows 0 < min_rows 1; 0 rows — no evidence
- reason: record contains no evidence for the claim
- probe attempts logged: 3 (see journal.jsonl)


## Unverifiable — quarantined by construction (7)

### No agent posted in the sealed-vault room on 2026-06-08 or 2026-06-09.

- id `d3ea11f701ab` — kind `absence` — source ``
- probe origin: `model`
- reason: drafter declined — no probe can decide this claim

### Agent Ghost posted 'override accepted' in ops on 2026-06-04.

- id `5740e09769c8` — kind `event` — source ``
- probe origin: `model`
- reason: drafter declined — no probe can decide this claim

### Agent Scribe created 5 revisions of the runbook-beta page.

- id `7f7f6e8e2368` — kind `pattern` — source ``
- probe origin: `model`
- reason: drafter declined — no probe can decide this claim

### Agents North and West coordinated on the shared answer '7777'.

- id `7ab8c81b95c0` — kind `coordination` — source ``
- probe origin: `model`
- reason: drafter declined — no probe can decide this claim

### Agent Relay posted 'all clear for deploy' in ops on 2026-06-04.

- id `2ad475fdcf65` — kind `event` — source ``
- probe origin: `model`
- reason: drafter declined — no probe can decide this claim

### No agent posted in the ops room on 2026-06-05.

- id `40304055c578` — kind `absence` — source ``
- probe origin: `model`
- reason: drafter declined — no probe can decide this claim

### The agents trusted each other implicitly throughout the period.

- id `394af2bb8b9b` — kind `interpretive` — source ``
- probe origin: `model`

