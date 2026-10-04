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
from cantheria.journal import Journal
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
    from cantheria.chat import chat_model, make_chat, using_alt_backend

    if using_alt_backend():
        typer.echo(f"chat backend: alt ({make_chat()._http.base_url}), model={chat_model()}")
    else:
        typer.echo(f"base_url: {settings.base_url}")
        typer.echo(f"api_key:  {'set' if settings.configured else 'MISSING'}")
        typer.echo(f"chat:     {chat_model()}")
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


# ---------------------------------------------------------------------------
# swarm forensics — ingest / audit / hunt (see SWARM.md)
# ---------------------------------------------------------------------------


@app.command("ingest")
def ingest_cmd(
    source_path: Path = typer.Argument(
        ..., help="dataset directory (aivillage) or file (collusion/swarmtraces)"
    ),
    corpus: Path = typer.Option(..., help="records.db path to create/extend"),
    source: str = typer.Option("aivillage", help="aivillage | collusion | swarmtraces"),
) -> None:
    """Normalize an external corpus into the `records` table."""
    from cantheria.swarm.corpus import Corpus
    from cantheria.swarm.ingest import LOADERS

    loader = LOADERS.get(source)
    if loader is None:
        typer.echo(f"unknown source {source!r}; expected one of {sorted(LOADERS)}")
        raise typer.Exit(code=2)
    db = Corpus(corpus)
    counts = loader(source_path, db)
    for kind, n in counts.items():
        typer.echo(f"  {kind}: {n}")
    if source == "aivillage-turns":
        typer.echo("topping up records_fts index…")
        db.topup_fts()
    else:
        typer.echo("building records_fts index…")
        db.build_fts()
    stats = db.stats()
    typer.echo(f"total records: {stats['total']}  span: {stats['span'][0]} .. {stats['span'][1]}")
    db.close()


@app.command("audit")
def audit_cmd(
    corpus: Path = typer.Argument(..., help="records.db from `cantheria ingest`"),
    claims: Path = typer.Option(..., help="jsonl of claims/documents, or a md/txt report"),
    out: Path = typer.Option(Path("runs/audit"), help="output directory"),
    docs: int = typer.Option(20, help="max documents to decompose (jsonl summaries etc.)"),
    budget: int = typer.Option(300, help="max LLM calls"),
    concurrency: int = typer.Option(4),
) -> None:
    """Audit a document's claims against the record — the slop-rate run."""
    from cantheria.chat import chat_configured, make_chat

    if not chat_configured():
        typer.echo("no chat backend: set SIE_API_KEY or CANTHERIA_CHAT_API_KEY/FEATHERLESS_API_KEY")
        raise typer.Exit(code=2)

    async def _run() -> dict:
        from cantheria.swarm.extract import claims_from_rows, extract_claims
        from cantheria.swarm.hunt import SwarmBudget, _schema_hint, audit_claim
        from cantheria.swarm.ingest import ingest_claims
        from cantheria.swarm.oracle import make_oracle

        budget_ = SwarmBudget(max_llm_calls=budget, max_probe_runs=budget * 2)
        journal = Journal(out / "journal.jsonl")
        sie = make_chat()
        oracle = make_oracle()
        hint = _schema_hint(corpus)
        claim_list: list = []
        try:
            rows = ingest_claims(claims)
            claim_list.extend(claims_from_rows(rows, corpus.name))
            doc_rows = [
                r for r in rows if r.get("document") or r.get("content") or r.get("summary")
            ]
            for r in doc_rows[:docs]:
                if budget_.spent:
                    break
                doc = str(r.get("document") or r.get("content") or r.get("summary"))
                src = str(r.get("id") or r.get("source_doc") or claims.name)
                claim_list.extend(await extract_claims(sie, doc, src, corpus.name, budget_))
            sem = asyncio.Semaphore(concurrency)

            async def one(c):
                async with sem:
                    try:
                        return await audit_claim(c, corpus, sie, oracle, journal, budget_, hint)
                    except Exception as exc:  # backend flake — one claim dies, not the batch
                        from cantheria.swarm.schemas import Verdict

                        c.verdict = Verdict.flaky
                        c.raw["backend_error"] = str(exc)[:500]
                        journal.log(c, "backend_error")
                        return c

            audited = await asyncio.gather(*(one(c) for c in claim_list))
        finally:
            await sie.close()
        return {
            "corpus": str(corpus),
            "llm_calls": budget_.llm_calls,
            "probe_runs": budget_.probe_runs,
            "claims": [json.loads(c.model_dump_json()) for c in audited],
        }

    out.mkdir(parents=True, exist_ok=True)
    result = asyncio.run(_run())
    (out / "results.json").write_text(json.dumps(result, indent=2))
    from cantheria.swarm.report import write_audit_report

    write_audit_report(result, out / "REPORT.md", corpus)
    verdicts: dict[str, int] = {}
    for c in result["claims"]:
        verdicts[c["verdict"]] = verdicts.get(c["verdict"], 0) + 1
    decided = verdicts.get("confirmed", 0) + verdicts.get("dismissed", 0)
    slop = verdicts.get("dismissed", 0) / decided if decided else 0.0
    typer.echo(f"{len(result['claims'])} claims → {verdicts}")
    typer.echo(f"decided {decided}, slop rate {slop:.0%} (dismissed / decided)")
    typer.echo(f"journal: {out / 'journal.jsonl'}  results: {out / 'results.json'}")
    typer.echo(f"report: {out / 'REPORT.md'}")


@app.command("hunt")
def hunt_cmd(
    corpus: Path = typer.Argument(..., help="records.db from `cantheria ingest`"),
    out: Path = typer.Option(Path("runs/hunt"), help="output directory"),
    segments: int = typer.Option(30, help="agent-day segments to hunt, busiest first"),
    budget: int = typer.Option(300, help="max LLM calls"),
    concurrency: int = typer.Option(4),
) -> None:
    """Hypothesize per segment, then put each hypothesis through the chain."""
    from cantheria.chat import chat_configured, make_chat

    if not chat_configured():
        typer.echo("no chat backend: set SIE_API_KEY or CANTHERIA_CHAT_API_KEY/FEATHERLESS_API_KEY")
        raise typer.Exit(code=2)

    async def _run() -> dict:
        from cantheria.swarm.hunt import SwarmBudget, _schema_hint, hunt_segment
        from cantheria.swarm.oracle import make_oracle
        from cantheria.swarm.segment import agent_day_segments

        budget_ = SwarmBudget(max_llm_calls=budget, max_probe_runs=budget * 2)
        journal = Journal(out / "journal.jsonl")
        sie = make_chat()
        oracle = make_oracle()
        hint = _schema_hint(corpus)
        segs = agent_day_segments(corpus, limit=segments)
        sem = asyncio.Semaphore(concurrency)
        try:

            async def one(s):
                async with sem:
                    try:
                        return await hunt_segment(s, corpus, sie, oracle, journal, budget_, hint)
                    except Exception:
                        return None

            found = [c for c in await asyncio.gather(*(one(s) for s in segs)) if c]
        finally:
            await sie.close()
        return {
            "corpus": str(corpus),
            "segments_hunted": len(segs),
            "llm_calls": budget_.llm_calls,
            "probe_runs": budget_.probe_runs,
            "claims": [json.loads(c.model_dump_json()) for c in found],
        }

    out.mkdir(parents=True, exist_ok=True)
    result = asyncio.run(_run())
    (out / "results.json").write_text(json.dumps(result, indent=2))
    verdicts: dict[str, int] = {}
    for c in result["claims"]:
        verdicts[c["verdict"]] = verdicts.get(c["verdict"], 0) + 1
    typer.echo(
        f"{result['segments_hunted']} segments → {len(result['claims'])} claims → {verdicts}"
    )
    from cantheria.swarm.report import write_audit_report

    write_audit_report(result, out / "REPORT.md", corpus)
    typer.echo(f"journal: {out / 'journal.jsonl'}  results: {out / 'results.json'}")
    typer.echo(f"report: {out / 'REPORT.md'}")


@app.command("audit-report")
def audit_report_cmd(
    results: Path = typer.Argument(..., help="results.json from `cantheria audit`"),
    out: Path = typer.Option(None, help="REPORT.md path (default: beside results)"),
    corpus: Path = typer.Option(None, help="records.db for deep-link receipts"),
) -> None:
    """Regenerate the markdown audit report from a results.json."""
    from cantheria.swarm.report import write_audit_report

    result = json.loads(results.read_text())
    dest = out or results.parent / "REPORT.md"
    db = corpus or Path(result.get("corpus", ""))
    write_audit_report(result, dest, db if db.exists() else None)
    typer.echo(f"report → {dest}")


if __name__ == "__main__":
    app()
