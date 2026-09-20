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

from cantheria.report import assign_severity, triage, write_reports
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
) -> None:
    """Index a repo, hunt its highest-blast-radius code, validate, triage."""
    if not settings.configured:
        typer.echo("SIE_API_KEY not set")
        raise typer.Exit(code=2)
    from cantheria.hunt import HuntBudget

    result = asyncio.run(
        scan(
            repo,
            out.parent if out.name != "default" else out,
            max_chunks=max_chunks,
            concurrency=concurrency,
            budget=HuntBudget(max_llm_calls=budget, max_sandbox_runs=sandbox_budget),
        )
    )
    payload = {
        "repo": result.repo,
        "llm_calls": result.budget.llm_calls,
        "sandbox_runs": result.budget.sandbox_runs,
        "findings": json.loads(json.dumps([f.model_dump(mode="json") for f in result.findings])),
    }
    (out / "results.json").write_text(json.dumps(payload, indent=2))
    typer.echo(f"{len(result.findings)} confirmed finding(s) → {out / 'results.json'}")
    typer.echo(f"journal: {result.journal_path}")


@app.command("report")
def report_cmd(
    results: Path = typer.Argument(..., help="results.json from a scan"),
    out: Path = typer.Option(Path("reports")),
    enrich: bool = typer.Option(True, help="run triage + severity via SIE"),
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
