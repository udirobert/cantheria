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

claims failing mechanical verification: 61% of decidable claims
  (97/159 — quarantined claims are excluded, not counted as failures:
   no mechanical probe could decide them)
cost: 513 model calls, 935 read-only probe executions
```

Every verdict is replayable: `journal.jsonl` keeps the complete
draft→probe→repair trajectory per claim; `REPORT.md` lists receipts that
resolve to real records.

## Corpus 2 — auditing the investigators

Same pipeline, different lens. Corpus: the collusion.wiki incident data
(HF `leonidas1712/public-agent-coordination-artifacts`) — 42,373 records of
German-wiki edits, save/delete events, author labels, and pastes where
rogue agents coordinated in mid-2026. Target: the investigators' own
public incident report.

```
108 claims extracted from the report
  → 10 confirmed (record-backed receipts)
  → 81 dismissed (mechanically unsupportable as stated)
  → 16 unverifiable + 1 flaky (quarantined / unstable — no reliable verdict)

claims failing mechanical verification: 89% of decidable claims
  (81/91 — same denominator rule as corpus 1)
```

Recorded confirmations include bypass-related evidence, tunnel-related
claims, GET-only restrictions, and moderator cleanup. The featured bypass
case distinguishes the observed outcome from unresolved mechanism wording.
The point isn't that the report
is sloppy — it's careful work — but that *any* narrative, human- or
model-written, deserves the same receipts-or-silence standard.

## Four vignettes

### 1. The day that wasn't — `summary:2026-07-03` → 0/12

One daily summary produced twelve claims. **All twelve failed
verification** — the rent figures, the roleplay personas, the "consensus
vote," the "unauthorized handout.html." We checked it's not a data gap:
that day has 825 chats, 1,993 events, 1,213 memories, and 23,114 turns in
the corpus. The record is dense; these probes did not establish the
summary's claims. Retrieval failure is not proof that they are false — but
this is what an unsupported narrative looks like when you actually measure
it.

### 2. The thing nobody was looking for — hunt mode

`cantheria hunt` doesn't audit a document — it *hypothesizes* over the
busiest agent-day segments, then puts its own hypotheses through the same
chain. Across 25 segments it autonomously surfaced and confirmed:

Recorded hypothesis (verbatim):

> **An agent initiated a private computer session to roll a d6 to
> determine its own role for Day 338.**

Evidence: an `AGENT_TALK` event from Opus 4.5 (Claude Code) —
*"Time to roll my d6 privately. Let me start my computer session to
determine my role for the day."* — confirmed with a clean control window.
To be exact: the receipt *is* the announcement — the record shows the
agent saying it, not a session-start record or a completed roll, and the
featured case says so beside the verdict. This is a lead about possible
private role selection, not proof of a completed roll.

### 3. Why the verifier can't trust its own model — the fallback

The daily summary claims Claude Opus 5 "disproved Conjecture 843 at
[2026-08-31 11:18:34 PT] using an elegant 24-odd-cycle partition," later
"formally verified with 47,780 checks EXIT 0."

The model-drafted probes failed three times: one over-constrained draft
demanded the summary's embellishments co-occur in a single row and found
nothing; two were rejected outright — `sqlite: no such column: odd`,
unquoted hyphens in the FTS expression, a bad *draft*, not a verdict on
the claim. Then the **mechanical fallback** took over: no model judgment,
just the claim's date and number co-occurring in non-summary records plus
a timezone-normalized window. Result: **17 rows matched the narrowed
probe**, all four evidence legs green, 12 receipts with deep links in
`REPORT.md`.

And the honest part: the lead receipt quotes the announcement in full —
timestamp, counterexample (icosahedral Goldberg GP(2,2), 240 vertices),
certificate (12 disjoint pentagons + 12 disjoint 15-cycles, independence
number 108 vs the conjectured 112) — but the other 16 matches are agent
memory headers carrying only the date and the number. The probe
establishes that *something about Conjecture 843 happened at that time*.
The receipt describes 12 pentagons plus 12 fifteen-cycles — 24 odd cycles —
but the probe did not validate that construction. The 47,780-check
verification remains source-summary wording without a supplied receipt.
`confirmed` scopes to what the probe tested —
the featured case prints the qualification beside the verdict.

That's the thesis running in production: the LLM proposed a test, the
record falsified the *probe* (not the claim), and a dumber-but-honest
mechanism recovered an inspectable announcement without establishing every
detail of the source claim. **6 of the 7 confirmations** in that pilot
audit came through the fallback — if we'd trusted the model's probes as
the oracle, the failure rate itself would have been a fabrication of our
own pipeline.

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
  **control** — when drafted, a disjoint query must not satisfy the same
  expectations: a negative-control check, not a calibrated
  false-positive-rate measure
- **Triage** — verdicts + receipts + deep links in `REPORT.md`;
  everything, including the failures, stays in an append-only journal

Prompt-injection discipline carries over from the PoC sandbox: probes are
SELECT-only, row-capped, watchdog-timed, and executed on read-only handles;
documents enter the model fenced, never as instructions.

## What this is not

- Not a summarizer — it *audits* summaries
- Not RAG — answers come with executable receipts or don't ship
- Not a trajectory dashboard — it produces verdicts with a negative-control
  discrimination check, not plots
- Not a chatbot — the model's own probes are treated as falsifiable drafts,
  and a mechanical fallback arbitrates when they can't express the test

## Reproduce

```bash
cantheria ingest data/aivillage --corpus records.db          # → 3.6M records + FTS
cantheria audit records.db --claims claims_big.jsonl         # → REPORT.md + journal
cantheria hunt records.db --segments 25                      # → autonomous hypotheses
```

Or replay the shipped verdicts — no key, no model, seconds:

```bash
uv sync
curl -LO https://github.com/udirobert/cantheria/releases/download/v1.0.1/cantheria-demo.tar.gz
tar xzf cantheria-demo.tar.gz
uv run cantheria replay demo/audit5/results.json --corpus demo/audit5/records.db  # 180/180
uv run cantheria replay demo/hunt1/results.json  --corpus demo/hunt1/records.db   # 24/24
uv run cantheria replay demo/audit3/results.json --corpus demo/audit3/records.db  # 24/24
uv run cantheria replay demo/collusion-audit2/results.json --corpus demo/collusion-audit2/records.db  # 108/108
```

## 90-second video script

Recording still pending — this storyboard targets the current static routes
(`/` Canary plate and case list, `/bench/`, `/cases/private-die/`,
`/cases/conjecture-843/`, `/cases/across-the-wire/`, `/reproduce/`,
`/identity/`). The replay beat uses actual terminal output — no staged or
mocked footage.

1. **(0:00–0:12) Cold open — home.** Canary plate + claim/receipt spread on
   the homepage. VO: *"Agent swarms leave records. Their summaries are
   hypotheses. Cantheria tests what those stories actually establish."*
2. **(0:12–0:25) The evidence index.** Bench page + case list. VO: *"We
   audited 180 AI Village summary claims and 108 collusion-report claims.
   97/159 and 81/91 decidable claims failed mechanical verification. That
   is not a falsehood rate."*
3. **(0:25–0:40) The Private Die.** Case opening + the announcement
   receipt. VO: *"A recorded confirmation found an agent announcing a
   private d6 roll. The receipt does not show a completed roll."*
4. **(0:40–1:03) Conjecture 843.** FlightMap over the failed model drafts,
   the mechanical fallback, and the lead receipt. VO: *"Three
   model-drafted tests failed. A mechanical fallback retrieved an
   announcement about Conjecture 843. It did not validate the
   mathematics."*
5. **(1:03–1:17) Across the Wire.** Case opening + provenance block.
   VO: *"Bypass-related outcomes have corroborating records. The specific
   mechanism remains beyond the winning receipts. This case uses
   corpus-internal references."*
6. **(1:17–1:26) Re-run the probes.** Reproduce page + actual terminal
   replay showing 180/180 verdict agreement. VO: *"Replay the committed
   checks without a model or API key. Agreement tests reproducibility, not
   every source claim."*
7. **(1:26–1:30) Card.** Identity mark + closing question. VO: *"An LLM
   proposes; the record decides. Who checks the story your agents tell
   you?"*
