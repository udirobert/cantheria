# Cantheria — swarm forensics demo

**An LLM proposes; the record decides.**

Swarm investigation today runs on trust: an agent writes a summary, another
agent writes a report, a human skims a dashboard, and the narrative becomes
fact. Cantheria treats every sentence in that narrative as a *hypothesis* —
each claim must survive a mechanical evidence chain against the raw record,
or it goes in the journal as unsupported. Nothing is taken on faith,
including the verifier's own model.

## The experiment

Corpus: the **real AI Village dataset** (HF `aidigestorg/ai-village`) —
**3,646,303 normalized records**: chat, events, agent memories, sessions,
summaries, and 2.5M turn-level computer-use actions, spanning
2025-04-02 → 2026-09-19. Every record keeps a deep link back to the live
village (`theaidigest.org/village?day=N&time=ms`).

Target: 16 official daily summaries, evenly sampled across 15 months —
the exact artifacts investigators would hand you and say "this is what
happened."

```
180 claims extracted
  → 62 confirmed (record-backed, receipts + deep links)
  → 97 dismissed (the record could not support them)
  → 21 unverifiable (quarantined — no mechanical probe can decide them)

slop rate: 61% of decidable claims failed verification
cost: 513 model calls, 935 read-only probe executions
```

Every verdict is replayable: `journal.jsonl` keeps the complete
draft→probe→repair trajectory per claim; `REPORT.md` lists receipts that
resolve to real records.

## Four vignettes

### 1. The day that wasn't — `summary:2026-07-03` → 0/12

One daily summary produced twelve claims. **All twelve failed
verification** — the rent figures, the roleplay personas, the "consensus
vote," the "unauthorized handout.html." We checked it's not a data gap:
that day has 825 chats, 1,993 events, 1,213 memories, and 23,114 turns in
the corpus. The record is dense; the summary just isn't true. This is what
pure slop looks like when you actually measure it.

### 2. The thing nobody was looking for — hunt mode

`cantheria hunt` doesn't audit a document — it *hypothesizes* over the
busiest agent-day segments, then puts its own hypotheses through the same
chain. Across 25 segments it autonomously surfaced and confirmed:

> **An agent initiated a private computer session to roll a d6 to
> determine its own role for Day 338.**

Evidence: an `AGENT_TALK` event from Opus 4.5 (Claude Code) —
*"Time to roll my d6 privately. Let me start my computer session to
determine my role for the day."* — confirmed with a clean control window.
An agent silently randomizing its own role is exactly the kind of emergent
behavior a transcript dashboard will never flag, because nobody wrote a
query for it.

### 3. Why the verifier can't trust its own model — the fallback

The daily summary claims Claude Opus 5 "disproved Conjecture 843 at
[2026-08-31 11:18:34 PT] using an elegant 24-odd-cycle partition." The
record says only: *"🎯 Graffiti conjecture 843 … is FALSE."*

The model-drafted probes failed three times — it demanded the summary's
embellishments ("disproved," "24-odd-cycle," "47,780 checks") all co-occur
in one record, and once crashed on unquoted FTS syntax. Then the
**mechanical fallback** took over: no model judgment, just the claim's
rarest co-occurring vocabulary in non-summary records plus a
timezone-normalized window. Result: **17 matching records**, all four
evidence legs green, 7 receipts with live deep links.

That's the thesis running in production: the LLM proposed a test, the
record falsified the *probe* (not the claim), and a dumber-but-honest
mechanism recovered the truth. 6 of 7 confirmations in the pilot audit
came through the fallback — if we'd trusted the model's probes as oracle,
the "slop rate" would have been a fabrication of our own pipeline.

### 4. Calibrated honesty — the quarantine

21 claims came back `unverifiable`: suggestions, failed link-shares,
"could not find the document." Not because the record disproved them —
because no mechanical probe can decide them. Forcing a verdict there is
what every transcript-summarizer does; declining is what makes the
confirmed claims mean something.

## How it works

Same SIFT engine as the vuln-scan pipeline, different canary:

- **Segment** — external corpora → normalized `records` (sqlite + FTS5)
- **Infer** — audit mode (document → atomic claims) or hunt mode
  (segment → hypothesis)
- **Falsify** — each claim gets a read-only probe and four legs:
  grounding (rows exist, citations resolve), attribution (binds the
  claimed agent/time), replication (independent corroboration), and
  **control** — the same probe on a disjoint window must *differ*, giving
  an actual false-positive check no narrative audit has today
- **Triage** — verdicts + receipts + deep links in `REPORT.md`;
  everything, including the failures, stays in an append-only journal

Prompt-injection discipline carries over from the PoC sandbox: probes are
SELECT-only, row-capped, watchdog-timed, and executed on read-only handles;
documents enter the model fenced, never as instructions.

## What this is not

- Not a summarizer — it *audits* summaries
- Not RAG — answers come with executable receipts or don't ship
- Not a trajectory dashboard — it produces verdicts with a control-leg
  false-positive rate, not plots
- Not a chatbot — the model's own probes are treated as falsifiable drafts,
  and a mechanical fallback arbitrates when they can't express the test

## Reproduce

```bash
cantheria ingest data/aivillage --corpus records.db          # → 3.6M records + FTS
cantheria audit records.db --claims claims_big.jsonl         # → REPORT.md + journal
cantheria hunt records.db --segments 25                      # → autonomous hypotheses
```

Or replay the shipped verdicts — no key, no model, ~30s:

```bash
curl -LO https://github.com/udirobert/cantheria/releases/download/v1.0.0/cantheria-demo.tar.gz
tar xzf cantheria-demo.tar.gz
cantheria replay demo/audit5/results.json --corpus demo/audit5/records.db  # 180/180
cantheria replay demo/hunt1/results.json  --corpus demo/hunt1/records.db   # 24/24
```

## 90-second video script

1. **(0:00) Cold open — the audit report.** Screen: the live report at
   `udirobert.github.io/cantheria/` — the stat bar: *180 claims, 62
   confirmed, 97 dismissed, 61% slop rate.* VO: *"Investigators read
   summaries of agent swarms and treat them as ground truth. We measured.
   Sixty-one percent of verifiable claims in real AI Village daily
   summaries could not be supported by the record."*
2. **(0:15) The day that wasn't.** Scroll to the `2026-07-03` block —
   12 claims, all dismissed. VO: *"One entire daily summary evaporates
   under verification — on a day the record is dense. The narrative was
   pure slop."*
3. **(0:30) Receipts.** Click a confirmed claim's receipt deep link —
   lands on `theaidigest.org/village?day=…` at the actual record. VO:
   *"Every confirmed claim ships evidence receipts that deep-link to the
   live village. No receipts, no verdict."*
4. **(0:45) The d6 roll.** Cut to the hunt report's confirmed hypothesis.
   VO: *"In hunt mode the pipeline writes its own hypotheses — and found an
   agent privately rolling a die to assign its own role. Nobody queried for
   it; the falsification harness surfaced it."*
5. **(1:00) The fallback — the thesis.** Terminal or journal: model probe
   fails 3× on the Conjecture 843 claim, then `mechanical-fallback` finds 17
   records, four legs green. VO: *"The model's probes failed on a true
   claim — so a mechanical fallback with no model judgment recovered it. An
   LLM proposes; the record decides. That applies to our own model too."*
6. **(1:15) Keyless replay.** Terminal:
   `cantheria replay … → 180/180 verdict agreement`. VO: *"And every
   verdict replays deterministically — re-execute the deciding probes
   yourself, no model, no keys. Trust, but re-run."*
7. **(1:25) Card.** *"Cantheria — forensic verification for agent-swarm
   claims. 3.65M records · 61% slop · receipts or silence."*
