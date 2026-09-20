"""Triage + maintainer-facing reports.

triage() sets confidence via SIE rerank: how well does each confirmed finding
match "a real vulnerability a maintainer would fix"? Below the quarantine
threshold it never appears in reports/ — same gating discipline as elcaro.

Each report is a directory a maintainer can run blind:
    reports/<id>/REPORT.md   — root cause, impact, repro, patch hint
    reports/<id>/poc/        — the PoC files verbatim
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from cantheria.schemas import Finding
from cantheria.settings import CHAT_MODEL, settings
from cantheria.sie import SIEClient

TRIAGE_QUERY = (
    "a confirmed, reproducible security vulnerability with real impact that a "
    "maintainer would prioritize fixing"
)
SEVERITY_SCALE = ("negligible", "low", "moderate", "high", "critical")


def _doc(f: Finding) -> str:
    trace = ""
    if f.runs:
        trace = (f.runs[0].stderr or f.runs[0].stdout)[-1500:]
    return f"{f.title}\n{f.detail}\nclass: {f.vuln_class.value}\ncrash trace:\n{trace}"


async def triage(sie: SIEClient, findings: list[Finding]) -> list[Finding]:
    live = [f for f in findings if f.verdict.value == "confirmed"]
    if not live:
        return findings
    try:
        ranked = await sie.rerank("Qwen/Qwen3-Reranker-4B", TRIAGE_QUERY, [_doc(f) for f in live])
    except Exception:  # noqa: BLE001 — triage must not eat the scan
        for f in live:
            f.confidence = 0.5
        return findings
    for idx, score in ranked:
        live[idx].confidence = max(0.0, min(1.0, float(score)))
    for f in live:
        if f.confidence < settings.quarantine_threshold:
            f.raw["quarantined"] = True
    return findings


async def assign_severity(sie: SIEClient, finding: Finding) -> None:
    try:
        raw = await sie.chat(
            CHAT_MODEL,
            [
                {
                    "role": "system",
                    "content": (
                        "Rate remediation priority for this confirmed vulnerability as exactly "
                        "one word from: negligible low moderate high critical. "
                        "Judge exploitability and blast radius, not scariness."
                    ),
                },
                {"role": "user", "content": _doc(finding)},
            ],
            temperature=0.0,
            max_tokens=5,
        )
    except Exception:  # noqa: BLE001
        return
    word = raw.strip().lower().split()[0] if raw.strip() else ""
    finding.severity = word if word in SEVERITY_SCALE else None


def write_reports(findings: list[Finding], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    keep = [f for f in findings if f.reportable and not f.raw.get("quarantined")]
    for f in keep:
        d = out_dir / f.id
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        if f.poc and f.poc.files:
            (d / "poc").mkdir()
            for name, content in f.poc.files.items():
                dest = (d / "poc" / name).resolve()
                if not dest.is_relative_to(d.resolve()):
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content)
        (d / "REPORT.md").write_text(_markdown(f))
        (d / "finding.json").write_text(f.model_dump_json(indent=2))
        paths.append(d)
    (out_dir / "index.json").write_text(
        json.dumps(
            [
                {
                    "id": f.id,
                    "title": f.title,
                    "severity": f.severity,
                    "confidence": round(f.confidence, 3),
                    "file": f.location.file if f.location else None,
                }
                for f in keep
            ],
            indent=2,
        )
    )
    return paths


_SARIF_LEVEL = {"critical": "error", "high": "error", "moderate": "warning", "medium": "warning"}


def write_sarif(findings: list[Finding], out_path: Path, tool_version: str = "0.1.0") -> Path:
    """SARIF 2.1.0 export — findings land in GitHub code scanning, VS Code,
    and every IDE that reads the standard. Only confirmed, non-quarantined
    findings are exported; candidates stay in the journal."""
    keep = [f for f in findings if f.reportable and not f.raw.get("quarantined")]
    rules = {}
    for f in keep:
        rules.setdefault(
            f.vuln_class.value,
            {
                "id": f.vuln_class.value,
                "name": f.vuln_class.value.replace("_", " ").title(),
                "shortDescription": {"text": f.vuln_class.value.replace("_", " ")},
            },
        )
    results = []
    for f in keep:
        loc = {}
        if f.location:
            loc = {
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": f.location.file,
                                "uriBaseId": "SRCROOT",
                            },
                            **(
                                {"region": {"startLine": f.location.line}}
                                if f.location.line
                                else {}
                            ),
                        }
                    }
                ]
            }
        results.append(
            {
                "ruleId": f.vuln_class.value,
                "level": _SARIF_LEVEL.get(f.severity or "", "note"),
                "message": {"text": f"{f.title}\n\n{f.detail}".strip()},
                "partialFingerprints": {"cantheriaFindingId": f.id},
                **loc,
            }
        )
    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Cantheria",
                        "version": tool_version,
                        "informationUri": "https://github.com/thisyearnofear/cantheria",
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
            }
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(sarif, indent=2))
    return out_path


def _markdown(f: Finding) -> str:
    loc = f.location
    where = (
        f"`{loc.file}`"
        + (f" line {loc.line}" if loc.line else "")
        + (f" (`{loc.symbol}`)" if loc.symbol else "")
        if loc
        else "see PoC"
    )
    crash = ""
    if f.runs:
        # runs[-1] is the benign-input control — the evidence a maintainer
        # wants is the exploit run that actually failed.
        exploit = next((r for r in f.runs if not r.ok), f.runs[0])
        crash = ((exploit.stderr or exploit.stdout)[-2000:]) or "(no output)"
    repro = ""
    if f.poc:
        expected = {
            "nonzero_exit": "exits non-zero",
            "signal": "dies on a signal",
            "sanitizer_report": "prints a sanitizer report",
            "assertion": "fails its safety assertion",
        }.get(f.poc.expect, "fails as expected")
        repro = (
            f"```bash\n# from the repo root\nmkdir poc && cd poc\n"
            f"# <copy files from poc/ beside this report>\n"
            f"{f.poc.entry}\n# expected: the program {expected}\n```"
        )
    return f"""# {f.title}

**Project:** {f.target_repo}  **Class:** {f.vuln_class.value}  \
**Severity:** {f.severity or "unrated"}  **Confidence:** {f.confidence:.2f}

## Location
{where}

## Root cause
{f.detail or "_no detail recorded_"}

## Proof of concept
{repro or "_PoC unavailable_"}

## Observed failure
```
{crash.strip()}
```

## Suggested fix
{f.patch_hint or "_none proposed — reviewer input welcome_"}

---
*Found by Cantheria (SIFT: embed → hunt → validate → triage). Every claim here
is replayable from `finding.json` + `poc/`.*
"""
