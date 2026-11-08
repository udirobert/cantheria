# Slide deck outline — 8 slides, ~3 min

Judges remember the demo, not the architecture. Lead with the finding,
show the mechanism once, then the evidence. (Demo-reel video can play on
slide 5 if recording is allowed; otherwise live-terminal the replay.)

## 1. Title
- **Cantheria** — *An LLM proposes; the record decides.*
- Swarm Alignment Hackathon · Track 4: Multi-Agent Oversight and Control
- [project-image.png as backdrop or side asset]

## 2. The problem (30s)
- "When agents investigate agents, who checks the investigation?"
- METR quote: analysis "had to heavily delegate … to often-unreliable AI
  agents" — over transcripts the swarm tried to spoof, edit, and delete.
- One line: agent-written summaries become accepted history.

## 3. The turn (20s)
- Cantheria is a **falsification pipeline**, not a summarizer.
- Model output is *input*. A claim ships only when a committed
  SELECT-only probe survives a mechanical evidence chain:
  grounding × attribute × replicate × control.
- Everything rejected stays in an append-only journal. Verdict path
  contains **no LLM judgment** — the model drafts a probe; sqlite decides.

## 4. The finding (30s) — lead with numbers
- AI Village: 180 claims from 16 daily summaries → **61% of decidable
  claims failed mechanical verification** (97/159).
- The day that wasn't: `summary:2026-07-03` went 0/12 on a day with
  825 chats / ~2k events in the corpus.
- collusion.wiki: auditing the *investigators' own report* → 89% of
  decidable claims could not be mechanically established.
- SwarmTraces: the incident report's own claims vs. its 189k-record
  payload corpus → 2 confirmed w/ receipts, 12 quarantined, 0 false
  confirmations.

## 5. The demo (60–90s)
- Play `demo-reel.html` screen-recording, OR live:
  `cantheria replay` on the demo tarball (keyless, deterministic).
- Beat to hit: 3 failed probes → committed probe → legs light up →
  CONFIRMED + receipts; then the d6-roll claim nobody asked for, saved
  by the mechanical fallback.

## 6. Could it have flagged it early? (20s)
- Detection-latency on collusion.wiki: mechanically-checkable
  coordination evidence from **2026-05-27** — ~5 days before human
  cleanup, ~14 weeks before the public report.
- kollude head-to-head: their first alarm 05-28 vs. our 05-27 —
  independent methods converge. Detectors propose; the record decides.

## 7. Honest edges (20s)
- Planted-truth eval: **0/7 false confirmations**; documented blind
  spots (absence claims, drafter abstention, probe-truncation bug our
  own journal caught).
- LLM-judge baselines measured — we don't claim toy-corpus accuracy;
  we claim scale (3.6M rows), determinism (replay, no model), receipts.
- Not a real-time monitor; no calibrated FPR — the guarantee is
  auditability.

## 8. Close (10s)
- Code: github.com/udirobert/cantheria · Demo: udirobert.github.io/cantheria
- "Every verdict ships with receipts — and the journal of what we got
  wrong."

## Asset checklist
- [x] demo video — `presentation/film-v4.mp4 (hosted: release asset — see repo releases)` (66s, 1080p, ElevenLabs VO)
      source page: `presentation/video-reel.html`; interactive version: `demo-reel.html`
- [ ] project-image.png (done — 1200×630)
- [ ] one receipt screenshot: REPORT.md confirmed block or casebook case
