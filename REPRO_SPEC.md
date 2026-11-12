# Task spec — `repro.py` (one command reprints every headline number)

Owner: the paper editor (Agent C). Build while the swe_agent_claims eval
runs. Do NOT touch `eval/swe_agent_claims/` — that directory is owned by
the eval builder.

## Why

The writeup's sharpest verifiability weakness: no single script reprints
every headline number. `repro.py` converts that into a strength — one
command, CPU-only, no model calls, no network, prints a check table where
each paper claim is recomputed from stored artifacts and marked
MATCH/MISS.

## File

`cantheria/repro.py` — stdlib only, `python3 repro.py`, exit 0 on all
match. Sections degrade to `SKIP` (not failure) if a sibling repo or
file is absent. Repos are expected as siblings: `../lemma`, `../elcaro`.

## Sections (in paper order)

### 1. Probe pipeline — planted truth (this repo)

Source of truth: `runs/synthetic-eval/audit2/results.json` +
`eval/synthetic_ground_truth/claims.jsonl` + `score.py` logic.
Recompute and assert:

- precision on confirmed: 6/6 (100%)
- false confirmations: 0/7
- true-claim recall: 6/7 (86%)
- interpretive quarantined: 1/1
- abstention taxonomy (paper §3.2 / §6): of the 5 false-claim
  abstentions — 3 nonexistent-entity, 1 false-absence (structural),
  1 attribution trap (decidable miss — print it, don't hide it)

### 2. Probe pipeline — real agent text

Source: the stored AI Village audit outputs (find the results file the
README references; if it can't be located, SKIP with the path tried).
Assert: 180 claims → 62 confirmed, 97 dismissed, 21 unverifiable;
61% of the 159 decidable failed.

### 3. Auditor (lemma)

Source: `../lemma/papers/*/results/audit_report.json` + improve logs.
Recompute: 48 claims across 9 paper dirs → 29 supported, 9 falsified,
10 inconclusive; 7 completed judge runs all PASS 5/5; the verify_gain
event in `improve_20261022-164946.json` (JMLR 22-1228 workdir): C1
falsified→supported flagged, C2/C4/C5 unmoved.

### 4. Injection benchmark (elcaro)

Source: `../elcaro/lexsi-eval/results-{naive,,wrapped}/summary.json` +
`results-safetune/comparison.json`. Recompute and assert the slot-2
table: 32B concealed 24/24/12, compromised 27/24/15; T21 18/18
concealed across arms; SafeTune 5→6 compromised, T13 new canary_code
failure. (Do not re-run run_eval.py — read the summaries. `selftest.py`
may be invoked if fast.)

### 5. Transfer cell (conditional)

If `eval/swe_agent_claims/NUMBERS.md` exists when this ships: add a
section replaying its score.py on the committed corpus. If absent, the
section prints `SKIP — eval pending`. Never fabricate.

## Output shape

```
repro.py — reprinting headline numbers (no model calls, no network)

[1] probe pipeline / planted truth
    confirmed precision ......... 6/6   MATCH
    false confirmations ......... 0/7   MATCH
    ...
    abstention taxonomy ......... 3 nonexistent, 1 absence, 1 attribution-miss   MATCH

SUMMARY: 14/15 checks match, 1 skip (transfer cell pending)
```

## Constraints

- Read-only over every artifact. No writes outside stdout.
- Every expected value in the script must match the paper text — the
  script IS the consistency check; a MISS is a paper bug to fix.
- Where the paper says a number, the script must print that same
  number — drift between the two is a MISS, not a pass to paper over.
- ≤ ~200 lines. If a section needs more, print SKIP with the reason.
