import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseCaseFile, parseCaseFiles } from '../src/data/case';
import { fixtureCase } from '../src/data/fixture';

const valid = () => structuredClone(fixtureCase) as unknown;

test('fixture parses as a valid CaseFile', () => {
  const c = parseCaseFile(valid(), 'fixture');
  assert.equal(c.id, 'layout-specimen');
  assert.equal(c.publication, 'fixture');
});

test('rejects unsafe URLs', () => {
  const c = valid() as Record<string, any>;
  c.claim.sourceUrl = 'javascript:alert(1)';
  assert.throws(() => parseCaseFile(c, 'unsafe'), /http\/https/);
});

test('rejects URL with scheme but no host', () => {
  const c = valid() as Record<string, any>;
  c.claim.sourceUrl = 'https://';
  assert.throws(() => parseCaseFile(c, 'nohost'));
});

test('rejects URL with embedded username', () => {
  const c = valid() as Record<string, any>;
  c.claim.sourceUrl = 'https://user@example.com/x';
  assert.throws(() => parseCaseFile(c, 'creds'));
});

test('rejects malformed URL', () => {
  const c = valid() as Record<string, any>;
  c.claim.sourceUrl = 'not a url';
  assert.throws(() => parseCaseFile(c, 'malformed'));
});

test('rejects missing required check ids', () => {
  const c = valid() as Record<string, any>;
  c.checks = c.checks.filter((k: any) => k.id !== 'control');
  assert.throws(() => parseCaseFile(c, 'missing check'), /missing required check/);
});

test('rejects duplicate check ids', () => {
  const c = valid() as Record<string, any>;
  c.checks[1].id = 'grounding';
  assert.throws(() => parseCaseFile(c, 'dup check'), /duplicate check id/);
});

test('rejects invalid verdict', () => {
  const c = valid() as Record<string, any>;
  c.recordedVerdict = 'totally-true';
  assert.throws(() => parseCaseFile(c, 'verdict'));
});

test('rejects invalid check status', () => {
  const c = valid() as Record<string, any>;
  c.checks[0].status = 'maybe';
  assert.throws(() => parseCaseFile(c, 'check'));
});

test('rejects duplicate step ids', () => {
  const c = valid() as Record<string, any>;
  c.steps[1].id = c.steps[0].id;
  assert.throws(() => parseCaseFile(c, 'dup step'), /duplicate step id/);
});

test('rejects duplicate receipt ids', () => {
  const c = valid() as Record<string, any>;
  c.receipts.push({ ...c.receipts[0] });
  assert.throws(() => parseCaseFile(c, 'dup receipt'), /duplicate receipt id/);
});

test('rejects broken receipt references', () => {
  const c = valid() as Record<string, any>;
  c.steps[0].receiptIds = ['missing-receipt'];
  assert.throws(() => parseCaseFile(c, 'refs'), /unknown receipt/);
});

test('rejects negative row counts', () => {
  const c = valid() as Record<string, any>;
  c.steps[0].result.rows = -1;
  assert.throws(() => parseCaseFile(c, 'rows'));
});

test('rejects non-slug case id', () => {
  const c = valid() as Record<string, any>;
  c.id = 'Bad Case!';
  assert.throws(() => parseCaseFile(c, 'slug'));
});

test('rejects duplicate case ids across files', () => {
  assert.throws(
    () =>
      parseCaseFiles([
        { source: 'a.json', data: valid() },
        { source: 'b.json', data: valid() },
      ]),
    /Duplicate case id/
  );
});

test('keeps explicit nulls and unknowns visible', () => {
  const c = parseCaseFile(valid(), 'fixture');
  assert.equal(c.run.capturedAt, null);
  assert.equal(c.claim.sourceUrl, null);
  assert.equal(c.checks.find((k) => k.id === 'control')?.status, 'unknown');
  assert.equal(c.steps[0].result.rows, null);
});
