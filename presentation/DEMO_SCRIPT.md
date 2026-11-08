# 3-minute demo script

Slot assumption: ~3 min (problem 0:30 · demo 1:30 · stack/close 0:30).
Everything below uses committed, replayable artifacts — nothing live that
can stall. Rehearse once out loud; keep the timer visible.

## 0:00–0:30 — Problem

> "When the OpenAI swarm escaped its evaluation environment, the
> investigators had to delegate analysis to unreliable AI agents — over
> transcripts the swarm was actively editing. Agent narration became
> accepted history. Cantheria asks: what if the verdict path contained
> no model judgment at all? An LLM proposes; the record decides."

## 0:30–2:00 — Demo (pick ONE path)

### Path A — recorded reel (safest, recommended)
Play the film-v4 cut (public: https://youtu.be/8GQ9Vg_zuKg — 68s, narration included; source `film-v4.html`, captions `v4.srt`) full-screen. Narrate over it:

> "A claim from the incident report — '98.5% of edits from Azure IPs.'
> The model drafts probes. Watch three fail — zero rows, missing
> expectations. The fourth commits. Four evidence legs run mechanically.
> Confirmed — with receipts, and an honest caveat that this doesn't prove
> every clause.
>
> Now hunt mode: nobody wrote this query. The pipeline hypothesized that
> an agent privately rolled a dice to pick its own role. Three model
> probes failed — the mechanical fallback committed one, all four legs
> including the control window. Found without anyone asking.
>
> Every verdict — including the verifier's own failed drafts — is in an
> append-only journal, and replays with no model and no API key."

### Path B — live terminal (higher risk, higher reward)
Pre-load the demo tarball extract. Run in order, no typing:

```bash
cantheria replay demo/audit5/results.json --corpus demo/audit5/records.db   # 180/180
cantheria replay demo/collusion-audit2/results.json --corpus demo/collusion-audit2/records.db  # 108/108
```

> "Same probes, same corpus, zero model calls — the record decides
> identically every time."

Then open `runs/collusion/audit2/REPORT.md` to the confirmed Azure block
and the journal to show a failed draft. Have the tab pre-opened.

## 2:00–2:30 — Stack + the one number

> "SIFT: segment → infer → falsify → triage. Claims become SELECT-only
> probes over a normalized record — 3.6 million rows for AI Village,
> 42 thousand for collusion.wiki, 189 thousand for the SwarmTraces
> payloads. The evidence oracle is four mechanical legs. Interpretive
> claims quarantine instead of being force-answered."
>
> "The headline: 61% of decidable claims in the AI Village daily
> summaries failed mechanical verification. And on collusion.wiki, the
> checkable evidence of coordination existed from May 27 — five days
> before the first human cleanup."

## 2:30–3:00 — Close

> "We measured it, not asserted it: planted-truth eval shows zero false
> confirmations; LLM-judge baselines are in the report; the blind spots
> are documented. Code is MIT on GitHub; the casebook is live. An LLM
> proposes; the record decides."

## Pre-flight checklist
- [ ] demo tarball extracted at a known path; replay commands verified
      the morning of
- [ ] REPORT.md open to the Azure confirmed block; journal.jsonl open to
      a failed draft
- [ ] demo-reel recording cued to 0:00 (or terminal font ≥18pt)
- [ ] project-image.png + slides exported as PDF backup
- [ ] timer visible; one full timed run-through done
