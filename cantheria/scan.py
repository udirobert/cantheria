"""End-to-end scan: repo in → confirmed findings + maintainer report out.

Prioritisation is the whole game on a one-day budget. We rank chunks with
a cheap blast-radius heuristic (does this code touch untrusted input, sinks,
crypto, parsing?) then let SIE similarity confirm it, and hunt top-down until
the budget dies. Random chunks are a lottery; entry points are a pattern.
"""

from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from cantheria.dedup import dedup
from cantheria.fence import FenceHit
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


# `git clone` is a code executor wearing a URL costume. `ext::sh -c '...'` runs
# on our machine before a single byte of source is read, and an argument that
# starts with `-` is parsed as an option, not a repo. This is the one place in
# the pipeline where an attacker-controlled string reaches argv instead of the
# model — so it gets an allowlist, and the fence's logic does not apply here.
_CLONE_URL = re.compile(r"^(?:https?://|git://|ssh://|[\w.-]+@[\w.-]+:)", re.I)


async def clone(url_or_path: str, dest: Path) -> Path:
    src = Path(url_or_path)
    # "" normalizes to Path(".") which always exists — a bare empty string
    # must hit the URL check below, not silently adopt the cwd as the target.
    if url_or_path.strip() and src.exists():
        return src.resolve()
    if not _CLONE_URL.match(url_or_path):
        raise ValueError(
            f"refusing to clone {url_or_path!r}: only http(s)://, git://, ssh:// or scp-style "
            "URLs are accepted (local paths are used directly)"
        )
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run(  # noqa: S603
        [  # noqa: S607
            "git",
            "-c",
            "protocol.ext.allow=never",
            # `git clone` checks out a working tree, and checkout runs the
            # repo's own post-checkout hook. That is RCE by URL, before we have
            # read a line of it. Point hooksPath at a directory that does not
            # exist instead of trusting whatever the target ships.
            "-c",
            "core.hooksPath=/nonexistent.cantheria-hooks",
            "clone",
            "--depth",
            "1",
            "--",
            url_or_path,
            str(dest),
        ],
        check=True,
    )
    return dest


def _prefetch(repo_root: Path) -> str:
    """Download dependency manifests' contents so network-jailed PoCs can
    build. Only *fetch* commands run here — `cargo fetch` and
    `npm ci --ignore-scripts` download bytes; they do NOT run build.rs or
    postinstall hooks, which would be unconfined repo-code execution.
    """
    did: list[str] = []

    def _try(argv: list[str]) -> bool:
        try:
            return (
                subprocess.run(  # noqa: S603
                    argv,
                    cwd=repo_root,
                    timeout=900,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                ).returncode
                == 0
            )
        except (OSError, subprocess.TimeoutExpired):
            return False

    if (repo_root / "Cargo.toml").exists() and _try(["cargo", "fetch", "--locked"]):
        did.append("cargo")
    js = repo_root / "package.json"
    if js.exists():
        if (repo_root / "pnpm-lock.yaml").exists():
            ok = _try(["pnpm", "install", "--frozen-lockfile", "--ignore-scripts"])
        elif (repo_root / "package-lock.json").exists():
            ok = _try(["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"])
        else:
            ok = _try(["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund"])
        if ok:
            did.append("node")
    return ",".join(did) or "none"


def _diff_scope(repo_root: Path, base: str) -> tuple[set[str], str]:
    """Delta review: files changed between `base` and HEAD + a focus preamble.

    Big Sleep's SQLite find and AIxCC delta-mode both say diff-seeded hunting
    outperforms unconstrained sweeps — the change supplies the theory, the
    model looks for what it introduced *and* the variants it missed.
    """
    subprocess.run(  # noqa: S603
        ["git", "-C", str(repo_root), "fetch", "--depth", "1", "origin", base],  # noqa: S607
        check=True,
        capture_output=True,
        timeout=180,
    )
    names = subprocess.run(  # noqa: S603
        ["git", "-C", str(repo_root), "diff", "--name-only", "FETCH_HEAD", "HEAD"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    stat = subprocess.run(  # noqa: S603
        ["git", "-C", str(repo_root), "diff", "--stat", "FETCH_HEAD", "HEAD"],  # noqa: S607
        check=False,
        capture_output=True,
        text=True,
    ).stdout[-3000:]
    msg = subprocess.run(  # noqa: S603
        ["git", "-C", str(repo_root), "log", "-1", "--format=%s", "FETCH_HEAD"],  # noqa: S607
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    focus = (
        f"DELTA REVIEW — the audit is scoped to files changed between base "
        f"'{base}' ({msg or 'unknown commit'}) and HEAD. Prioritise bugs "
        f"INTRODUCED by these changes, and variants of the same defect the "
        f"change missed nearby.\nChanged files ({len(names)}):\n"
        + "\n".join(f"  {n}" for n in names[:80])
        + f"\n{stat}"
    )
    return set(names), focus


@dataclass
class ScanResult:
    repo: str
    findings: list[Finding] = field(default_factory=list)
    budget: HuntBudget = field(default_factory=HuntBudget)
    journal_path: Path | None = None
    fence_hits: list[FenceHit] = field(default_factory=list)
    merged: int = 0  # duplicate reports avoided, not bugs removed
    prefetched: str = ""  # dep ecosystems fetched for sandboxed builds


async def scan(
    repo: str,
    out_dir: Path,
    *,
    max_chunks: int = 120,
    concurrency: int = 4,
    budget: HuntBudget | None = None,
    fence_enabled: bool = True,
    diff_base: str = "",
) -> ScanResult:
    out_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="cantheria-scan-", dir=out_dir))
    repo_root = await clone(repo, work / "src")
    # Clones land in work/"src" — recover the real repo name from the URL so
    # findings say "vibe-kanban", not "src". Local paths already have one.
    name = (
        Path(repo.rstrip("/").removesuffix(".git")).name
        if repo_root.name == "src"
        else repo_root.name
    ) or "src"

    # Delta mode: scope the hunt to files changed vs a base ref.
    changed: set[str] | None = None
    focus = ""
    if diff_base and (repo_root / ".git").exists():
        try:
            changed, focus = _diff_scope(repo_root, diff_base)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            focus = ""
            changed = None
            print(f"diff scope failed ({exc}); falling back to full scan")

    # Fetch deps up front so network-jailed PoCs can still compile/run.
    # Fetch-only commands — no build.rs, no postinstall, see _prefetch.
    prefetched = _prefetch(repo_root)

    sie = SIEClient()
    journal = Journal(out_dir / "journal.jsonl")
    result = ScanResult(
        repo=name,
        budget=budget or HuntBudget(),
        journal_path=journal.path,
        prefetched=prefetched,
    )
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
        if changed is not None:
            ordered = [c for c in ordered if c.path in changed]
        targets = ordered[:max_chunks]

        oracle = LocalOracle()
        sem = asyncio.Semaphore(concurrency)

        async def one(chunk: Chunk) -> Finding | None:
            async with sem:
                if result.budget.spent:
                    return None
                try:
                    return await hunt_chunk(
                        chunk,
                        sie,
                        oracle,
                        journal,
                        result.budget,
                        name,
                        repo_root,
                        fence_sink=result.fence_hits,
                        fence_enabled=fence_enabled,
                        index=index,
                        focus=focus,
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
        # One bug, one report — see dedup.py for why the merge rule is this tight.
        before = len(result.findings)
        result.findings = dedup(result.findings)
        result.merged = before - len(result.findings)
        result.findings.sort(key=lambda f: f.confidence, reverse=True)
    finally:
        await sie.close()
        shutil.rmtree(work, ignore_errors=True)
    return result
