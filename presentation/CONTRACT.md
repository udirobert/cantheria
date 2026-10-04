# Presentation case contract (v1)

Developer B produces the data; Developer A renders it. The UI must not infer
verdicts, invent missing checks, or recompute findings. B must not embed
layout-specific HTML in the evidence export.

Source of truth for rendering: `site/src/data/case.ts` (`SCHEMA_VERSION = 1`,
zod `caseFileSchema`). This document explains each field group's provenance
obligation — what B must supply and what A must not invent.

## Field groups

| Field group | Contents | B's obligation |
|---|---|---|
| Identity | Case ID (URL-safe slug), claim ID, corpus, run identity | Stable IDs; run id + source artifact path recorded in `run.sourceArtifact`; corpus name as stored (`records.db` basename or corpus label) |
| Narrative | Original claim text (verbatim), source passage, editorial title/question/deck | Claim text copied verbatim from `results.json`; source excerpt copied verbatim from the claims input file; title/question/deck are the only editorial prose and must be labeled as such |
| Outcome | Stored verdict (`recordedVerdict`), separate reviewed qualification (`review.label/supported/unresolved/assumptions`) | Stored verdict copied from results; review written by a human after reading receipts; never rewrite the stored verdict to match the review |
| History | Actual probe attempts, results, repairs, fallback (`steps[]` with `origin: model|mechanical|control|editorial`) | Every step corresponds to a real entry: `probe_history[i]` → `origin: model`, committed `probe` → `origin: mechanical` when `raw.probe_origin == "mechanical-fallback"` else `origin: model`, control execution → `origin: control`. `result.status` maps: `ok:true`→`passed`, `ok:false`→`failed`, `error` set→`error`. `receiptIds` must reference real receipts. Never invent a step. |
| Checks | Passed / failed / not-run, with reasons (`checks[]`: grounding, attribution, replication, control) | Derived from `raw.legs`: leg string starting with `ok`→`passed`; leg present but not ok→`failed`; leg absent / "not run"→`not-run`. Quote the leg string in `detail`. Do not upgrade "not run" to "passed". |
| Receipts | Record identity, excerpt, agent, time, provenance (`receipts[]` + `sourceUrl`) | `id` = `record_id`; `excerpt` = verbatim sample content (may truncate with `…`, never paraphrase); `agent/timestamp/kind` from the sample row; `sourceUrl` = deep link from REPORT.md / corpus `source_uri`, or `null` with the gap stated. Only rows the winning probe actually matched. |
| Annotations | Exact quote anchors, clearly labeled editorial notes (`annotations[]`: exact/prefix/suffix/label) | Anchors must resolve in the excerpt (site verifies via `resolveAnnotations`); labels are editorial (`announced intent`, `claimed completion`, …). Fail visibly: if an anchor is ambiguous/unresolved it must not render as support. |
| Reproduction | Commands, artifact links, scope limitations (`reproduction.commands/artifactUrl/limitations`) | Commands must be commands B actually ran or that CI runs; `artifactUrl` null until a release asset exists; `limitations` must state what replay does NOT prove (slice vs full corpus, semantic correctness). |

## Publication states

- `publication: "reviewed"` — clause-level review complete (see `reviews/`); eligible for the published site.
- `publication: "fixture"` — synthetic layout data owned by A in `site/src/data/fixture.ts`; must never reach the published demo. B never writes fixtures.

## Change protocol

Contract changes are agreed before either side implements them. Bumping
`SCHEMA_VERSION` requires updating `site/src/data/case.ts`, this doc, and all
files under `cases/` in the same change.
