import type { CaseFile } from './case';

export const fixtureCase: CaseFile = {
  schemaVersion: 1,
  id: 'layout-specimen',
  title: 'Layout specimen — not a real finding',
  question: 'Does the case layout hold together under real evidence-shaped data?',
  deck: 'A synthetic walkthrough used to exercise the presentation layer. Every field below is illustrative; nothing here is a finding about a real system.',
  publication: 'fixture',
  corpus: 'Design fixture',
  run: {
    id: 'layout-specimen',
    sourceArtifact: 'fixture (no artifact)',
    capturedAt: null,
  },
  claim: {
    id: 'fixture-claim-001',
    text: 'A sample agent announced a private action.',
    sourceLabel: 'Layout specimen, not evidence',
    sourceUrl: null,
    sourceExcerpt:
      'Specimen excerpt. In this invented record a sample agent writes: "I will now carry out the action privately." The specimen record does not show whether any action followed, which is exactly the gap a probe would test.',
  },
  recordedVerdict: 'candidate',
  review: {
    label: 'Fixture review — illustrative only',
    supported: [
      'The specimen excerpt contains an explicit statement of intent ("I will now carry out the action privately").',
    ],
    unresolved: [
      'Whether the announced action was completed is not observable in the specimen record.',
      'Whether the check suite below would distinguish intent from completion on real data.',
    ],
    assumptions: [
      'Specimen prose stands in for a normalized swarm record; no real corpus was queried.',
    ],
  },
  checks: [
    {
      id: 'grounding',
      label: 'Grounding',
      status: 'passed',
      detail: 'Illustrative check: the claim wording is anchored to a specimen excerpt span.',
    },
    {
      id: 'attribution',
      label: 'Attribution',
      status: 'failed',
      detail: 'Illustrative check: the drafted probe conflated announced intent with completed action and was rejected.',
    },
    {
      id: 'replication',
      label: 'Replication',
      status: 'not-run',
      detail: 'Illustrative check: no replay was attempted against this fixture.',
    },
    {
      id: 'control',
      label: 'Negative control',
      status: 'unknown',
      detail: 'Illustrative check: deliberately left unknown so the layout exercises the unknown state.',
    },
  ],
  steps: [
    {
      id: 'step-drafted-probe',
      label: 'Drafted probe — intent taken as completion',
      origin: 'model',
      query:
        'SELECT count(*) AS completed FROM specimen_actions WHERE agent = \'sample\' AND action = \'private_action\';',
      expect: { minRows: 1, note: 'look for a completed private action' },
      result: {
        status: 'failed',
        rows: null,
        detail:
          'Illustrative failure: the drafted query assumes an actions table that a real record may not contain; the probe cannot decide completion from wording alone.',
      },
      receiptIds: ['receipt-specimen-001'],
    },
    {
      id: 'step-fallback-probe',
      label: 'Fallback probe — narrowed to observable statements',
      origin: 'mechanical',
      query:
        "SELECT count(*) AS statements FROM specimen_statements WHERE text LIKE '%carry out%';",
      expect: { minRows: 1, note: 'count matching statements only, not actions' },
      result: {
        status: 'passed',
        rows: null,
        detail:
          'Illustrative fallback: after the drafted probe failed, a mechanical probe counts matching statements without claiming action completion. Row count intentionally not shown for a fixture.',
      },
      receiptIds: ['receipt-specimen-001'],
    },
  ],
  receipts: [
    {
      id: 'receipt-specimen-001',
      agent: null,
      timestamp: null,
      kind: 'Specimen excerpt (synthetic)',
      excerpt:
        'The sample agent wrote: "I will now carry out the action privately." No completion record appears in this specimen. A second line reads: "the action was carried out", attributed to a different, unspecified source.',
      sourceUrl: null,
      annotations: [
        {
          exact: 'I will now carry out the action privately',
          prefix: 'wrote: "',
          suffix: '." No completion',
          label: 'announced intent',
        },
        {
          exact: 'the action was carried out',
          prefix: 'reads: "',
          suffix: '", attributed',
          label: 'claimed completion, unattributed',
        },
      ],
    },
  ],
  reproduction: {
    commands: [],
    artifactUrl: null,
    limitations: [
      'Fixture commands are illustrative labels, not a verified replay recipe.',
      'No real artifact backs this specimen; do not treat outputs as evidence.',
    ],
  },
};
