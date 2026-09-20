"""Self-contained HTML report — Cantheria's public face.

Renders results.json + journal.jsonl into ONE html file: no server, no
build step, works off file://. Data is embedded as JSON and rendered
client-side. Used by `cantheria report --html` and for demos.

Structure is deliberately agnostic: the tool leads (what Cantheria is,
how the kill chain works) and the scanned repo is presented as a case
study. Progressive disclosure throughout — findings, candidates and the
journal all collapse; nothing is a wall of text unless you open it.

Honesty contract: the journal is the record — hypothesis_only events,
dismissed candidates, and fence hits render alongside confirmed
findings, and hand-authored PoCs are labelled confirmed_manual.
"""

from __future__ import annotations

import json
from pathlib import Path

_CSS = """
:root {
  --bg: #0b0b09; --panel: #141310; --panel2: #1a1913; --line: #29271d;
  --ink: #ece7d6; --dim: #97917c; --faint: #5d5947;
  --canary: #f5c518; --canary-soft: rgba(245,197,24,.12); --canary-dim: #9a8317;
  --crit: #ff5a45; --high: #ff9e45; --med: #f5c518; --low: #7dc9a5;
  --ok: #86d075; --fail: #ff5a45;
  --radius: 10px;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { background: var(--bg); scroll-behavior: smooth; }
body {
  background: var(--bg); color: var(--ink);
  font-family: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 14px; line-height: 1.6; padding-bottom: 120px;
}
body::before {
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background:
    radial-gradient(900px 420px at 50% -10%, rgba(245,197,24,.07), transparent 65%),
    repeating-linear-gradient(0deg, transparent 0 3px, rgba(0,0,0,.10) 3px 4px);
}
.wrap { max-width: 920px; margin: 0 auto; padding: 0 28px; position: relative; z-index: 1; }
a { color: var(--canary); text-decoration: none; }
code { color: var(--canary); }

/* ── top bar ─────────────────────────────── */
.topbar {
  position: sticky; top: 0; z-index: 10;
  backdrop-filter: blur(12px); background: rgba(11,11,9,.82);
  border-bottom: 1px solid var(--line);
}
.topbar .wrap { display: flex; align-items: center; gap: 22px; height: 52px; }
.wordmark { font-family: "Archivo", monospace; font-weight: 800; letter-spacing: .38em; font-size: 12px; color: var(--canary); }
.topbar nav { margin-left: auto; display: flex; gap: 18px; font-size: 11px; letter-spacing: .12em; text-transform: uppercase; }
.topbar nav a { color: var(--dim); }
.topbar nav a:hover { color: var(--ink); }

/* ── hero (scene 1: pitch + live replay) ─── */
.hero {
  min-height: calc(100vh - 52px); display: flex; flex-direction: column;
  justify-content: center; padding: 48px 0 32px;
}
.eyebrow { font-size: 11px; letter-spacing: .3em; text-transform: uppercase; color: var(--canary); margin-bottom: 18px; }
.hero h1 {
  font-family: "Archivo", monospace; font-weight: 800;
  font-size: clamp(38px, 7vw, 64px); line-height: 1.0; letter-spacing: -.015em;
}
.hero h1 em { font-style: normal; color: var(--faint); }
.hero .lede { color: var(--dim); max-width: 600px; margin-top: 18px; font-size: 15px; }
.hero .lede b { color: var(--ink); font-weight: 600; }

/* replay terminal — streams the real journal */
.replay {
  margin-top: 34px; border: 1px solid var(--line); border-radius: var(--radius);
  background: #070705; overflow: hidden;
  box-shadow: 0 24px 60px -30px rgba(0,0,0,.9), 0 0 0 1px rgba(245,197,24,.04);
}
.rp-bar {
  display: flex; align-items: center; gap: 8px; padding: 9px 14px;
  border-bottom: 1px solid var(--line); font-size: 10px;
  letter-spacing: .22em; text-transform: uppercase; color: var(--faint);
}
.rp-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--panel2); border: 1px solid var(--line); }
.rp-dot:first-child { background: var(--canary); border-color: var(--canary); opacity: .7; }
.rp-bar .rp-title { margin-left: 8px; }
.rp-bar .rp-live { margin-left: auto; color: var(--canary-dim); }
.rp-lines {
  padding: 14px 16px; height: 218px; overflow: hidden;
  font-size: 12px; line-height: 1.75;
  display: flex; flex-direction: column; justify-content: flex-end;
}
.rpl { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--dim); opacity: 0; animation: rpin .2s forwards; }
.rpl .rv { font-weight: 700; }
.rpl.sys { color: var(--faint); }
.rpl .rv.confirmed, .rpl .rv.confirmed_manual { color: var(--canary); }
.rpl .rv.dismissed, .rpl .rv.fence_hit { color: var(--fail); }
.rpl .rv.hypothesis, .rpl .rv.hypothesis_only { color: var(--dim); }
.rpl.fin { color: var(--canary); font-weight: 700; }
.rpl .cur { display: inline-block; width: 7px; height: 13px; margin-left: 4px; vertical-align: -2px; background: var(--canary); animation: blink 1s steps(1) infinite; }
@keyframes rpin { to { opacity: 1; } }
@keyframes blink { 50% { opacity: 0; } }

.scrollcue {
  margin-top: 30px; font-size: 11px; letter-spacing: .26em; text-transform: uppercase;
  color: var(--faint); display: flex; align-items: center; gap: 10px;
}
.scrollcue a { color: var(--dim); }
.scrollcue a:hover { color: var(--canary); }
.scrollcue .ar { animation: bob 1.6s ease-in-out infinite; display: inline-block; }
@keyframes bob { 50% { transform: translateY(4px); } }

/* the method — collapsed by default, progressive disclosure */
details.method { margin: 8px 0 0; border: 1px solid var(--line); border-radius: var(--radius); background: var(--panel); }
details.method summary {
  list-style: none; cursor: pointer; user-select: none;
  display: flex; align-items: center; gap: 14px; padding: 16px 20px;
}
details.method summary::-webkit-details-marker { display: none; }
details.method summary .t-label { font-size: 11px; letter-spacing: .22em; text-transform: uppercase; color: var(--dim); }
details.method summary .t-sub { font-size: 11px; color: var(--faint); }
details.method[open] > summary .chev { transform: rotate(90deg); color: var(--canary); }

.killchain {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;
  padding: 0 20px 20px;
}
.kc {
  border: 1px solid var(--line); border-radius: var(--radius);
  background: var(--panel); padding: 16px;
}
.kc .num { font-family: "Archivo", monospace; font-weight: 800; font-size: 20px; color: var(--canary); }
.kc .t { font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: var(--ink); margin-top: 6px; }
.kc .d { font-size: 11.5px; color: var(--dim); margin-top: 4px; line-height: 1.45; }
@media (max-width: 720px) { .killchain { grid-template-columns: repeat(2, 1fr); } }

/* ── case study divider ──────────────────── */
.divider {
  display: flex; align-items: center; gap: 16px; margin: 72px 0 32px;
  font-size: 11px; letter-spacing: .3em; text-transform: uppercase; color: var(--faint);
}
.divider::before, .divider::after { content: ""; flex: 1; border-top: 1px solid var(--line); }
.divider b { color: var(--canary); font-weight: 600; }

/* ── the funnel (scene 2: how it was found) ── */
.funnel { margin-top: 8px; }
.fstage { display: grid; grid-template-columns: 150px 1fr; gap: 18px; align-items: center; padding: 12px 0; }
.f-n { font-family: "Archivo", monospace; font-size: 34px; font-weight: 800; text-align: right; }
.fstage.fin .f-n { color: var(--canary); }
.f-track { position: relative; height: 40px; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
.f-bar {
  position: absolute; inset: 0 auto 0 0; width: 0;
  background: linear-gradient(90deg, rgba(245,197,24,.05), rgba(245,197,24,.16));
  border-right: 1px solid var(--canary-dim);
  transition: width 1.1s cubic-bezier(.2,.7,.2,1);
}
.fstage.mid .f-bar { background: linear-gradient(90deg, rgba(245,197,24,.02), rgba(245,197,24,.07)); }
.fstage.fin .f-bar { background: linear-gradient(90deg, rgba(245,197,24,.25), rgba(245,197,24,.5)); border-right-color: var(--canary); }
.f-lab {
  position: relative; z-index: 1; height: 100%; display: flex; align-items: center;
  gap: 12px; padding: 0 14px; font-size: 11px; letter-spacing: .16em; text-transform: uppercase;
}
.f-lab .f-k { color: var(--ink); font-weight: 600; }
.f-lab .f-s { color: var(--faint); letter-spacing: .04em; text-transform: none; }
.fstage.fin .f-lab .f-k { color: var(--canary); }
.f-go { display: inline-block; margin-top: 10px; font-size: 11px; letter-spacing: .2em; text-transform: uppercase; }
.f-note { color: var(--faint); font-size: 11.5px; margin-top: 14px; }

/* ── scroll reveal ───────────────────────── */
.reveal { opacity: 0; transform: translateY(16px); transition: opacity .55s ease, transform .55s ease; }
.reveal.in { opacity: 1; transform: none; }
@media (prefers-reduced-motion: reduce) {
  .reveal { opacity: 1; transform: none; transition: none; }
  .f-bar { transition: none; }
  .scrollcue .ar, .rpl .cur { animation: none; }
  .rpl { opacity: 1; animation: none; }
}

/* ── sections ────────────────────────────── */
h2 { font-family: "Archivo", monospace; font-size: 12px; font-weight: 800; letter-spacing: .3em; text-transform: uppercase; color: var(--canary); margin: 56px 0 18px; }
h2 .count { color: var(--dim); font-weight: 400; letter-spacing: .1em; }
.sec-sub { color: var(--faint); font-size: 12px; margin: -10px 0 18px; }

/* ── finding rows (progressive disclosure) ─ */
.row {
  border: 1px solid var(--line); border-radius: var(--radius);
  background: var(--panel); margin-bottom: 12px; overflow: hidden;
  transition: border-color .2s;
}
.row:hover { border-color: var(--faint); }
.row[open] { border-color: var(--canary-dim); }
.row summary {
  list-style: none; cursor: pointer; display: flex; align-items: center;
  gap: 14px; padding: 16px 20px; user-select: none;
}
.row summary::-webkit-details-marker { display: none; }
.chev { flex: none; width: 14px; height: 14px; color: var(--faint); transition: transform .25s; }
.row[open] > summary .chev { transform: rotate(90deg); color: var(--canary); }
.dot { flex: none; width: 8px; height: 8px; border-radius: 50%; background: var(--sev, var(--faint)); box-shadow: 0 0 8px var(--sev, transparent); }
.row .title { font-weight: 600; font-size: 14.5px; flex: 1 1 340px; min-width: 0; }
.row .meta { flex: none; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; justify-content: flex-end; }
.pill {
  font-size: 9.5px; letter-spacing: .14em; text-transform: uppercase;
  border: 1px solid var(--line); color: var(--dim); border-radius: 99px;
  padding: 3px 9px; white-space: nowrap;
}
.pill.sev { border-color: var(--sev); color: var(--sev); }
.pill.manual { border-color: var(--canary-dim); color: var(--canary); }
.pill.loc { color: var(--faint); border: 0; padding: 0; font-size: 11px; letter-spacing: 0; text-transform: none; }
.pill.loc code { color: var(--dim); }
.row .body { padding: 4px 20px 20px 48px; border-top: 1px dashed var(--line); }
.row .body > * { margin-top: 16px; }
.loc-line { font-size: 11.5px; color: var(--faint); }
.prov { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-size: 11px; }
.pv-label { font-size: 9.5px; letter-spacing: .2em; text-transform: uppercase; color: var(--faint); }
.pv-step { display: inline-flex; gap: 6px; align-items: baseline; }
.pv-t { color: var(--faint); }
.pv-arrow { color: var(--faint); }
.detail { color: var(--dim); font-size: 13.5px; max-width: 720px; }

.legs { display: flex; gap: 8px; flex-wrap: wrap; }
.leg { font-size: 11px; padding: 6px 10px; border: 1px solid var(--line); border-radius: 6px; background: var(--panel2); color: var(--dim); }
.leg b { color: var(--ok); font-weight: 600; }
.leg.na b { color: var(--faint); }

.term {
  background: #070705; border: 1px solid var(--line); border-radius: 8px;
  padding: 14px 16px; font-size: 12px; line-height: 1.65; overflow-x: auto;
  white-space: pre; color: #b3ad97; max-height: 240px; overflow-y: auto;
}
.term .vuln { color: var(--canary); font-weight: 700; }
.term .err { color: var(--fail); }
.fix { border-left: 2px solid var(--canary-dim); padding: 2px 14px; color: var(--dim); font-size: 13px; }
.fix b { color: var(--ink); font-weight: 600; display: block; font-size: 10px; letter-spacing: .2em; text-transform: uppercase; margin-bottom: 4px; }
.adv { padding: 10px 0; border-bottom: 1px dashed var(--line); }
.adv:last-of-type { border-bottom: 0; }
.adv-id { font-size: 12px; font-weight: 600; }
.adv-sum { color: var(--dim); font-size: 12.5px; margin-top: 2px; }

/* ── journal trace ───────────────────────── */
.trace { border: 1px solid var(--line); border-radius: var(--radius); background: #080806; overflow: hidden; }
.trace summary { list-style: none; cursor: pointer; padding: 16px 20px; display: flex; align-items: center; gap: 14px; user-select: none; }
.trace summary::-webkit-details-marker { display: none; }
.trace summary .t-label { font-size: 12px; letter-spacing: .2em; text-transform: uppercase; color: var(--dim); }
.trace summary .t-sub { font-size: 11px; color: var(--faint); }
.trace[open] > summary .chev { transform: rotate(90deg); color: var(--canary); }
.chips { display: flex; gap: 8px; flex-wrap: wrap; padding: 12px 20px; border-top: 1px dashed var(--line); }
.chip { font-size: 10.5px; letter-spacing: .08em; border: 1px solid var(--line); border-radius: 99px; padding: 4px 10px; color: var(--dim); cursor: pointer; background: none; font-family: inherit; }
.chip.on { border-color: var(--canary); color: var(--canary); }
.jlines { border-top: 1px solid var(--line); max-height: 480px; overflow-y: auto; }
.jline { display: grid; grid-template-columns: 84px 150px 1fr; gap: 14px; padding: 8px 20px; border-bottom: 1px solid #17160f; font-size: 12px; }
.jline:last-child { border-bottom: 0; }
.jline .t { color: var(--faint); }
.jline .ev { font-weight: 700; }
.ev.confirmed, .ev.confirmed_manual { color: var(--canary); }
.ev.hypothesis_only, .ev.hypothesis { color: var(--dim); }
.ev.dismissed, .ev.fence_hit { color: var(--fail); }
.jline .what { color: var(--dim); }
.jline .what code { color: var(--ink); }
.jline.hide { display: none; }

footer { margin-top: 80px; border-top: 1px solid var(--line); padding-top: 24px; color: var(--faint); font-size: 12px; }
footer b { color: var(--dim); }
"""

_JS = """
const data = JSON.parse(document.getElementById('scan-data').textContent);
const esc = s => String(s ?? '').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const SEV = {critical:'var(--crit)', high:'var(--high)', moderate:'var(--med)', medium:'var(--med)', low:'var(--low)', negligible:'var(--low)'};
const EXPECT = {nonzero_exit:'exit≠0', signal:'signal', sanitizer_report:'sanitizer', assertion:'assertion'};
const CHEV = '<svg class="chev" viewBox="0 0 16 16" fill="none"><path d="M5 3l6 5-6 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';

const confirmed = data.findings.filter(f => f.verdict === 'confirmed');
const journal = data.journal || [];
const confirmedIds = new Set(confirmed.map(f => f.id));
const candMap = new Map();
for (const f of data.findings) if (f.verdict !== 'confirmed') candMap.set(f.id, f);
for (const e of journal) {
  if ((e.event === 'hypothesis_only' || e.event === 'hypothesis' || e.event === 'dismissed')
      && e.finding && !confirmedIds.has(e.finding.id)) {
    candMap.set(e.finding.id, {...e.finding, verdict: e.finding.verdict || 'candidate'});
  }
}
const candidates = [...candMap.values()];
const fenceN = Array.isArray(data.fence_hits) ? data.fence_hits.length : (data.fence_hits || 0);
const hyp = journal.filter(e => e.event === 'hypothesis' || e.event === 'hypothesis_only').length;
const manualIds = new Set(journal.filter(e => e.event === 'confirmed_manual').map(e => e.finding && e.finding.id));
const isManual = f => manualIds.has(f.id) || /hand-authored|browser-demonstrated|manual/i.test((f.raw && f.raw.note) || '');
const eventTypes = [...new Set(journal.map(e => e.event))];
const advisories = data.advisories || [];
// group advisories per package@version — aws-lc-sys with 5 GHSAs is one
// remediation, not five rows.
const advGroups = new Map();
for (const a of advisories) {
  const k = `${a.ecosystem}|${a.package}|${a.version}`;
  if (!advGroups.has(k)) advGroups.set(k, {...a, items: []});
  advGroups.get(k).items.push(a);
}
const SEV_ORDER = ['critical','high','moderate','low'];
for (const g of advGroups.values()) {
  const sevs = g.items.map(i => i.severity).filter(Boolean);
  g.severity = sevs.sort((x,y) => SEV_ORDER.indexOf(x)-SEV_ORDER.indexOf(y))[0] || null;
}
const prefetchedN = typeof data.prefetched === 'string'
  ? (data.prefetched ? data.prefetched.split(',').filter(Boolean).length : 0)
  : (data.prefetched || []).length;
// provenance: which journal events touched each finding — the honest
// "how was this found" answer (model hypothesis → oracle/human proof).
const provById = {};
for (const e of journal) {
  if (e.finding && e.finding.id) (provById[e.finding.id] ??= []).push(e);
}
const chunksN = data.chunks_indexed || 0;
const hypTotal = hyp || (candidates.length + confirmed.length);
// sandbox_runs only counts scan-executed PoCs — manual PoCs ran through the
// same sandbox but outside that counter, so fall back to the runs ledger.
const pocRuns = data.sandbox_runs ||
  data.findings.reduce((a, f) => a + (f.runs || []).length, 0);

document.getElementById('app').innerHTML = `
<div class="topbar"><div class="wrap">
  <span class="wordmark">CANTHERIA</span>
  <nav>
    <a href="#method">method</a><a href="#case">case study</a>
    <a href="#findings">findings</a><a href="#journal">journal</a>
  </nav>
</div></div>

<div class="wrap">
<section class="hero">
  <div class="eyebrow">autonomous vulnerability discovery</div>
  <h1>Flies canaries.<br><em>Only reports the ones that die.</em></h1>
  <p class="lede">
    An open model <b>hypothesizes</b>; a sandbox <b>falsifies</b>. Only PoCs that
    reproduce, pass a benign control, and attribute to target code ship as findings.
  </p>
  <div class="replay">
    <div class="rp-bar">
      <span class="rp-dot"></span><span class="rp-dot"></span><span class="rp-dot"></span>
      <span class="rp-title">journal replay · ${esc(data.repo)}</span>
      <span class="rp-live">● actual scan</span>
    </div>
    <div class="rp-lines" id="rp"></div>
  </div>
  <div class="scrollcue">
    <a href="#case">the case study</a><span class="ar">↓</span>
  </div>
</section>

<details class="method" id="method">
  <summary>${CHEV}<span class="t-label">the method</span><span class="t-sub">— the four legs a finding must survive before it's called confirmed</span></summary>
  <div class="killchain">
    <div class="kc"><div class="num">01</div><div class="t">mechanical PoC</div><div class="d">crash, sanitizer report, or failing safety assertion — never a vibe</div></div>
    <div class="kc"><div class="num">02</div><div class="t">reproduces</div><div class="d">N consecutive runs fail the same way, same signature</div></div>
    <div class="kc"><div class="num">03</div><div class="t">control passes</div><div class="d">the same harness with benign input must exit clean</div></div>
    <div class="kc"><div class="num">04</div><div class="t">attributes</div><div class="d">a real frame of target code in the trace, not harness noise</div></div>
  </div>
</details>

<div class="divider" id="case"><span>case study · <b>${esc(data.repo)}</b></span></div>

<section class="funnel reveal">
  <div class="fstage"><span class="f-n" data-n="${chunksN}">0</span>
    <div class="f-track"><div class="f-bar"></div>
      <div class="f-lab"><span class="f-k">chunks indexed</span><span class="f-s">first-party source, embedded</span></div></div></div>
  <div class="fstage mid"><span class="f-n" data-n="${hypTotal}">0</span>
    <div class="f-track"><div class="f-bar"></div>
      <div class="f-lab"><span class="f-k">hypotheses inferred</span><span class="f-s">${esc(data.llm_calls)} llm calls · ${pocRuns} PoC executions</span></div></div></div>
  <div class="fstage fin"><span class="f-n" data-n="${confirmed.length}">0</span>
    <div class="f-track"><div class="f-bar"></div>
      <div class="f-lab"><span class="f-k">confirmed</span><span class="f-s">repro ×N · control pass · target frame</span></div></div></div>
  <a class="f-go" href="#findings">see the survivors ↓</a>
  <p class="f-note">also in the record: ${candidates.length} candidates held (not proven) · ${fenceN} sandbox fence hits · ${advisories.length} dependency advisories — a separate evidence class, below</p>
</section>

<h2 id="findings">Confirmed findings <span class="count">· ${confirmed.length} survived the kill chain — first-party code</span></h2>
<p class="sec-sub">click a row to open its evidence — discovery path, PoC output, reproduction legs, suggested fix</p>
${confirmed.map((f, i) => findingRow(f, i === 0)).join('') || '<p class="sec-sub">none — the canaries lived.</p>'}

${advisories.length ? `
<h2>Supply chain <span class="count">· ${advisories.length} known advisories in dependencies</span></h2>
<p class="sec-sub">different evidence class — lockfile versions matched against OSV, not novel bugs proven here</p>
${[...advGroups.values()].map(g => advisoryRow(g)).join('')}` : ''}

<h2>Candidates <span class="count">· ${candidates.length} hypothesized, not yet proven</span></h2>
<p class="sec-sub">real hypotheses the pipeline declined to confirm — triage material, not reports</p>
${candidates.map(f => findingRow(f, false, true)).join('')}

<h2 id="journal">Journal <span class="count">· ${journal.length} events, append-only</span></h2>
<details class="trace">
  <summary>${CHEV}<span class="t-label">scan trace</span><span class="t-sub">— every hypothesis, refusal, dismissal and confirmation, in order</span></summary>
  <div class="chips">
    <button class="chip on" data-ev="*">all</button>
    ${eventTypes.map(t => `<button class="chip" data-ev="${esc(t)}">${esc(t)}</button>`).join('')}
  </div>
  <div class="jlines">${journal.map(jline).join('')}</div>
</details>

<footer>
  <b>Cantheria</b> — SIFT: index → infer → falsify → triage.<br>
  A finding is only <em>confirmed</em> when a machine-checkable PoC reproduces N times,
  a benign-input control passes, and the failure attributes to target code.
  Findings tagged <span style="color:var(--canary)">confirmed_manual</span> had
  hand-authored PoCs — the journal records which is which.
</footer>
</div>`;

const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

// ── hero replay: stream the real journal, verbatim ──
(function replay() {
  const rpEl = document.getElementById('rp');
  if (!rpEl) return;
  const evTitle = e => e.finding ? (e.finding.title || '') :
    (e.chunk ? (e.chunk.file || e.chunk) : (e.note || e.detail || ''));
  const lines = [
    {cls: 'sys', html: `$ cantheria scan ${esc(data.repo)}`},
    {cls: 'sys', html: `index  · ${Number(chunksN).toLocaleString()} chunks embedded`},
  ];
  const isHyp = e => e.event === 'hypothesis' || e.event === 'hypothesis_only';
  let seq = journal;
  if (journal.length > 24) {
    const must = journal.filter(e => !isHyp(e)).length;
    const hypsN = journal.length - must;
    const step = Math.max(1, Math.ceil(hypsN / Math.max(4, 24 - must)));
    let hi = 0;
    seq = journal.filter(e => isHyp(e) ? (hi++ % step === 0) : true);
  }
  for (const e of seq) {
    const ts = (e.ts || (e.finding && e.finding.created_utc) || '').replace('T', ' ').slice(11, 19);
    lines.push({cls: '', ev: e.event,
      html: `<span style="color:var(--faint)">${esc(ts)}</span> <span class="rv ${esc(e.event)}">${esc(e.event)}</span> ${esc(String(evTitle(e)).slice(0, 68))}`});
  }
  lines.push({cls: 'fin', ev: 'fin',
    html: `▸ ${confirmed.length} finding${confirmed.length === 1 ? '' : 's'} survived the kill chain`});
  let i = 0;
  const push = () => {
    const L = lines[i];
    const d = document.createElement('div');
    d.className = 'rpl ' + L.cls;
    d.innerHTML = L.html;
    rpEl.appendChild(d);
    if (++i < lines.length) {
      const delay = L.cls === 'sys' ? 380 :
        (/confirmed|dismissed|fence/.test(L.ev || '') ? 620 : 140);
      setTimeout(push, delay);
    } else {
      d.innerHTML += '<span class="cur"></span>';
    }
  };
  if (reduced) {
    for (const L of lines) {
      const d = document.createElement('div');
      d.className = 'rpl ' + L.cls; d.innerHTML = L.html; rpEl.appendChild(d);
    }
  } else setTimeout(push, 700);
})();

// ── scroll reveal + funnel bars/count-ups ──
document.querySelectorAll('h2, .sec-sub, .row, .trace, .f-note, .f-go').forEach(el => el.classList.add('reveal'));
const fNums = [...document.querySelectorAll('.f-n')];
const maxN = Math.max(...fNums.map(el => +el.dataset.n || 0), 1);
const countUp = (el, n) => {
  if (reduced || n < 10) { el.textContent = n.toLocaleString(); return; }
  const t0 = performance.now();
  const tick = t => {
    const p = Math.min(1, (t - t0) / 950);
    el.textContent = Math.round(n * (1 - Math.pow(1 - p, 3))).toLocaleString();
    if (p < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
};
const io = new IntersectionObserver(entries => {
  for (const en of entries) {
    if (!en.isIntersecting) continue;
    en.target.classList.add('in');
    if (en.target.classList.contains('funnel')) {
      document.querySelectorAll('.fstage').forEach(st => {
        const n = +st.querySelector('.f-n').dataset.n || 0;
        st.querySelector('.f-bar').style.width =
          Math.max(5, Math.round(Math.log10(Math.max(n, 1)) / Math.log10(maxN) * 100)) + '%';
      });
      fNums.forEach(el => countUp(el, +el.dataset.n || 0));
    }
    io.unobserve(en.target);
  }
}, {threshold: .12});
document.querySelectorAll('.reveal').forEach(el => io.observe(el));

function legs(f) {
  const runs = f.runs || [];
  const exploit = runs.filter(r => !r.ok);
  const control = runs.length > exploit.length ? runs[runs.length - 1] : null;
  const attrib = runs.some(r => (r.target_frames || []).length);
  const l = [];
  if (f.poc) l.push(`<span class="leg">PoC · <b>${esc(EXPECT[f.poc.expect] || f.poc.expect)}</b></span>`);
  if (exploit.length) l.push(`<span class="leg">repro · <b>×${exploit.length}</b></span>`);
  l.push(`<span class="leg ${control && control.ok ? '' : 'na'}">control · <b>${control ? (control.ok ? 'pass' : 'FAIL') : '—'}</b></span>`);
  l.push(`<span class="leg ${attrib ? '' : 'na'}">attribution · <b>${attrib ? 'target frame' : '—'}</b></span>`);
  return `<div class="legs">${l.join('')}</div>`;
}

function evidence(f) {
  const runs = f.runs || [];
  const exploit = runs.find(r => !r.ok) || runs[0];
  if (!exploit) return '';
  let t = (exploit.stderr || exploit.stdout || '').slice(-1600);
  t = esc(t)
    .replace(/(VULN:.*|assertion.*failed.*|panicked at.*)/g, '<span class="vuln">$1</span>')
    .replace(/(error(\\[\\w+\\])?:.*|FAIL.*)/g, '<span class="err">$1</span>');
  return `<div class="term">${t}</div>`;
}

function provenance(f) {
  const evs = [...(provById[f.id] || [])];
  // hypotheses get fresh finding ids, so also pull events about the same
  // file — that's what the model actually contributed to this finding.
  const file = f.location && f.location.file;
  if (file) {
    for (const e of journal) {
      if (e.finding && e.finding.id !== f.id && e.finding.location &&
          e.finding.location.file === file) evs.unshift(e);
    }
  }
  if (!evs.length) return '';
  const steps = evs.map(e => {
    const ts = (e.ts || e.finding?.created_utc || '').replace('T', ' ').slice(11, 19);
    return `<span class="pv-step"><span class="ev ${esc(e.event)}">${esc(e.event)}</span><span class="pv-t">${esc(ts)}</span></span>`;
  }).join('<span class="pv-arrow">→</span>');
  return `<div class="prov"><span class="pv-label">discovery</span>${steps}</div>`;
}

function findingRow(f, open, isCandidate) {
  const sev = SEV[f.severity] || 'var(--faint)';
  const manual = isManual(f);
  const loc = f.location ? `<code>${esc(f.location.file)}</code>${f.location.line ? ':' + f.location.line : ''}${f.location.symbol ? ' · ' + esc(f.location.symbol) : ''}` : '';
  return `<details class="row" style="--sev:${isCandidate ? 'var(--faint)' : sev}" ${open ? 'open' : ''}>
    <summary>
      ${CHEV}<span class="dot"></span>
      <span class="title">${esc(f.title)}</span>
      <span class="meta">
        <span class="pill">${esc(f.vuln_class)}</span>
        ${!isCandidate && f.severity ? `<span class="pill sev">${esc(f.severity)}</span>` : ''}
        ${manual ? '<span class="pill manual">confirmed_manual</span>' : ''}
      </span>
    </summary>
    <div class="body">
      ${loc ? `<div class="loc-line">location · ${loc}</div>` : ''}
      ${provenance(f)}
      <p class="detail">${esc(f.detail)}</p>
      ${legs(f)}
      ${evidence(f)}
      ${f.patch_hint ? `<div class="fix"><b>suggested fix</b>${esc(f.patch_hint)}</div>` : ''}
    </div>
  </details>`;
}

function advisoryRow(g) {
  const sev = SEV[g.severity] || 'var(--faint)';
  const items = g.items.map(a => {
    const cve = (a.aliases || []).find(x => /^CVE-/.test(x));
    return `<div class="adv">
      <div class="adv-id"><a href="${esc(a.url)}">${esc(cve || a.id)}</a>${cve && a.id !== cve ? ` <span style="color:var(--faint)">(${esc(a.id)})</span>` : ''}</div>
      <div class="adv-sum">${esc(a.summary || 'no summary published')}</div>
    </div>`;
  }).join('');
  return `<details class="row" style="--sev:${sev}">
    <summary>
      ${CHEV}<span class="dot"></span>
      <span class="title">${esc(g.package)}<span style="color:var(--faint)">@${esc(g.version)}</span></span>
      <span class="meta">
        <span class="pill">${esc(g.ecosystem)}</span>
        <span class="pill">${g.items.length} advisor${g.items.length > 1 ? 'ies' : 'y'}</span>
        ${g.severity ? `<span class="pill sev">${esc(g.severity)}</span>` : ''}
      </span>
    </summary>
    <div class="body">
      <div class="loc-line">matched in <code>${esc(g.lockfile)}</code></div>
      ${items}
      ${g.fixed ? `<div class="fix"><b>remediation</b>upgrade to ${esc(g.fixed)} or later</div>` : ''}
    </div>
  </details>`;
}

function jline(e) {
  const ts = (e.ts || e.finding?.created_utc || '').replace('T', ' ').slice(11, 19);
  let what = '';
  if (e.finding) {
    what = `${esc(e.finding.title || '')}` +
      (e.finding.location ? ` — <code>${esc(e.finding.location.file)}</code>` : '');
  } else if (e.chunk) {
    what = `<code>${esc(e.chunk.file || e.chunk)}</code>`;
  } else {
    what = esc(e.note || e.detail || '');
  }
  return `<div class="jline" data-ev="${esc(e.event)}"><span class="t">${esc(ts)}</span><span class="ev ${esc(e.event)}">${esc(e.event)}</span><span class="what">${what}</span></div>`;
}

// journal filter chips
document.querySelectorAll('.chip').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('on'));
    chip.classList.add('on');
    const ev = chip.dataset.ev;
    document.querySelectorAll('.jline').forEach(l =>
      l.classList.toggle('hide', ev !== '*' && l.dataset.ev !== ev));
  });
});
"""


def render_html(results: dict, journal: list[dict] | None = None) -> str:
    payload = dict(results)
    payload["journal"] = journal or []
    blob = json.dumps(payload, default=str).replace("</", "<\\/")
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>cantheria · {payload.get("repo", "scan")} debrief</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@700;800&family=IBM+Plex+Mono:wght@400;600;700&display=swap" rel="stylesheet">
<style>{_CSS}</style>
</head><body>
<script id="scan-data" type="application/json">{blob}</script>
<div id="app"></div>
<script>{_JS}</script>
</body></html>"""


def write_html(results_path: Path, out_path: Path, journal_path: Path | None = None) -> Path:
    results = json.loads(results_path.read_text())
    journal = None
    if journal_path and journal_path.exists():
        journal = [
            json.loads(line) for line in journal_path.read_text().splitlines() if line.strip()
        ]
    index_dir = results_path.parent / "index"
    if index_dir.is_dir():
        for jf in index_dir.glob("*.jsonl"):
            results.setdefault("chunks_indexed", sum(1 for line in jf.open() if line.strip()))
            break
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_html(results, journal))
    return out_path
