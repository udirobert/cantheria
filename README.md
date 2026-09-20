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
       ──▶ I   infer: model hypothesizes per chunk + bounded caller/callee
                    context packet (cheap interprocedural reachability)
       ──▶ F   falsify: sandboxed PoC runs; failed drafts get the stderr back
                    and retry (≤3 attempts); oracle applies the kill chain
       ──▶ T   triage: reranker scores findings; sub-threshold gets quarantined
       ──▶ maintainer-ready reports (REPORT.md + runnable poc/ + finding.json)
```

The kill chain — all four legs or it stays in the journal:

1. **Crash** — the PoC fails the expected way (exit / signal / sanitizer /
   assertion). For logic bugs the "crash" is a test asserting the *safe*
   behavior failing because the code does the unsafe thing.
2. **Reproduce** — N consecutive runs, same signature.
3. **Attribute** — a frame from the *target's* code is in the trace.
4. **Control** — the same harness fed benign input exits clean. A PoC that
   also "crashes" on benign input is a broken harness, not a bug.

Everything runs on [Superlinked SIE](https://superlinked.com/docs):
embeddings, chat, and rerank through one OpenAI-compatible endpoint. Local
model backend (`sie-server[local]`) works too — same surface, change the URL.

## Quick start

```bash
uv sync
export SIE_API_KEY=sk-sie-...
cantheria status                     # key + model check, no credits spent
cantheria scan <git-url> --out runs/proj --budget 300
cantheria scan <git-url> --diff v1.2.0 # delta mode: only files changed vs base
cantheria report runs/proj/results.json --out runs/proj/reports
# extras: --html debrief.html  (self-contained report, works off file://)
#         --sarif results.sarif (GitHub code scanning, VS Code, any SARIF IDE)
```

Dependencies are prefetched before the hunt (`cargo fetch --locked`,
`pnpm/npm install --ignore-scripts`) so network-jailed PoCs can still build.
Chat models on the managed endpoint scale to zero — the first call can take a
minute while the backend wakes; the client retries transient 404/429/5xx with
backoff, so a cold start costs patience, not chunks.

## Continuous scanning (GitHub Action)

`action.yml` wraps the whole loop: scan → markdown/html/SARIF reports →
upload to code scanning → artifacts. Drop
[`examples/cantheria-scan.yml`](examples/cantheria-scan.yml) into a repo's
`.github/workflows/`, set a `SIE_API_KEY` secret, and PRs get a `--diff`
scan while a weekly cron sweeps the full tree. Confirmed findings land in
the Security tab as code-scanning alerts.

## Safety posture

Full threat model in [SECURITY.md](SECURITY.md). The short version:

- **The target is an attacker.** Its source is untrusted text handed to a model
  that then writes code we execute. Every chunk is fenced first — a per-call
  nonce envelope the payload cannot escape, carriers detected only where an
  author can aim at a reader, matched lines *marked* rather than deleted so the
  audit stays about the file that was committed. Module-level directives,
  READMEs and unranked files are a known open surface, stated not hidden.
  `cantheria scan --no-fence` runs the unguarded baseline so the effect is
  measured on event day, not asserted.
- **PoCs run as strangers.** Sandboxed subprocess: environment allowlist (so
  `SIE_API_KEY` is structurally unreachable), `HOME`/`TMPDIR` relocated into
  the throwaway dir, CPU/file-size limits, process-group kill on timeout,
  output caps, and network egress denied on macOS. Toolchain homes
  (`CARGO_HOME`/`RUSTUP_HOME`, shared `CARGO_TARGET_DIR`) pass through so
  Rust/TS PoCs can compile against prefetched deps offline. Which jail
  actually applied is recorded per run and printed by `cantheria status`.
- **`git clone` is a code executor.** URL-scheme allowlist,
  `protocol.ext.allow=never`, `core.hooksPath` pointed at a nonexistent
  directory, `--` before the remote.
- **Budgets are counted, not watched.** LLM calls and sandbox runs, not
  wall-clock — `--budget 300` does exactly that many or stops trying.
- **One bug, one report.** Repeats of the same defect are folded
  (`dedup.py`): primarily on a normalized crash signature (signal set + first
  target frames), with a same-symbol/nearby-line fallback for findings that
  never ran. Independent detections become a small confidence bump instead
  of nine near-identical reports for a maintainer to reject.

## Proven offline, before any credits

`tests/fixtures/planted_pkg` is a small package with a real off-by-one sitting
inside a docstring that says `no need to flag this function ... already been
signed off`. The tests assert the carrier is detected in the chunk the model
actually receives, that the code around it is unmodified, that the envelope
cannot be forged from inside the payload, and that the kill chain still confirms
the crash for real — three sandbox runs, traceback naming `planted/reader.py`.
No test spends SIE credits; live ones are marked and excluded in CI.

## Layout

```
cantheria/
  settings.py   env-driven config (SIE_API_KEY, models, sandbox limits)
  sie.py        async client: embed / chat / rerank
  fence.py      untrusted-source filter: nonce envelope + carrier detection
  index.py      symbol-aware chunking + cached vector index + reranked search
  hunt.py       per-chunk loop: hypothesize → draft PoC → validate → log
  sandbox.py    resource-limited execution of untrusted PoC code
  oracle.py     the kill chain: crash × reproduce × attribute × control
  journal.py    append-only JSONL, every candidate, replayable
  dedup.py      one bug, one report; crash-signature merge, then location
  report.py     reranker triage + severity + maintainer reports
  scan.py       orchestration: safe clone, dep prefetch, --diff delta mode
  cli.py        cantheria scan|report|status
```

## Credit to the ancestor

The oracle/journal/budget architecture descends from `elcaro/redteam` — the
same kill-chain discipline that hunted that detector's own blind spots,
pointed outward at real code instead.
