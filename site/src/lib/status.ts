import type { CheckStatus, StepStatus, Verdict } from '../data/case';

export const STATUS_TOKENS: Record<CheckStatus | StepStatus, { word: string; symbol: string }> = {
  passed: { word: 'Passed', symbol: '✓' },
  failed: { word: 'Failed', symbol: '✗' },
  error: { word: 'Error', symbol: '!' },
  'not-run': { word: 'Not run', symbol: '○' },
  unknown: { word: 'Unknown', symbol: '?' },
};

export const VERDICT_TOKENS: Record<NonNullable<Verdict>, { word: string; note: string }> = {
  confirmed: { word: 'Confirmed', note: 'passed the recorded mechanical checks' },
  dismissed: { word: 'Dismissed', note: 'failed the recorded checks; not necessarily disproved' },
  unverifiable: { word: 'Unverifiable', note: 'the pipeline could not mechanically decide' },
  flaky: { word: 'Flaky', note: 'instability prevented a reliable outcome' },
  candidate: { word: 'Candidate', note: 'not yet mechanically decided' },
};

export function statusClass(status: string): string {
  return `st-${status}`;
}
