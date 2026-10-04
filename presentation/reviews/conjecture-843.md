# The Canary That Misled Us — clause-level evidence review (Developer B)

Case: `conjecture-843` · claim `236ef07d0453` · run `audit3`
Source: `runs/village/audit3/results.json` + `REPORT.md` + full receipt
contents fetched from the corpus DB (server) for all 17 matched IDs.
Reviewed: 2026-10-04 (Developer B). Slice `presentation/inputs/audit3-slice.db` replays 24/24.

## Recorded claim (verbatim)

> Claude Opus 5 disproved Conjecture 843 at [2026-08-31 11:18:34 PT] using
> an elegant 24-odd-cycle partition.

## Clause review

| Clause | Verdict | Evidence |
|---|---|---|
| Disproof announced by Claude Opus 5 at 11:18 PT, with counterexample (icosahedral Goldberg GP(2,2), 240 vertices) and certificate (12 pentagons + 12 15-cycles, bounds 108 vs 112) | SUPPORTED | `aivillage:943a5fa6` (DeepSeek-V4-Pro SEARCH_HISTORY quoting the announcement). Corroboration, not first-party. |
| Method was a 24-odd-cycle partition | DESCRIBED, NOT INDEPENDENTLY VALIDATED | The announcement describes 12 pentagons plus 12 fifteen-cycles: 24 odd cycles. The committed probe did not execute or validate that construction. |
| Formally verified with 47,780 checks EXIT 0 | NOT IN EVIDENCE | Source-summary wording only; zero receipts. |
| Attribution to Claude Opus 5 | WEAK | Other agents records about the announcement (content-mention), not authorship. |
| 16 further matched rows | MATCHED, NOT SUBSTANTIVE | Fetched all 17 in full: the other 16 are memory headers with no conjecture content \u2014 they matched date+number co-occurrence, not the claim. Case carries the 12 with REPORT.md links; 5 capped, noted in review. |

## Probe history (recorded)

1. Model draft (all four needles incl "using") \u2192 0 rows.
2-3. Unquoted FTS alternation \u2192 `sqlite: no such column: odd` (quoting bug, not a crash).
4. Mechanical fallback \u2192 17 rows ok. 5. Control \u2192 clean.

## Lead review clarification

The absence of the exact literal phrase "24-odd-cycle" is not the absence of the
method description: the receipt describes the method in equivalent terms (12
pentagons + 12 fifteen-cycles = 24 odd cycles). "The receipt describes the method
in equivalent terms. This is evidence of the announcement, not an independent
proof check."
