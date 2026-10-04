import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { loadCasesFromDirectory } from '../src/data/load-cases';
import { fixtureCase } from '../src/data/fixture';

function reviewedCase(id: string): unknown {
  const c = structuredClone(fixtureCase) as Record<string, any>;
  c.id = id;
  c.publication = 'reviewed';
  c.title = 'Reviewed specimen';
  c.corpus = 'audit5';
  return c;
}

test('loads only reviewed cases from a directory', () => {
  const dir = mkdtempSync(join(tmpdir(), 'cantheria-cases-'));
  try {
    writeFileSync(join(dir, 'b-reviewed.json'), JSON.stringify(reviewedCase('reviewed-one')));
    writeFileSync(join(dir, 'a-fixture.json'), JSON.stringify(fixtureCase));
    const cases = loadCasesFromDirectory(dir, false);
    assert.equal(cases.length, 1);
    assert.equal(cases[0].id, 'reviewed-one');
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('fixture flag appends the layout specimen', () => {
  const dir = mkdtempSync(join(tmpdir(), 'cantheria-cases-'));
  try {
    writeFileSync(join(dir, 'reviewed.json'), JSON.stringify(reviewedCase('reviewed-one')));
    const cases = loadCasesFromDirectory(dir, true);
    assert.deepEqual(cases.map((c) => c.id).sort(), ['layout-specimen', 'reviewed-one']);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('malformed case json throws instead of disappearing', () => {
  const dir = mkdtempSync(join(tmpdir(), 'cantheria-cases-'));
  try {
    const bad = structuredClone(fixtureCase) as Record<string, any>;
    bad.recordedVerdict = 'bogus';
    writeFileSync(join(dir, 'bad.json'), JSON.stringify(bad));
    assert.throws(() => loadCasesFromDirectory(dir, false), /Invalid CaseFile/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('missing directory yields an empty case list', () => {
  const cases = loadCasesFromDirectory(join(tmpdir(), 'cantheria-does-not-exist'), false);
  assert.deepEqual(cases, []);
});
