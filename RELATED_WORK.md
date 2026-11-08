# Related work & competitive position

Where Cantheria sits relative to the state of the art, and exactly what it
claims (and does not claim) to be. Written for the sprint report's related-
work/positioning section; every entry verified by search on 2026-11-08.

## The gap Cantheria occupies

Multi-agent incident investigation today runs on narration: agents write
summaries, investigators (human or AI) skim them, and the narrative becomes
fact. The METR/Redwood investigation of the OpenAI–Hugging Face incident
states the problem in its own words — analysis "had to heavily delegate …
to often-unreliable AI agents" over transcripts the swarm tried to spoof,
edit, and delete.

Three properties are needed and, as of this writing, no single system has
all three:

1. **Executable evidence** — a verdict backed by something that re-runs,
   not a model's say-so.
2. **Replay without the model** — verdicts re-verifiable keylessly, so the
   check doesn't itself depend on the unreliable component.
3. **Audit of the auditor** — the verification process's own failures are
   recorded, because the investigator's model is also untrusted.

Cantheria is built to supply all three for claims about agent-swarm
records. Everything below is either a different layer, a different claim
type, or missing one of the three properties.

## Closest neighbors — and the difference

### Swarm-collusion detectors

- **kollude** (PyPI, github.com/dhruva137/kollude) — *built for this same
  hackathon*. Reads agent logs (JSONL/CSV/Parquet), detects coordinated
  template-copying via multiplicity (M) and coordinated share (C)
  statistics, alarms through an anytime-valid e-CUSUM with false-alarm
  rate bounded by α, names the seeder and carriers, ships an MCP server
  and investigator console.
  - **Layer difference:** kollude is a *detector* — it answers "is there
    coordinated copying in this population?" with a calibrated statistical
    alarm. Cantheria is a *verifier* — it answers "is this specific claim
    true?" for any claim type (event, pattern, coordination, absence),
    with per-claim receipts.
  - **Honest trade:** kollude has *calibrated* false-alarm bounds
    (e-values). Cantheria's verdicts are mechanically replayable but
    probe-drafting is LLM-dependent — Cantheria claims auditability, not
    calibration. The two are complementary: a kollude alarm is exactly the
    kind of suspicion Cantheria can convert into an adjudicated claim.
- **Audit the Whisper / Secret Collusion line** (Motwani et al., NeurIPS
  2024; Ostailor's steganographic-collusion detector with ColludeBench)
  — covert-channel capacity theory and calibrated steganography detectors.
  Detects *hidden* channels; Cantheria verifies claims about the visible
  record. Complementary.
- **MAIA — Multi-Agent Collusion** (Apart AI Control Hackathon 2026,
  2nd place LinuxArena track) — omission attacks and compositional
  collusion in monitored settings; showed GPT-4-class monitors miss
  merge-only harms. Evidence that monitor-based oversight has measured
  gaps — motivation for a verification layer.
- **kmad/agent-swarm-forensics** — secondary analysis of the collusion.wiki
  dataset with runnable scripts. One corpus, bespoke analysis; Cantheria
  is corpus-agnostic and additionally audits the *investigators' own
  report* against its underlying record.

### Claim verification / fact-checking

- **FEVER → AVeriTeC** — the field's claim-verification benchmarks.
  AVeriTeC scores verdict *and* evidence quality jointly; its four-way
  label set (supported / refuted / not-enough-evidence / conflicting)
  maps onto Cantheria's confirmed / dismissed / unverifiable /
  (conflicting ≈ control-leg failure). **InFact** (GPT-4o pipeline, 63%
  AVeriTeC score) is the current SOTA bar for open-web claim verification.
- **SummaC, QAFactEval, MiniCheck, AlignScore, UniEval** — factual-
  consistency metrics scoring (document, summary) pairs statistically
  (NLI, QA, specialized models). "Do Automatic Factuality Metrics
  Measure Factuality?" (arXiv 2411.16638) documents their brittleness.
  Cantheria differs in kind: per-claim *executable* probes over a
  normalized structured record, not a scalar consistency score.
- **Evidence Chain Evaluation** (arXiv 2607.18240) — selective fact-
  checking with an explicit `uncertain` verdict; abstention as a
  safety-oriented mechanism (91.6% accuracy, defers low-evidence cases).
  Validates Cantheria's `unverifiable` quarantine; we adopt its reporting
  vocabulary (coverage vs selective accuracy).
- **SufficientFacts / NEI-CAP** — work on the "not enough evidence"
  label and its construction artifacts; relevant to Cantheria's
  absence-claim boundary (see eval README — true absences on empty
  windows are currently unconfirmable).
- **Attributable by Construction** (arXiv 2606.23989) — closest claim-
  decomposition neighbor: LLM extracts atomic claims + verbatim quotes,
  provenance resolved deterministically. They verify *where* a claim is
  stated; Cantheria verifies *whether it is true*.
- **sui-1** — grounded long-form summarization with a citation-
  verification stage; generation-side, not post-hoc audit.

### Agent-trajectory oversight & failure attribution

- **AgentDojo-based detectors, AlignmentCheck, agent-as-a-proxy attacks**
  (arXiv 2602.05066) — LLM monitors for tool-call trajectories; shown
  bypassable (>90% ASR). Motivates Cantheria's architecture: the verdict
  path contains no LLM judgment — the model drafts a probe, the record
  decides.
- **TraceElephant** (ACL 2026), **LongRCA Bench** (arXiv 2608.15242),
  **AgentLocate** (arXiv 2607.07989), **MP-Bench** (arXiv 2603.25001),
  trajectory-attribution benchmark (arXiv 2608.06909) — failure
  attribution/localization benchmarks over agent trajectories. Cantheria's
  attribute leg + receipts are adjacent but aimed at claim truth, not
  failure root-causing.
- **Audit/observability infra** — synapse, hansard, premier, agentpeek:
  unified agent logs, attribution confidence, session replay. They capture
  *what happened*; Cantheria decides *which claims about it hold*.

## Landscape sweep 2 — Parallel web search, 2026-11-08

A second sweep (Parallel Search API) surfaced neighbors the first pass
missed. Two are close enough to require explicit differentiation:

- **blasrodri/truth** (GitHub) — "deterministic fact-checker for AI coding
  agents": verifies an agent's claims about *its own work* against the
  real code, git diff, and logs; local MCP server, cited verdicts,
  "refuses to bluff." **Closest architectural neighbor.** Difference:
  truth operates in the single-agent development loop — the evidence is
  the repo the agent just touched. Cantheria operates on *populations* of
  agents in shared, adversarially-edited records (3.6M-row normalized
  corpus), where the investigator's own model is also untrusted, and adds
  hunt mode, the verifier journal, and keyless replay of committed
  probes. Truth answers "did the agent do what it claims?"; Cantheria
  answers "which claims about the swarm survive the record?"
- **NovaFabric** (arXiv 2609.12582) — tamper-evident, replayable evidence
  for agent runs: Run Capsule schema, DSSE signatures, Merkle log,
  four-mode replay. **Provenance layer, not adjudication** — it seals
  what happened; it does not decide which claims about it are true.
  Natural composition: a NovaFabric-sealed run could be the corpus
  Cantheria audits.
- **Monitor Red Teaming** (ICLR 2026) — standardizes adversarial
  stress-testing of agent monitors; shows targeted human escalation
  improves TPR. Supports our claim that oversight claims need adversarial
  evaluation — which is what the synthetic ground-truth eval supplies.
- **VLA — Verifiable Latent Alignments** (arXiv 2608.19161) — monitors
  covert coordination in *latent* multi-agent channels (AUROC 0.993
  homogeneous). Requires white-box activation access; Cantheria is
  black-box over the observable record — complementary coverage of
  different channels.
- **Steganalysis of Adaptive Covert Collusion** (arXiv 2608.02698) —
  black-box, trace-only, calibrated-FPR population collusion detector.
  Same family as kollude; same layer difference applies.
- **Agent Autopsy / OpenClaw forensic foundations** (arXiv 2604.05589,
  agentautopsy.com) — forensic methodology and playbooks for agentic
  incidents. Human-facing investigation guidance; no mechanical claim
  verification.
- **Chanl tool receipts** — per-tool-call signed receipts. Evidence
  capture, not claim adjudication.
- **KLA deterministic replay** — replays *policy decisions* over recorded
  inputs with pinned versions; recorded model/judge verdicts are reused,
  not re-derived. Different object: decision replay vs. claim truth.

**Sprint-culture signal (from the AI Collusion Research Sprint gallery,
392 entries):** the projects judges rewarded used pre-registered
evaluations, explicit "channel but no collusion" controls, and detector
critiques ("Collusion Detectors See Shared Secrets, Not Collusion";
"LLM Monitors Mistake Open Cooperation for Collusion"). Cantheria's
control leg, planted-truth eval, and documented blind spots match exactly
this register — the differentiation to emphasize is *adjudication with
receipts*, not another detector.

## What Cantheria claims — precisely

- A claim ships only when a committed SELECT-only probe passes a
  mechanical evidence chain (grounding × attribute × replicate × control)
  against the normalized record; receipts are record_ids a human can
  inspect.
- Every verdict — including the auditor's own failed drafts — is in an
  append-only journal and replays deterministically with no model and no
  API key (`cantheria replay`).
- Claims no probe can decide are quarantined `unverifiable` by
  construction rather than force-answered.
- Measured, not asserted: audit of 16 AI Village daily summaries (180
  claims, 61% of decidable claims failed verification), audit of the
  collusion.wiki incident *report* against its own 42k-record dataset
  (108 claims), keyless replay agreement 180/180, 24/24, 24/24, 108/108.

## What Cantheria does NOT claim

- Not a real-time monitor — batch forensics over a normalized record.
  Detection-latency analysis (reports/detection-latency-collusion.md)
  shows when evidence *would have been* verifiable, not live alerting.
- Not a calibrated detector — no e-value/FPR guarantees like kollude's;
  the guarantee is replayability and auditability.
- Not proof of narrative truth — a `confirmed` verdict means the
  committed probe passed the implemented checks, nothing more.
- Probe-pass ≠ claim-true in general: the synthetic ground-truth eval
  (eval/synthetic_ground_truth/) measures exactly this gap, including
  known blind spots (absence claims, drafter abstention on fabricated
  specifics).
