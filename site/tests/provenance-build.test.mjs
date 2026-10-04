import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const dist = join(process.cwd(), 'dist');
const read = (p) => readFileSync(join(dist, p), 'utf8');

test('production build emitted all reviewed case routes', () => {
  for (const id of ['private-die', 'conjecture-843', 'across-the-wire']) {
    assert.ok(existsSync(join(dist, 'cases', id, 'index.html')), `missing ${id}`);
  }
  assert.ok(!existsSync(join(dist, 'cases', 'layout-specimen', 'index.html')), 'fixture leaked');
});

test('across-the-wire renders corpus-internal provenance, no broken link state', () => {
  const html = read('cases/across-the-wire/index.html');
  assert.ok(html.includes('Corpus-internal reference'));
  assert.ok(html.includes('runs/collusion/audit2/results.json'));
  assert.ok(html.includes('No public web link is supplied'));
  assert.ok(!html.includes('no public source link'));
  assert.ok(!html.includes('href=""') && !html.includes('href="null"') && !html.includes('href="undefined"'));
  assert.ok(!html.includes('href="collusion') && !html.includes('src="collusion'));
  const receiptsAside = html.split('Evidence receipts')[1] ?? html;
  assert.ok(!/<a[^>]*href="[^"]*collusion-wiki[^"]*"/.test(receiptsAside));
});

test('conjecture-843 retains public source record link', () => {
  const html = read('cases/conjecture-843/index.html');
  assert.ok(html.includes('Public source record'));
  assert.match(html, /<a href="https:\/\/[^"]+">Public source record<\/a>/);
});

test('no empty or non-http hrefs anywhere in built pages', () => {
  for (const p of ['index.html', 'bench/index.html', 'reproduce/index.html', 'identity/index.html']) {
    const html = read(p);
    const bad = html.match(/href="(?!https?:\/\/|\/|#|mailto:)[^"]*"/g);
    assert.equal(bad, null, `${p} has suspicious href: ${bad}`);
  }
});

for (const id of ['private-die', 'conjecture-843', 'across-the-wire']) {
  test(`${id}: compact case architecture — closed desk groups, full data present, unique ids`, () => {
    const html = read(`cases/${id}/index.html`);
    assert.ok(html.includes('Evidence desk'));
    assert.ok(html.includes('Probe history — inspect recorded attempts'));
    assert.ok(html.includes('Receipt archive — inspect all supplied records'));
    assert.ok(html.includes('Assumptions &amp; limitations'));
    assert.ok(html.includes('Selected passages from the supplied excerpt'));
    assert.ok(html.includes('Scope qualification'));
    assert.ok(html.includes('Read the full editorial review'));
    assert.ok(html.includes('Recorded checks'));
    const groups = html.match(/<details class="desk-group">/g) ?? [];
    assert.ok(groups.length === 4, `${id} should have 4 desk groups, got ${groups.length}`);
    const ids = [...html.matchAll(/ id="([^"]+)"/g)].map((m) => m[1]);
    const dup = ids.filter((v, i) => ids.indexOf(v) !== i);
    assert.deepEqual(dup, [], `${id} duplicate ids: ${dup}`);
    const stepIds = [...html.matchAll(/ id="step-[^"]+"/g)];
    const receiptIds = [...html.matchAll(/ id="receipt-[^"]+"/g)];
    assert.ok(stepIds.length >= 1, 'step disclosures present');
    assert.ok(receiptIds.length >= 1, 'receipt disclosures present');
    assert.ok(!/<script>[^<]*SELECT/i.test(html), 'no raw unsafe injection');
  });
}

test('across-the-wire keeps full supplied excerpt in closed archive, control note separate', () => {
  const html = read('cases/across-the-wire/index.html');
  assert.ok(html.includes('Query expectation not met'));
  assert.ok(html.includes('For a negative control, a non-match can be the intended result'));
  assert.ok(html.includes('receipt-disclosure'));
  assert.ok(html.includes('step-disclosure'));
  assert.ok((html.match(/Corpus-internal reference/g) ?? []).length >= 10);
});

test('private-die retains SQL verbatim in closed probe history', () => {
  const html = read('cases/private-die/index.html');
  assert.ok(html.includes('records_fts MATCH'));
  assert.ok(html.includes('privately'));
  assert.ok(html.includes('step-disclosure'));
});
