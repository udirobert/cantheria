"""cantheria CLI — the only entry point the hackathon day needs.

export SIE_API_KEY=sk-sie-...
cantheria scan https://github.com/some/project --out runs/proj1
cantheria report runs/proj1/results.json --out runs/proj1/reports
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer

from cantheria.fence import summarize
from cantheria.report import assign_severity, triage, write_reports
from cantheria.sandbox import describe_confinement
from cantheria.scan import scan
from cantheria.schemas import Finding
from cantheria.settings import settings
from cantheria.sie import SIEClient

app = typer.Typer(help="Cantheria — autonomous OSS vulnerability discovery.")


@app.command("scan")
def scan_cmd(
    repo: str = typer.Argument(..., help="git URL or local path of the target project"),
    out: Path = typer.Option(Path("runs/default"), help="output directory"),
    max_chunks: int = typer.Option(120, help="chunks to hunt, best-first"),
    budget: int = typer.Option(400, help="max LLM calls"),
    sandbox_budget: int = typer.Option(200, help="max sandbox PoC runs"),
    concurrency: int = typer.Option(4),
    fence: bool = typer.Option(
        True,
        "--fence/--no-fence",
        help="fence instruction-shaped text in target source; --no-fence is the A/B baseline",
    ),
    diff: str = typer.Option(
        "",
        "--diff",
        help="base ref for delta review — hunt only files changed vs this ref",
    ),
) -> None:
    """Index a repo, hunt its highest-blast-radius code, validate, triage."""
    if not settings.configured:
        typer.echo("SIE_API_KEY not set")
        raise typer.Exit(code=2)
    if not fence:
        typer.echo("⚠ fence OFF: target source goes to the model unguarded. Baseline runs only.")
    from cantheria.hunt import HuntBudget

    result = asyncio.run(
        scan(
            repo,
            out,
            max_chunks=max_chunks,
            concurrency=concurrency,
            budget=HuntBudget(max_llm_calls=budget, max_sandbox_runs=sandbox_budget),
            fence_enabled=fence,
            diff_base=diff,
        )
    )
    payload = {
        "repo": result.repo,
        "llm_calls": result.budget.llm_calls,
        "sandbox_runs": result.budget.sandbox_runs,
        "merged_duplicates": result.merged,
        "confinement": describe_confinement(),
        "fence_hits": [h.as_dict() for h in result.fence_hits],
        "findings": json.loads(json.dumps([f.model_dump(mode="json") for f in result.findings])),
        "prefetched": result.prefetched,
        "advisories": result.advisories,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(payload, indent=2))
    typer.echo(f"{len(result.findings)} confirmed finding(s) → {out / 'results.json'}")
    if result.merged:
        typer.echo(f"  ({result.merged} duplicate report(s) folded into their twin — see dedup.py)")
    typer.echo(f"  deps prefetched: {result.prefetched or 'none'}")
    if result.advisories:
        typer.echo(f"  supply chain: {len(result.advisories)} known advisor(ies) in lockfiles")
    typer.echo(f"  sandbox confinement: {describe_confinement()}")
    for line in summarize(result.fence_hits).splitlines():
        typer.echo(f"  fence: {line}")
    typer.echo(f"journal: {result.journal_path}")


@app.command("report")
def report_cmd(
    results: Path = typer.Argument(..., help="results.json from a scan"),
    out: Path = typer.Option(Path("reports")),
    enrich: bool = typer.Option(True, help="run triage + severity via SIE"),
    html: Path | None = typer.Option(None, help="also write a self-contained HTML debrief"),
    sarif: Path | None = typer.Option(None, help="also write a SARIF 2.1.0 export"),
) -> None:
    data = json.loads(results.read_text())
    findings = [Finding.model_validate(f) for f in data["findings"]]
    if enrich and settings.configured:

        async def _enrich() -> None:
            sie = SIEClient()
            try:
                await triage(sie, findings)
                for f in findings:
                    if f.reportable:
                        await assign_severity(sie, f)
            finally:
                await sie.close()

        asyncio.run(_enrich())
    paths = write_reports(findings, out)
    typer.echo(f"{len(paths)} report(s) → {out}")
    for p in paths:
        typer.echo(f"  {p}/REPORT.md")
    if html:
        from cantheria.report_html import write_html

        p = write_html(results, html, journal_path=results.parent / "journal.jsonl")
        typer.echo(f"html debrief → {p}")
    if sarif:
        from cantheria.report import write_sarif

        p = write_sarif(findings, sarif)
        typer.echo(f"sarif → {p}")


@app.command()
def status() -> None:
    """Check wiring: key present, models reachable."""
    typer.echo(f"base_url: {settings.base_url}")
    typer.echo(f"api_key:  {'set' if settings.configured else 'MISSING'}")
    if settings.configured:

        async def _check() -> None:
            import httpx

            async with httpx.AsyncClient(
                base_url=settings.base_url,
                headers={"Authorization": f"Bearer {settings.api_key}"},
                timeout=30,
            ) as c:
                r = await c.get("/v1/models")
                r.raise_for_status()
                names = [m["id"] for m in r.json().get("data", r.json())]
                typer.echo(f"{len(names)} model(s) available; chat={_pick(names)}")

        try:
            asyncio.run(_check())
        except Exception as exc:  # noqa: BLE001
            typer.echo(f"models check failed: {exc}")


def _pick(names: list[str]) -> str:
    for want in ("Coder", "coder", "qwen3", "Qwen3"):
        for n in names:
            if want in n:
                return n
    return names[0] if names else "?"


if __name__ == "__main__":
    app()
