"""End-to-end scan: repo in → confirmed findings + maintainer report out.

Prioritisation is the whole game on a one-day budget. We rank chunks with
a cheap blast-radius heuristic (does this code touch untrusted input, sinks,
crypto, parsing?) then let SIE similarity confirm it, and hunt top-down until
the budget dies. Random chunks are a lottery; entry points are a pattern.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from cantheria.hunt import HuntBudget, hunt_chunk
from cantheria.index import Chunk, RepoIndex
from cantheria.journal import Journal
from cantheria.oracle import LocalOracle
from cantheria.schemas import Finding
from cantheria.settings import EMBED_MODEL
from cantheria.sie import SIEClient

# Detection surface only — these strings are searched FOR, never executed.
SINK_HINTS = (
    "eval(",
    "exec(",
    "pickle",
    "subprocess",
    "os.system",
    "shell=True",
    "scanf",
    "strcpy",
    "strcat",
    "sprintf",
    "memcpy",
    "malloc",
    "realloc",
    "MD5",
    "SHA1",
    "ECB",
    "verify=False",
    "ssl.",
    "md5(",
    "sha1(",
    "query(",
    "execute(",
    "cursor",
    "format(",
    'f"',
    "render_template_string",
    "yaml.load",
    "torch.load",
    "unsafe",
    "deserial",
    "unserialize",
)
INPUT_HINTS = (
    "request",
    "param",
    "args",
    "argv",
    "input",
    "read",
    "recv",
    "parse",
    "decode",
    "load",
    "upload",
    "header",
    "cookie",
    "body",
    "url",
    "path",
    "user",
    "client",
    "socket",
    "file",
    "stream",
    "buf",
)
SEED_QUERY = (
    "function that parses, decodes, or deserializes untrusted external input "
    "and passes it to a dangerous sink without validation"
)


def rank_score(chunk: Chunk) -> float:
    """Cheap lexical blast-radius prior. Deliberately crude — the model does
    the reasoning; this only decides the order we feed it."""
    text = chunk.text
    hits = sum(text.count(h) for h in SINK_HINTS) * 2.0
    hits += sum(text.count(h.lower()) for h in INPUT_HINTS) * 1.0
    sym = chunk.symbol.lower()
    if any(k in sym for k in ("parse", "load", "decode", "read", "accept", "handle", "recv")):
        hits += 3.0
    hits += min(len(text) / 1000, 4.0) * 0.5  # bigger surface, more to hide
    return hits


async def clone(url_or_path: str, dest: Path) -> Path:
    src = Path(url_or_path)
    if src.exists():
        return src
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "--depth", "1", url_or_path, str(dest)], check=True)  # noqa: S607, S603
    return dest


@dataclass
class ScanResult:
    repo: str
    findings: list[Finding] = field(default_factory=list)
    budget: HuntBudget = field(default_factory=HuntBudget)
    journal_path: Path | None = None


async def scan(
    repo: str,
    out_dir: Path,
    *,
    max_chunks: int = 120,
    concurrency: int = 4,
    budget: HuntBudget | None = None,
) -> ScanResult:
    out_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="cantheria-scan-", dir=out_dir))
    repo_root = await clone(repo, work / "src")
    name = repo_root.name

    sie = SIEClient()
    journal = Journal(out_dir / "journal.jsonl")
    result = ScanResult(repo=name, budget=budget or HuntBudget(), journal_path=journal.path)
    try:
        cache = out_dir / "index"
        index_path = cache / f"{name}.index"
        if index_path.with_suffix(".npy").exists():
            index = RepoIndex.load(index_path)
        else:
            index = await RepoIndex.build(repo_root, sie)
            cache.mkdir(exist_ok=True)
            index.save(index_path)

        ranked = sorted(index.chunks, key=rank_score, reverse=True)
        [qv] = await sie.embed(EMBED_MODEL, [SEED_QUERY])
        semantic = dict((c.key, s) for c, s in index.search(qv, k=min(300, len(index.chunks))))
        lexical_max = max((rank_score(c) for c in ranked), default=1.0) or 1.0
        # blend: lexical prior decides, semantic similarity breaks ties
        ordered = sorted(
            ranked,
            key=lambda c: rank_score(c) / lexical_max + semantic.get(c.key, 0.0),
            reverse=True,
        )
        targets = ordered[:max_chunks]

        oracle = LocalOracle()
        sem = asyncio.Semaphore(concurrency)

        async def one(chunk: Chunk) -> Finding | None:
            async with sem:
                if result.budget.spent:
                    return None
                try:
                    return await hunt_chunk(
                        chunk, sie, oracle, journal, result.budget, name, repo_root
                    )
                except Exception as exc:  # noqa: BLE001 — one bad chunk must not kill the scan
                    journal.path.open("a").write(
                        f'{{"event": "error", "detail": {{"message": {str(exc)!r}}}}}\n'
                    )
                    return None

        for coro in asyncio.as_completed([one(c) for c in targets]):
            f = await coro
            if f:
                result.findings.append(f)
        result.findings.sort(key=lambda f: f.confidence, reverse=True)
    finally:
        await sie.close()
        shutil.rmtree(work, ignore_errors=True)
    return result
