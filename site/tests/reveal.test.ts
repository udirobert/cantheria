import test from 'node:test';
import assert from 'node:assert/strict';
import { openDetailsChain, type DetailsNode } from '../src/lib/reveal';

function details(parent: DetailsNode | null = null): DetailsNode {
  return { tagName: 'DETAILS', open: false, parentElement: parent };
}
function div(parent: DetailsNode | null = null): DetailsNode {
  return { tagName: 'DIV', open: false, parentElement: parent };
}

test('opens target details and all ancestor details', () => {
  const outer = details();
  const inner = details(outer);
  const content = div(inner);
  openDetailsChain(content);
  assert.equal(outer.open, true);
  assert.equal(inner.open, true);
});

test('null target is safe', () => {
  assert.doesNotThrow(() => openDetailsChain(null));
});

test('non-details ancestors untouched', () => {
  const wrap = div();
  const leaf = div(wrap);
  openDetailsChain(leaf);
  assert.equal(wrap.open, false);
});
