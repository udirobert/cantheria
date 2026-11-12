# Kaggle submission checklist — Gemma 4 Developer Agent **Paper Track**

Deadline: **2026-11-12 23:59 UTC**. The paper track is a *separate*
competition from the main one — joining the main competition does not
enter you here.

## Before submitting

- [x] Join `kaggle.com/competitions/gemma-4-developer-agent-paper` and
      accept its rules. Verified 2026-11-12 via `kaggle competitions
      list`: `userHasEntered=True` on the paper track for `papajams`.
- [x] Fill `【PENDING】` in `SUBMISSION_TEXT.md` with
      `eval/swe_agent_claims` results, or take OUTCOME B (delete markers,
      keep "specified and unnumbered"). Fill skeleton with `⟨N⟩`
      placeholders for both outcomes is ready at
      `eval/swe_agent_claims/PENDING_FILL.md` — the editor substitutes
      from `NUMBERS.md` only; nothing gets invented.
      **RESOLVED 2026-11-12 13:0x UTC — the numbers exist.** The eval ran
      (`eval/swe_agent_claims/NUMBERS.md`, commit `eb50031`): 69-record
      planted session, 16 claims (8 true / 7 false / 1 interpretive),
      7/8 true confirmed, **0/7 false confirmed**, 2 dismissed, 5 abstained,
      1/1 interpretive quarantined, 16/16 keyless replay.
      `SUBMISSION_TEXT.md` regenerated from the draft body: **2,817 words,
      zero `【PENDING】` markers**. The fill kept the honest framing — the
      headline is *zero false confirmations*, and §4 says the whole-context
      judge is not weaker on this corpus rather than claiming a win the
      numbers do not show.
- [x] Final word count ≤ 3,000 for the resource writeup body:
      `elcaro/SUBMISSION_TEXT.md` is 1,999 words. Slot 1: **2,817 words**
      after the PENDING fill (was 2,300 with markers). Both under cap.
- [x] Verify every linked artifact is public *before* the writeup goes
      up: github repos, HF dataset `Papajams/elcaro-ipi-eval`, adapter.
      Slot 2 checked 2026-11-12: `udirobert/elcaro` private=false, MIT,
      default branch `main`; dataset private=false, gated=false, license
      mit; adapter `Papajams/aya-expanse-8b-elcaro-sft` private=false
      (API omitted `gated`). Collection page also returned 200.
- [x] Dual submission RESOLVED (rules reviewed 2026-11-12): Kaggle rules
      are explicitly **Non-Archival** — "submission does not prevent
      submission to other conferences or venues"; arXiv preprints fine
      per host. Lexsi rules require only originality/own-work + teams
      retain IP — no exclusivity clause. Green light both ways.
- [x] **Tie-break is earlier entry wins** ("the Paper that was entered
      first wins") — submit as early as ready, not at the deadline.
      Slot 2 published + confirmed **submitted** 2026-11-12 ~11:55 UTC —
      timestamp locked. Slot 1 still buys position every hour it waits.
- [x] **LLM-writing warning** (host): "purely LLM-generated writing will
      not score well" — humanize the drafts: own-voice pass on every
      section, first-person judgments, cut anything you wouldn't say.
      Slot 2 done 2026-11-12 (first person, counts in place of the
      rounded table). Slot 1 not part of this pass.
- [x] Optional relevance bonus: the competition released an official
      graph + embedding dataset and "highly encourages" its use — a
      future-work line proposing claim-probes over code-graph repo
      representations earns relevance without implementation cost.
      Slot 1: IN the draft (§4, "the follow-up I would run is the same
      claim probes over those representations"). Slot 2: not added —
      not supported by the repo notes, kept honest.
- [x] **Winner license is Apache 2.0** (rules: winners license the work
      Apache 2.0 + reproducible code/docs where applicable). elcaro is
      MIT — fine to dual-license; be ready to state it.
      Stated in the resource writeup Availability section: repo MIT,
      selected submission text also Apache 2.0.
- [ ] Escape hatch: **private attached resources auto-publish after the
      deadline** — a private Kaggle dataset/notebook attached now
      becomes public post-deadline. Slot 2: not needed, artifacts public.
      Slot 1: still open — `eval/swe_agent_claims/` must be committed +
      pushed to `github.com/udirobert/cantheria` before submit (runs/ is
      gitignored; the corpus copy beside the eval dir is the evidence).
      If push slips, attach the frozen records.db + claims.jsonl as a
      private Kaggle dataset instead.
- [ ] One-command repro: `repro.py` reprints every headline number from
      stored artifacts — spec at `REPRO_SPEC.md`, owned by the paper
      editor while the eval runs. Also adds the abstention taxonomy
      (3 nonexistent-entity, 1 structural absence, 1 attribution miss)
      to the paper where §3.2/§6 currently show a bare "5 of 7".
- [ ] If running a Gemma eval arm: even one row in the §3 table of the
      resource writeup makes it competition-relevant. Optional.
      No Gemma transcripts in the tree (2026-11-12). The resource
      writeup says that and does not add a row. Leave this open until
      an arm actually runs.

## Submitting (per writeup — max 2 final submissions)

**Order: slot 2 (resource) first** — it needs no pending numbers, so
publishing it early locks a valid entry. Then finish slot 1.

1. On the paper-track competition page → **Writeups** → create writeup.
2. Paste the body (markdown supported — tables render; strip the
   "Working notes" section and the draft header block first).
3. Set the title (draft titles at the top of each file).
4. **Publish** it — unpublished/draft writeups are ineligible.
5. Select it as a competition submission (writeup ≠ submission until
   selected; up to 2 allowed, one writeup can be considered for
   multiple award categories but wins only one).
6. Verify status shows **submitted**, not draft — for BOTH writeups.

## The two writeups

| Slot | Draft file | Category target | Status |
|---|---|---|---|
| 1 | `cantheria/SUBMISSION_TEXT.md` (2,300 w) | Overall Best Paper ($15k) | 4 PENDING markers → fill via `eval/swe_agent_claims/PENDING_FILL.md` once `NUMBERS.md` lands, else OUTCOME B |
| 2 | `elcaro/SUBMISSION_TEXT.md` (1,999 w) | Best New Resource ($10k) | **PUBLISHED + SUBMITTED** 2026-11-12 ~11:55 UTC — done |

## Judging rubric (5 criteria, 0–5 each, averaged) — official text

| Criterion | What judges ask |
|---|---|
| Novelty | New insights, deeper understanding, or important properties of existing methods? |
| Quality | Does the approach generalize beyond this competition? |
| Relevance | Significance/impact on software engineering and agentic learning? |
| Verifiability | Enough detail to understand how the innovation works + how data was obtained, analyzed, interpreted? |
| Clarity | Clearly presented and written? |

Rubric scores are not shared back. **Tie → earliest-entered writeup wins.**

## Required writeup sections (official)

Title + subtitle · Abstract · Introduction · Description of research
(methods + experiments) · Related works + citations. Optional: public
notebook via Project Links, or arXiv-ready PDF via Public Project Link
(can replace the writeup body).
