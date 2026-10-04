import { motionLive, controlState, replayControlState } from '../lib/motion';
import { openDetailsChain } from '../lib/reveal';

document.documentElement.classList.remove('no-js');
const motionMq = window.matchMedia('(prefers-reduced-motion: reduce)');
const reduced = motionMq.matches;
if (reduced) document.documentElement.classList.add('reduced-motion');

document.addEventListener('click', (event) => {
  const el = event.target instanceof Element ? event.target : null;
  const copyBtn = el?.closest<HTMLButtonElement>('[data-copy]');
  const dlBtn = el?.closest<HTMLButtonElement>('[data-download]');
  const target = copyBtn ?? dlBtn;
  if (!target) return;
  const status = target.closest('.copytext')?.querySelector<HTMLElement>('.copy-status');
  const report = (msg: string, ok: boolean) => {
    if (!status) return;
    status.hidden = false;
    status.textContent = msg;
    status.classList.toggle('copy-ok', ok);
    setTimeout(() => {
      status.hidden = true;
      status.classList.remove('copy-ok');
    }, 2500);
  };
  if (copyBtn) {
    const text = copyBtn.getAttribute('data-copy') ?? '';
    const clip = navigator.clipboard;
    if (!clip || typeof clip.writeText !== 'function') {
      report('Copy unavailable; select the text manually', false);
      return;
    }
    Promise.resolve()
      .then(() => clip.writeText(text))
      .then(() => report('Copied', true))
      .catch(() => report('Copy unavailable; select the text manually', false));
  } else if (dlBtn) {
    const text = dlBtn.getAttribute('data-download') ?? '';
    const name = dlBtn.getAttribute('data-filename') ?? 'query.sql';
    try {
      const blob = new Blob([text], { type: 'application/sql' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = name;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
      report('Downloaded', true);
    } catch {
      report('Download unavailable; copy the text manually', false);
    }
  }
});

const stepItems = document.querySelectorAll('.step-item');
let nodeAnim: { cancel(): void } | null = null;
const fmPaused = () =>
  (document.querySelector<HTMLElement>('.flightmap')?.dataset.userPaused ?? '') === 'true';
if (stepItems.length > 0) {
  import('scrollama')
    .then((scrollamaModule) => {
      const scroller = (scrollamaModule.default ?? scrollamaModule)();
      scroller
        .setup({ step: '.step-item', offset: 0.55 as never })
        .onStepEnter(({ element }) => {
          stepItems.forEach((s) => s.classList.remove('active'));
          element.classList.add('active');
          document
            .querySelectorAll<HTMLElement>('[data-flightmap-node]')
            .forEach((n) => n.classList.toggle('active', n.dataset.stepId === element.id.replace(/^step-/, '')));
          const node = element.querySelector<HTMLElement>('.node');
          if (node && !motionMq.matches && !document.hidden && !fmPaused()) {
            nodeAnim?.cancel();
            nodeAnim = node.animate(
              [{ transform: 'scale(1)' }, { transform: 'scale(1.5)' }, { transform: 'scale(1)' }],
              { duration: 450, easing: 'ease-out' }
            );
          }
        });
    })
    .catch(() => {
      stepItems.forEach((s) => s.classList.add('active'));
    });
} else {
  stepItems.forEach((s) => s.classList.add('active'));
}

const benchForm = document.querySelector<HTMLFormElement>('[data-bench-form]');
if (benchForm) {
  const rows = Array.from(document.querySelectorAll<HTMLElement>('[data-case-row]'));
  const count = document.querySelector<HTMLElement>('[data-bench-count]');
  const apply = () => {
    const q = (benchForm.querySelector<HTMLInputElement>('[name=q]')?.value ?? '').toLowerCase();
    const corpus = benchForm.querySelector<HTMLSelectElement>('[name=corpus]')?.value ?? '';
    const verdict = benchForm.querySelector<HTMLSelectElement>('[name=verdict]')?.value ?? '';
    let shown = 0;
    for (const row of rows) {
      const text = (row.dataset.search ?? '').toLowerCase();
      const ok =
        (!q || text.includes(q)) &&
        (!corpus || row.dataset.corpus === corpus) &&
        (!verdict || row.dataset.verdict === verdict);
      row.hidden = !ok;
      if (ok) shown++;
    }
    if (count) {
      const preview = document.querySelector('.fixture-banner') ? ' (preview may include a layout specimen)' : '';
      count.textContent = `${shown} ${shown === 1 ? 'entry' : 'entries'} shown${preview}`;
    }
  };
  benchForm.addEventListener('input', apply);
  benchForm.addEventListener('submit', (e) => e.preventDefault());
  apply();
}

const artifactVis = new Map<Element, boolean>();
const onceTimers = new Map<Element, number>();
const refreshArtifact = (el: Element) => {
  const he = el as HTMLElement;
  const paused = he.dataset.userPaused === 'true';
  const visible = artifactIo ? artifactVis.get(el) === true : true;
  const once = he.dataset.motionOnce === 'true';
  const done = once && he.dataset.motionDone === 'true';
  const live = motionLive(motionMq.matches, paused, visible, document.hidden) && !done;
  el.classList.toggle('motion-live', live);
  if (live && once) {
    const existing = onceTimers.get(el);
    if (existing !== undefined) clearTimeout(existing);
    onceTimers.set(
      el,
      window.setTimeout(() => {
        onceTimers.delete(el);
        he.dataset.motionDone = 'true';
        el.classList.remove('motion-live');
      }, 2400)
    );
  } else if (!live) {
    const t = onceTimers.get(el);
    if (t !== undefined) {
      clearTimeout(t);
      onceTimers.delete(el);
    }
  }
  const ctl = controlState(motionMq.matches, paused);
  const btn = el.querySelector<HTMLButtonElement>('[data-motion-toggle]');
  if (btn) {
    btn.textContent = ctl.label;
    btn.setAttribute('aria-pressed', String(ctl.pressed));
    btn.disabled = ctl.disabled;
  }
  const rbtn = el.querySelector<HTMLButtonElement>('[data-motion-replay]');
  if (rbtn) {
    const rs = replayControlState(motionMq.matches, paused);
    rbtn.textContent = rs.label;
    rbtn.disabled = rs.disabled;
  }
  const note = el.querySelector<HTMLElement>('.motion-note');
  if (note) note.hidden = ctl.note === null;
  if (el.classList.contains('flightmap') && (paused || motionMq.matches)) {
    nodeAnim?.cancel();
    nodeAnim = null;
  }
};
const artifactIo =
  'IntersectionObserver' in window
    ? new IntersectionObserver((entries) => {
        for (const e of entries) {
          artifactVis.set(e.target, e.isIntersecting);
          refreshArtifact(e.target);
        }
      })
    : null;
document.querySelectorAll<HTMLElement>('.artifact[data-motion]').forEach((el) => {
  artifactIo?.observe(el);
  el.querySelector<HTMLButtonElement>('[data-motion-toggle]')?.addEventListener('click', () => {
    el.dataset.userPaused = el.dataset.userPaused === 'true' ? 'false' : 'true';
    refreshArtifact(el);
  });
  el.querySelector<HTMLButtonElement>('[data-motion-replay]')?.addEventListener('click', () => {
    if (motionMq.matches || el.dataset.userPaused === 'true') return;
    delete el.dataset.motionDone;
    el.classList.remove('motion-live');
    void el.offsetWidth;
    refreshArtifact(el);
  });
  refreshArtifact(el);
});
document.addEventListener('visibilitychange', () => {
  document.querySelectorAll('.artifact[data-motion]').forEach(refreshArtifact);
});
const revealHash = (hash: string) => {
  try {
    const id = decodeURIComponent(hash.replace(/^#/, ''));
    if (!id) return;
    const el = document.getElementById(id);
    if (!el) return;
    openDetailsChain(el as unknown as Parameters<typeof openDetailsChain>[0]);
    el.scrollIntoView({ behavior: motionMq.matches ? 'auto' : 'smooth', block: 'start' });
  } catch {}
};
document.addEventListener('click', (event) => {
  const t = event.target instanceof Element ? event.target : null;
  const link = t?.closest<HTMLAnchorElement>('[data-flightmap-node] .fm-link');
  if (link) {
    document.querySelectorAll<HTMLElement>('[data-flightmap-node]').forEach((n) => n.classList.remove('active'));
    link.closest<HTMLElement>('[data-flightmap-node]')?.classList.add('active');
  }
  const anchor = t?.closest<HTMLAnchorElement>('a[href^="#"]');
  if (anchor) revealHash(anchor.getAttribute('href') ?? '');
});
window.addEventListener('hashchange', () => revealHash(window.location.hash));
revealHash(window.location.hash);
motionMq.addEventListener('change', () => {
  document.documentElement.classList.toggle('reduced-motion', motionMq.matches);
  document.querySelectorAll('.artifact[data-motion]').forEach(refreshArtifact);
  if (motionMq.matches) stepItems.forEach((s) => s.classList.add('active'));
});
