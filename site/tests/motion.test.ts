import test from 'node:test';
import assert from 'node:assert/strict';
import { motionLive, controlState, replayControlState } from '../src/lib/motion';

test('motionLive requires all conditions true', () => {
  assert.equal(motionLive(false, false, true, false), true);
  assert.equal(motionLive(true, false, true, false), false);
  assert.equal(motionLive(false, true, true, false), false);
  assert.equal(motionLive(false, false, false, false), false);
  assert.equal(motionLive(false, false, true, true), false);
});

test('reduced motion cannot be overridden by resume', () => {
  const s = controlState(true, true);
  assert.equal(s.disabled, true);
  assert.equal(s.note, 'Motion reduced by system preference');
  assert.equal(motionLive(true, false, true, false), false);
});

test('control toggles pause/resume labels', () => {
  assert.deepEqual(controlState(false, false), { label: 'Pause motion', pressed: false, disabled: false, note: null });
  assert.deepEqual(controlState(false, true), { label: 'Resume motion', pressed: true, disabled: false, note: null });
});

test('replay control disabled under reduced or paused', () => {
  assert.deepEqual(replayControlState(false, false), { label: 'Replay diagram motion', disabled: false });
  assert.deepEqual(replayControlState(true, false), { label: 'Replay diagram motion', disabled: true });
  assert.deepEqual(replayControlState(false, true), { label: 'Resume motion to replay', disabled: true });
});
