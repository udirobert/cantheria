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

## Interim results (2026-11-08, SIE chat Qwen3.8-27B)

Cantheria (`runs/synthetic-eval/audit2`, 18 llm calls / 24 probe runs):

| metric | value |
|---|---|
| true claims confirmed | 6/7 (the miss: true absence — structural) |
| false claims confirmed (FP) | **0/7 — no false confirmations** |
| false claims dismissed | 2/7 |
| false claims abstained (`unverifiable`) | 5/7 — drafter declined to probe fabricated specifics |
| interpretive quarantined | 1/1 |

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

Honest read: on 53 records the retrieval-limited judge is *better* than
Cantheria at dismissing fabricated claims (it said `contradicted` where we
abstained). Cantheria's remaining edges are the ones this eval cannot
show at toy scale: probes are precise predicates, not fuzzy retrieval +
judgment — at 3.6M records the judge's evidence pack is only as good as
keyword recall, while a probe either lands or doesn't, with receipts.
Plus determinism (judge verdicts flip run to run; probes replay
identically) and the journal. The eval's real product is documenting
where each system's boundary sits.

## Known limitations this eval documents

1. **Absence claims on empty windows are unconfirmable.** `_eval_expect`
   treats `max_rows: 0` + 0 rows as failure and the oracle dismisses on
   0 rows — a true absence can never reach `confirmed`. Documented, not
   yet fixed.
2. **Drafter abstention.** When every claim term scores zero corpus hits,
   the drafter tends to decline (`{"query": ""}`) → `unverifiable`. For
   fabricated claims the honest verdict is `dismissed` (the record lacks
   the evidence); abstention is safe but less useful. The mechanical
   fallback probe is *not* applied on drafter-declined claims — extending
   it is possible but risky (a vocab probe on a fabricated claim can
   match unrelated rows and false-confirm).
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
