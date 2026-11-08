# M1 — Evidence and language baseline (Developer B working notes)

Owner: Developer B. Scope: `presentation/`, `DEMO.md`, `SUBMISSION.md`,
`SWARM.md`, `README.md` (prose only). Developer A owns `site/`.
The shared contract is `presentation/CONTRACT.md`; the renderer schema is
`site/src/data/case.ts` (SCHEMA_VERSION 1).

## Featured cases — review state

| Case | Claim | Run | State | Qualification |
|---|---|---|---|---|
| private-die ("The Private Die") | `94beae7e87a8` — d6 roll | `runs/village/hunt1` | REVIEWED — `presentation/cases/private-die.json` parses + anchors resolve `ok/ok` | Announcement verified; initiation + Day-338 outcome exceed the receipt. See `reviews/private-die.md`. |
| conjecture-843 ("The Canary That Misled Us") | `236ef07d0453` — Conjecture 843 | `runs/village/audit3` | REVIEWED — `presentation/cases/conjecture-843.json` (12 receipts, 5 steps, anchors ok/ok/ok); review `reviews/conjecture-843.md` | Corroborating record describes an announcement and a 24-odd-cycle certificate; the committed probe did not validate the construction or formal verification count. All 17 matched IDs fetched in full: 16 are memory headers with no conjecture content. Slice `inputs/audit3-slice.db` replays 24/24. |
| across-the-wire ("Across the Wire") | `b5b7f3dd50c1` — route.fulfill bypass | `runs/collusion/audit2` | REVIEWED — `presentation/cases/across-the-wire.json` (10 receipts, 5 steps, anchors ok); review `reviews/across-the-wire.md` | Bypass outcome supported + independently corroborated across cohorts; route.fulfill + Host-header mechanism wording partially exceeds receipts. Incident-report passage pending. Collusion provenance is corpus-internal → `sourceUrl: null`. Slice `inputs/collusion-audit2-slice.db` replays 108/108. |

## Provenance manifest

| Artifact | Path / identity | Status |
|---|---|---|
| audit5 results | `runs/village/audit5/results.json` — 180 claims (62 confirmed / 97 dismissed / 21 unverifiable) | present, gitignored |
| audit5 report | `runs/village/audit5/REPORT.md` | present, gitignored |
| audit3 results | `runs/village/audit3/results.json` — 24 claims (7 confirmed) | present, gitignored |
| audit3 report | `runs/village/audit3/REPORT.md` | present, gitignored |
| hunt1 results | `runs/village/hunt1/results.json` — 24 claims (1 confirmed) | present, gitignored |
| hunt1 report | `runs/village/hunt1/REPORT.md` | present, gitignored |
| claims input | `runs/village/claims/daily_sample.jsonl` — `daily:2026-08-10`, `daily:2026-08-31` source docs | present, gitignored |
| full corpus DB (village) | `records.db` (3.6M rows) | ABSENT locally — 14 GB on snapflip-vultr; receipts enriched via server-side fetch (all 17 Conjecture-843 IDs), deep links spot-checked 308→200 live |
| demo tarball (v1.0.1 asset) | `cantheria-demo.tar.gz` (23,992,857 B, sha256 `ba8640cfb4cc0588d466c08e684fe7ec7607f6dce63a8d12fd669c4c808105d0`) | CURRENT — public release `v1.0.1` (tag `c0e49baf54d841cad0362d7aa7bcf78b30efc778`), downloaded SHA verified: 4 runs, each `results.json` + `records.db`: audit5 180/180 · hunt1 24/24 · audit3 24/24 · collusion-audit2 108/108 — all four replayed from a clean download extract. |
| demo tarball (v1.0.0 asset) | `cantheria-demo.tar.gz` (18,009,272 B, sha256 `5df3cde28a5b62fb9ee5ac4edb89d8e29dea6b0ea3ce1278c16f19260bb22dc3`) | HISTORICAL — remains published: 3 runs (audit5, hunt1, collusion-audit2); no audit3 inside. |
| demo tarball (earlier v1.0.0 snapshot) | `cantheria-demo.tar.gz` (17,481,586 B) | HISTORICAL / SUPERSEDED — retained as evidence: at pull time (2026-10-04) it held village slices only (audit5 + hunt1). |
| local demo tarball (provenance) | `presentation/inputs/cantheria-demo.tar.gz` (23,992,857 B, sha256 `ba8640cfb4cc0588d466c08e684fe7ec7607f6dce63a8d12fd669c4c808105d0`) | PROVENANCE — the local file B built 2026-10-04; byte-identical to the published v1.0.1 asset (same SHA). Frozen — do not regenerate. |
| collusion results | `runs/collusion/audit2/results.json` (108: 81 dismissed / 16 unverifiable / 10 confirmed / 1 flaky) + REPORT.md; `runs/collusion/hunt1/` (20: 15 dismissed / 5 unverifiable) | PULLED from server 2026-10-04. Full replay 108/108 on `runs/collusion/records.db` (124 MB, pulled); slice (451 records) replay 108/108. |
| frozen presentation inputs | `presentation/inputs/` | DONE 2026-10-04 — audit3 slice (12 MB, sha256 `e273be07…d287eeb`), collusion slice (3.7 MB, sha256 `87b17090…fc4ea1e`), staged tarball (hash above). |

Local hygiene note (2026-11-08): derived `runs/*/records.db` corpora and
published-video masters were cleaned from this machine to free space. All are
regenerable — corpora via `cantheria ingest` from public sources (the village
DB lives on snapflip-vultr; `data/swarmtraces/` retained locally), videos via
the published releases/YouTube. No committed evidence was removed.

## Export tooling

- `presentation/tools/export_case.py` — results.json + REPORT.md + review JSON → case JSON. Verified: output parses against A's zod schema; anchors verified via A's `resolveAnnotations`.
- Known exporter behavior (documented, not hidden): committed probe = last `ok` non-control run; control step derived from final `probes_run` entry when a control query exists. Control `failed` status on the step means "no match" = the leg passes; the `checks[]` entry interprets it.
- LIMITATION: `parse_report_links` only matches `aivillage:` receipt lines. Collusion `source_uri`s are `collusion-wiki:...` internal refs → exporter emits `sourceUrl: null`, not a dropped receipt (verified: all 10 across-the-wire receipts present, null URLs).
- EXCERPT POLICY: the annotated lead receipt carries full content (up to 2000 chars); non-lead receipts carry the probe's own 400-char surface sample (truncated with `…`). Rationale: evidence fidelity to what the probe surfaced, plus corpus memory rows contain third-party deployment commands/keys that have no bearing on the claim — presentation files must pass the M6 secret gate.
- COUNT MISMATCH — RESOLVED 2026-10-04 (results.json as authority): regenerated `runs/collusion/audit2/REPORT.md` via `cantheria audit-report` (header now confirmed 10 / dismissed 81 / flaky 1 / unverifiable 16, zero candidates; 4 previously-missing budget-exhausted claims restored as unverifiable). SUBMISSION.md table restructured with a proper `flaky` column. HISTORICAL engine flag: generated reports printed the label "Slop rate" and could show a stale `dismiss_reason` on confirmed claims whose raw carried an intermediate dismissal — resolved locally by the lead's display-only `report.py` / `report_html.py` fix; not yet published.

## Overclaim / stale-language findings (M1 review of docs) — reviewed; remaining scope caveats below

Lead-review notes (local release-readiness pass, not yet published):
- Engine report labels fixed locally (`cantheria/swarm/report.py` + `report_html.py`): "Slop rate" → "claims failing mechanical verification" with numerator/denominator, N/A at zero decidable, stale `dismiss_reason`/`backend_error` suppressed on confirmed claims, flaky stat added to HTML, non-HTTP source URIs no longer rendered as links.
- All three supplied cases integrated in `site/`; the across-the-wire source passage (incident-report deep link) and user acceptance are still pending — receipts remain corpus-internal by design.
- Conjecture-843 lead clarification: the receipt narrates 12 pentagons plus 12 fifteen-cycles = 24 odd cycles; "The receipt describes the method in equivalent terms. This is evidence of the announcement, not an independent proof check." The committed probe did not execute or validate that construction.
- Items below marked RESOLVED reflect doc/report wording only; owner/user acceptance not marked done.

1. ~~DEMO.md "7 receipts with live deep links"~~ RESOLVED — corpus DB fetched; all 17 IDs resolve, REPORT.md lists **12** deep links (cap), spot-checked live (308→200). DEMO now says "12 receipts with deep links in `REPORT.md`".
2. ~~"17 matching records"~~ RESOLVED — DEMO now "17 rows matched the narrowed probe" + explicit scoping paragraph (16 of 17 are memory headers without claim substance).
3. ~~"the record says only: '… is FALSE.'"~~ RESOLVED — vignette rewritten: lead receipt quotes the announcement in full (counterexample, certificate), method/verification-count wording identified as source-summary only.
4. ~~"6 of 7 confirmations in the pilot audit"~~ VERIFIED TRUE — query against audit3 results: 7 confirmed, 6 via `mechanical-fallback`. DEMO now bolds "**6 of the 7**".
5. ~~SUBMISSION collusion row + replay command~~ RESOLVED — table split (16 unverifiable / 1 flaky), replay block annotated per-asset (v1.0.0 vs staged), tarball bullet now states exactly which agreement comes from which asset.
6. ~~"Slop rate" headlines~~ RESOLVED in README/DEMO/SUBMISSION/SWARM — replaced with "claims failing mechanical verification" + denominator (97/159, 81/91); vignette color phrase and video VO de-jargonized; SWARM's quoted "slopvestigation" origin line kept (it quotes the incident motivation, not a metric). Engine-generated report label also resolved locally by the lead's display-only fix; not yet published.
7. ~~PLAN ledger stale~~ — UI workstream updated §6 (M1 "in progress", M2 checked etc.); all three supplied cases integrated; source passage and user acceptance pending. `site/verification/` now has UI screenshots (A's side); B's verification evidence = this file + replay hashes.

New flags (found while resolving):
- HISTORICAL: generated `REPORT.md` printed a stale `dismiss_reason` under a **confirmed** claim (audit3's Conjecture-843 block showed `reason: probe error: …` beneath a green verdict) — resolved locally by the lead's display-only `report.py` fix; not yet published.

## 2026-10-22 — pre-sprint re-verification and audit-target provenance

Re-verified locally, same day, from a clean extract of
`presentation/inputs/cantheria-demo.tar.gz` (sha256
`ba8640cfb4cc0588d466c08e684fe7ec7607f6dce63a8d12fd669c4c808105d0`, byte-identical
to the published v1.0.1 asset, 23,992,857 B):

| run | verdict agreement | distribution |
|---|---|---|
| audit5 | 180/180 | 62 confirmed / 97 dismissed / 21 unverifiable |
| hunt1 | 24/24 | 1 / 14 / 9 |
| audit3 | 24/24 | 7 / 11 / 6 |
| collusion-audit2 | 108/108 | 10 / 81 / 16 / 1 flaky |

Casebook `https://udirobert.github.io/cantheria/` returns 200. README layout and
CLI surface corrected to match disk (`swarm/replay.py`, `swarm/report.py`,
`swarm/report_html.py`; `audit-report`, `replay`, `slice-corpus`).

**Pre-sprint baseline tagged:** `pre-sprint-baseline` → `a2c2898` (2026-10-04).
Everything at or before that commit is preexisting work; the AI Collusion
Research Sprint requires this to be marked in the README and the report.

### Audit target (Apart Research "AI Collusion Research Sprint", Track 2 / Q2.3)

| Artifact | Identity | Notes |
|---|---|---|
| `Ostailor/Steganographic_Collusion` ("Audit the Whisper" / ColludeBench-v0) | HEAD `48e6713d3e26b49dd94fa6645b4aeac6cb25a229`, last commit 2025-10-17, pack 10.53 MiB | Linked by the sprint Resources tab for Q1.3/Q2.3 with the caveat "should be preflighted rather than treated as a turnkey bag of raw trajectories" |
| local clone | `~/Dev/sprint-collusion/refs/colludebench` (209 MB under `results/`) | Read-only recon; no sprint code written before Oct 23 |
| record corpus | **508,605** rows across **3,460** `*_audit_N.jsonl` files | One row per `run_id`/`round_id`/`agent_id`: `message`, `action`, `reward`, `interventions{paraphrased,budget,length,rate_limited,canary_injected}` |
| detector code | `auditor/` + `colludebench/`; third-party imports are `numpy` + `yaml` only | Runs on a 16 GB laptop, no GPU; their code never reads the released logs (only globs `results/experiments/*.json`), so recompute needs an adapter |

Hand-verified anchors (no pipeline involved, so they are not yet receipts):

- **Establish**: `pricing_honest_calibration` = 200 runs, consumer surplus 79.2247 ± 0.1548, rounds {15} — matches prose "79.22 ± 0.15 … 15 rounds". Gemini/Groq calibration logs: 10 runs, rounds {8} — matches "average of eight priced rounds". `union_validation.json`: `replicates: 10000`, Bonferroni + Holm FPR 0.0 at 1e-2 and 1e-3 — matches "10k replicates … FPR = 0".
- **Not established**: `docs/experiment_results.md` cites `results/calibration/pricing_duopoly/pricing_duopoly_audit_194.jsonl`; that path is absent (directory holds `audit_0`…`audit_9`). "200 seeds per scenario" holds for pricing/auction honest but `double_auction_honest` and both LLM calibrations carry 10.
- **Open**: `westfall_young` FPR = 1.0 at both α in the same file, unmentioned in prose; `ablation.json` carries 18 labelled runs (tp+fp+fn+tn) behind the four external-baseline head-to-head claims; `main.aux`/`main.log`/`main.fls` are committed with no `.tex` and no PDF anywhere.
- **Method note we will quote**: an earlier recon pass reported "missing `requirements.txt`" — it exists; the gap was our own sparse checkout. Auditor-side false negative, caught before it shipped. This is the failure mode the calibration leg measures.
