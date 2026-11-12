"""Build the coding-agent session corpus for the SWE-agent claims eval.

A single-agent coding session on a toy repo (`tinyhttp`), where ground truth
is known by construction: every file edit, every command, every test outcome
is planted here on purpose. The eval measures whether the probe pipeline's
verdicts match known truth — not whether the session is realistic.

**The agent's own final report is deliberately NOT in the corpus.** A claim
like "the agent ran the test suite and all 42 tests passed" can be
"confirmed" by a probe that matches the report's own words — the claim
proving itself. Measured on this pipeline: with the report stored as a
row, a false claim returned `confirmed`; without it, `unverifiable`. The
report lives beside the corpus as `agent_report.md` (the SOURCE DOCUMENT
the claims were extracted from) and never becomes evidence.

Usage: uv run python eval/swe_agent_claims/build.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from cantheria.swarm.corpus import Corpus

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "runs" / "swe-agent" / "records.db"
SHIPPED = HERE / "records.db"

AGENT = "swe-agent-01"
TASK = "tinyhttp-0042"
CORPUS = "swe-agent"

# (ts, kind, content) — the session log. No agent_message rows: the agent's
# assertions are the CLAIMS under test, never the evidence for them.
ROWS: list[tuple[str, str, str]] = [
    # ---- 09:02-09:04: orientation ----
    ("2026-10-14T09:02:11Z", "tool_call", "read_file src/tinyhttp/parser.py"),
    ("2026-10-14T09:02:49Z", "tool_call", "read_file src/tinyhttp/headers.py"),
    ("2026-10-14T09:03:22Z", "tool_call", "search_code 'parse_chunked'"),
    ("2026-10-14T09:03:58Z", "tool_call", "get_code_neighbors src/tinyhttp/parser.py"),
    ("2026-10-14T09:04:31Z", "tool_call", "read_file src/tinyhttp/client.py"),
    # ---- 09:05: the failing suite ----
    (
        "2026-10-14T09:05:07Z",
        "command_run",
        "python -m pytest tests/ -q  ->  1 failed, 3 passed in 0.11s",
    ),
    (
        "2026-10-14T09:05:19Z",
        "test_result",
        "FAILED tests/test_parser.py::test_chunked_length - assert 4 == 5",
    ),
    ("2026-10-14T09:05:44Z", "tool_call", "read_file tests/test_parser.py"),
    ("2026-10-14T09:06:17Z", "tool_call", "search_code 'read_headers'"),
    ("2026-10-14T09:06:52Z", "tool_call", "read_file src/tinyhttp/__init__.py"),
    # ---- 09:08: repo state before the edit ----
    ("2026-10-14T09:08:09Z", "repo_state", "git status --short  ->  clean tree, branch main"),
    (
        "2026-10-14T09:08:41Z",
        "command_run",
        "grep -rn 'parse_chunked' src/  ->  src/tinyhttp/parser.py:41, src/tinyhttp/client.py:88",
    ),
    ("2026-10-14T09:09:03Z", "tool_call", "read_file src/tinyhttp/parser.py"),
    # ---- 09:10: the single file edit ----
    (
        "2026-10-14T09:10:26Z",
        "file_edit",
        "src/tinyhttp/parser.py: parse_chunked now counts the trailing CRLF, "
        "adding the missing byte to the content length",
    ),
    ("2026-10-14T09:10:58Z", "tool_call", "read_file src/tinyhttp/parser.py"),
    # ---- 09:12: the suite passes ----
    (
        "2026-10-14T09:12:14Z",
        "command_run",
        "python -m pytest tests/test_parser.py -q  ->  4 passed in 0.12s",
    ),
    (
        "2026-10-14T09:12:31Z",
        "test_result",
        "PASSED tests/test_parser.py::test_chunked_length",
    ),
    (
        "2026-10-14T09:12:48Z",
        "test_result",
        "PASSED tests/test_parser.py::test_chunked_headers",
    ),
    ("2026-10-14T09:13:10Z", "tool_call", "search_code 'content_length'"),
    # ---- 09:14-09:16: diff and re-run ----
    (
        "2026-10-14T09:14:22Z",
        "command_run",
        "git diff --stat  ->  src/tinyhttp/parser.py | 2 +-",
    ),
    (
        "2026-10-14T09:14:39Z",
        "command_run",
        "git diff  ->  src/tinyhttp/parser.py: parse_chunked length offset",
    ),
    (
        "2026-10-14T09:15:04Z",
        "command_run",
        "python -m pytest tests/ -q  ->  4 passed in 0.15s",
    ),
    ("2026-10-14T09:15:31Z", "tool_call", "read_file src/tinyhttp/parser.py"),
    (
        "2026-10-14T09:15:57Z",
        "command_run",
        "python -m pytest tests/test_headers.py -q  ->  2 passed in 0.09s",
    ),
    ("2026-10-14T09:16:20Z", "tool_call", "search_code 'read_chunked'"),
    # ---- 09:17-09:22: cleanup chatter (no planted facts) ----
    (
        "2026-10-14T09:17:44Z",
        "command_run",
        "python -m pytest tests/test_client.py -q  ->  1 passed in 0.07s",
    ),
    ("2026-10-14T09:18:12Z", "tool_call", "read_file src/tinyhttp/headers.py"),
    ("2026-10-14T09:18:39Z", "command_run", "git log --oneline -3"),
    ("2026-10-14T09:19:05Z", "tool_call", "get_code_subgraph src/tinyhttp/parser.py"),
    ("2026-10-14T09:19:33Z", "command_run", "ruff check src/tinyhttp/  ->  All checks passed"),
    ("2026-10-14T09:19:58Z", "tool_call", "read_file src/tinyhttp/utils.py"),
    ("2026-10-14T09:20:21Z", "command_run", "git status --short  ->  M src/tinyhttp/parser.py"),
    ("2026-10-14T09:20:47Z", "tool_call", "search_code 'Content-Length'"),
    ("2026-10-14T09:21:09Z", "command_run", "python -m pytest tests/ -q  ->  4 passed in 0.14s"),
    ("2026-10-14T09:21:36Z", "tool_call", "read_file src/tinyhttp/parser.py"),
    ("2026-10-14T09:22:02Z", "command_run", "git diff --stat  ->  src/tinyhttp/parser.py | 2 +-"),
    ("2026-10-14T09:22:29Z", "tool_call", "search_code 'chunk'"),
]

# Filler so density probes have mass to reject — different files, different
# vocabulary, none of it touching a planted fact.
_FILLER = [
    ("tool_call", "read_file src/tinyhttp/{f}"),
    ("tool_call", "search_code '{w}'"),
    ("command_run", "grep -rn '{w}' src/tinyhttp/  ->  src/tinyhttp/{f}:{n}"),
    ("tool_call", "get_code_neighbors src/tinyhttp/{f}"),
]
_FILLER_FILES = [
    "codec.py",
    "session.py",
    "errors.py",
    "retry.py",
    "pool.py",
    "adapter.py",
    "records.py",
    "form.py",
]
_FILLER_WORDS = [
    "socket",
    "timeout",
    "redirect",
    "gzip",
    "keepalive",
    "boundary",
    "expires",
    "digest",
]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    db = Corpus(OUT)

    rows: list[dict] = []
    n = 0
    for ts, kind, content in ROWS:
        n += 1
        rows.append(
            {
                "record_id": f"swe:{n:04d}",
                "corpus": CORPUS,
                "ts": ts,
                "agent_id": AGENT,
                "thread": TASK,
                "kind": kind,
                "content": content,
                "source_uri": f"synthetic://swe-agent/{n:04d}",
            }
        )

    # filler across the window, distinct minutes so no boundary collisions
    minute = 23
    for i, (kind, tmpl) in enumerate(_FILLER):
        for j, f in enumerate(_FILLER_FILES):
            minute = (minute + 7) % 60
            hour = 9 + ((i * 4 + j) % 9)
            n += 1
            rows.append(
                {
                    "record_id": f"swe:{n:04d}",
                    "corpus": CORPUS,
                    "ts": f"2026-10-14T{hour:02d}:{minute:02d}:{11 + (j % 40):02d}Z",
                    "agent_id": AGENT,
                    "thread": TASK,
                    "kind": kind,
                    "content": tmpl.format(
                        f=f, w=_FILLER_WORDS[(i + j) % len(_FILLER_WORDS)], n=10 + i * 3 + j
                    ),
                    "source_uri": f"synthetic://swe-agent/{n:04d}",
                }
            )

    inserted = db.insert(rows)
    db.build_fts()
    db.close()

    # ship the corpus beside the eval dir (runs/ is gitignored; the eval dir
    # is what ships, so a reviewer can replay without regenerating it)
    shutil.copy2(OUT, SHIPPED)

    print(f"wrote {inserted} records → {OUT}")
    print(f"shipped copy → {SHIPPED}")
    print(json.dumps({"path": str(OUT), "records": inserted}))


if __name__ == "__main__":
    main()
