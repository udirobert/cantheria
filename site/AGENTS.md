# Cantheria site — working notes

Static presentation layer (Astro) for the Cantheria evidence instrument.
Everything in this directory is owned by the site workstream; the case data it
renders is owned separately and must never be edited here.

## Commands

Run from this directory (`site/`):

- `npm ci` — clean install from `package-lock.json` (versions are pinned exactly)
- `npm run dev` — Astro dev server
- `npm run check` — `astro check` types/diagnostics
- `npm test` — node:test suites via tsx (schema, anchors, loader)
- `npm run build` — production static build into `dist/`
- `npm run preview` — serve `dist/` on `http://localhost:4321`
- `npm run build:preview` — build with `CANTHERIA_INCLUDE_FIXTURES=1`
- `npm run dev:fixtures` — dev server including the fixture case

## Base path and deployment surface

All routes are served under `/cantheria/` (see `astro.config.mjs`). Keep that
base in links, assets, and any future search artifacts. Do not add routes that
collide with the existing report paths (`audit5/`, `hunt1/`, `collusion/`).

## Case data contract

- Reviewed case files are individual `CaseFile` JSON documents in
  `../presentation/cases/*.json`, read by `src/data/load-cases.ts`.
- The schema lives in `src/data/case.ts` and is the contract with the data
  workstream. Malformed input fails the build on purpose — never catch and skip.
- `presentation/` files are owned by Developer B. Do not modify, reformat,
  re-derive, or regenerate them; treat contents as supplied evidence.
- Only `publication: 'reviewed'` cases enter production builds. The synthetic
  layout specimen (`src/data/fixture.ts`) exists only when
  `CANTHERIA_INCLUDE_FIXTURES=1` and must never be presented as a finding.

## Conventions

- No code comments in authored files.
- No secrets, credentials, or embedded-credential URLs anywhere in source or data.
- Verdicts, checks, queries, and receipts render exactly as recorded; editorial
  review content is kept separate and labeled.

## Design preferences

- The user favors visual metaphors, storytelling, motion, animation, and
  expressive craft: eccentric editorial folio, not dashboard or marketing page.
- Every page carries at least one meaningful visual artifact (home: canary
  plate; bench: murmuration; case: flight map; reproduce: replay diagram;
  identity: mark/grammar sheet). Keep each artifact legible when static.
- Illustrations are always labeled as illustration — never imply they show
  corpus activity, agent counts, or measured traces.
- Motion is progressive enhancement: shared state helper `src/lib/motion.ts`,
  per-artifact pause/resume toggles, honored `prefers-reduced-motion` (system
  wins over manual resume), paused when offscreen or the tab is hidden.
- Accessibility and the evidence boundary outrank decoration: no hover-only
  meaning, no fabricated metrics, recorded data renders verbatim.
- Case pages are compact editorial briefs: qualifications visible up front,
  bulk records live in the native evidence desk with stable deep links. Do not
  revert to expanded raw-record dumps.
