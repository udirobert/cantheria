"""Self-contained HTML rendering of an audit/hunt results.json.

One file, no assets, no JS dependency beyond markup — judges click it.
Every confirmed claim shows the legs that held and receipt records with
deep links back to the live village UI.
"""

from __future__ import annotations

import html
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from .report import _public_source_uri

_CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { font: 15px/1.6 -apple-system, "SF Mono", ui-monospace, Menlo, monospace;
  background: #0d1117; color: #c9d1d9; max-width: 900px; margin: 0 auto; padding: 2rem 1.2rem 4rem; }
h1 { color: #f0f6fc; font-size: 1.5rem; }
h2 { color: #f0f6fc; font-size: 1.05rem; margin-top: 2.4rem;
  border-bottom: 1px solid #21262d; padding-bottom: .4rem; }
.claim { background: #161b22; border: 1px solid #21262d; border-left: 3px solid #30363d;
  border-radius: 6px; padding: .9rem 1.1rem; margin: .8rem 0; }
.claim.confirmed { border-left-color: #3fb950; }
.claim.dismissed { border-left-color: #f85149; }
.claim.unverifiable { border-left-color: #d29922; }
.claim.flaky { border-left-color: #a371f7; }
.text { color: #e6edf3; margin-bottom: .4rem; }
.meta { color: #8b949e; font-size: .82rem; }
.meta b { color: #c9d1d9; }
.legs { font-size: .8rem; color: #8b949e; margin: .3rem 0; }
.legs span { margin-right: 1rem; }
.receipts { margin: .4rem 0 0; padding-left: 1.1rem; font-size: .8rem; }
.receipts a { color: #58a6ff; text-decoration: none; word-break: break-all; }
.receipts a:hover { text-decoration: underline; }
.stat { display: inline-block; background: #161b22; border: 1px solid #21262d;
  border-radius: 6px; padding: .5rem .9rem; margin: .15rem .3rem .15rem 0; font-size: .85rem; }
.stat b { color: #f0f6fc; }
.tag { font-size: .7rem; text-transform: uppercase; letter-spacing: .08em;
  padding: .1rem .45rem; border-radius: 999px; border: 1px solid #30363d; color: #8b949e; }
blockquote { border-left: 3px solid #30363d; margin: 1rem 0; padding: .2rem 1rem; color: #8b949e; }
"""


def _esc(s: Any) -> str:
    return html.escape(str(s), quote=True)


def _receipt_links(claim: dict, db_path: Path | str | None) -> list[str]:
    ids: list[str] = []
    for r in claim.get("probes_run") or []:
        ids.extend(r.get("matched_ids") or [])
    ids = list(dict.fromkeys(ids))[:10]
    links: dict[str, str] = {}
    if db_path and ids:
        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
            try:
                for rid in ids:
                    row = conn.execute(
                        "SELECT source_uri, ts, agent_id FROM records WHERE record_id=?",
                        (rid,),
                    ).fetchone()
                    if row and row[0]:
                        links[rid] = row[0]
            finally:
                conn.close()
        except sqlite3.Error:
            pass
    return [
        f"<li><code>{_esc(r)}</code>"
        + (
            f' — <a href="{_esc(links[r])}">{_esc(links[r])}</a>'
            if r in links and _public_source_uri(links[r])
            else " — <span>corpus-internal reference</span>"
            if r in links
            else " — <span>no public source link supplied</span>"
        )
        + "</li>"
        for r in ids
    ]


def _claim_html(c: dict, db_path: Path | str | None) -> str:
    verdict = c.get("verdict", "candidate")
    raw = c.get("raw") or {}
    legs = raw.get("legs") or {}
    leg_bits = "".join(
        f"<span><b>{_esc(k)}</b> {_esc(str(v)[:60])}</span>" for k, v in legs.items()
    )
    receipts = ""
    if verdict == "confirmed":
        rl = _receipt_links(c, db_path)
        if rl:
            receipts = f'<ul class="receipts">{"".join(rl)}</ul>'
    if verdict == "confirmed":
        reason = raw.get("note")
        reason_label = "note"
    else:
        reason = raw.get("dismiss_reason") or raw.get("note") or raw.get("backend_error") or ""
        reason_label = "reason"
    return f"""<div class="claim {_esc(verdict)}">
<div class="text">{_esc(c.get("text", ""))}</div>
<div class="meta"><span class="tag">{_esc(verdict)}</span> {_esc(c.get("kind", ""))} · source {_esc(c.get("source_doc", ""))} · probe origin <b>{_esc(raw.get("probe_origin", "model"))}</b></div>
{f'<div class="legs">{leg_bits}</div>' if legs else ""}
{f'<div class="meta">{reason_label}: {_esc(reason)}</div>' if reason else ""}
{receipts}
</div>"""


def write_audit_html(
    result: dict[str, Any],
    out_path: Path,
    db_path: Path | str | None = None,
    title: str = "Cantheria swarm audit",
) -> Path:
    claims: list[dict] = result.get("claims") or []
    verdicts = Counter(c.get("verdict") for c in claims)
    decided = verdicts.get("confirmed", 0) + verdicts.get("dismissed", 0)
    slop = verdicts.get("dismissed", 0) / decided if decided else 0.0
    failing = (
        f"{verdicts.get('dismissed', 0)}/{decided} ({slop:.0%})"
        if decided
        else "N/A (0 decidable claims)"
    )

    sections: list[str] = []
    for verdict, label in (
        ("confirmed", "Confirmed — record-backed"),
        ("dismissed", "Dismissed — unsupported by the record"),
        ("flaky", "Flaky — probe/backend failures"),
        ("unverifiable", "Unverifiable — quarantined by construction"),
    ):
        items = [c for c in claims if c.get("verdict") == verdict]
        if not items:
            continue
        body = "".join(_claim_html(c, db_path) for c in items)
        sections.append(f"<h2>{label} ({len(items)})</h2>{body}")

    page = f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{_esc(title)}</title><style>{_CSS}</style></head><body>
<h1>{_esc(title)}</h1>
<div>
<span class="stat">claims <b>{len(claims)}</b></span>
<span class="stat">confirmed <b>{verdicts.get("confirmed", 0)}</b></span>
<span class="stat">dismissed <b>{verdicts.get("dismissed", 0)}</b></span>
<span class="stat">unverifiable <b>{verdicts.get("unverifiable", 0)}</b></span>
<span class="stat">flaky <b>{verdicts.get("flaky", 0)}</b></span>
<span class="stat">claims failing mechanical verification <b>{failing}</b></span>
<span class="stat">cost <b>{result.get("llm_calls", "?")} calls / {result.get("probe_runs", "?")} probes</b></span>
</div>
<blockquote>An LLM proposes; the record decides. Confirmed means the recorded
mechanical checks passed; it does not establish every clause of the narrative.
Unverifiable claims were quarantined rather than force-verified. Public source
links are shown where supplied; other receipts retain their corpus record IDs.
Decidable means confirmed or dismissed. Unverifiable and flaky outcomes are
excluded. A failed probe does not establish that the original claim is false.</blockquote>
{"".join(sections)}
<div class="meta">generated {__import__("datetime").datetime.now().isoformat(timespec="seconds")} · cantheria swarm pipeline</div>
</body></html>"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page)
    return out_path
