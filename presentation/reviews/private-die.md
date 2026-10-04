# The Private Die — clause-level evidence review (Developer B)

Case: `private-die` · claim `94beae7e87a8` · run `hunt1`
Source: `runs/village/hunt1/results.json` + `REPORT.md`
Reviewed: 2026-10-04 (Developer B) against recorded artifacts.

## Recorded claim (verbatim)

> The agent initiated a computer session to roll a d6 privately to determine
> their role for Day 338.

- kind: `event` · subjects: `["agent"]` (generic — attribution gate skipped
  by design, see `oracle.py` GENERIC_SUBJECTS)
- window: 2026-03-05T18:01:56 → 18:01:57 UTC
- recorded verdict: `confirmed` · origin `mechanical-fallback`, attempt 3

## Clause review

| Clause | Verdict | Evidence |
|---|---|---|
| An agent announced an intent to roll a d6 privately | SUPPORTED | Receipt `aivillage:e50274fa-34fb-4616-9b02-3b9b3188acab` — `[AGENT_TALK] Exciting new goal! Time to roll my d6 privately. Let me start my computer session to determine my role for the day.` (Opus 4.5 (Claude Code), 2026-03-05T18:01:57, kind `event`) |
| A computer session was initiated (completed action) | QUALIFIED | The receipt announces the intent and names the session start; the record shows one `event` row only. Committed probe `expect` was `{min_rows: 1}` — satisfied by the announcement row. No separate session-start record is cited. The claim wording "initiated" exceeds what a single announcement row establishes. |
| The roll determined the agent's role for Day 338 | NOT ESTABLISHED | "Day 338" appears in the claim's hypothesis context and failed probe needles (`must_contain missing: Day 338` on attempts 1–3); the winning receipt's 400-char excerpt contains no "Day 338". The role outcome is not in evidence. |
| Attribution to a specific agent | PARTIAL | Receipt binds `Opus 4.5 (Claude Code)`; claim subject is the generic "agent" so the attribution leg passes vacuously. Site copy must name the agent from the receipt, not imply a broader subject. |

## Probe history (recorded)

1. Model draft: FTS `"d6 roll" AND "privately" AND "Day 338"`, kind=`event` → 0 rows (`must_contain missing: d6 roll, Day 338`).
2. Model draft: same FTS, kind=`chat`, agent IN (GPT-5.1/5/5.2/5.4) → 0 rows.
3. Model draft: same FTS, agent=`GPT-5.1` → 0 rows. (Wrong-agent narrowing; the true author is Opus 4.5.)
4. Mechanical fallback: FTS `"privately" AND "roll"`, window ±1s, generic-subject gate → 1 row, `ok:true`, 17-char… 1 receipt.
5. Control on disjoint window (2026-02-26): 0 rows → control clean.

## Review qualification for the site

`review.label` must read: "Reviewed: announcement verified; completion and
Day-338 role outcome exceed the receipt." `supported[]` carries only the
announcement clause. `unresolved[]` carries the initiation-vs-announcement
gap and the Day-338 outcome gap. The case title "The Private Die" is
editorial; the claim text stays verbatim.

## Provenance gaps (blockers, not silent)

- Corpus DB (`records.db`) is gitignored and no local copy exists in this
  checkout — deep-link URLs below are taken from the committed REPORT.md,
  not re-resolved against a live corpus. A must re-resolve or mark
  `sourceUrl: null` before publishing if links cannot be verified.
- Full corpus replay is not possible from this checkout (no records.db);
  reproduction commands must be labeled slice-replay until the demo tarball
  is present.
