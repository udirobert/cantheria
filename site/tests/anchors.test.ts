import { test } from 'node:test';
import assert from 'node:assert/strict';
import { resolveAnnotations, annotateHtml } from '../src/lib/anchors';
import type { Annotation } from '../src/data/case';

const text = 'The agent wrote: "I will run it." Later the agent wrote: "I will run it." again.';

const ok: Annotation = { exact: 'run it', prefix: 'I will ', suffix: '." Later', label: 'first' };
const ambiguous: Annotation = { exact: 'I will run it', prefix: '', suffix: '', label: 'amb' };
const missing: Annotation = { exact: 'nope', prefix: 'x', suffix: 'y', label: 'miss' };

test('resolves a unique exact+prefix+suffix match', () => {
  const [r] = resolveAnnotations(text, [ok]);
  assert.equal(r.status, 'ok');
  if (r.status === 'ok') {
    assert.equal(text.slice(r.start, r.end), 'run it');
  }
});

test('flags ambiguous anchors and does not guess', () => {
  const [r] = resolveAnnotations(text, [ambiguous]);
  assert.equal(r.status, 'ambiguous');
  assert.equal(r.start, null);
});

test('flags unresolved anchors', () => {
  const [r] = resolveAnnotations('nothing here', [missing]);
  assert.equal(r.status, 'unresolved');
});

test('ambiguous annotations produce no mark', () => {
  const resolutions = resolveAnnotations(text, [ambiguous]);
  const segs = annotateHtml(text, resolutions);
  assert.ok(segs.every((s) => s.kind === 'text'));
});

test('resolved annotation produces an exact mark', () => {
  const resolutions = resolveAnnotations(text, [ok]);
  const segs = annotateHtml(text, resolutions);
  const marks = segs.filter((s) => s.kind === 'mark');
  assert.equal(marks.length, 1);
  assert.equal(marks[0].html, 'run it');
  assert.equal(marks[0].label, 'first');
});

test('escapes HTML in excerpts, including script tags', () => {
  const hostile = 'before <script>alert("x")</script> after';
  const segs = annotateHtml(hostile, resolveAnnotations(hostile, []));
  const html = segs.map((s) => s.html).join('');
  assert.ok(!html.includes('<script>'));
  assert.ok(html.includes('&lt;script&gt;'));
});

test('shiki escapes markup embedded in SQL queries', async () => {
  const { codeToHtml } = await import('shiki');
  const { canaryHouseTheme } = await import('../src/lib/shiki-theme');
  const html = await codeToHtml("SELECT '<script>alert(1)</script>';", {
    lang: 'sql',
    theme: canaryHouseTheme,
  });
  assert.ok(!html.includes('<script>'));
  assert.ok(html.includes('&#x3C;script>'));
});

test('overlapping identical matches are ambiguous', () => {
  const ann: Annotation = { exact: 'aa', prefix: '', suffix: '', label: 'overlap' };
  const [r] = resolveAnnotations('aaa', [ann]);
  assert.equal(r.status, 'ambiguous');
  assert.equal(r.start, null);
});

test('context disambiguates otherwise identical matches', () => {
  const ann: Annotation = { exact: 'aa', prefix: 'x', suffix: ' y', label: 'ctx' };
  const [r] = resolveAnnotations('xaa y aa', [ann]);
  assert.equal(r.status, 'ok');
});

test('adjacent annotations can both resolve', () => {
  const a: Annotation = { exact: 'alpha', prefix: 'see ', suffix: ' beta', label: 'a' };
  const b: Annotation = { exact: 'beta', prefix: 'alpha ', suffix: ' done', label: 'b' };
  const res = resolveAnnotations('see alpha beta done', [a, b]);
  assert.deepEqual(res.map((r) => r.status), ['ok', 'ok']);
  const marks = annotateHtml('see alpha beta done', res).filter((s) => s.kind === 'mark');
  assert.equal(marks.length, 2);
});

test('annotation match still applies when exact text contains html chars', () => {
  const t = 'a <b> c';
  const ann: Annotation = { exact: '<b>', prefix: 'a ', suffix: ' c', label: 'tag' };
  const [r] = resolveAnnotations(t, [ann]);
  assert.equal(r.status, 'ok');
  const segs = annotateHtml(t, [r]);
  const mark = segs.find((s) => s.kind === 'mark');
  assert.equal(mark?.html, '&lt;b&gt;');
});
