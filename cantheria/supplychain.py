"""Supply-chain leg: known advisories in the target's dependency tree.

Distinct from hunt findings — these are *known* CVEs/GHSAs matched against
lockfile versions via the public OSV batch API (no key needed), not novel
bugs proven by the kill chain. They run host-side (network) during scan,
alongside prefetch.

Parsers cover Cargo.lock (tomllib), package-lock.json, and pnpm-lock.yaml
(best-effort regex — pnpm's yaml shape shifts across versions).
"""

from __future__ import annotations

import asyncio
import json
import re
import tomllib
from pathlib import Path
from typing import Any

import httpx

OSV_BATCH = "https://api.osv.dev/v1/querybatch"
OSV_VULN = "https://api.osv.dev/v1/vulns/"

_SEV_MAP = {
    "CRITICAL": "critical",
    "HIGH": "high",
    "MODERATE": "moderate",
    "MEDIUM": "moderate",
    "LOW": "low",
}


def parse_lockfiles(repo: Path) -> list[dict[str, str]]:
    pkgs: list[dict[str, str]] = []

    cargo = repo / "Cargo.lock"
    if cargo.exists():
        try:
            data = tomllib.loads(cargo.read_text())
            for p in data.get("package", []):
                pkgs.append(
                    {
                        "ecosystem": "crates.io",
                        "name": p["name"],
                        "version": p["version"],
                        "lockfile": "Cargo.lock",
                    }
                )
        except (tomllib.TOMLDecodeError, KeyError):
            pass

    plock = repo / "package-lock.json"
    if plock.exists():
        try:
            data = json.loads(plock.read_text())
            for key, meta in data.get("packages", {}).items():
                if key and "version" in meta:
                    pkgs.append(
                        {
                            "ecosystem": "npm",
                            "name": key.removeprefix("node_modules/"),
                            "version": meta["version"],
                            "lockfile": "package-lock.json",
                        }
                    )
        except json.JSONDecodeError:
            pass

    pnpm = repo / "pnpm-lock.yaml"
    if pnpm.exists():
        # entries look like:  name@1.2.3:   or   'name@1.2.3':
        pat = re.compile(r"^\s{2,}['\"]?(@?[\w./-]+)@(\d[\w.-]*)['\"]?:", re.M)
        for m in pat.finditer(pnpm.read_text()):
            name = m.group(1)
            # snapshot keys may carry peer suffixes (name@1.0(peer@2)) whose
            # leading version segment can misparse as a name
            if name[0].isdigit() or "(" in name:
                continue
            pkgs.append(
                {
                    "ecosystem": "npm",
                    "name": name,
                    "version": m.group(2),
                    "lockfile": "pnpm-lock.yaml",
                }
            )

    # dedupe (same dep can appear in several lockfiles)
    seen = set()
    out = []
    for p in pkgs:
        k = (p["ecosystem"], p["name"], p["version"])
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out


def _severity(v: dict[str, Any]) -> str | None:
    sev = (v.get("database_specific") or {}).get("severity")
    if sev and sev.upper() in _SEV_MAP:
        return _SEV_MAP[sev.upper()]
    return None  # CVSS vectors don't carry a numeric base score; leave unrated


def _fixed(v: dict[str, Any]) -> str | None:
    for aff in v.get("affected", []):
        for rng in aff.get("ranges", []):
            for ev in rng.get("events", []):
                if "fixed" in ev:
                    return ev["fixed"]
    return None


async def check_advisories(
    pkgs: list[dict[str, str]],
    *,
    batch_size: int = 1000,
    detail_concurrency: int = 16,
    timeout_s: float = 30.0,
) -> list[dict[str, Any]]:
    """Query OSV for known vulns affecting the locked versions."""
    if not pkgs:
        return []
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        hits: list[tuple[dict[str, str], str]] = []  # (pkg, vuln id)
        for i in range(0, len(pkgs), batch_size):
            batch = pkgs[i : i + batch_size]
            resp = await client.post(
                OSV_BATCH,
                json={
                    "queries": [
                        {
                            "package": {"name": p["name"], "ecosystem": p["ecosystem"]},
                            "version": p["version"],
                        }
                        for p in batch
                    ]
                },
            )
            resp.raise_for_status()
            for p, r in zip(batch, resp.json().get("results", []), strict=False):
                for v in r.get("vulns") or []:
                    hits.append((p, v["id"]))

        if not hits:
            return []

        sem = asyncio.Semaphore(detail_concurrency)

        async def detail(vid: str) -> dict[str, Any]:
            async with sem:
                r = await client.get(OSV_VULN + vid)
                r.raise_for_status()
                return r.json()

        details = {v["id"]: v for v in await asyncio.gather(*(detail(vid) for _, vid in hits))}

    advisories = []
    seen = set()
    for p, vid in hits:
        if (p["name"], vid) in seen:
            continue
        seen.add((p["name"], vid))
        v = details[vid]
        advisories.append(
            {
                "id": vid,
                "aliases": v.get("aliases", []),
                "summary": v.get("summary", ""),
                "severity": _severity(v),
                "package": p["name"],
                "version": p["version"],
                "ecosystem": p["ecosystem"],
                "lockfile": p["lockfile"],
                "fixed": _fixed(v),
                "url": f"https://osv.dev/vulnerability/{vid}",
            }
        )
    order = ["critical", "high", "moderate", "low"]
    advisories.sort(key=lambda a: order.index(a["severity"]) if a["severity"] in order else 9)
    return advisories
