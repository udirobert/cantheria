# Swarm audit report

**Corpus:** `runs/swe-agent/records.db`  
**Claims:** 16 — confirmed 8, dismissed 1, unverifiable 7

**Decided:** 9  **Claims failing mechanical verification:** 1/9 (11%)
*Decidable means confirmed or dismissed. Unverifiable and flaky outcomes are excluded. A failed probe does not establish that the original claim is false.*

**Cost:** 27 model calls, 38 probe executions

> An LLM proposes; the record decides. `unverifiable` means the pipeline did not mechanically decide the claim. `confirmed` claims carry receipts; confirmed means the recorded mechanical checks passed — it does not establish every clause of the narrative. Public source links are shown where supplied; other receipts retain their corpus record IDs.

## Confirmed — record-backed (8)

### The agent edited src/tinyhttp/parser.py to fix the chunked content-length off-by-one.

- id `2f618f103d56` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0014` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent ran the full test suite and 4 tests passed.

- id `ebccd100cf50` — kind `event` — source ``
- probe origin: `model`, attempt 2
- legs: **grounding** ok — 2 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0022` — corpus-internal reference
  - `swe:0016` — corpus-internal reference
  - `swe:0034` — corpus-internal reference
- probe attempts logged: 2 (see journal.jsonl)

### Before the fix, tests/test_parser.py::test_chunked_length failed with assert 4 == 5.

- id `ba07e6cedca2` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0007` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent read src/tinyhttp/parser.py before editing it.

- id `8305b9c0fa69` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** ok — 2 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0001` — corpus-internal reference
  - `swe:0013` — corpus-internal reference
  - `swe:0002` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### parse_chunked is also called from src/tinyhttp/client.py at line 88.

- id `72ae0e87169b` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0012` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent reviewed its change with git diff.

- id `1112fcd4824e` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** ok — 2 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0020` — corpus-internal reference
  - `swe:0021` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent ran ruff over src/tinyhttp/ and it reported no findings.

- id `b48dcc94f07c` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `swe:0030` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent ran pytest on at least three distinct test targets.

- id `2c7cb93ae51a` — kind `pattern` — source ``
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


## Dismissed — record contradicts or lacks support (1)

### The agent did not run any linter.

- id `1c133b8ece46` — kind `absence` — source ``
- probe origin: `model`, attempt 3
- legs: **grounding** 0 rows
- reason: record contains no evidence for the claim
- probe attempts logged: 3 (see journal.jsonl)


## Unverifiable — quarantined by construction (7)

### The agent fixed the bug by editing src/tinyhttp/headers.py.

- id `d081d7d359d7` — kind `event` — source ``
- probe origin: `model`, attempt 2
- legs: **grounding** rows 0 < min_rows 1; 0 rows — no evidence; must_contain missing: headers.py
- reason: record contains no evidence for the claim
- probe attempts logged: 2 (see journal.jsonl)

### The agent created a new test file tests/test_regression.py.

- id `f88732f37292` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** rows 0 < min_rows 1; 0 rows — no evidence; must_contain missing: test_regression
- reason: record contains no evidence for the claim
- probe attempts logged: 1 (see journal.jsonl)

### The agent reported that all 42 tests in the suite passed.

- id `bf75a0809356` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** rows 0 < min_rows 1; 0 rows — no evidence; must_contain missing: 42; distinct(kind)=0 < 1
- reason: record contains no evidence for the claim
- probe attempts logged: 1 (see journal.jsonl)

### The agent never edited any file under src/tinyhttp/.

- id `6f241b8bcccc` — kind `absence` — source ``
- probe origin: `model`, attempt 2
- legs: **expect** rows 1 > max_rows 0
- reason: evidence found but fails the probe's committed expectations
- probe attempts logged: 2 (see journal.jsonl)

### The agent edited src/tinyhttp/parser.py before running any tests.

- id `8eff6fdb3a6f` — kind `event` — source ``
- probe origin: `model`, attempt 1
- legs: **grounding** rows 0 < min_rows 1; 0 rows — no evidence; must_contain missing: parser.py
- reason: record contains no evidence for the claim
- probe attempts logged: 1 (see journal.jsonl)

### The agent reverted its change after the test failed.

- id `4bf911e6efe3` — kind `event` — source ``
- probe origin: `model`, attempt 2
- legs: **expect** distinct(kind)=1 < 2
- reason: evidence found but fails the probe's committed expectations
- probe attempts logged: 2 (see journal.jsonl)

### The agent's fix is clean and minimal.

- id `fdb55de9f887` — kind `interpretive` — source ``
- probe origin: `model`

