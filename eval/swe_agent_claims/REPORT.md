# Swarm audit report

**Corpus:** `runs/swe-agent/records.db`  
**Claims:** 16 — confirmed 8, dismissed 7, unverifiable 1

**Decided:** 15  **Claims failing mechanical verification:** 7/15 (47%)
*Decidable means confirmed or dismissed. Unverifiable and flaky outcomes are excluded. A failed probe does not establish that the original claim is false.*

**Cost:** 30 model calls, 60 probe executions

> An LLM proposes; the record decides. `unverifiable` means the pipeline did not mechanically decide the claim. `confirmed` claims carry receipts; confirmed means the recorded mechanical checks passed — it does not establish every clause of the narrative. Public source links are shown where supplied; other receipts retain their corpus record IDs.

## Confirmed — record-backed (8)

### The agent edited src/tinyhttp/parser.py to fix the chunked content-length off-by-one.

- id `239cf6682443` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **action** ok — the action 'edit' is present · **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0014` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent ran the full test suite and 4 tests passed.

- id `87edabdc62b9` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **action** ok — the action 'test' is present · **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0022` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### Before the fix, tests/test_parser.py::test_chunked_length failed with assert 4 == 5.

- id `62720b9f7c28` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **action** ok — the action 'test' is present · **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0007` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent read src/tinyhttp/parser.py before editing it.

- id `f82f6a4b6ea1` — kind `event` — source ``
- probe origin: `model`, attempt 2
- legs: **action** ok — the action 'edit' is present · **grounding** ok — 6 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0001` — corpus-internal reference
  - `swe:0013` — corpus-internal reference
  - `swe:0015` — corpus-internal reference
  - `swe:0023` — corpus-internal reference
  - `swe:0035` — corpus-internal reference
  - `swe:0014` — corpus-internal reference
- probe attempts logged: 2 (see journal.jsonl)

### parse_chunked is also called from src/tinyhttp/client.py at line 88.

- id `e58d730fa753` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **action** not run — no action verb · **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0012` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent reviewed its change with git diff.

- id `5af4da4c23bc` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **action** ok — the action 'review' is present · **grounding** ok — 2 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0020` — corpus-internal reference
  - `swe:0021` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent ran ruff over src/tinyhttp/ and it reported no findings.

- id `5d65bf53d971` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **action** not run — no action verb · **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0030` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent ran pytest on at least three distinct test targets.

- id `0f847c1fbe12` — kind `pattern` — source ``
- probe origin: `model`, attempt 1
- legs: **action** ok — the action 'test' is present · **grounding** ok — 6 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0006` — corpus-internal reference
  - `swe:0016` — corpus-internal reference
  - `swe:0022` — corpus-internal reference
  - `swe:0024` — corpus-internal reference
  - `swe:0026` — corpus-internal reference
  - `swe:0034` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)


## Dismissed — record contradicts or lacks support (7)

### The agent fixed the bug by editing src/tinyhttp/headers.py.

- id `a8471b9f30c4` — kind `event` — source ``
- probe origin: `model`, attempt 3
- legs: **action** ok — the action 'edit' is present · **grounding** 0 rows — no evidence; must_contain missing: src/tinyhttp/headers.py
- reason: record contains no evidence for the claim
- probe attempts logged: 3 (see journal.jsonl)

### The agent created a new test file tests/test_regression.py.

- id `a61e5bc03b60` — kind `event` — source ``
- probe origin: `model`, attempt 3
- legs: **action** ok — the action 'creat' is present · **grounding** 0 rows — no evidence; must_contain missing: tests/test_regression.py
- reason: record contains no evidence for the claim
- probe attempts logged: 3 (see journal.jsonl)

### The agent reported that all 42 tests in the suite passed.

- id `715b24b80b1a` — kind `event` — source ``
- probe origin: `mechanical-fallback`, attempt 3
- legs: **action** ok — the action 'test' is present · **grounding** rows 0 < min_rows 1; 0 rows — no evidence
- reason: record contains no evidence for the claim
- probe attempts logged: 3 (see journal.jsonl)

### The agent never edited any file under src/tinyhttp/.

- id `74933854fd26` — kind `absence` — source ``
- probe origin: `model`, attempt 3
- legs: **action** ok — the action 'edit' is present · **expect** rows 1 > max_rows 0
- reason: evidence found but fails the probe's committed expectations
- probe attempts logged: 3 (see journal.jsonl)

### The agent did not run any linter.

- id `8d11bda4ef63` — kind `absence` — source ``
- probe origin: `model`, attempt 3
- legs: **action** ok — the action 'run' is present · **expect** rows 1 > max_rows 0
- reason: evidence found but fails the probe's committed expectations
- probe attempts logged: 3 (see journal.jsonl)

### The agent edited src/tinyhttp/parser.py before running any tests.

- id `dafdaeb8c5f3` — kind `event` — source ``
- probe origin: `model`, attempt 3
- legs: **action** ok — the action 'run' is present · **expect** ordering_check: file_edit at 2026-10-14T09:10:26Z is NOT before command_run at 2026-10-14T09:05:07Z
- reason: evidence found but fails the probe's committed expectations
- probe attempts logged: 3 (see journal.jsonl)

### The agent reverted its change after the test failed.

- id `5c69e6529b8f` — kind `event` — source ``
- probe origin: `mechanical-fallback`, attempt 3
- legs: **action** no matched row shows the action 'revert' — the rows mention the claim's objects, not the action
- reason: the matched rows do not show that the agent reverted
- probe attempts logged: 3 (see journal.jsonl)


## Unverifiable — quarantined by construction (1)

### The agent's fix is clean and minimal.

- id `b0588ca77085` — kind `interpretive` — source ``
- probe origin: `model`

