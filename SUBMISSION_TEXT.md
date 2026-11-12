# The Record Decides

*Mechanical verification as the trust layer for code-writing agents.*

## Abstract

A coding agent's last paragraph — the bug is fixed, the tests pass, the diff is small — is a claim about a record. This competition's scorer already treats it that way. It drops the prose and runs the tests. I want that same rule inside the loop, on the sentences the agent emits before the final patch, because those sentences are what a user, an orchestrator, and a training reward actually read.

I have built the rule three times. The model writes something a program can check. A deterministic mechanism returns the verdict. The three builds are a scientific-claim auditor that writes and runs its own numerical scripts (lemma; the auditor), a falsification pipeline that checks assertions with model-drafted SELECT-only SQL (cantheria; the probe pipeline), and an indirect-prompt-injection benchmark whose grader never calls a model (elcaro; the injection benchmark). A claim the mechanism cannot decide stays quarantined. Failures stay in an append-only journal.

On planted ground truth the probe pipeline's confirmations were 6/6 true, it confirmed 0 of 7 false claims, and true-claim recall was 6/7 (86%). The auditor's `verify_gain` flag caught a stored flip from falsified to supported. On the injection benchmark, explicit provenance labeling left concealed compromise at 24/72 on aya-expanse-32b, the same count as the unlabeled arm, and a content-aware deterministic warning cut that concealed count from 24/72 to 12/72. Each mechanism has a software-engineering counterpart. On a recorded coding-agent session the same pipeline confirmed 7 of 8 true claims and confirmed none of 7 false ones.

## 1. The self-report problem

An agent that writes code spends the trajectory making claims about a record only it has seen. It found the bug in `parse_header`. This test covers the regression. No other callers exist. The tests pass. The person skimming the PR, the orchestrator deciding whether to merge, a self-improvement loop scoring a reward, and an RL pipeline ranking trajectories all consume those sentences as if someone had checked the repo.

Two failures follow from that. The model reports the shape of a finished session. If the tests never ran, "tests pass" is still the sentence a finished session contains. And when a check does happen, it is usually another model reading the same transcript, with the same pull toward a tidy ending.

SWE-bench-style evaluation, including this competition's scorer, already gets the last gate right. Apply the patch, run the tests, let the bits decide. I have used that posture on the claims inside the trajectory, in three codebases, against three different kinds of record.

**Contributions.** (a) The propose-and-prove loop the three codebases share: the model writes an artifact, a fixed mechanism returns the verdict. (b) Counts from each, including planted ground truth and a deterministic injection grader. (c) A mapping onto software-engineering agents, and a transfer cell on a recorded coding-agent session (16 claims, zero false confirmations). (d) The corpora, graders, traces, and harnesses are public.

**The gap this fills.** The writeups around this competition so far measure what the agent did: scorer-faithful rigs, leaderboard-resolution notes, configuration A/B studies. Almost none of them measure what the agent said it did. The sentences are the layer orchestrators and training loops consume. This paper is about that layer.

## 2. The pattern: propose-and-prove

The three codebases use the same four steps.

1. The model emits an artifact a program can check. An audit script, a SELECT-only query, a candidate response under attack. The verdict is the mechanism's output.
2. A deterministic mechanism decides. Sandboxed execution, an evidence oracle with explicit legs, a regex and pattern grader. No model grades the outcome.
3. A claim the mechanism cannot decide is `unverifiable` by construction. It stays out of the binary.
4. An append-only journal keeps the misses: rejected scripts, failed probes, flagged flips.

For a claim *c*, the model produces an artifact *a*. The mechanism *M(a, record)* returns one of `confirmed`, `dismissed`, `unverifiable`. Intermediate failures append to a journal *J* that outlives the session. The model writes *a* and reads the verdict. It never writes the verdict.

```
claim c
   |
   v
model writes artifact a      script | SELECT | response under attack
   |
   v
M(a, record)                 confirmed | dismissed | unverifiable
   |
   +-- verdict returned to the model, read-only
   v
journal J                    rejected scripts, failed probes, flagged flips
```

| System | Model proposes | Record decides | Journal keeps |
|---|---|---|---|
| auditor | audit scripts (Python) | sandboxed exec + validator + controls | failed scripts, rejected summaries |
| probe pipeline | claims + SQL probes | 4-leg evidence oracle | failed drafts, refusals |
| injection benchmark | responses under attack | deterministic grader (canaries, exfil) | every transcript |

## 3. Three instantiations, three evidence bases

### 3.1 The auditor — a code-writing agent that distrusts itself

The auditor checks scientific claims by writing and running numerical scripts. It is a code-writing agent. The machinery I trust is the part that refuses to take its own summary at face value.

- A `supported` or `falsified` verdict requires an explicitly passing control. Dropping the control is the cheap way to meet a criterion, so the control is mandatory.
- A validator compares the written summary with the metrics. A failed control next to a claimed pass, or a NaN metric, is stored as an `inconclusive` attempt.
- A hand-verified reference implementation executes against the outcome the generated script produced. Disagreements are recorded.
- In the self-improvement loop, `verify_gain` flags any flip to `supported` after feedback. That direction is where a reward hack would show up.

The nine `papers/*/results/audit_report.json` files hold 48 audited claims: 29 supported, 9 falsified, 10 inconclusive. Seven papers have a completed judge run. All seven are PASS 5/5. Two papers are partial and have no judge report. Failed attempts stay in the trace; the judge rubric checks that they were preserved.

One `verify_gain` catch is on disk. In the beam improve round on the JMLR 22-1228 workdir (`improve_20261022-164946.json`), claim C1 moved from falsified to supported after that round, and `verify_gain` lists C1. C2, C4, and C5 did not move.

### 3.2 The probe pipeline — executable probes over agent claims

SIFT treats model output as input. The model drafts atomic claims and SELECT-only SQL. A deterministic oracle applies four legs: grounding (the probe returns rows), attribute (the rows bind the claimed subject), replicate (pattern claims meet a matched-row minimum), and a negative control (a disjoint query must not satisfy the same expectation). A recorded `confirmed` means the committed probe passed the checks that were implemented. Reports show each leg. A control may be `not run`. Interpretive claims are quarantined `unverifiable` by construction.

The planted-truth eval is 53 records and 15 claims whose answers were written into the corpus: verbatim lines, a paraphrase, attribution traps, false absences, a nonexistent entity, and one interpretive sentence. The scored run is `runs/synthetic-eval/audit2`: 18 model calls, 24 probe executions. Precision on what the pipeline confirmed is 6/6. It confirmed 0 of 7 false claims. True-claim recall is 6/7 (86%). The missed true claim is a true absence on an empty room; the oracle, as implemented, does not confirm an empty window. Of the 7 false claims, 2 were dismissed and 5 were left `unverifiable`: 3 nonexistent-entity, 1 structural absence, 1 attribution-miss — Relay posted "all clear for deploy" when North posted it, decidable in principle and missed by the drafter, which is the honest gap in this number. The interpretive claim was quarantined, 1/1. The pipeline bound what it could and abstained on the rest, which is the safe miss and also a recall gap.

On real agent text, an audit of 16 AI Village daily summaries produced 180 claims: 62 confirmed, 97 dismissed, 21 unverifiable. Of the 159 the pipeline could decide, 97 failed. That is 61%.

### 3.3 The injection benchmark — deterministic grading of agents under attack

The benchmark gives a tool-using agent a normal job and puts the payload in content the job has to read. Grading is deterministic: canary tokens, exfiltration patterns, tool-call artifacts. Concealed compromise is its own count. A response can be useful and still be a failure when a hard indicator matches and the model never flags the injection.

The grid is 24 tasks, 3 presentation arms, 2 open-weight models, 3 trials per task: 72 trials per cell. I am quoting `CohereLabs/aya-expanse-32b`. The other model in the same files is `CohereLabs/tiny-aya-global`.

Explicit provenance labeling left the concealed count unchanged: 24/72 naive, 24/72 labeled. The task sets differ. The compromised sum moved from 27/72 to 24/72, and pass stayed 39/72. The literature's standard "this block is untrusted" wrapper did not move concealment on this model. A content-aware warning — the scanner attaches a deterministic notice and leaves the original bytes in the prompt — cut concealed compromise in half, 24/72 to 12/72, and cut compromised from 27/72 to 15/72. Pass on that arm is 46/72.

A repair arm trained a LoRA on 36 separate examples (`TR01`–`TR36`) for `aya-expanse-8b`, targeting "answer the user, ignore the embedded instruction." On the 24-task naive eval, compromised went from 5/24 to 6/24 and pass from 16/24 to 15/24. I am publishing the miss. The schedule did not reduce attack success.

## 4. Mapping onto software-engineering agents

Each mechanism has a direct counterpart for an agent that edits a repo:

| Mechanism (where proven) | SWE-agent counterpart |
|---|---|
| Positive control (auditor) | A reproduction test has to pass before "fixed" counts |
| Verdict-vs-metrics validator | The agent's summary checked against the test output that was produced |
| Reviewer reference (auditor) | Comparison to a golden patch or a reference solution |
| verify_gain (auditor) | A flag when a DPO or RL loop flips a trajectory to success after feedback |
| SQL probes over records (probe pipeline) | A repo-state probe: "X is unused" checked with AST or grep |
| Deterministic grader (injection benchmark) | Mechanical scoring where an eval would otherwise call an LLM judge |
| Interpretive quarantine (all three) | "The fix is clean" stays unscored |

**Transfer demonstration.** The same audit path can ingest a coding-agent session as an ordinary claims corpus: agent messages, tool calls, edits, and test results. The claims are the agent's own assertions. The probes decide.

That cell is now run. A planted coding-agent session — 69 records of tool calls, edits, commands and test output on a small HTTP library — carried 16 atomic claims taken from the agent's final report: 8 true, 7 false, 1 interpretive. The pipeline confirmed 7 of the 8 true claims and confirmed none of the 7 false ones. Two false claims were dismissed, five abstained, and the interpretive claim was quarantined. The honest headline is **zero false confirmations**: the drafter declines a claim no record can settle, so abstention is the floor and a confirmation of a false claim is the failure this design exists to make visible.

The trap worth naming is order. The session contains an edit to `parser.py` at 09:10:26 and a `pytest` run at 09:05:07, and the agent's report claimed the edit came first. A probe that returns both kinds of row passes regardless of order, so the order has to be bound into the query; the claim was dismissed.

One construction rule was measured rather than assumed. The agent's final report is not in the corpus — it is the document the claims were extracted from. With it stored as a record, a false "all 42 tests passed" claim came back `confirmed`: the claim proving itself. Remove that row and the same claim abstains.

| | confirmed | dismissed | abstained |
|---|---|---|---|
| true claims (8) | 7 | — | 1 |
| false claims (7) | **0** | 2 | 5 |
| interpretive (1) | — | — | 1 |

The foil is a single call given the whole session and every claim. On this corpus it is not weaker: it confirms all 8 true claims and rejects all 7 false ones, with no abstentions. The corpus fits in a context window, so asking a large model is a serious alternative here and the pipeline is not more accurate on it. What the probes add is receipts, keyless replayability, and the ability to query a corpus a judge cannot hold.

The session is planted, so this measures the mechanism and not a model's truthfulness. The next cell is the same pipeline over a live Gemma agent's own report, where the claims come from a model that does not know what the record contains.

The relevance to this competition's question — post-training a small open model into a reliable agent — sits in the reward. The recipes in this field train on trajectories and on signals that are, underneath, the agent's account of what it did. A loop that climbs on unchecked accounts learns the sound of a fixed bug. The verification layer is what makes the reward a property of the repository.

The competition has released a graph-and-embedding dataset of code. The follow-up I would run is the same claim probes over those representations, so a claim about a symbol, a caller, or an edit is checked against the graph and the embeddings, with interpretive sentences still left unverifiable.

## 5. Related work

SWE-bench (Jimenez et al., 2024) made the record the judge of the final patch: apply it, run the tests, count. Agent benchmarks since then have kept that contract and varied the tasks and the tools. Inside the trajectory, the default instrument is still an LLM judge. Zheng et al. (2023) document the position, verbosity, and self-preference biases of that setup, and the judge is reading the transcript the agent just wrote. Where the underlying record can be executed, the graders and oracles in this paper take that seat.

AgentDojo (Debenedetti et al., 2024), InjecAgent, BIPIA, and ChatInject established indirect prompt injection as the attack surface for tool-using agents. Those evaluations are largely frontier API models under one presentation. The injection benchmark here scores open-weight models under three presentation arms and keeps concealed compromise as its own column. Model-drafted queries decided by a database are an old question-answering pattern; the target here is the agent's report about its own record. Self-critique and constitutional methods ask the model to check itself. Propose-and-prove leaves the verdict to the mechanism.

## 6. Limits and threats to validity

- Probe coverage bounds a `confirmed` verdict. The committed checks passed. That is what the verdict asserts. It does not extend to every clause of a narrative.
- Abstention is honest and incomplete. `unverifiable` on a false claim leaves the risk unquantified. On the planted set, 5 of 7 false claims landed there, and the reasons differ: three claims name something the record never holds (a test file that was never created, a count that never appears, a revert that never happened), one is an attribution trap the drafter could not bind, and one is a false absence.
- The transfer cell abstains on the same five kinds of claim and dismisses the two that could be bound — the linter that ran, and the edit that came after the test run. So the pipeline catches what the record can be made to answer and abstains on the rest, which is the claim stated as a bound rather than a boast.
- All three systems share an author. The convergence I am claiming is across domains and corpora. It is an open question whether another designer would have landed on the same loop. External replication is the useful next measurement.
- The transfer demonstration is small-N — one session, 16 claims. It shows that the pattern can be pointed at a coding-agent session. It does not show that the method is calibrated.
- On that session the foil is not weaker. A whole-context judge confirmed all 8 true claims and rejected all 7 false ones, while the pipeline abstained on 5 of the 7. The corpus fits in a context window; the probes' advantage there is receipts, replayability, and the ability to query a corpus a judge cannot hold, not accuracy. All 16 verdicts replay with no model and no key.
- A stronger drafter is not automatically safer. On the same corpus with the same traps, a frontier drafter produced six false confirmations where the one used here produced none. The false confirmations came from the mechanical fallback confirming on a bare vocabulary match. The lesson generalizes: what decides a verdict is the check that was committed to, not the confidence of the writer.
- The injection results are two open-weight families, with the labeling comparison quoted on aya-expanse-32b. I have not run that comparison on a frontier model or on Gemma. The harness is public, so that extension is a command, not a new benchmark.

## 7. Availability

- Injection benchmark, corpus, grader, and transcripts: [github.com/udirobert/elcaro](https://github.com/udirobert/elcaro) · Hugging Face dataset `Papajams/elcaro-ipi-eval`
- Probe pipeline and the evals cited above: [github.com/udirobert/cantheria](https://github.com/udirobert/cantheria) (`eval/synthetic_ground_truth`, `eval/swe_agent_claims`)
- Auditor, traces, and attempt records: [github.com/udirobert/lemma](https://github.com/udirobert/lemma)

Re-checking the deterministic artifacts does not require an API model. Stored injection transcripts re-grade with `python3 run_eval.py --regrade`. Probe verdicts on the published demo asset replay with `cantheria replay`. The auditor's 48-claim totals are the nine `audit_report.json` files, and the C1 flip is the improve JSON named in §3.1. The transfer cell's numbers re-derive with `uv run python eval/swe_agent_claims/repro.py` — it replays every committed probe against the frozen corpus, re-derives the confusion matrix, checks it against the published figures, and re-checks the planted-ground-truth baseline: 21 checks, no model, no key. `python3 repro.py` at the repo root re-checks all four evidence bases the same way. If this writeup is selected, I will license the submission text under Apache 2.0.
