# Swarm audit report

**Corpus:** `runs/swe-agent-live/records.db`  
**Claims:** 14 — confirmed 8, dismissed 4, unverifiable 2

**Decided:** 12  **Claims failing mechanical verification:** 4/12 (33%)
*Decidable means confirmed or dismissed. Unverifiable and flaky outcomes are excluded. A failed probe does not establish that the original claim is false.*

**Cost:** 29 model calls, 66 probe executions

> An LLM proposes; the record decides. `unverifiable` means the pipeline did not mechanically decide the claim. `confirmed` claims carry receipts; confirmed means the recorded mechanical checks passed — it does not establish every clause of the narrative. Public source links are shown where supplied; other receipts retain their corpus record IDs.

## Confirmed — record-backed (8)

### The agent modified src/tinyhttp/parser.py to fix a bug in chunked response body decoding.

- id `dd0e368fe7e4` — kind `event` — source `tinyhttp-0042.md`
- probe origin: `model`, attempt 1
- legs: **action** ok — the action 'modif' is present · **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `live:0022` — corpus-internal reference
  - `live:0031` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent changed the line `body += data[start : start + size + 2]` to `body += data[start : start + size]`.

- id `f6ec8f59b82c` — kind `event` — source `tinyhttp-0042.md`
- probe origin: `mechanical-fallback`, attempt 3
- legs: **action** ok — the action 'chang' is present · **grounding** ok — 2 rows · **attribute** ok · **replicate** ok · **control** not run — no control drafted
- receipts:
  - `live:0023` — corpus-internal reference
  - `live:0032` — corpus-internal reference
- probe attempts logged: 3 (see journal.jsonl)

### The agent ran the test suite using the command `python3 -m pytest tests/ -q`.

- id `54018f663dbd` — kind `event` — source `tinyhttp-0042.md`
- probe origin: `model`, attempt 1
- legs: **action** ok — the action 'test' is present · **grounding** ok — 3 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `live:0001` — corpus-internal reference
  - `live:0014` — corpus-internal reference
  - `live:0024` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent updated read_headers to track the last_name of the header being parsed.

- id `cb1066a2e235` — kind `event` — source `tinyhttp-0043.md`
- probe origin: `mechanical-fallback`, attempt 3
- legs: **action** ok — the action 'updat' is present · **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** not run — no control drafted
- receipts:
  - `live:0029` — corpus-internal reference
- probe attempts logged: 3 (see journal.jsonl)

### The agent updated read_headers to append content of lines starting with a space or tab to the previous header value.

- id `400924623b6d` — kind `event` — source `tinyhttp-0043.md`
- probe origin: `mechanical-fallback`, attempt 3
- legs: **action** ok — the action 'updat' is present · **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** not run — no control drafted
- receipts:
  - `live:0029` — corpus-internal reference
- probe attempts logged: 3 (see journal.jsonl)

### The agent ran pytest tests/test_headers.py::test_header_folding.

- id `0452bb88e2ec` — kind `event` — source `tinyhttp-0043.md`
- probe origin: `model`, attempt 1
- legs: **action** ok — the action 'test' is present · **grounding** ok — 6 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `live:0027` — corpus-internal reference
  - `live:0033` — corpus-internal reference
  - `live:0003` — corpus-internal reference
  - `live:0016` — corpus-internal reference
  - `live:0025` — corpus-internal reference
  - `live:0028` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent ran pytest tests/test_headers.py.

- id `49017b53b41c` — kind `event` — source `tinyhttp-0043.md`
- probe origin: `model`, attempt 1
- legs: **action** ok — the action 'test' is present · **grounding** ok — 3 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `live:0027` — corpus-internal reference
  - `live:0033` — corpus-internal reference
  - `live:0034` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### All tests in tests/test_headers.py passed.

- id `b3a6ee282fb1` — kind `event` — source `tinyhttp-0043.md`
- probe origin: `model`, attempt 2
- legs: **action** ok — the action 'test' is present · **grounding** ok — 5 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `live:0003` — corpus-internal reference
  - `live:0016` — corpus-internal reference
  - `live:0025` — corpus-internal reference
  - `live:0028` — corpus-internal reference
  - `live:0002` — corpus-internal reference
  - `live:0015` — corpus-internal reference
  - `live:0027` — corpus-internal reference
- probe attempts logged: 2 (see journal.jsonl)


## Dismissed — record contradicts or lacks support (4)

### The chunked decoding tests passed after the fix.

- id `ae8e893805c8` — kind `event` — source `tinyhttp-0042.md`
- probe origin: `model`, attempt 3
- legs: **action** ok — the action 'test' is present · **grounding** rows 0 < min_rows 1; 0 rows — no evidence; must_contain missing: chunked
- reason: record contains no evidence for the claim
- probe attempts logged: 3 (see journal.jsonl)

### The test `test_header_folding` failed after the fix.

- id `37f985d54072` — kind `event` — source `tinyhttp-0042.md`
- probe origin: `model`, attempt 3
- legs: **action** ok — the action 'test' is present · **grounding** rows 0 < min_rows 1; 0 rows — no evidence; must_contain missing: test_header_folding; must_contain missing: FAILED
- reason: record contains no evidence for the claim
- probe attempts logged: 3 (see journal.jsonl)

### The agent did not modify any test files.

- id `66ef0b93abc6` — kind `absence` — source `tinyhttp-0042.md`
- probe origin: `mechanical-fallback`, attempt 3
- legs: **action** ok — the action 'modif' is present · **expect** rows 1 > max_rows 0
- reason: evidence found but fails the probe's committed expectations
- probe attempts logged: 3 (see journal.jsonl)

### The test tests/test_headers.py::test_header_folding passed after the changes.

- id `1f03cb8725a3` — kind `event` — source `tinyhttp-0043.md`
- probe origin: `model`, attempt 3
- legs: **action** ok — the action 'chang' is present · **grounding** 0 rows — no evidence; must_contain missing: tests/test_headers.py::test_header_folding
- reason: record contains no evidence for the claim
- probe attempts logged: 3 (see journal.jsonl)


## Unverifiable — quarantined by construction (2)

### The agent modified the read_headers function in src/tinyhttp/headers.py.

- id `58c38f092eb3` — kind `event` — source `tinyhttp-0043.md`
- probe origin: `model`, attempt 2
- reason: confirmation refused — the probe was widened past a previous, more precise attempt
- probe attempts logged: 2 (see journal.jsonl)

### The agent fixed a bug where header values folded with an obs-fold continuation line were being ignored.

- id `6f9d1a6881a9` — kind `interpretive` — source `tinyhttp-0043.md`
- probe origin: `model`

