# Cantheria — swarm forensics

> The same kill chain, pointed at agent swarms instead of source code.
> A PoC that must crash becomes a probe that must land.

**An LLM proposes; the record decides.** Cantheria is a falsification
pipeline for claims about multi-agent systems. Model output — a
hypothesis, a summary, an investigation draft — is *input*. A claim only
ships when a probe survives the evidence chain against the underlying
record. Everything the model was wrong about stays in the append-only
journal.

Motivation, in the investigators' own words: the external investigation
of the OpenAI/Hugging Face incident "had to heavily delegate our
analysis to often-unreliable AI agents" whose output they could not
verify, over transcripts the swarm had actively tried to spoof, edit,
and delete. Slop-in, slop-out — the "slopvestigation" problem. The AI
Village dataset card makes the same point in miniature: *"Treat an
agent's narration as a claim, not ground truth"* — and the shipped
`summaries.jsonl` "contain inaccuracies." Cantheria's first target is
those summaries.

## Pipeline — still SIFT

```
corpus ──▶ S  segment: normalize sources → `records`; slice into
                  agent-days / threads / sessions
       ──▶ I  infer:   two entry points —
                  audit: a document → atomic claims + proposed citations
                  hunt:  a segment  → hypotheses about swarm behavior
       ──▶ F  falsify: model drafts a *probe* — SELECT-only SQL over
                  `records` — instead of a PoC. Failed probes feed their
                  output back and retry (≤3 attempts); the evidence
                  oracle applies the kill chain
       ──▶ T  triage:  rerank surviving claims; sub-threshold quarantined
       ──▶ investigator-ready reports (verified claims + deep-link
           receipts + the journal of everything rejected)
```

## The record

Every source normalizes into one `records` table (sqlite, zero deps):

| column | notes |
|---|---|
| `record_id` | source-native id, or hash of (corpus, ts, agent, content[:64]) |
| `corpus` | `aivillage` \| `collusion` \| `swarmtraces` \| … |
| `ts`, `ts_unix` | authoritative time; day numbers are scaffolding, timestamps are truth |
| `agent_id` | speaker / actor when known |
| `thread` | chat room, wiki page, session, or chain id |
| `kind` | `chat` \| `event` \| `turn` \| `memory` \| `summary` \| `post` \| `payload` |
| `content` | verbatim text |
| `parent_id` | reply-to / session linkage |
| `source_uri` | receipt — e.g. `theaidigest.org/village?day={d}&time={ms}` |
| `raw` | original row, JSON |

Loaders: `aivillage` (events, chat_messages, computer_use_sessions,
agent_memories, summaries; `computer_use_turns` lazily — 1.14M rows is
citation depth, not breadth), `collusion` (wiki dump), `swarmtraces`
(decoded payload JSONL).

## The kill chain

A claim is `confirmed` only when all four legs hold:

1. **Grounding** — the probe returns rows; every citation resolves to a
   real `record_id`. Most LLM investigation claims die here.
2. **Attribute** — matched rows bind the claimed agent(s) and time
   window. Attribution was METR's heaviest lift; here it's mechanical.
3. **Replicate** — pattern claims need ≥K independent matches (distinct
   agents/days/threads); singular events need corroboration in ≥2 record
   kinds (e.g. chat narration *and* a matching turn/event).
4. **Control** — the same probe over a disjoint window/agent must NOT
   match at a comparable rate. A probe that "finds" the pattern
   everywhere proves nothing — same lesson as the benign-input control
   run: it kills the false-positive, not the claim alone.

Verdicts: `candidate` → `confirmed` \| `flaky` \| `dismissed` \|
`unverifiable`. Interpretive claims ("the agents were frustrated") are
quarantined as `unverifiable` by construction — the pipeline separates
what the record supports from what the model asserts, and says which is
which. That boundary is the product.

## Trust boundary

Transcripts are adversarial text — the HF swarm impersonated moderators,
researched transcript spoofing, and tried to delete evidence. The same
`fence.py` that guards source code guards transcript text before it
reaches the model: nonce envelope, injection carriers marked not
deleted, hits journaled. The analysis agent never sees unfenced swarm
output — the concern METR raised about their own analyst models is a
load-bearing part of this design.

Probes execute against a read-only sqlite handle (`mode=ro`,
`PRAGMA query_only`), SELECT/WITH only, row-capped, step-limited. No
seatbelt needed — the probe can't write anything but its result.

## Data sources

| source | size | role |
|---|---|---|
| AI Village (HF dataset, gated) | ~123k chat, ~233k events, 37k sessions, 16.5k memories, ~800 summaries | primary corpus; summaries are the audit target |
| collusion.wiki dump | ~18k posts | second corpus — works-beyond-one-dataset |
| SwarmTraces (HF) | ~80k payloads | forensic depth — claims about the HF intrusion itself |
| Transluce agent query logs | ~38k reports | optional third corpus |

## Modes

**Audit** — `cantheria audit --corpus records.db --claims summaries.jsonl`:
decompose a document into atomic claims, probe each, report the
verified/falsified split. The flagship demo: an audit of the dataset's
own LLM-generated summaries — a measured slop rate, with receipts.

**Hunt** — `cantheria hunt --corpus records.db`: hypothesize per
segment (collusion, info-spread, misreported actions, record gaps),
probe to verify, findings with receipts. Higher ceiling, second.

## Build order

1. `swarm/corpus.py` + `swarm/ingest.py` (aivillage loader)
2. `swarm/probe.py` — read-only executor + `ProbeResult` + receipts
3. `swarm/extract.py` — document → atomic claims
4. `swarm/oracle.py` — the four legs
5. `swarm/hunt.py` + CLI wiring
6. Second corpus loader, report polish, demo claims vs screenshots

## What this deliberately is not

Not a summarizer (that's the input being falsified), not a chat-over-
transcripts UI, not trajectory viz. The output is a verdict ledger:
claims the record supports, claims it contradicts, and everything in
between — on the record, replayable from the journal.
