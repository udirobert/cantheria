# Swarm audit report

**Corpus:** `runs/swe-agent/records.db`  
**Claims:** 16 — confirmed 7, dismissed 2, unverifiable 7

**Decided:** 9  **Claims failing mechanical verification:** 2/9 (22%)
*Decidable means confirmed or dismissed. Unverifiable and flaky outcomes are excluded. A failed probe does not establish that the original claim is false.*

**Cost:** 26 model calls, 42 probe executions

> An LLM proposes; the record decides. `unverifiable` means the pipeline did not mechanically decide the claim. `confirmed` claims carry receipts; confirmed means the recorded mechanical checks passed — it does not establish every clause of the narrative. Public source links are shown where supplied; other receipts retain their corpus record IDs.

## Confirmed — record-backed (7)

### The agent edited src/tinyhttp/parser.py to fix the chunked content-length off-by-one.

- id `79f786f93339` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0014` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### Before the fix, tests/test_parser.py::test_chunked_length failed with assert 4 == 5.

- id `9d6bc2a19f8e` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0007` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent read src/tinyhttp/parser.py before editing it.

- id `3ce50146aa82` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** ok — 2 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0001` — corpus-internal reference
  - `swe:0013` — corpus-internal reference
  - `swe:0002` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### parse_chunked is also called from src/tinyhttp/client.py at line 88.

- id `b21ab70c60b6` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0012` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent reviewed its change with git diff.

- id `0ffef34a24e9` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** ok — 2 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0020` — corpus-internal reference
  - `swe:0021` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent ran ruff over src/tinyhttp/ and it reported no findings.

- id `b06afa74c57f` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0030` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent ran pytest on at least three distinct test targets.

- id `df47da436392` — kind `pattern` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** ok — 6 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0006` — corpus-internal reference
  - `swe:0016` — corpus-internal reference
  - `swe:0022` — corpus-internal reference
  - `swe:0024` — corpus-internal reference
  - `swe:0026` — corpus-internal reference
  - `swe:0034` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)


## Dismissed — record contradicts or lacks support (2)

### The agent did not run any linter.

- id `d08d13d11934` — kind `absence` — source ``
- probe origin: `model`, attempt 3
- legs: **grounding** 0 rows
- reason: record contains no evidence for the claim
- probe attempts logged: 3 (see journal.jsonl)

### The agent edited src/tinyhttp/parser.py before running any tests.

- id `b7904338e978` — kind `event` — source ``
- probe origin: `mechanical-fallback`, attempt 3
- legs: **grounding** ok — 1 rows · **attribute** no matched row inside claimed window 2026-10-14T09:00:00+00:00..2026-10-14T09:11:00+00:00
- reason: evidence does not bind the claimed subject/window
- probe attempts logged: 3 (see journal.jsonl)


## Unverifiable — quarantined by construction (7)

### The agent ran the full test suite and 4 tests passed.

- id `0070b4136f0d` — kind `event` — source ``
- probe origin: `model`, attempt 2
- reason: confirmation refused — the probe was widened past a previous, more precise attempt
- probe attempts logged: 2 (see journal.jsonl)

### The agent fixed the bug by editing src/tinyhttp/headers.py.

- id `06e44204b316` — kind `event` — source ``
- probe origin: `model`, attempt 2
- legs: **grounding** rows 0 < min_rows 1; must_contain missing: headers.py
- reason: record contains no evidence for the claim
- probe attempts logged: 2 (see journal.jsonl)

### The agent created a new test file tests/test_regression.py.

- id `8fa84b4777ec` — kind `event` — source ``
- probe origin: `model`
- reason: drafter declined — no probe can decide this claim

### The agent reported that all 42 tests in the suite passed.

- id `6edda240b117` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** rows 0 < min_rows 1; 0 rows — no evidence; must_contain missing: 42; distinct(kind)=0 < 1
- reason: record contains no evidence for the claim
- probe attempts logged: 1 (see journal.jsonl)

### The agent never edited any file under src/tinyhttp/.

- id `8bee0c4d258b` — kind `absence` — source ``
- probe origin: `model`, attempt 2
- legs: **expect** rows 1 > max_rows 0
- reason: evidence found but fails the probe's committed expectations
- probe attempts logged: 2 (see journal.jsonl)

### The agent reverted its change after the test failed.

- id `2e32fdac7b5c` — kind `event` — source ``
- probe origin: `model`, attempt 2
- reason: confirmation refused — the probe was widened past a previous, more precise attempt
- probe attempts logged: 2 (see journal.jsonl)

### The agent's fix is clean and minimal.

- id `6fd37471235b` — kind `interpretive` — source ``
- probe origin: `model`

