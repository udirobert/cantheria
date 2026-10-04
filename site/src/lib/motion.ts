export interface MotionControlState {
  label: string;
  pressed: boolean;
  disabled: boolean;
  note: string | null;
}

export function motionLive(reduced: boolean, userPaused: boolean, visible: boolean, hidden: boolean): boolean {
  return !reduced && !userPaused && visible && !hidden;
}

export function controlState(reduced: boolean, userPaused: boolean): MotionControlState {
  if (reduced) {
    return { label: 'Pause motion', pressed: false, disabled: true, note: 'Motion reduced by system preference' };
  }
  return { label: userPaused ? 'Resume motion' : 'Pause motion', pressed: userPaused, disabled: false, note: null };
}

export function replayControlState(reduced: boolean, userPaused: boolean): { label: string; disabled: boolean } {
  if (reduced) return { label: 'Replay diagram motion', disabled: true };
  if (userPaused) return { label: 'Resume motion to replay', disabled: true };
  return { label: 'Replay diagram motion', disabled: false };
}
