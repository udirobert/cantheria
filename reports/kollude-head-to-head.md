# kollude head-to-head — collusion.wiki

Direct comparison against **kollude 0.4.0** (PyPI, github.com/dhruva137/kollude —
built for this same hackathon). Run 2026-11-08 on kollude's own bundled
`wiki` dataset (the collusion.wiki public revision dump, 3.1 MB gz) vs.
Cantheria's normalized `runs/collusion/records.db` (42,373 records).

## What each system emitted

**kollude scan wiki** — 14,591 events · 3,668 actors · 948 hourly bins ·
6 anytime-valid alarms (e-CUSUM, false-alarm rate ≤ α):

| alarm (UTC) | C | M | S | top template |
|---|---|---|---|---|
| 2026-05-28 16:00 | 0.462 | 5.0 | 1721 | "u u u u …" (folded placeholder spam) |
| 2026-06-16 21:00 | 0.056 | 9.7 | 483 | "test coordination page ignore" |
| 2026-06-18 15:00 | 0.425 | 36.0 | 118 | "describe the new page here" |
| 2026-06-18 18:00 | 0.125 | 146.0 | 262 | "describe the new page here" |
| 2026-06-18 21:00 | 0.122 | 35.5 | 115 | "describe the new page here" |
| 2026-06-20 18:00 | 0.500 | 8.0 | 149 | "describe the new page here" |

Largest coordinated cluster: template "describe the new page here" —
**539 distinct actors**, 555 events, 939 h span. `kollude spread` names
seeders per template (e.g. DataUserXYZ seeding the "u u u" spam line,
FederalDataR… / AgentResearc… / AgentManual0… seeding page-template lines)
and hours-until-N-actors-copied.

**Cantheria audit (collusion report)** — 108 claims → 10 confirmed /
81 dismissed / 16 unverifiable / 1 flaky, each with committed SELECT
probes, receipts, and keyless replay.

## Agreement — and where it matters

- **First-alarm timing converges independently.** kollude's first alarm:
  **2026-05-28 16:00Z**. Cantheria's density monitor first fires:
  **2026-05-27** (front page crosses 10 distinct agent posters; 179
  distinct agent labels/day). Two unrelated methods — template-folding
  e-CUSUM vs. actor-density + claim probes — flag coordination within
  ~a day of each other, ~5 days after first writes (05-24) and ~5 days
  before the first human moderator cleanup (~06-02).
- **Both concentrate on 06-16 → 06-20.** kollude's 5 later alarms and
  Cantheria's densest cluster of confirmed bypass-evidence claims
  (SSH tunnels, AWS attribution, GET-only restriction, route.fulfill
  rewriting) occupy the same window, ending in the 06-22 shutdown.
- **They measure different things.** kollude answers *"is a population
  copying a template, and who started it?"* — calibrated (α-bounded
  false alarms), population-level, template-specific. Cantheria answers
  *"is this specific claim true?"* — any claim type, per-claim receipts,
  replayable without a model, plus audit of the investigators' own
  report. kollude cannot confirm "agent X opened an SSH tunnel on
  06-17"; Cantheria cannot produce an e-value.
- **Complementary pipeline:** a kollude alarm is precisely the kind of
  suspicion that can be handed to Cantheria as a claim to adjudicate —
  detector proposes, record decides.

## Caveats

- Different event extraction: kollude ingests raw revision JSONL
  (14,591 events); Cantheria normalizes 42,373 records including posts,
  pages, events, agents, pastes. Counts are not apples-to-apples.
- kollude's `wiki` loader is their curated path; our corpus came through
  our own ingest. Agreement on timing is therefore meaningful but the
  underlying row sets differ.
- This is one corpus, one detector configuration (defaults). Not a
  benchmark — a sanity check that the two layers see the same incident.
