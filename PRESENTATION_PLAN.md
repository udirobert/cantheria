# Cantheria — The Canary House

## Purpose and success condition

This is the working plan for Cantheria's hackathon presentation: product design,
UI/UX, documentation, demo, and submission materials. It consolidates the agreed
storytelling direction and the subsequent tooling and creative-reference passes.
It is a delivery plan, not a claim that these experiences already exist.

The goal is for a judge to say:

> I understand the problem, I inspected the evidence, and I would use this in an investigation.

Build an evidence instrument with a recognizable identity, not merely a nicer
report. Technical credibility and memorable craft must reinforce each other.
No additional corpus or model expansion is on the critical path.

## Progress protocol

- All delivery checkboxes below start unchecked. Existing engine capabilities do
  not count as completion of the new presentation work.
- Check an item only after its acceptance criteria are met and reviewed.
- Record proof in the delivery ledger: artifact path or URL, verification result,
  and remaining limitations. A checkbox alone is not release evidence.
- Preserve blockers in the ledger; do not silently remove requested deliverables.
- Implement locally before publishing. Do not call a deployment live until its
  public URLs and assets have been checked successfully.
- Record changes to scope here before substituting a different design or tool.

## 1. Product story

### Positioning

> When agents investigate agents, who checks the investigation?

Cantheria turns swarm narratives into inspectable evidence cases. Its signature:

> An LLM proposes; the record decides.

The Canary House is a place where claims are tested before becoming accepted
history. Use the canary metaphor to explain observable probes, not infallible
truth detection:

| Metaphor | Product meaning |
|---|---|
| Environment | Normalized swarm record |
| Canary | Executable probe sent into that record |
| Response | Observable execution result |
| Flight Recorder | Recorded probe, repair, fallback, and verification history |
| Investigator | Person who assesses what the evidence establishes |

A silent canary does not automatically mean a false claim. Brand terms must have
plain-language labels: for example, "Flight Recorder — probe history".
Do not foreground the proposed Greek etymology until independently verified.

### Evidence-language contract

| Stored outcome | Judge-facing meaning |
|---|---|
| Confirmed | Passed the recorded mechanical checks; inspect the receipts |
| Dismissed | Failed the recorded checks; not necessarily disproved |
| Unverifiable | The pipeline could not mechanically decide |
| Flaky | Execution or evidence instability prevented a reliable outcome |

- Replace headline "slop rate" with "claims failing mechanical verification";
  disclose the denominator, exclusions, and limitations nearby.
- Failed retrieval does not prove falsity, even when a corpus day is dense.
- Deterministic replay demonstrates reproducibility of committed checks, not
  semantic correctness, completeness, or full-corpus equivalence of a slice.
- A negative control is a discrimination check, not a calibrated false-positive
  rate estimate. Show passed, failed, and not run separately.
- Matching vocabulary is not sufficient proof of every component of a claim.
- Do not describe collusion-report dismissals as proof its authors were wrong.
- Treat source narration as evidence of narration; distinguish announced intent
  from completed action and independent corroboration from repeated reporting.
- Review every featured claim against its exact receipts before publishing it.
- Do not change stored verdicts merely to improve the story. Keep editorial
  qualifications separate and explicitly labeled.
- Explain prompt-injection defenses without claiming immunity.

## 2. Creative direction and identity

### Natural-history field journal meets precision instrument

A contemporary forensic instrument with editorial warmth, not cartoon birds,
steampunk decoration, or a neon AI dashboard.

- Bone-white paper, near-black ink, restrained texture, generous negative space.
- Canary yellow for identity, selection, and the flight path, not universal success.
- Deep teal for passed checks, vermilion for failed checks, slate for unknowns.
  Text and symbols must carry status independently of color.
- Newsreader for editorial titles, Source Sans 3 for UI and explanatory prose,
  IBM Plex Mono for SQL, record IDs, timestamps, and terminal material.
- Self-host a small set of font weights with license notices and robust fallbacks.
- Use fine rules, specimen labels, margin notes, and precise alignment.
- Create an original vector canary mark. Reuse its geometric strokes as a wing,
  probe-path branch, excerpt bracket, and provenance mark: "the feather becomes a trace".

### Three signature motifs

1. **Flight path:** a yellow line connects claim, test, execution, checks, and
   outcome. A real fallback branches from failed model attempts. The path
   represents provenance, never invented confidence or measured agent movement.
2. **Investigator's marginalia:** bracket exact passages and highlight tested
   fragments. Use annotations sparingly; do not cross out a failed claim as if
   disproved. Always provide readable explanatory text.
3. **Specimen label:** each receipt shows record ID, agent when known, timestamp,
   source kind, and provenance link. Unknown fields remain visibly unknown.

### Ambient swarm motif

Use a sparse flock of ink-colored marks with one yellow canary in the opening,
explicitly identified as illustrative artwork rather than dataset visualization.
When a case opens, the ambient artwork recedes and the yellow mark becomes the
Flight Recorder navigation marker. Real evidence appears in an ordered layout.

- Prefer lightweight Canvas or SVG over a WebGL scene.
- Keep the effect bounded, pausable, and disabled for reduced motion; stop work
  when offscreen. Provide a static alternative.
- Do not morph simulated birds into supposedly measured agents or draw invented
  coordination links inside evidence panels.
- No endless background movement, bird sounds, cursor mascot, or flocking controls.
- Build the evidence experience first. If the birds disappear, the product must
  remain useful and complete.

## 3. Judge-facing experience

### Two routes

**Take the field tour:** a short guided investigation, minimal jargon, strong
pacing, and clear qualifications. Borrow interactive journalism's sticky evidence
panel beside narrative passages. Scrolling enhances the story; it never gates
access to evidence. Mobile can use stacked passages and evidence.

**Open the evidence bench:** searchable published claims, corpus/verdict filters,
stable claim links, probe history, receipts, limitations, and downloads. Label
search as published-case search, not full-corpus search.

### Opening

Present one reviewed real claim and ask, "What does the record actually establish?"
Use "Inspect this claim" as the primary action and "Reproduce the checks" as the
secondary action. Do not put a wall of statistics before the case.

The d6 case can illustrate how a plausible sentence exceeds its evidence, but
its displayed wording must distinguish announced intent from completed rolling
unless the receipts establish both. Label the tour as inspection of a recorded
run: no fabricated quotes, simulated computation, or fake live verification.

### Signature case view

Narrative on the left; record on the right; verification trail between them.

Each case contains:

- Original claim, source wording, and stable identity.
- Exact supporting excerpts with enough context and specimen labels.
- A navigable Flight Recorder: claim -> drafted test -> recorded execution ->
  checks -> outcome, including failed attempts and fallback where present.
- What each check tested, what happened, and what was not run.
- Expandable exact SQL and faithful copy/download actions.
- A "What this does—and does not—establish" section.
- A "Challenge this finding" panel: assumptions, missing evidence, probe scope,
  and reproduction instructions. No invented confidence percentages.
- An investigator handoff: supported conclusion, unresolved details, next records
  to inspect, provenance links, and downloadable artifacts.

### Featured field investigations

| Working title | Question | Intended payoff | Publication condition |
|---|---|---|---|
| The Private Die | What happened beyond the public summary? | Autonomous lead discovery | Review intent versus completed action |
| The Canary That Misled Us | What if our model drafts an inadequate test? | Expose the verifier's own failure | Review Conjecture 843 receipts against every featured clause |
| Across the Wire | Does the method transfer to another incident? | Cross-corpus usefulness | Select and review a well-supported collusion case |

Titles are editorial; source claims remain verbatim and traceable. If a proposed
case fails review, document the reason and choose a defensible replacement.
Keep negative hunt results visible as limitations, not proof of perfect restraint.

The current narrative starting points are [DEMO.md](DEMO.md), especially the d6
and Conjecture 843 vignettes, and [SUBMISSION.md](SUBMISSION.md) for the run inventory.
These are pointers, not evidence authority: M1 must locate the actual results,
probe history, and receipt records, then capture their identities and artifact
paths in the ledger before building featured cases.

## 4. Architecture and reusable toolkit

Keep the Python verifier and current exports intact. Add a separate static
presentation layer, proposed location `site/`, rather than migrating the engine.

Frozen run artifacts + reviewed editorial annotations -> static build ->
casebook, explorer, and downloads. Capture the presentation inputs once and
render from that capture. Do not rerun extraction or recompute evidence merely
to restyle a page. Keep editorial annotations distinct from recorded results.

| Primitive | Decision | Scope and constraints |
|---|---|---|
| Astro | Core | Static pages and selective interactivity; no server required |
| Scrollama + CSS sticky | Core | Guided story steps; direct links and stacked fallback remain usable |
| Motion, vanilla JS + SVG | Core | Flight-path drawing and short coordinated transitions; explicit reduced-motion handling |
| Shiki | Core | Build-time SQL highlighting; copied/downloaded probes stay exact |
| Fontsource | Core | Self-hosted licensed typography, limited weights |
| Rough Notation | Add after case layout | Sparse highlights/brackets; no misleading rejection marks |
| Pagefind | Add for explorer | One page per claim; corpus/verdict facets; indexes published content only |
| asciinema player | Add for replay proof | Real self-hosted recording labeled "Recorded execution", not live computation |
| Satori | Optional | Build-time preview cards; limited CSS support; no hosting migration |
| Canvas boids reference | Optional polish | Small attributed adaptation after code/license review; illustrative only |

No tools are installed by this plan. Documentation was researched, but integration
has not been tested. Select compatible dependency versions published at least
seven days earlier, lock them, retain licenses, and do not bypass security controls.
Do not introduce a React application, browser code editor, or graph-layout engine
unless a concrete interaction requires it.

### Anchored annotations

Use W3C text-selector vocabulary for reviewed excerpt annotations: exact quote,
prefix/suffix context, and position where useful. Bind them to record ID and source
snapshot identity. Detect ambiguous or broken anchors rather than guessing.
This is a presentation primitive, not automated semantic verification.

### Deployment

Preserve existing public report URLs and reproduction assets. Initially build
locally and publish static output through the existing Pages arrangement. An
Actions-based deployment is an option, not permission to silently change project
settings. Account for the `/cantheria/` base path in links, assets, search, and casts.
No login, API key, live inference, or external CDN is required to inspect cases.
Do not expose credentials in exports, recordings, generated pages, or downloads.

## 5. Delivery milestones and acceptance criteria

### M1 — Evidence and language baseline

- [ ] Review the three candidate cases clause by clause against exact receipts.
- [ ] Capture source artifacts and separate reviewed annotations for rendering.
- [ ] Document outcome meanings, headline denominators, missing checks, and replay limits.
- [ ] Identify overclaims and stale language in README, DEMO, SUBMISSION, and SWARM.

**Accept when:** every featured statement has inspectable support or an explicit
qualification; no failed search is described as proof of falsity. Record any case
replacement and its reason.

### M2 — Identity and flagship vertical slice

- [x] Produce identity sheet: original mark, typography, colors, spacing, status grammar.
- [x] Build one complete case with source/evidence comparison and specimen labels.
- [x] Build Flight Recorder with real attempts, fallback, and check states.
- [x] Add limitations, challenge panel, exact SQL, provenance, and reproduction actions.
- [x] Verify anchored excerpts and mobile/keyboard/reduced-motion behavior.

**Accept when:** the complete flagship case is understandable without animation
or JavaScript, except enhanced controls; a visitor can inspect its decision and
limitations without decoding raw IDs. Technical inspection preserves exact artifacts.

### M3 — Field tour and opening craft

- [x] Extend the case system to all three reviewed investigations.
- [ ] Build the landing page and short guided tour with direct access to every stage.
- [x] Add restrained marginalia and yellow flight-path choreography.
- [x] Add the optional illustrative flock only after the evidence experience works.
- [x] Provide static artwork, pause/reduced-motion behavior, and mobile stacked view.

**Accept when:** the opening explains the product through a case, not setup;
ambient simulation cannot be mistaken for findings; no scroll hijacking or hover-only
content is required to navigate.

### M4 — Evidence bench and reproduction

- [ ] Publish stable individual claim pages with filters and search.
- [x] Show failure reasons and not-run checks, not only confirmed receipts.
- [x] Provide clear installation, download, and keyless replay instructions.
- [ ] Capture and embed actual replay execution with context and a text transcript.
- [x] Preserve old report paths or provide intentional compatible redirects.

**Accept when:** visitors can find claims by corpus/verdict and link to them;
search scope is honest; reproduction artifacts remain downloadable and the clean
extraction path is verified. Sliced replay is not represented as exhaustive auditing.

### M5 — Coordinated docs and submission artifacts

- [ ] Rewrite README's opening around understand -> inspect -> reproduce.
- [ ] Update DEMO with exact clicks, reviewed narration, and a backup presentation path.
- [ ] Align SUBMISSION's evidence outline with verified official judging criteria.
- [ ] Reconcile terminology and limitations in SWARM while preserving technical depth.
- [ ] Move legacy vulnerability material out of the main introductory path without removing it.
- [ ] Produce three screenshots: claim/record, Flight Recorder, real replay.
- [ ] Produce a printable case brief with supported conclusion, unresolved details, and provenance.
- [ ] Produce site/case preview cards; Satori automation is optional.
- [ ] Produce a 90-second storyboard, captions, and final screen recording.
- [ ] Obtain the user's review of submission wording and final video.

**Video spine:** problem -> inspect one case -> expose the verifier's failed test
-> show qualified evidence -> actual keyless replay -> signature closing.
Use the same typography, annotations, and flight path as the site. Avoid frantic
scrolling and terminal-heavy setup. The closing question: "Who checks the story
your agents tell you?"

**Accept when:** docs, site, screenshots, and video tell the same defensible story;
installation precedes replay commands; timings include context rather than guarantees.
A script is not completion of the recorded video.

### M6 — Judge-path QA and release

- [ ] Test comprehension with a fresh visitor; record their confusion and resolve it.
- [x] Check responsive layout, keyboard/focus behavior, and reduced motion.
- [ ] Audit color contrast across text and status states.
- [ ] Check static/no-JavaScript reading and external-source outage fallback.
- [x] Run relevant frontend build/checks and existing offline regression checks.
- [x] Verify no secrets, unintended large assets, or mutated evidence enter the release.
- [ ] Check all public entry points, claim links, fonts, search files, casts, and downloads.
- [x] Verify clean-download replay and document agreements and limitations.
- [ ] Review final diff and record deployment revision and verification evidence.

**Accept when:** a fresh visitor can explain Cantheria, open a case, understand its
outcome, inspect a receipt, find limitations, and locate reproduction instructions.
Do not claim a live deployment until public HTTP and browser checks support it.

## 6. Delivery ledger

Update this table as milestones progress. Keep failed checks and blockers visible.

| Milestone | State | Artifact / verification evidence | Blocker or limitation |
|---|---|---|---|
| M1 Evidence baseline | Integrated and reviewed locally; user acceptance pending | `presentation/CONTRACT.md`, `presentation/EVIDENCE_BASELINE.md`, all three rendered cases and clause reviews; lead clarified that the Conjecture-843 receipt describes a 24-odd-cycle certificate but the probe does not independently validate it; published v1.0.1 four-run package SHA-256 `ba8640cfb4cc0588d466c08e684fe7ec7607f6dce63a8d12fd669c4c808105d0` (byte-identical to the frozen local file) | Across-the-wire incident-report passage remains unavailable and disclosed. Report labels and stale confirmed-claim reasons fixed without changing verification behavior |
| M2 Flagship case | Complete locally; awaiting user design feedback | `site/`; integrated `/cases/private-die/`; 38 passing tests, clean Astro diagnostics and production build in `site/verification/`; desktop/mobile screenshots `final-home-1440.png`, `final-case-1440.png`, `final-case-390.png` | Committed; not publicly deployed; recorded verdict and editorial qualification remain distinct |
| M3 Tour and craft | In progress; visual artifacts and motion ready for user feedback | All three supplied case files render; original canary plate, illustrative murmuration, recorded-sequence FlightMap, explanatory ReplayDiagram, and identity grammar plate; 38 passing tests and screenshots in `site/verification/artifact-final-*` | Full guided tour and user acceptance remain; static/mobile views and live reduced-motion/manual pause verified; hidden-tab pause is code-reviewed, not observed in headless browser |
| M4 Bench and replay | In progress | Local `/bench/` text/corpus/verdict filters and `/reproduce/` installation/download/replay instructions; published v1.0.1 asset verified by lead from a clean download — all four replays agree (180/180, 24/24, 24/24, 108/108) | No embedded execution recording yet; public site deployment pending |
| M5 Materials | In progress | Revised README/DEMO/SUBMISSION prose and the 90-second video storyboard in DEMO.md now exist; local identity page and verification screenshots available as source material | Printable case brief, preview cards, final screen recording, and owner review still required |
| M6 QA and release | Local gates green; main commit/push completed; site deployment pending | Offline Python suite passed (92 tests observed); fresh report tests 14/14, ruff clean, frontend diagnostics/build clean, provenance smoke 9/9 and fidelity checks 12/12; pre-commit hooks green on the staged release set. Owner approved two `is_secret:false` baseline entries for the UUID-derived claim IDs; v1.0.1 published and replay-verified | Public site deployment and post-deploy browser checks pending — do not claim a live deployment until public HTTP and browser checks support it. Fresh-visitor comprehension, video, and the absent collusion incident-report source passage remain |

Execution order is M1 -> M2 -> M3/M4 -> M5 -> M6. Do not expand the optional
artwork workstream before the flagship evidence interaction is complete.

## 7. Non-goals and scope guardrails

- No third corpus, speculative model architecture, or expensive run for spectacle.
- No fake upload workflow, fake live analysis, fabricated quotes, or replay theater.
- No 3D aviary, GPU-heavy hero, flock-settings playground, or sound effects.
- No invented confidence scores, coordination edges, or statistically unsupported metrics.
- No competitor put-downs; demonstrate concrete differentiation through the product.
- No new backend or hosting migration merely to support a static presentation.
- No silent changes to verdicts, test controls, source records, or security policy.

## 8. Research references and reuse notes

These references support design/tool decisions; their existence does not establish
that our integration works or that every linked asset is licensed for reuse.

### Core tooling and approaches

- [Astro islands](https://docs.astro.build/en/concepts/islands/): static HTML with selective interactivity.
- [Astro on GitHub Pages](https://docs.astro.build/en/guides/deploy/github/): deployment and repository base paths.
- [The Pudding: introducing Scrollama](https://pudding.cool/process/introducing-scrollama/): editorial scrollytelling pattern.
- [Responsive scrollytelling](https://pudding.cool/process/responsive-scrollytelling/): mobile/stacked fallback principles; older implementation details need current review.
- [Scrollama](https://github.com/russellsamora/scrollama/): IntersectionObserver-driven story steps.
- [Motion animate](https://motion.dev/docs/animate): vanilla JS, SVG paths, and coordinated sequences.
- [Rough Notation](https://roughnotation.com/): animated or static passage annotations.
- [Shiki transformers](https://shiki.style/packages/transformers): line/word highlights and diff classes.
- [Pagefind filtering](https://pagefind.app/docs/js-api-filtering/): static search and facets.
- [asciinema player](https://docs.asciinema.org/manual/player/quick-start/): self-hosted actual terminal recordings.
- [W3C selectors](https://www.w3.org/TR/selectors-states/): quote/context and position anchoring; references the normative Web Annotation model.
- [Satori](https://github.com/vercel/satori/): optional build-time artwork, limited HTML/CSS support.
- [Newsreader](https://fontsource.org/fonts/newsreader), [Source Sans 3](https://fontsource.org/fonts/source-sans-3), [IBM Plex Mono](https://fontsource.org/fonts/ibm-plex-mono/about): self-hosted OFL typography; retain licenses.

### Canary and swarm references

- [BoidsCanvas](https://github.com/mschristensen/BoidsCanvas): older configurable Canvas implementation; MIT notice in README. Inspect code before adaptation and retain attribution.
- [Canvas boids](https://github.com/jqlee85/boids): MIT-licensed reference implementation, not an approved production dependency.
- [Animated SVG birds source mirror](https://gist.github.com/scarabcoder/45bd40eb538aea52a602905848a813b9): wing-cycle/flight-motion reference; linked licensing and third-party sprite rights require verification before reuse.
- [Three.js GPU birds](https://threejs.org/examples/webgl_gpgpu_birds_gltf.html): conceptual reference only; not selected for the main experience.
- [Squiggle birds](https://codepen.io/trys/pen/NmgBGj/) and [Animated Flying Birds](https://codepen.io/The-early-bird/details/rNyVrGG): search-discovered candidates; direct inspection was blocked, so not vetted for reuse.
- [Observable Vanilla Boids](https://observablehq.com/@harrystevens/vanilla-boids): search-discovered candidate; direct fetch was rate-limited, not vetted for integration.
- [Smithsonian Open Access](https://www.si.edu/openaccess): possible illustration source, but direct fetch was blocked. Verify individual item rights before selecting any asset. Original vector artwork remains the core direction.

## Final principle

Reuse the plumbing. Make the identity, choreography, and evidence relationship
bespoke. If the birds disappeared entirely, Cantheria should still be an excellent
investigation tool; with them, it should become unmistakably Cantheria.
