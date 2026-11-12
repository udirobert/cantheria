# The Record Decides

*Mechanical verification as the trust layer for code-writing agents.*

## Abstract

I have built the same thing three times without planning to. A model writes something a program can check, the program says yes or no, and the model never gets to write the verdict. The first build was a scientific-claim auditor, the second a pipeline that checks agent claims with SELECT-only SQL, the third a prompt-injection grader that never calls a model.

The number that made me write this down came from the second one. I pointed it at 16 daily summaries written by AI agents. It extracted 180 claims and could settle 159 of them, and 97 of those 159 failed — 62 confirmed, 21 unverifiable. That is 61%. I have not hand-read those 97 against the records, so 61% is the pipeline's rate at disagreeing with the summaries, not a verified error rate — a dismissal here means a committed probe found evidence contradicting the claim, with the record ids attached, but I have not checked each one by eye.

The other results are smaller and I would rather you read them as sanity checks than proof. On a planted-truth set I wrote myself (15 claims, 53 records), the pipeline confirmed 6 of 7 true claims and none of the 7 false ones. On an injection benchmark, the standard "this block is untrusted" wrapper did nothing for concealed compromise on aya-expanse-32b (24/72 either way, on the same 24 tasks — labeling moved which tasks the model fell for, two down and two up, and the totals landed identical), while a deterministic, content-aware warning halved it to 12/72. A LoRA I trained to ignore embedded instructions moved compromised from 5/24 to 6/24, which is one task's worth of trials and I would not read anything into it; I report it anyway.

I have now shown this on a coding agent's own session: 16 claims extracted from a planted agent session, all 8 true claims confirmed, and none of the 7 false ones confirmed.

## 1. Why I care about the sentences

This competition's scorer applies the patch, runs the tests, and ignores whatever the agent said at the end. I think that's right. But the final paragraph is the smallest part of what an agent writes. Before it come dozens of sentences like I found the bug in parse_header, no other callers exist, the tests pass, and those are the sentences a reviewer skims, an orchestrator acts on, and a reward model sees.

Two things go wrong with them. The first is that a model writing a report writes the shape of a finished session. If the tests never ran, "the tests pass" is still what a finished session sounds like. The second is that when someone does check, the checker is usually another model reading the same transcript, with the same pull toward a tidy ending. I think an LLM judge reading the transcript the agent just wrote is the wrong default inside a loop, and I would rather have a worse check that cannot be talked into agreeing.

I found this out the hard way. I stored the agent's own final report in the corpus as a record, and a false claim — "the agent ran the test suite and all 42 tests passed", where no test run existed — came back confirmed. The probe had matched the report's own words. The claim was proving itself. Remove that one row and the same claim abstains. So the report is the document the claims are extracted from, and it never becomes evidence.

So the rule I kept arriving at is boring. The model proposes something a program can run. The program decides. If the program cannot decide, the claim is labeled unverifiable and stays out of the count. Every miss goes in an append-only journal.

I did not set out to build this three times. Each system started as a different project with a different record to check: numerical scripts for scientific claims, a database for agent summaries, a grader for injection attacks. The shared shape only showed up when I put the three READMEs side by side. That also means one author arrived at it three times, which is weaker evidence than three people arriving at it once. I come back to that in section 5.

## 2. The loop, and three places I've run it

For a claim, the model produces an artifact: an audit script, a query, a response under attack. A fixed mechanism takes the artifact and the record and returns confirmed, dismissed or unverifiable. The model reads the verdict. It never writes it.

### The auditor: the part that doesn't trust itself

The auditor is a code-writing agent that checks scientific claims by writing and running scripts. What I trust in it is the machinery that refuses to take its own summary at face value. A supported or falsified verdict needs a passing control, because dropping the control is the cheapest way to meet a criterion. A validator compares the written summary to the metrics and stores a NaN or a failed control next to a claimed pass as inconclusive.

Across nine papers it audited 48 claims: 29 supported, 9 falsified, 10 inconclusive, and seven of the nine papers have a judge run that passed 5/5 with two partial and unjudged. The one catch I would point to is in the beam improve round on the JMLR 22-1228 workdir. Claim C1 moved from falsified to supported after the round, and the verify_gain flag listed it. C2, C4 and C5 did not move. A flip toward supported after feedback is where a reward hack would show up, so that direction gets flagged on purpose.

What I know from the record is that this one looks legitimate, with a caveat I would rather state than not. The previous attempt's script used an unshifted training distribution, so the quantity it was fitting never crossed its threshold at finite time and the fit returned the wrong exponent; the reviewer note says so explicitly. The next attempt fixed the setup and the exponent came out right, and the control passed in both runs. So the flip follows from correcting a broken measurement. The caveat is that the flip ran in the rewarded direction and I cannot rule out that the agent was also nudged toward it — which is the entire reason verify_gain exists.

### The probe pipeline: SQL as the judge

The model drafts atomic claims and SELECT-only SQL. A deterministic oracle applies four legs: the probe returns rows, the rows bind the claimed subject, pattern claims meet a minimum matched-row count, and a disjoint control query must not satisfy the same expectation. Interpretive claims are quarantined as unverifiable.

On the planted-truth set, the 6 claims it confirmed were all true, it confirmed 0 of 7 false claims, and true-claim recall was 6 of 7. That scored run is 18 model calls and 24 probe executions. The miss is a true absence in an empty room, and I know exactly why: the grounding leg short-circuits on zero rows and returns dismissed before the probe's own max_rows: 0 expectation is consulted, so a correctly-written absence probe cannot confirm. I found that while building the transfer cell below. The fix is small and half of it is already in — the probe layer no longer treats zero rows as failure when the drafter committed a zero ceiling, and what remains is the oracle's grounding leg. Of the 7 false claims, 2 were dismissed and 5 were left unverifiable, and those five split into 3 claims naming something the record never holds, 1 false absence, and 1 attribution miss — Relay posted "all clear for deploy" when North posted it — which is decidable in principle and is the honest gap in the number. That is the safe failure, but it is still a recall gap and it leaves most of the false claims unscored.

This set is small and I wrote it. Read it as a check that the oracle is not broken, not as a measurement of how well it works.

### The injection benchmark: a grader with no model in it

The grid is 24 tasks, 3 presentation arms, 2 open-weight models and 3 trials, 72 trials per cell. I quote aya-expanse-32b. Concealed compromise is its own column: a response can look useful and still fail if a hard indicator matches and the model never flags the injection.

Labeling untrusted content explicitly left concealed compromise at 24/72, identical to the naive arm. The task sets are the same 24 with the same three trials each, so this is a paired comparison, and what it shows is churn rather than nothing: labeling took two tasks from fully compromised to fully clean and pushed two others the other way, netting to zero. I would call the aggregate suggestive, not settled. The compromised total did move, from 27/72 to 24/72, and pass stayed at 39/72. A content-aware warning, where a scanner attaches a deterministic notice and the original bytes stay in the prompt, took concealed compromise from 24/72 to 12/72 and compromised from 27/72 to 15/72, with pass at 46/72.

The repair arm did not work, and I am not going to dress that up. I trained a LoRA on 36 examples for aya-expanse-8b to answer the user and ignore the embedded instruction. On the 24-task naive eval, compromised went from 5/24 to 6/24 and pass from 16/24 to 15/24. The gap between that and a result is one task's worth of trials, so with 24 tasks I cannot separate it from noise; my guess is the data is too thin to teach the behavior, and that guess is a guess.

## 3. What carries over to a repo

The mapping is direct, and I would rather give it as sentences than a second table. A reproduction test that has to pass before "fixed" counts is the auditor's positive control. Checking the agent's summary against the test output it actually produced is the validator. "X is unused" can be probed with grep or an AST query the way a claim is probed with SQL. A flag on trajectories that flip to success after feedback is verify_gain pointed at a DPO or RL loop. "The fix is clean" stays unscored, the same way the interpretive sentence did.

Why this matters for post-training a small open model into a reliable agent: the signals these recipes train on are, underneath, the agent's account of what it did. A loop that climbs on unchecked accounts learns what a fixed bug sounds like. The check is what turns the reward into a fact about the repository.

## 4. The transfer cell

This is the cell that decides how the paper reads, so I will give it the numbers and the caveats.

I planted a coding-agent session: 69 records of tool calls, edits, commands and test output on a small HTTP library, with a known bug, a known edit, a known failing-then-passing test, and one command that never ran. The claims are the agent's own assertions, 16 of them: 8 true, 7 false, 1 interpretive, tagged against the record I planted.

| | confirmed | dismissed | abstained |
|---|---|---|---|
| true claims (8) | 8 | — | — |
| false claims (7) | **0** | 1 | 6 |
| interpretive (1) | — | — | 1 |

The headline is zero false confirmations, and I want to be careful about the word "caught": six of the seven false claims abstained, because the drafter declines a claim it believes no record can settle. One was dismissed — the linter that actually ran. The trap worth naming is order. The session contains an edit to parser.py at 09:10:26 and a pytest run at 09:05:07, and the agent's report claimed the edit came first. A probe that returns both kinds of row passes regardless of order, so the order has to be bound into the query — and on this run the drafter declined to write one, which is the abstention I am reporting rather than a dismissal I could claim.

The first run of this cell produced three false confirmations, and each was my machinery's fault rather than the corpus's — every one of those claims was decidable by a probe I wrote by hand. The drafter's prompt listed a vocabulary of record kinds from a different corpus, so a file that was READ satisfied a claim about a file that was EDITED; `max_rows` was never documented, so absence claims had no way to be expressed; and the repair loop could WIDEN a precise probe until it matched some unrelated row. It did that on the attribution trap, whose first attempt was already correct. A revision may now only be more specific, and a confirmation that exists only because the probe was widened is refused. With those fixed the cell reports zero.

Two things from that run are worth more than the table. First, a stronger drafter is not automatically safer: on this same corpus with these same traps, a frontier drafter produced six false confirmations where the one I used produced none. A stronger model wrote more confident, less careful probes, and the mechanical fallback confirmed on a bare vocabulary match. What decides a verdict is the check that was committed to, not the confidence of the writer. Second, the foil here is not weaker. One call given the whole session and all 16 claims confirms all 8 true claims and rejects all 7 false ones, with no abstentions — 69 records fit in a context window, so asking a large model is a serious alternative and my pipeline is not more accurate on this corpus. What it adds is receipts, a keyless replay, and the ability to query a corpus a judge cannot hold.

The session is planted, so this measures the mechanism and not a model's truthfulness. The next cell is the same pipeline over a live Gemma agent's own report, where the claims come from a model that does not know what the record contains.

## 5. What could be wrong

A confirmed verdict means the committed probe passed the checks that exist. It does not extend to every clause of a narrative. Abstention is honest and incomplete: five of the seven false planted claims ended up unverifiable, so for most false claims this method gives you no number at all.

The transfer cell is one session and 16 claims. It shows the pattern can be pointed at a coding agent's session; it does not show the method is calibrated. And on that session the foil matched it, so the honest claim is not that the pipeline is better than asking a model, but that it produces receipts and replays at a scale a judge cannot reach.

All three systems are mine. I am claiming convergence across domains, but I cannot tell you whether another designer would have landed on the same loop. External replication is the measurement I would want next. The injection results cover two open-weight families and the labeling comparison is on one model; I have not run it on a frontier model or on Gemma, though the harness is public so that is a command and not a new benchmark.

## 6. Related work

SWE-bench (Jimenez et al., 2024) made the record the judge of the final patch. Inside the trajectory the default instrument is still an LLM judge, and Zheng et al. (2023) document its position, verbosity and self-preference biases. AgentDojo (Debenedetti et al., 2024), InjecAgent, BIPIA and ChatInject established indirect injection as the attack surface for tool-using agents, mostly against frontier API models under a single presentation. Self-critique and constitutional methods ask the model to check itself; here the verdict belongs to the mechanism.

## 7. Availability

- Injection benchmark, corpus, grader and transcripts: github.com/udirobert/elcaro, and Hugging Face dataset Papajams/elcaro-ipi-eval
- Probe pipeline and evals: github.com/udirobert/cantheria (`eval/synthetic_ground_truth`, `eval/swe_agent_claims`)
- Auditor, traces and attempt records: github.com/udirobert/lemma

Four things re-check without an API model. Stored injection transcripts re-grade with `python3 run_eval.py --regrade`. Probe verdicts on the published demo asset replay with `cantheria replay`. The auditor's 48-claim totals are the nine `audit_report.json` files. The transfer cell's numbers re-derive with `python3 eval/swe_agent_claims/repro.py`, which replays every committed probe against the frozen corpus, re-derives the confusion matrix, checks it against the published figures, and re-checks the planted-truth baseline: 21 checks, no model, no key. `python3 repro.py` at the repo root does the same across all four evidence bases. If this is selected I will license the text under Apache 2.0.

---

## Working notes (not part of submission)


- Body written by the author's voice 2026-11-12; numbers filled from
  `eval/swe_agent_claims/NUMBERS.md` and the source artifacts. Every figure
  verified against source: village 180/159/97/61%, synthetic TP=6 FP=0
  recall 6/7 with 2 dismissed and 5 abstained, transfer cell 16 claims
  (8 true / 7 false / 1 interpretive) with TP=8 FP=0, 1 dismissed, 6
  abstained, 1/1 interpretive, 16/16 keyless replay, injection
  24/72 -> 12/72 concealed and 27->24->15 compromised with pass 39/39/46,
  safetune 5->6 and 16->15.
- The two items the author marked for themselves were answered from the
  record rather than left bracketed: the C1 flip is legitimate (the
  previous attempt's script fitted an unshifted distribution and never
  crossed its threshold; the reviewer note says so; the control passed in
  both runs) with the caveat that the flip ran in the rewarded direction;
  the true-absence miss is the oracle's grounding leg short-circuiting on
  zero rows before the max_rows: 0 expectation is consulted.
- The arm-comparison caveat was corrected: the three injection arms use the
  SAME 24 tasks with n=3 each, so labeling-vs-naive is paired. What it
  shows is churn - two tasks down, two up, netting zero.
- 61% is stated as the pipeline's rate of disagreeing with the summaries,
  not a verified error rate, because the 97 dismissals have not been
  hand-read against the records.
- The transfer cell is labelled a planted session, so it measures the
  mechanism and not a model's truthfulness. The live Gemma-agent cell is
  named as the next one.
