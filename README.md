# Cantheria

> A cantheria is the place where canaries are kept. Cantheria flies canaries
> into open-source software — cheaply, exhaustively, and on the record — and
> only reports what kills them.

Autonomous vulnerability discovery for open-source projects, built for the
Superlinked x partner one-day hackathon. Every claim it makes is replayable:
a finding is only real when a PoC crashes, the crash reproduces, and the
trace names target code.

## Pipeline — SIFT

```
repo ──▶ S   index: chunk by symbol, embed with SIE (Qwen3-Embedding)
       ──▶ I   infer: open coder model hypothesizes bug classes per chunk
       ──▶ F   falsify: sandboxed PoC runs; oracle applies the kill chain
       ──▶ T   triage: reranker scores findings; sub-threshold gets quarantined
       ──▶ maintainer-ready reports (REPORT.md + runnable poc/ + finding.json)
```

The kill chain — all three legs or it stays in the journal:

1. **Crash** — the PoC fails the expected way (exit / signal / sanitizer).
2. **Reproduce** — N consecutive runs, same signature.
3. **Attribute** — a frame from the *target's* code is in the trace.

Everything runs on [Superlinked SIE](https://superlinked.com/docs):
embeddings, chat, and rerank through one OpenAI-compatible endpoint. Local
model backend (`sie-server[local]`) works too — same surface, change the URL.

## Quick start

```bash
uv sync
export SIE_API_KEY=sk-sie-...
cantheria status                     # key + model check, no credits spent
cantheria scan <git-url> --out runs/proj --budget 300
cantheria report runs/proj/results.json --out runs/proj/reports
```

## Safety posture

- All PoCs execute in a sandboxed subprocess: address/CPU/process limits,
  killed process group on timeout, throwaway copy of the repo, output caps.
- The scan budget is counted in LLM calls and sandbox runs, not wall-clock —
  a `--budget 300` scan does exactly that many calls or stops trying.
- The audited code is treated as untrusted *data* in every prompt; the model
  is told so, and PoCs never run until the oracle executes them.
- Not a kernel-level jailbreak barrier: a malicious PoC exploiting a container
  escape would beat it. Hackathon threat model, stated honestly.

## Layout

```
cantheria/
  settings.py   env-driven config (SIE_API_KEY, models, sandbox limits)
  sie.py        async client: embed / chat / rerank
  index.py      symbol-aware chunking + cached vector index + reranked search
  hunt.py       per-chunk loop: hypothesize → draft PoC → validate → log
  sandbox.py    resource-limited execution of untrusted PoC code
  oracle.py     the kill chain: crash × reproduce × attribute
  journal.py    append-only JSONL, every candidate, replayable
  report.py     reranker triage + severity + maintainer reports
  scan.py       end-to-end orchestration, budgeted, best-first
  cli.py        cantheria scan|report|status
```

## Credit to the ancestor

The oracle/journal/budget architecture descends from `elcaro/redteam` — the
same kill-chain discipline that hunted that detector's own blind spots,
pointed outward at real code instead.
