"""Repo index — chunk code by symbol, embed with SIE, search + rerank.

Why chunk by function/class instead of lines: a vulnerability hypothesis is
about a *function* (its inputs, its sinks), and call-site context matters.
Line windows split the very thing the model is reasoning about.

numpy brute-force scoring is fine for hackathon-scale repos (a few thousand
chunks); no vector DB needed. The index is cached on disk keyed by model +
commit so re-runs are free.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from cantheria.settings import (  # noqa: F401  (CHAT_MODEL re-export convenience)
    CHAT_MODEL,
    EMBED_MODEL,
)
from cantheria.sie import SIEClient

SOURCE_GLOBS = ("*.py", "*.js", "*.ts", "*.go", "*.c", "*.h", "*.cpp", "*.rs", "*.java", "*.rb")
SKIP_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "target",
    "dist",
    "build",
    "__pycache__",
    "tests",
}
MAX_CHUNK_CHARS = 6000

_LANG_PATTERNS: dict[str, re.Pattern[str]] = {
    ".py": re.compile(r"^(?:async\s+)?(?:def|class)\s+(\w+)", re.MULTILINE),
    ".js": re.compile(
        r"^(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:function|\())",
        re.MULTILINE,
    ),
    ".ts": re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.MULTILINE),
    ".go": re.compile(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)", re.MULTILINE),
    ".c": re.compile(r"^\w[\w\s\*]*?\b(\w+)\s*\([^;]*\)\s*\{", re.MULTILINE),
    ".h": re.compile(r"^\w[\w\s\*]*?\b(\w+)\s*\(", re.MULTILINE),
    ".cpp": re.compile(r"^(?:\w+::)?\w[\w\s\*]*?\b(\w+)\s*\([^;]*\)\s*\{", re.MULTILINE),
    ".rs": re.compile(r"^(?:pub\s+)?(?:async\s+)?fn\s+(\w+)", re.MULTILINE),
    ".java": re.compile(
        r"^(?:public|private|protected)[\w\s]*?\b(\w+)\s*\([^)]*\)\s*\{", re.MULTILINE
    ),
    ".rb": re.compile(r"^\s*def\s+(\w+)", re.MULTILINE),
}


@dataclass(frozen=True)
class Chunk:
    key: str  # sha1 of text — stable id across runs
    path: str  # repo-relative
    symbol: str  # function/class name, or "<file>" for whole-file chunks
    start_line: int
    text: str

    @property
    def header(self) -> str:
        return f"# {self.path}:{self.symbol} (line {self.start_line})"


def _python_chunks(rel: str, src: str) -> list[Chunk]:
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return _fallback_chunks(rel, src)
    lines = src.splitlines()
    out: list[Chunk] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            end = getattr(node, "end_lineno", node.lineno)
            seg = "\n".join(lines[node.lineno - 1 : end])
            if len(seg) > MAX_CHUNK_CHARS:
                seg = seg[:MAX_CHUNK_CHARS] + "\n... [truncated]"
            out.append(_mk(rel, node.name, node.lineno, seg))
    return out or _fallback_chunks(rel, src)


def _fallback_chunks(rel: str, src: str) -> list[Chunk]:
    pat = _LANG_PATTERNS.get(Path(rel).suffix)
    lines = src.splitlines()
    if pat:
        marks = [
            (m.start(), (m.group(1) or "anon"))
            for m in pat.finditer(src)
            if m.group(0)
            .lstrip()
            .startswith(
                (
                    "def",
                    "fn",
                    "func",
                    "function",
                    "pub",
                    "public",
                    "private",
                    "protected",
                    "async",
                    "class",
                    "const",
                    "let",
                    "var",
                )
            )
            or "." not in m.group(0)
        ]
        if marks:
            out, cur_line = [], 1
            for pos, name in marks:
                ln = src.count("\n", 0, pos) + 1
                seg = "\n".join(lines[cur_line - 1 : ln - 1]) or "\n".join(lines[:80])
                if seg.strip():
                    out.append(_mk(rel, name, cur_line, seg[:MAX_CHUNK_CHARS]))
                cur_line = ln
            tail = "\n".join(lines[cur_line - 1 :])
            if tail.strip():
                out.append(_mk(rel, "<file>", cur_line, tail[:MAX_CHUNK_CHARS]))
            return out
    win = 80
    return [
        _mk(rel, "<file>", i + 1, "\n".join(lines[i : i + win])) for i in range(0, len(lines), win)
    ]


def _mk(rel: str, symbol: str, start: int, text: str) -> Chunk:
    key = hashlib.sha1(f"{rel}:{start}:{text}".encode(), usedforsecurity=False).hexdigest()[:16]
    return Chunk(key=key, path=rel, symbol=symbol, start_line=start, text=text)


def iter_sources(root: Path) -> list[Path]:
    files: list[Path] = []
    for glob in SOURCE_GLOBS:
        for p in root.glob(f"**/{glob}"):
            if not (set(p.relative_to(root).parts) & SKIP_DIRS) and p.is_file():
                files.append(p)
    return sorted(files)


def chunk_repo(root: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in iter_sources(root):
        rel = str(path.relative_to(root))
        try:
            src = path.read_text(errors="replace")
        except OSError:
            continue
        if not src.strip():
            continue
        chunks.extend(
            _python_chunks(rel, src) if path.suffix == ".py" else _fallback_chunks(rel, src)
        )
    return chunks


class RepoIndex:
    def __init__(self, chunks: list[Chunk], vectors: np.ndarray) -> None:
        self.chunks = chunks
        self._vectors = vectors / (np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-9)
        # symbol name -> defining chunks. The cheap call graph: name equality,
        # not resolution — collisions just mean an occasional extra context
        # slice, which costs tokens, never correctness.
        self._by_symbol: dict[str, list[Chunk]] = {}
        for c in chunks:
            if c.symbol != "<file>":
                self._by_symbol.setdefault(c.symbol, []).append(c)

    def related(self, chunk: Chunk, k: int = 4) -> list[Chunk]:
        """Bounded caller/callee neighbourhood for one chunk.

        Callees: symbols this chunk's text invokes, resolved to their
        definitions. Callers: chunks whose text invokes this chunk's symbol.
        Name-based on purpose — approximate reachability is enough to give the
        hypothesis the preconditions and sinks one hop away. Ranked so same-dir
        neighbours and shorter (more legible) snippets come first.
        """
        if chunk.symbol == "<file>":
            symbol_re = None
        else:
            symbol_re = re.compile(rf"\b{re.escape(chunk.symbol)}\s*\(")

        callees: list[Chunk] = []
        for name, defs in self._by_symbol.items():
            if name == chunk.symbol:
                continue
            if re.search(rf"\b{re.escape(name)}\s*\(", chunk.text):
                callees.extend(d for d in defs if d.key != chunk.key)

        callers = [
            c
            for c in self.chunks
            if c.key != chunk.key and symbol_re is not None and symbol_re.search(c.text)
        ]

        def _rank(c: Chunk) -> tuple[int, int]:
            same_dir = 0 if Path(c.path).parent == Path(chunk.path).parent else 1
            return (same_dir, len(c.text))

        out, seen = [], {chunk.key}
        for c in sorted(callees, key=_rank) + sorted(callers, key=_rank):
            if c.key not in seen:
                seen.add(c.key)
                out.append(c)
            if len(out) >= k:
                break
        return out

    @classmethod
    async def build(cls, root: Path, sie: SIEClient, batch: int = 64) -> RepoIndex:
        chunks = chunk_repo(root)
        if not chunks:
            raise ValueError(f"no source files found under {root}")
        vecs: list[list[float]] = []
        for i in range(0, len(chunks), batch):
            texts = [c.header + "\n" + c.text for c in chunks[i : i + batch]]
            vecs.extend(await sie.embed(EMBED_MODEL, texts))
        return cls(chunks, np.array(vecs, dtype=np.float32))

    def search(self, query_vec: list[float] | np.ndarray, k: int = 12) -> list[tuple[Chunk, float]]:
        q = np.asarray(query_vec, dtype=np.float32)
        q = q / (np.linalg.norm(q) + 1e-9)
        sims = self._vectors @ q
        order = np.argsort(-sims)[:k]
        return [(self.chunks[i], float(sims[i])) for i in order]

    async def find(
        self,
        sie: SIEClient,
        query: str,
        k: int = 12,
        rerank: bool = True,
        rerank_model: str = "Qwen/Qwen3-Reranker-4B",
    ) -> list[tuple[Chunk, float]]:
        """Semantic top-k, optionally reranked. Rerank on ~2k chars of context
        around the hit beats raw cosine for picking *the* function you meant."""
        [qv] = await sie.embed(EMBED_MODEL, [query])
        hits = self.search(qv, k=min(k * 3, len(self.chunks)) if rerank else k)
        if not rerank:
            return hits[:k]
        docs = [c.header + "\n" + c.text[:2000] for c, _ in hits]
        ranked = await sie.rerank(rerank_model, query, docs, top_n=k)
        return [(hits[i][0], float(score)) for i, score in ranked]

    def get(self, key: str) -> Chunk | None:
        return next((c for c in self.chunks if c.key == key), None)

    def save(self, path: Path) -> None:
        """Cache format: <path>.npy vectors + <path>.jsonl chunk metadata.
        Plain files — no pickle, nothing executes on load."""
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path.with_suffix(".npy"), self._vectors)
        with path.with_suffix(".jsonl").open("w") as f:
            for c in self.chunks:
                f.write(json.dumps(c.__dict__) + "\n")

    @classmethod
    def load(cls, path: Path) -> RepoIndex:
        vectors = np.load(path.with_suffix(".npy"))
        chunks = [json.loads(line) for line in path.with_suffix(".jsonl").read_text().splitlines()]
        return cls([Chunk(**c) for c in chunks], vectors)
