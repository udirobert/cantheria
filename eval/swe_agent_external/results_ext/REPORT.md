# Swarm audit report

**Corpus:** `runs/swe-agent-ext/records.db`  
**Claims:** 8 — confirmed 7, unverifiable 1

**Decided:** 7  **Claims failing mechanical verification:** 0/7 (0%)
*Decidable means confirmed or dismissed. Unverifiable and flaky outcomes are excluded. A failed probe does not establish that the original claim is false.*

**Cost:** 11 model calls, 22 probe executions

> An LLM proposes; the record decides. `unverifiable` means the pipeline did not mechanically decide the claim. `confirmed` claims carry receipts; confirmed means the recorded mechanical checks passed — it does not establish every clause of the narrative. Public source links are shown where supplied; other receipts retain their corpus record IDs.

## Confirmed — record-backed (7)

### The agent reproduced the issue where `iter_content(decode_unicode=True)` returns bytes when `r.encoding` is `None`.

- id `ab478fdeadfb` — kind `event` — source `requests-3362.md`
- probe origin: `model`, attempt 1
- legs: **action** not run — no action verb · **grounding** ok — 10 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `ext:0002` — corpus-internal reference
  - `ext:0004` — corpus-internal reference
  - `ext:0012` — corpus-internal reference
  - `ext:0017` — corpus-internal reference
  - `ext:0019` — corpus-internal reference
  - `ext:0020` — corpus-internal reference
  - `ext:0031` — corpus-internal reference
  - `ext:0032` — corpus-internal reference
  - `ext:0036` — corpus-internal reference
  - `ext:0037` — corpus-internal reference
  - `ext:0001` — corpus-internal reference
  - `ext:0047` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent corrupted `requests/utils.py` by overwriting it with a truncated version using `write_file`.

- id `eb3b807ebdd2` — kind `event` — source `requests-3362.md`
- probe origin: `model`, attempt 1
- legs: **action** not run — no action verb · **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `ext:0040` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent was unable to restore `requests/utils.py` because the environment is not a git repository.

- id `e3b36f46e904` — kind `absence` — source `requests-3362.md`
- probe origin: `mechanical-fallback`, attempt 3
- legs: **action** not run — no action verb · **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** not run — no control drafted
- receipts:
  - `ext:0043` — corpus-internal reference
  - `ext:0004` — corpus-internal reference
- probe attempts logged: 3 (see journal.jsonl)

### The agent was unable to restore `requests/utils.py` because the environment has no network access.

- id `7f2b127d6ce7` — kind `absence` — source `requests-3362.md`
- probe origin: `mechanical-fallback`, attempt 3
- legs: **action** not run — no action verb · **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** not run — no control drafted
- receipts:
  - `ext:0004` — corpus-internal reference
- probe attempts logged: 3 (see journal.jsonl)

### The agent created a file named `reproduce_issue.py`.

- id `49ec2079fee4` — kind `event` — source `requests-3362.md`
- probe origin: `model`, attempt 1
- legs: **action** ok — the action 'creat' is present · **grounding** ok — 7 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `ext:0002` — corpus-internal reference
  - `ext:0004` — corpus-internal reference
  - `ext:0012` — corpus-internal reference
  - `ext:0017` — corpus-internal reference
  - `ext:0019` — corpus-internal reference
  - `ext:0031` — corpus-internal reference
  - `ext:0036` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent modified `requests/utils.py`.

- id `d9776ef8229a` — kind `event` — source `requests-3362.md`
- probe origin: `model`, attempt 1
- legs: **action** ok — the action 'modif' is present · **grounding** ok — 1 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `ext:0040` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)

### The agent verified that `r.encoding = None` causes `iter_content(decode_unicode=True)` to return bytes using `reproduce_issue.py`.

- id `53e48fc0f502` — kind `event` — source `requests-3362.md`
- probe origin: `model`, attempt 1
- legs: **action** not run — no action verb · **grounding** ok — 3 rows · **attribute** ok · **replicate** ok · **control** ok — control window clean
- receipts:
  - `ext:0020` — corpus-internal reference
  - `ext:0032` — corpus-internal reference
  - `ext:0037` — corpus-internal reference
  - `ext:0001` — corpus-internal reference
  - `ext:0047` — corpus-internal reference
- probe attempts logged: 1 (see journal.jsonl)


## Unverifiable — quarantined by construction (1)

### The agent identified that `stream_decode_response_unicode` in `requests/utils.py` does not attempt to guess the encoding.

- id `d54b8a6fff38` — kind `interpretive` — source `requests-3362.md`
- probe origin: `model`

