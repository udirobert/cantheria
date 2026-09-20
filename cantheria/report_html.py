"""Self-contained HTML report — the "flight recorder" view of a scan.

Renders results.json + journal.jsonl into ONE html file: no server, no
build step, works off file:// on a projector. Data is embedded as JSON and
rendered client-side. Used by `cantheria report --html` and for demos.

Design intent: the journal is the honest record — hypothesis_only events,
dismissed candidates, and fence hits render alongside confirmed findings.
Hand-authored PoCs are labelled `confirmed_manual`, never hidden.
"""

from __future__ import annotations

import json
from pathlib import Path

_CSS = """
:root {
  --bg: #0d0c0a; --panel: #15140f; --panel2: #1c1a13; --line: #2c2a20;
  --ink: #e8e3d3; --dim: #8f8a76; --faint: #57543f;
  --canary: #f5c518; --canary-dim: #8a7514;
  --crit: #ff5a45; --high: #ff9e45; --med: #f5c518; --low: #7dc9a5;
  --ok: #86d075; --fail: #ff5a45;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { background: var(--bg); }
body {
  background: var(--bg); color: var(--ink);
  font-family: "IBM Plex Mono", "JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 14px; line-height: 1.55;
  padding: 0 0 96px;
}
body::before {
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background:
    radial-gradient(1200px 500px at 70% -10%, rgba(245,197,24,.05), transparent 60%),
    repeating-linear-gradient(0deg, transparent 0 3px, rgba(0,0,0,.12) 3px 4px);
}
.wrap { max-width: 1080px; margin: 0 auto; padding: 0 32px; position: relative; z-index: 1; }
a { color: var(--canary); }
header {
  border-bottom: 1px solid var(--line);
  padding: 48px 0 28px; margin-bottom: 40px;
}
.brand {
  font-family: "Archivo", "IBM Plex Mono", ui-monospace, monospace;
  font-weight: 800; font-size: 13px; letter-spacing: .45em;
  color: var(--canary); text-transform: uppercase;
}
h1 {
  font-family: "Archivo", "IBM Plex Mono", ui-monospace, monospace;
  font-weight: 800; font-size: clamp(34px, 6vw, 58px);
  line-height: 1.02; letter-spacing: -.01em; margin: 14px 0 10px;
}
h1 .dim { color: var(--faint); }
.sub { color: var(--dim); max-width: 640px; }
.sub b { color: var(--ink); font-weight: 600; }
.stats {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 1px; background: var(--line); border: 1px solid var(--line);
  margin: 28px 0 0;
}
.stat { background: var(--panel); padding: 16px 18px; }
.stat .n { font-family: "Archivo", monospace; font-size: 30px; font-weight: 800; color: var(--ink); }
.stat .n.canary { color: var(--canary); }
.stat .k { font-size: 10px; letter-spacing: .18em; text-transform: uppercase; color: var(--dim); margin-top: 4px; }
.pipeline {
  display: flex; align-items: stretch; gap: 0; margin: 40px 0 8px;
  border: 1px solid var(--line);
}
.stage { flex: 1; padding: 14px 16px; position: relative; background: var(--panel); }
.stage + .stage { border-left: 1px solid var(--line); }
.stage .s-name { font-size: 10px; letter-spacing: .2em; text-transform: uppercase; color: var(--dim); }
.stage .s-val { font-family: "Archivo", monospace; font-size: 22px; font-weight: 800; margin-top: 2px; }
.stage .s-note { font-size: 11px; color: var(--faint); margin-top: 2px; }
.stage.hot .s-val { color: var(--canary); }
h2 {
  font-family: "Archivo", monospace; font-size: 13px; font-weight: 800;
  letter-spacing: .3em; text-transform: uppercase; color: var(--canary);
  margin: 56px 0 20px; padding-top: 20px; border-top: 1px solid var(--line);
}
h2 .count { color: var(--dim); }
.finding {
  border: 1px solid var(--line); background: var(--panel);
  margin-bottom: 28px; position: relative;
}
.finding::before {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
  background: var(--sev, var(--faint));
}
.f-head { padding: 22px 26px 14px; display: flex; gap: 16px; align-items: flex-start; }
.stamp {
  flex: none; border: 2px solid var(--sev); color: var(--sev);
  font-family: "Archivo", monospace; font-weight: 800; font-size: 11px;
  letter-spacing: .25em; text-transform: uppercase;
  padding: 5px 10px; transform: rotate(-2deg); margin-top: 3px;
}
.f-head h3 { font-size: 19px; font-weight: 700; line-height: 1.3; }
.loc { font-size: 12px; color: var(--dim); margin-top: 6px; }
.loc code { color: var(--canary); }
.badges { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
.badge {
  font-size: 10px; letter-spacing: .14em; text-transform: uppercase;
  border: 1px solid var(--line); color: var(--dim); padding: 3px 8px;
}
.badge.manual { border-color: var(--canary-dim); color: var(--canary); }
.f-body { padding: 0 26px 22px; }
.f-body p.detail { color: var(--dim); max-width: 780px; margin-bottom: 16px; }
.legs { display: flex; gap: 10px; flex-wrap: wrap; margin: 0 0 16px; }
.leg {
  font-size: 11px; padding: 6px 10px; border: 1px solid var(--line);
  background: var(--panel2); color: var(--dim);
}
.leg b { color: var(--ok); font-weight: 600; }
.leg.na b { color: var(--faint); }
.term {
  background: #060605; border: 1px solid var(--line); padding: 14px 16px;
  font-size: 12px; line-height: 1.6; overflow-x: auto; white-space: pre;
  color: #b8b29c; margin-bottom: 16px; max-height: 260px; overflow-y: auto;
}
.term .vuln { color: var(--canary); font-weight: 700; }
.term .err { color: var(--fail); }
.fix { border-left: 2px solid var(--canary-dim); padding: 4px 14px; color: var(--dim); font-size: 13px; }
.fix b { color: var(--ink); font-weight: 600; display: block; font-size: 10px; letter-spacing: .2em; text-transform: uppercase; margin-bottom: 4px; }
.journal { border: 1px solid var(--line); background: #060605; }
.jline {
  display: grid; grid-template-columns: 92px 150px 1fr; gap: 14px;
  padding: 9px 16px; border-bottom: 1px solid #1a190f; font-size: 12px;
}
.jline:last-child { border-bottom: 0; }
.jline .t { color: var(--faint); }
.jline .ev { font-weight: 700; letter-spacing: .05em; }
.ev.confirmed, .ev.confirmed_manual { color: var(--canary); }
.ev.hypothesis_only, .ev.hypothesis { color: var(--dim); }
.ev.dismissed, .ev.fence_hit { color: var(--fail); }
.jline .what { color: var(--dim); overflow: hidden; text-overflow: ellipsis; }
.jline .what code { color: var(--ink); }
footer { margin-top: 64px; color: var(--faint); font-size: 12px; border-top: 1px solid var(--line); padding-top: 20px; }
@media (max-width: 720px) {
  .pipeline { flex-direction: column; }
  .stage + .stage { border-left: 0; border-top: 1px solid var(--line); }
  .jline { grid-template-columns: 80px 120px 1fr; }
}
"""

_JS = """
const data = JSON.parse(document.getElementById('scan-data').textContent);
const esc = s => String(s ?? '').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const SEV = {critical:'var(--crit)', high:'var(--high)', moderate:'var(--med)', medium:'var(--med)', low:'var(--low)', negligible:'var(--low)'};
const EXPECT = {nonzero_exit:'exit≠0', signal:'signal', sanitizer_report:'sanitizer', assertion:'assertion'};

const confirmed = data.findings.filter(f => f.verdict === 'confirmed');
const journal = data.journal || [];
const confirmedIds = new Set(confirmed.map(f => f.id));
// candidates live in the journal (hypothesis_only / dismissed events carry
// the finding payload); results.json only stores what survived triage.
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

document.getElementById('app').innerHTML = `
<header><div class="wrap">
  <div class="brand">CANTHERIA · FLIGHT RECORDER</div>
  <h1>${esc(data.repo)}<span class="dim"> — scan debrief</span></h1>
  <div class="sub">
    <b>${confirmed.length}</b> confirmed · <b>${candidates.length}</b> candidates held ·
    <b>${hyp}</b> hypotheses · <b>${data.llm_calls}</b> LLM calls ·
    <b>${data.sandbox_runs}</b> sandbox runs · <b>${fenceN}</b> fence hits ·
    <b>${data.merged_duplicates}</b> merged duplicates
  </div>
  <div class="stats">
    <div class="stat"><div class="n canary">${confirmed.length}</div><div class="k">confirmed</div></div>
    <div class="stat"><div class="n">${candidates.length}</div><div class="k">candidates</div></div>
    <div class="stat"><div class="n">${data.sandbox_runs}</div><div class="k">sandbox runs</div></div>
    <div class="stat"><div class="n">${data.llm_calls}</div><div class="k">llm calls</div></div>
    <div class="stat"><div class="n">${(data.prefetched||[]).length}</div><div class="k">deps prefetched</div></div>
  </div>
</div></header>

<div class="wrap">
<div class="pipeline">
  <div class="stage"><div class="s-name">S · index</div><div class="s-val">${esc(data.chunks_indexed ?? '—')}</div><div class="s-note">chunks embedded</div></div>
  <div class="stage"><div class="s-name">I · infer</div><div class="s-val">${hyp}</div><div class="s-note">hypotheses</div></div>
  <div class="stage"><div class="s-name">F · falsify</div><div class="s-val">${data.sandbox_runs}</div><div class="s-note">sandbox executions</div></div>
  <div class="stage hot"><div class="s-name">T · triage</div><div class="s-val">${confirmed.length}</div><div class="s-note">survived the kill chain</div></div>
</div>

<h2>Confirmed findings <span class="count">— kill chain passed</span></h2>
${confirmed.map(f => findingCard(f)).join('') || '<p class="sub">none — the canaries lived.</p>'}

<h2>Candidates <span class="count">— hypothesized, not yet proven (${candidates.length})</span></h2>
${candidates.map(f => findingCard(f, true)).join('')}

<h2>Journal <span class="count">— append-only record, ${journal.length} events</span></h2>
<div class="journal">${journal.map(jline).join('')}</div>

<footer>
  Generated by Cantheria — SIFT: index → infer → falsify → triage.<br>
  A finding is only <em>confirmed</em> when a machine-checkable PoC reproduces N times
  AND a benign-input control passes AND the failure attributes to target code.
  Findings tagged <span style="color:var(--canary)">confirmed_manual</span> had hand-authored
  PoCs — the journal records which is which.
</footer>
</div>`;

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

function findingCard(f, isCandidate) {
  const sev = SEV[f.severity] || 'var(--faint)';
  const manual = isManual(f);
  const loc = f.location ? `<code>${esc(f.location.file)}</code>${f.location.line ? ':' + f.location.line : ''}${f.location.symbol ? ' · ' + esc(f.location.symbol) : ''}` : 'see PoC';
  return `<div class="finding" style="--sev:${isCandidate ? 'var(--faint)' : sev}">
    <div class="f-head">
      ${isCandidate ? '' : `<div class="stamp">${esc(f.severity || 'unrated')}</div>`}
      <div>
        <h3>${esc(f.title)}</h3>
        <div class="loc">${loc}</div>
        <div class="badges">
          <span class="badge">${esc(f.vuln_class)}</span>
          <span class="badge">${esc(f.verdict)}</span>
          ${manual ? '<span class="badge manual">confirmed_manual · hand-authored PoC</span>' : ''}
          ${f.confidence ? `<span class="badge">conf ${f.confidence.toFixed(2)}</span>` : ''}
        </div>
      </div>
    </div>
    <div class="f-body">
      <p class="detail">${esc(f.detail)}</p>
      ${legs(f)}
      ${evidence(f)}
      ${f.patch_hint ? `<div class="fix"><b>suggested fix</b>${esc(f.patch_hint)}</div>` : ''}
    </div>
  </div>`;
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
  return `<div class="jline"><span class="t">${esc(ts)}</span><span class="ev ${esc(e.event)}">${esc(e.event)}</span><span class="what">${what}</span></div>`;
}
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
