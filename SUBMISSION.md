# Cantheria — swarm claim verification

**An LLM proposes; the record decides.**

Swarm investigation runs on narration: agents write summaries, humans skim
them, and the narrative becomes fact. Cantheria treats every sentence as a
hypothesis — each claim must survive a mechanical evidence chain against
the normalized record, or it goes in the journal as unsupported. Nothing is
taken on faith, *including the verifier's own model*.

## Live demo

https://udirobert.github.io/cantheria/

- **Audit report** — 180 claims extracted from 16 official AI Village daily
  summaries, with evidence receipts deep-linking to the live village UI
- **Hunt report** — 25 agent-day segments, fully autonomous hypothesize→verify
- **Corpus 2** — the collusion.wiki incident report audited against its own
  underlying record (42k German-wiki edits/events/pastes): 108 claims,
  10 confirmed, receipts included
- **Replayable demo corpus** (~24MB / 23,992,857-byte tarball) —
  `cantheria replay` re-runs every committed probe deterministically:
  **no model, no API key** — 180/180 (audit), 24/24 (hunt), and 108/108
  (collusion audit2) in the v1.0.1 asset in seconds; audit3 (24/24) ships in
  the same tarball

## The findings (real data, real numbers)

Corpus 1: HF `aidigestorg/ai-village`, normalized to `records` —
3,646,303 rows (chat, events, memories, sessions, summaries, 2.5M
computer-use turns), 2025-04-02 → 2026-09-19.

Corpus 2: HF `leonidas1712/public-agent-coordination-artifacts` — the
collusion.wiki incident data (42,373 records: wiki revisions, save/delete
events, author labels, paste bodies), May–Sep 2026.

| run | corpus | claims | confirmed | dismissed | unverifiable | flaky |
|---|---|---|---|---|---|---|
| audit: 16 daily summaries | aivillage | 180 | 62 | 97 | 21 | — |
| hunt: 25 segments | aivillage | 24 | 1 | 14 | 9 | — |
| audit: collusion.wiki report | collusion | 108 | 10 | 81 | 16 | 1 |
| hunt: 20 segments | collusion | 20 | 0 | 15 | 5 | — |

**61% of decidable daily-summary claims failed mechanical verification**
(97/159 — quarantined claims excluded from the denominator: the pipeline
couldn't mechanically decide them, and flaky outcomes are excluded too),
measured not asserted. On the second corpus the pipeline
inverts the lens: it audits the *investigators' own incident report* — 10
of its claims received recorded confirmed verdicts covering bypass-related evidence,
tunnel-related claims, GET-only restrictions, and the six-week moderator
cleanup (the featured bypass case distinguishes the observed outcome from
unresolved mechanism wording), while 89% of its decidable claims (81/91) could not be
mechanically established against the underlying record. Verification
failure is not unique to agent-generated summaries — human-written
investigation reports fail too, which is exactly why receipts must ship
with the narrative.

Three findings worth reading the receipts on:

- **The day that wasn't**: `summary:2026-07-03` went **0/12** — every claim
  dismissed on a day with 825 chats / ~2k events / 23k turns in the corpus.
  All twelve probes failed to establish their claims on a well-populated
  day; that is a warning about the summary, not proof that each claim is false.
- **The thing nobody searched for**: hunt mode autonomously confirmed an
  agent *announcing* a private session to roll a d6 to assign its own
  role — a private-role-selection lead found without anyone writing a query for
  it. The receipt is the announcement; whether the roll happened stays
  open, and the case says so.
- **The verifier auditing itself**: the Conjecture-843 claim's
  model-drafted probes failed 3× — one over-constrained, two rejected by
  sqlite on unquoted FTS hyphens (`no such column: odd`); a mechanical
  fallback matched 17 rows (12 receipts) and confirmed the announcement.
  If model probes were the oracle, our own failure rate would have been a
  fabrication. That failure mode — *the auditor's model producing false
  negatives* — is invisible to summarizers and dashboards.

## How it works

```
document ─fenced→ claim extraction ─→ atomic claims (event|pattern|
                                      coordination|absence|interpretive)
per claim:  draft probe → SELECT-only execution → repair loop
            → grounding → attribution → replication → control
            → verdict + receipts → append-only journal
```

The legs that matter: **control**, when drafted, runs a disjoint query and
requires it *not* to satisfy the same expectations — a negative-control
discrimination check on the claim. **Interpretive** claims are quarantined as
`unverifiable` at zero probe cost rather than force-answered. Probes are
SELECT-only, row-capped, watchdog-timed, on read-only handles; source
documents enter the model fenced, never as instructions.

## What this is not

Not a summarizer (it audits summaries), not RAG (claims carry executable
receipts or don't ship), not a trajectory dashboard (verdicts, not plots),
not a chatbot (the model's own probes are falsifiable drafts, and a
mechanical fallback arbitrates when they can't express the test).

## Reproduce

```bash
# keyless — deterministic replay of the committed probes
uv sync
curl -LO https://github.com/udirobert/cantheria/releases/download/v1.0.1/cantheria-demo.tar.gz
tar xzf cantheria-demo.tar.gz
uv run cantheria replay demo/audit5/results.json --corpus demo/audit5/records.db          # 180/180 (v1.0.1 asset)
uv run cantheria replay demo/hunt1/results.json  --corpus demo/hunt1/records.db           #  24/24  (v1.0.1 asset)
uv run cantheria replay demo/audit3/results.json --corpus demo/audit3/records.db           #  24/24  (v1.0.1 asset)
uv run cantheria replay demo/collusion-audit2/results.json --corpus demo/collusion-audit2/records.db  # 108/108 (v1.0.1 asset)

# full pipeline (needs a chat backend — see .env.example)
cantheria ingest data/aivillage --corpus records.db
cantheria audit records.db --claims summaries.jsonl
cantheria hunt records.db --segments 25
```

Design doc: `SWARM.md`. Demo narrative: `DEMO.md`.
Origin domain (LLM-assisted vuln falsification) intact under `cantheria/`.

## Submission update — 2026-11-08 (Swarm Alignment Hackathon)

New evidence since the numbers above:

- **Detection latency** (`reports/detection-latency-collusion.md`): the
  collusion.wiki record contained mechanically-checkable coordination
  evidence from 2026-05-27 — ~5 days before the first human moderator
  cleanup and ~14 weeks before the public report.
- **Ground-truth eval** (`eval/synthetic_ground_truth/`): planted-claims
  corpus; Cantheria confirmed 6/7 true claims, **0/7 false claims**,
  quarantined the interpretive claim. Blind spots documented (absence
  claims, drafter abstention). LLM-judge baselines (full-context and
  keyword-retrieval) matched on this toy corpus — Cantheria's edge is
  scale, determinism, and receipts, not raw accuracy at 53 records.
- **kollude head-to-head** (`reports/kollude-head-to-head.md`): the
  same-hackathon statistical detector alarms first at 2026-05-28 vs. our
  density monitor's 2026-05-27 — independent methods converge; different
  layers (calibrated population alarm vs. per-claim adjudication).
- **Related work & positioning**: `RELATED_WORK.md`.
- **SwarmTraces audit** (`eval/swarmtraces_claims/`): the incident report's
  own 14 checkable claims against its 189,579-record payload corpus —
  2 confirmed with receipts (Kubernetes, Docker Hub), 12 quarantined,
  0 false confirmations; documents abstention on unattributed corpora and
  a probe-truncation hazard.
- **PDF report**: `presentation/cantheria-report.pdf` (source:
  `presentation/report.html`).
