# PENDING fill — handoff for the paper editor

Prepared 2026-11-12 while the eval runs. Substitute `⟨…⟩` values from
`eval/swe_agent_claims/NUMBERS.md`. If NUMBERS.md does not exist at the
fill deadline, use OUTCOME B.

---

## §4 — replace the 【PENDING: results…】 block (line ~105)

Keep the lead-in paragraph ("The same audit path can ingest…") and insert
after it:

> The run is a planted coding-agent session of `⟨N records⟩` records —
> tool calls, edits, commands, test output, and one never-run command —
> with `⟨N claims⟩` atomic claims drawn from the session's final report.
> The report itself is not in the corpus. The reason is measured, not
> principled: with the report stored as a record, a false "tests pass"
> claim returned `confirmed` — the claim proving itself. With the report
> kept as the source document only, the same claim returns `unverifiable`.
>
> `⟨Result: e.g. X of Y true claims confirmed, 0 of Z false claims
> confirmed, W abstained.⟩` `⟨One caught-lie example, one sentence —
> e.g. "the claim 'all 42 tests pass' was unverifiable: no test_result
> record exists."⟩`

Optional table (only if NUMBERS.md has the counts):

| | confirmed | dismissed | unverifiable |
|---|---|---|---|
| true claims (⟨t⟩) | | | |
| false claims (⟨f⟩) | | | |
| interpretive (⟨i⟩) | | | |

Phrase the headline as **zero false confirmations** — absence traps
abstain by design (the drafter declines claims no record can settle), so
"all false claims caught" is not supported.

## Abstract (line ~11)

- If numbers land: replace "A transfer cell … is specified and still
  unnumbered 【PENDING: N】" with:
  > On a recorded coding-agent session with planted truth, the same
  > pipeline extracted `⟨N⟩` claims and confirmed `⟨x/y⟩` true claims
  > with zero false confirmations.
- OUTCOME B: delete the marker, keep "…is specified and still
  unnumbered." The sentence already reads honestly without it.

## Contributions (line ~21)

- If numbers land: "…and a transfer cell on recorded coding-agent
  sessions 【PENDING: N】" → "…and a transfer cell on a recorded
  coding-agent session (`⟨N⟩` claims, zero false confirmations)"
- OUTCOME B: delete the marker → "…and a transfer cell specified for
  recorded coding-agent sessions"

## Abstention taxonomy — add regardless of outcome (§3.2 / §6)

The synthetic eval's "5 of 7 false claims abstained" decomposes
(verified in `eval/synthetic_ground_truth/RESULTS.txt`):

- 3 claims about entities absent from the record (Ghost, runbook-beta,
  '7777')
- 1 false absence — undismissable by oracle construction
- 1 attribution trap — **decidable miss** ("Relay posted 'all clear'",
  North posted it). Name it as the known gap; do not fold it into
  "structural".

Two lines + the attribution sentence converts a blob weakness into a
failure taxonomy.

## §6 limits (line ~122)

- If numbers land: "The transfer demonstration is small-N 【PENDING: N】"
  → "The transfer demonstration is one session, `⟨N⟩` claims"
- OUTCOME B: → "The transfer demonstration is specified but unrun"

## Sanity checks before shipping

- `grep -n PENDING SUBMISSION_TEXT.md` must return nothing.
- Any number in the fill must appear verbatim in NUMBERS.md/RESULTS.txt.
- The caught-lie example must be a real claim id from claims.jsonl.
- §7 says "`python3 repro.py` … 21 checks" — if NUMBERS.md lands and the
  transfer-cell section stops being a SKIP, update that count.
- If the audit produced `flaky` verdicts: the stale FEATHERLESS_API_KEY
  was not unset — results with 'flaky' are degraded, do not ship them.
