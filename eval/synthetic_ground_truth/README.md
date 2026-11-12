# Synthetic ground-truth eval

Does the pipeline's verdict match *known* truth? The real-corpus runs
measure verdict agreement on replay, but can't say whether `confirmed`
means true. This eval plants the answers.

## Design

- `build.py` — writes `runs/synthetic-eval/records.db`: 53 records over
  2026-06-01 → 06-10, agents Relay / Scribe / North / South / East / West
  (Ghost never appears), threads lobby / ops / ops-war-room / sealed-vault.
  Every checkable fact is planted on purpose; `sealed-vault` is left empty
  as a planted absence.
- `claims.jsonl` — 15 atomic claims, each tagged `"truth": true|false|
  interpretive` with a note naming the trap it sets:
  - 7 true: verbatim event, paraphrase, 3-revision pattern, two
    coordination claims, one *true absence* on the empty room
  - 7 false: nonexistent agent, wrong time, nonexistent page, fabricated
    coordination token, **attribution trap** (North posted it, claim says
    Relay), **false absence**, wrong-day window
  - 1 interpretive: correct outcome is `unverifiable` quarantine
- `score.py` — joins `results.json` verdicts to planted truth; reports
  TP/FN/TN/FP, abstentions, precision, true-claim recall.
- `baseline.py` — foil 1: whole 53-record corpus in one prompt, judge
  verdicts per claim (the "just ask a big model" upper bound — only
  feasible because the corpus fits in context).
- `baseline_rag.py` — foil 2: per-claim keyword-retrieved evidence packs
  (what a RAG fact-checker sees at real scale), 3 runs for judge variance.

## Shipped result (`results.json`, the run `repro.py` scores)

Gemma re-run. 28 model calls, 56 probe executions. This is the table to quote.

| metric | value |
|---|---|
| true claims confirmed | **7/7**, including the sealed-vault true absence |
| false claims confirmed (FP) | **0/7** |
| false claims dismissed | **6/7** |
| false claims abstained (`unverifiable`) | **1/7** — "No agent posted in the ops room on 2026-06-05." |
| interpretive quarantined | 1/1 |

The older Qwen run is still in `results_baseline_qwen.json` (18 model calls, 24 probe executions): 6/7 true confirmed, the miss a true absence; 2/7 false dismissed; 5/7 false abstained. `repro.py` also replays that file. It is not the headline.

## Older foil, measured on the Qwen sheet (2026-11-08)

Full-context LLM baseline (3 runs): ~14–15/15 aligned with truth per run —
near-perfect *because everything fit in context*. Its verdicts carry no
receipts, can't be replayed, and flip between runs.

RAG-limited baseline (`baseline_rag_results.json`, committed copy of
`runs/synthetic-eval/baseline_rag.json`; 3 runs ×
15 per-claim calls): the strongest foil. Per run it supported all 6
decidable-true claims, contradicted **all 7 decidable-false claims**
(including every trap), abstained on the true absence and the
interpretive claim — and abstained on the Ghost claim in 2/3 runs.
~13–14/15 aligned with truth per run, **0 false confirmations**.

Honest read, against that Qwen sheet: the retrieval-limited judge dismissed fabricated claims where Cantheria abstained. The shipped Gemma re-run dismisses 6 of 7 false claims and still abstains on the false absence, which the RAG foil contradicted. The RAG foil abstained on the true absence that the Gemma re-run confirms.

## Known limitations this eval documents

1. **Absence is not settled in both directions.** The shipped run
   confirms the planted empty-room absence (sealed-vault, zero rows) and
   abstains on the false absence (ops, 2026-06-05). Confirming one empty
   room is not a general absence decider. The live cell's true absence
   ("did not modify any test files") was dismissed.
2. **The older run abstained on fabricated claims.** In
   `results_baseline_qwen.json`, five of seven false claims came back
   `unverifiable` because the drafter declined. The Gemma re-run
   dismisses six of those seven and still abstains on the false absence.
   Abstaining is safe. It is not a dismissal.
3. **Tiny corpus.** 53 records is a unit test, not a benchmark. The eval
   proves the plumbing end-to-end and exposes boundary behavior; it does
   not estimate field accuracy.

## Reproduce

```bash
uv run python eval/synthetic_ground_truth/build.py
uv run cantheria audit runs/synthetic-eval/records.db \
  --claims eval/synthetic_ground_truth/claims.jsonl \
  --out runs/synthetic-eval/audit2 --budget 250
env -u FEATHERLESS_API_KEY uv run python eval/synthetic_ground_truth/baseline.py
BASELINE_RUNS=3 env -u FEATHERLESS_API_KEY uv run python \
  eval/synthetic_ground_truth/baseline_rag.py
uv run python eval/synthetic_ground_truth/score.py \
  runs/synthetic-eval/audit2/results.json
```

Note: unset `FEATHERLESS_API_KEY` to use the SIE backend — the exported
shell key is stale (403s).
