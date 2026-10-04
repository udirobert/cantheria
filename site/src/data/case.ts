import { z } from 'zod';

export const SCHEMA_VERSION = 1;

const urlOrNull = z
  .string()
  .nullable()
  .refine(
    (v) => {
      if (v === null) return true;
      try {
        const u = new URL(v);
        if (u.protocol !== 'http:' && u.protocol !== 'https:') return false;
        if (u.hostname.length === 0) return false;
        if (u.username !== '' || u.password !== '') return false;
        return true;
      } catch {
        return false;
      }
    },
    { message: 'only http/https URLs with a hostname and no credentials, or null' }
  );

const checkId = z.enum(['grounding', 'attribution', 'replication', 'control']);
const checkStatus = z.enum(['passed', 'failed', 'not-run', 'unknown']);
const verdict = z.enum(['confirmed', 'dismissed', 'unverifiable', 'flaky', 'candidate']);
const stepOrigin = z.enum(['model', 'mechanical', 'control', 'editorial']);
const stepStatus = z.enum(['passed', 'failed', 'error', 'not-run', 'unknown']);
const publication = z.enum(['fixture', 'reviewed']);

const annotationSchema = z.object({
  exact: z.string().min(1),
  prefix: z.string(),
  suffix: z.string(),
  label: z.string().min(1),
});

const checkSchema = z.object({
  id: checkId,
  label: z.string().min(1),
  status: checkStatus,
  detail: z.string(),
});

const stepSchema = z.object({
  id: z.string().min(1),
  label: z.string().min(1),
  origin: stepOrigin,
  query: z.string().nullable(),
  expect: z.record(z.string(), z.unknown()).nullable(),
  result: z.object({
    status: stepStatus,
    rows: z.number().int().nonnegative().nullable(),
    detail: z.string(),
  }),
  receiptIds: z.array(z.string().min(1)),
});

const receiptSchema = z.object({
  id: z.string().min(1),
  agent: z.string().nullable(),
  timestamp: z.string().nullable(),
  kind: z.string().min(1),
  excerpt: z.string(),
  sourceUrl: urlOrNull,
  annotations: z.array(annotationSchema),
});

export const caseFileSchema = z
  .object({
    schemaVersion: z.literal(SCHEMA_VERSION),
    id: z
      .string()
      .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, 'id must be URL-safe lowercase slug'),
    title: z.string().min(1),
    question: z.string().min(1),
    deck: z.string(),
    publication,
    corpus: z.string().min(1),
    run: z.object({
      id: z.string().min(1),
      sourceArtifact: z.string().min(1),
      capturedAt: z.string().nullable(),
    }),
    claim: z.object({
      id: z.string().min(1),
      text: z.string().min(1),
      sourceLabel: z.string().min(1),
      sourceUrl: urlOrNull,
      sourceExcerpt: z.string().nullable(),
    }),
    recordedVerdict: verdict.nullable(),
    review: z.object({
      label: z.string().min(1),
      supported: z.array(z.string()),
      unresolved: z.array(z.string()),
      assumptions: z.array(z.string()),
    }),
    checks: z.array(checkSchema),
    steps: z.array(stepSchema).min(1),
    receipts: z.array(receiptSchema),
    reproduction: z.object({
      commands: z.array(z.string()),
      artifactUrl: urlOrNull,
      limitations: z.array(z.string()),
    }),
  })
  .superRefine((cf, ctx) => {
    const requiredChecks = new Set(['grounding', 'attribution', 'replication', 'control']);
    const seenChecks = new Set<string>();
    for (const chk of cf.checks) {
      if (seenChecks.has(chk.id)) {
        ctx.addIssue({ code: 'custom', message: `duplicate check id: ${chk.id}` });
      }
      seenChecks.add(chk.id);
    }
    for (const id of requiredChecks) {
      if (!seenChecks.has(id)) {
        ctx.addIssue({ code: 'custom', message: `missing required check: ${id}` });
      }
    }
    const stepIds = new Set<string>();
    for (const s of cf.steps) {
      if (stepIds.has(s.id)) {
        ctx.addIssue({ code: 'custom', message: `duplicate step id: ${s.id}` });
      }
      stepIds.add(s.id);
    }
    const receiptIds = new Set<string>();
    for (const r of cf.receipts) {
      if (receiptIds.has(r.id)) {
        ctx.addIssue({ code: 'custom', message: `duplicate receipt id: ${r.id}` });
      }
      receiptIds.add(r.id);
    }
    for (const s of cf.steps) {
      for (const rid of s.receiptIds) {
        if (!receiptIds.has(rid)) {
          ctx.addIssue({
            code: 'custom',
            message: `step ${s.id} references unknown receipt: ${rid}`,
          });
        }
      }
    }
  });

export type Annotation = z.infer<typeof annotationSchema>;
export type Check = z.infer<typeof checkSchema>;
export type Step = z.infer<typeof stepSchema>;
export type Receipt = z.infer<typeof receiptSchema>;
export type CaseFile = z.infer<typeof caseFileSchema>;
export type Verdict = z.infer<typeof verdict>;
export type CheckStatus = z.infer<typeof checkStatus>;
export type StepStatus = z.infer<typeof stepStatus>;

export function parseCaseFile(input: unknown, source = 'case file'): CaseFile {
  const parsed = caseFileSchema.safeParse(input);
  if (!parsed.success) {
    const detail = parsed.error.issues
      .map((i) => `${i.path.join('.') || '(root)'}: ${i.message}`)
      .join('; ');
    throw new Error(`Invalid CaseFile in ${source} — ${detail}`);
  }
  return parsed.data;
}

export function parseCaseFiles(inputs: Array<{ source: string; data: unknown }>): CaseFile[] {
  const cases = inputs.map((i) => parseCaseFile(i.data, i.source));
  const seen = new Map<string, string>();
  for (let i = 0; i < cases.length; i++) {
    const prev = seen.get(cases[i].id);
    if (prev) {
      throw new Error(
        `Duplicate case id "${cases[i].id}" in ${inputs[i].source}; already defined by ${prev}`
      );
    }
    seen.set(cases[i].id, inputs[i].source);
  }
  return cases;
}
