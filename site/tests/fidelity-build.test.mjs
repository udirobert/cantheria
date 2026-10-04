import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';

const dist = join(process.cwd(), 'dist');
const casesDir = resolve(process.cwd(), '../presentation/cases');
const decode = (s) =>
  s.replace(/&(#x?[0-9a-fA-F]+|[a-zA-Z]+);/g, (m, g) => {
    if (g[0] === '#') {
      const n = g[1] === 'x' || g[1] === 'X' ? parseInt(g.slice(2), 16) : parseInt(g.slice(1), 10);
      return String.fromCodePoint(n);
    }
    return { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' }[g] ?? m;
  });
const stripTags = (s) => decode(s.replace(/<[^>]*>/g, ''));

const files = readdirSync(casesDir).filter((f) => f.endsWith('.json'));
assert.ok(files.length >= 3, 'expected supplied case files');
for (const f of files) {
  const c = JSON.parse(readFileSync(join(casesDir, f), 'utf8'));
  const html = readFileSync(join(dist, 'cases', c.id, 'index.html'), 'utf8');
  const decoded = decode(html);

  test(`${c.id}: every receipt excerpt rendered verbatim in archive`, () => {
    const excerpts = [...html.matchAll(/<blockquote class="excerpt">([\s\S]*?)<\/blockquote>/g)].map(
      (m) => stripTags(m[1]).trim()
    );
    assert.equal(
      excerpts.length,
      c.receipts.length,
      `expected ${c.receipts.length} excerpt blocks, got ${excerpts.length}`
    );
    c.receipts.forEach((r, i) => {
      assert.equal(
        excerpts[i].trim(),
        r.excerpt.trim(),
        `receipt ${r.id} excerpt mismatch (first diff near: ${JSON.stringify(excerpts[i].slice(0, 80))})`
      );
    });
  });

  test(`${c.id}: step queries copied verbatim, expectations verbatim`, () => {
    for (const step of c.steps) {
      if (step.query) {
        const copies = [...html.matchAll(/data-copy="([\s\S]*?)"/g)].map((m) => decode(m[1]));
        assert.ok(
          copies.includes(step.query),
          `step ${step.id} query not verbatim in any data-copy attribute`
        );
      }
      if (step.expect) {
        const expects = [...html.matchAll(/<p class="expect">([\s\S]*?)<\/p>/g)].map((m) =>
          stripTags(m[1])
        );
        const want = JSON.stringify(step.expect);
        assert.ok(
          expects.some((e) => e.includes(want)),
          `step ${step.id} expected payload not rendered verbatim`
        );
      }
    }
  });

  test(`${c.id}: review lists and limitations represented verbatim`, () => {
    for (const list of [c.review.supported, c.review.unresolved, c.review.assumptions, c.reproduction.limitations]) {
      for (const s of list) {
        assert.ok(decoded.includes(s), `missing verbatim string: ${s.slice(0, 60)}`);
      }
    }
    assert.ok(decoded.includes(c.review.label), 'review label missing verbatim');
    assert.ok(decoded.includes(c.claim.text), 'claim text missing verbatim');
    assert.ok(decoded.includes(c.deck), 'deck missing verbatim');
    assert.ok(decoded.includes(c.run.sourceArtifact), 'sourceArtifact missing');
  });

  test(`${c.id}: selected quotes are exact substrings of the first receipt`, () => {
    const sels = [...html.matchAll(/<blockquote class="sel-quote">([\s\S]*?)<\/blockquote>/g)].map(
      (m) => stripTags(m[1].split(/<span class="sel-label">/)[0]).replace(/^“|”$/g, '').trim()
    );
    const excerpt = c.receipts[0].excerpt;
    for (const sel of sels) {
      assert.ok(
        excerpt.includes(sel) || sel === excerpt.slice(0, 240).trim(),
        `selected quote not exact substring: ${sel.slice(0, 60)}`
      );
    }
  });
}
