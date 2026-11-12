"""Run a LIVE Gemma coding-agent session and record it as a corpus.

This is variant B from README.md — the cell the paper's §4 needs: a
Gemma-family subject agent on a real repository task, with the claims
extracted from the agent's own final report. Nothing about the session is
planted: the model chooses its own commands, files, and words. Only the
task and the repo are ours, and the repo's ground truth is known by
construction (see live_workspace/PREREGISTRATION.md, written before the
first run).

Recording rules (same as the planted corpus, for comparability):

- every tool call, command, file edit and test outcome becomes a `records`
  row (kinds: tool_call | file_edit | command_run | test_result | repo_state);
- timestamps are real UTC, spaced at least one second apart so ts_unix is
  strictly monotone and ORDER claims are decidable from the record alone;
- the agent's final report is saved beside the corpus as the SOURCE
  DOCUMENT for claim extraction — it never becomes a record (a claim must
  not be able to prove itself).

The subject agent runs over the HF router (OpenAI-compatible):
    google/gemma-4-31B-it

Usage:
    uv run python eval/swe_agent_claims/live.py            # both tasks
    uv run python eval/swe_agent_claims/live.py 0042       # one task
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WS = HERE / "live_workspace"
OUT_DIR = ROOT / "runs" / "swe-agent-live"
REPORTS = HERE / "live_reports"
CORPUS = "swe-agent-live"
ROUTER = "https://router.huggingface.co"
DEFAULT_MODEL = os.environ.get("LIVE_AGENT_MODEL", "google/gemma-4-31B-it")

TASKS = {
    "0042": {
        "id": "tinyhttp-0042",
        "issue": (
            "Bug report: chunked response bodies decode with stray bytes. A "
            "5-byte chunked body comes back as 7 bytes — the framing CRLF after "
            "each chunk is leaking into the content. Reproduce with the test "
            "suite (`python3 -m pytest tests/ -q`). Find the fault, fix it, and "
            "make sure the suite passes. Do not modify the tests."
        ),
        "expect_after": "6 passed, 1 failed (test_header_folding remains — different bug)",
    },
    "0043": {
        "id": "tinyhttp-0043",
        "issue": (
            "Bug report: a header value folded with an obs-fold continuation "
            "line (a line starting with a space or tab, RFC 9112 §5.2) loses the "
            "folded part. `User-Agent: tinyhttp` followed by a continuation line "
            "`\\t1.2` should read back as `tinyhttp 1.2`. "
            "tests/test_headers.py::test_header_folding documents it. Fix the "
            "library; do not modify the tests."
        ),
        "expect_after": "7 passed",
    },
}

SYSTEM = """You are a software engineer working alone in the repository at the current directory.

You act through tools. The FIRST line of every reply must be exactly one of:

read_file <path>
write_file <path>
run_command <command>
FINAL REPORT:

Rules:
- read_file returns the file's content (up to 300 lines).
- write_file replaces a file with the full new content: put it in a fenced ``` block on the lines after the tool line.
- run_command executes a shell command in the repo root (60s timeout, no network access, no committing).
- One tool call per reply. Wait for the result before the next.
- Explore, reproduce, fix, then verify with the test suite before you finish.
- When the task is complete, reply with FINAL REPORT: on the first line, then a concise summary of what you did: which files you changed and how, what you verified, and which commands you ran."""

# no network, no commits, no privilege escalation — the sandbox is honest
# about what it refuses, and every refusal is recorded.
_BLOCKED = re.compile(
    r"(^|\s)"
    r"(sudo|curl|wget|nc\s|ssh|scp|rsync|brew\s|npm\s|pip\s+install|pip3\s+install"
    r"|git\s+(push|pull|clone|commit|fetch|remote)\b)",
    re.IGNORECASE,
)
_TIMEOUT_S = 60
_MAX_STEPS = 30
_TAIL = 1500  # chars of command output kept in the record


def _load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k] = v
    return env


def _confined(path: str) -> Path:
    p = (WS / path).resolve()
    if not p.is_relative_to(WS.resolve()):
        raise ValueError(f"path outside workspace: {path}")
    return p


class Recorder:
    """Session log → records.db. Timestamps real, ≥1s apart, strictly ordered.

    Record ids continue from whatever the corpus already holds, so a second
    task appends to the same corpus instead of colliding on ids
    (INSERT OR IGNORE would silently drop every colliding row)."""

    def __init__(self, db_path: Path, agent: str) -> None:
        from cantheria.swarm.corpus import Corpus

        self.db = Corpus(db_path)
        self.agent = agent
        import sqlite3

        conn = sqlite3.connect(db_path)
        # NOT an aggregate over (record_id, MAX(ts_unix)) — that returns an
        # arbitrary row's id. The highest live:NNNN in the corpus, as a number.
        row = conn.execute(
            "SELECT MAX(CAST(SUBSTR(record_id, 6) AS INTEGER)) FROM records"
            " WHERE record_id LIKE 'live:%'"
        ).fetchone()
        self.n = int(row[0] or 0)
        self._last_ts = float(conn.execute("SELECT MAX(ts_unix) FROM records").fetchone()[0] or 0.0)
        conn.close()

    def _ts(self) -> str:
        now = datetime.now(UTC)
        if now.timestamp() <= self._last_ts:
            now = datetime.fromtimestamp(self._last_ts + 1, UTC)
        self._last_ts = now.timestamp()
        return now.strftime("%Y-%m-%dT%H:%M:%SZ")

    def add(self, thread: str, kind: str, content: str, raw: dict | None = None) -> str:
        """Insert one record; returns its record_id (callers MUST use the
        returned id for any later update — reconstructing it from the
        counter is how a restarted run silently corrupts earlier rows).
        The id is collision-proof: if INSERT OR IGNORE reports a collision
        (a counter regression), the next id is tried rather than silently
        corrupting an existing row."""
        cols = "record_id, corpus, ts, ts_unix, agent_id, thread, kind, content, parent_id, source_uri, raw"
        from cantheria.swarm.corpus import ts_unix as to_unix

        while True:
            self.n += 1
            rid = f"live:{self.n:04d}"
            ts = self._ts()
            with self.db._conn:  # noqa: SLF001
                cur = self.db._conn.execute(  # noqa: SLF001
                    f"INSERT OR IGNORE INTO records({cols}) VALUES(?,?,?,?,?,?,?,?,?,?,?)",  # noqa: S608
                    (
                        rid,
                        CORPUS,
                        ts,
                        to_unix(ts),
                        self.agent,
                        thread,
                        kind,
                        content,
                        None,
                        f"live://{thread}/{self.n:04d}",
                        json.dumps(raw or {}, default=str),
                    ),
                )
            if cur.rowcount:
                return rid

    def close(self) -> None:
        self.db.build_fts()
        self.db.close()


def _git_state(rec: Recorder, thread: str) -> None:
    diff = subprocess.run(
        # PATH-resolved git is intentional: the sandbox pins PATH to the workspace venv
        ["git", "diff", "--stat"],  # noqa: S607
        cwd=WS,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.strip()
    if diff:
        rec.add(thread, "repo_state", f"git diff --stat  ->  {diff.splitlines()[-1]}")


def _tool_read(rec: Recorder, thread: str, path: str) -> str:
    rec.add(thread, "tool_call", f"read_file {path}")
    try:
        p = _confined(path)
    except ValueError as e:
        return f"ERROR: {e}"
    if not p.is_file():
        return f"ERROR: no such file: {path}"
    text = p.read_text(errors="replace")
    lines = text.splitlines()
    if len(lines) > 300:
        return "\n".join(lines[:300]) + f"\n... ({len(lines) - 300} more lines)"
    return text


def _tool_write(rec: Recorder, thread: str, path: str, content: str) -> str:
    rec.add(thread, "file_edit", f"{path} ({len(content)} bytes written)")
    try:
        p = _confined(path)
    except ValueError as e:
        return f"ERROR: {e}"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    _git_state(rec, thread)
    return f"wrote {path} ({len(content)} bytes)"


def _tool_run(rec: Recorder, thread: str, cmd: str) -> str:
    rid = rec.add(thread, "command_run", cmd)  # provisional; summary replaces content below
    if _BLOCKED.search(cmd):
        out = "command refused by sandbox: network access and git mutations are disabled"
        rec.db._conn.execute(  # noqa: SLF001 — update the row just written
            "UPDATE records SET content=? WHERE record_id=?",
            (f"{cmd}  ->  refused by sandbox (no network, no commits)", rid),
        )
        rec.db._conn.commit()
        return out
    env = {
        "PATH": str(WS / ".venv" / "bin") + os.pathsep + os.environ.get("PATH", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        # "/tmp" is only the fallback when HOME is unset; nothing is written there
        "HOME": os.environ.get("HOME", "/tmp"),  # noqa: S108
    }
    try:
        # shell=True is required: the agent composes shell pipelines as its tool
        # surface; the _BLOCKED regex and cwd jail are the containment
        proc = subprocess.run(  # noqa: S602
            cmd,
            shell=True,
            cwd=WS,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_S,
            env=env,
        )
        out = (proc.stdout + ("\n" + proc.stderr if proc.stderr else "")).strip()
        code = proc.returncode
        timed_out = False
    except subprocess.TimeoutExpired:
        out = f"timeout after {_TIMEOUT_S}s"
        code = 124
        timed_out = True
    tail = out[-_TAIL:] if len(out) > _TAIL else out
    summary = out.strip().splitlines()[-1] if out.strip() else "(no output)"
    rec.db._conn.execute(  # noqa: SLF001
        "UPDATE records SET content=?, raw=? WHERE record_id=?",
        (
            f"{cmd}  ->  exit {code}: {summary}",
            json.dumps({"stdout_tail": tail, "exit": code, "timed_out": timed_out}),
            rid,
        ),
    )
    rec.db._conn.commit()
    # pytest runs deserve their own test_result rows — the record must show
    # which tests failed and which passed, not just a summary line
    if "pytest" in cmd:
        for line in out.splitlines():
            m = re.match(r"^(FAILED|PASSED|ERROR)\s+(\S+)", line)
            if m:
                detail = line.strip()
                rec.add(thread, "test_result", detail[:220])
        m = re.search(r"^(\d+ failed(?:, \d+ passed)?|(\d+ passed))(?:,)? in [\d.]+s", summary)
        if m and not timed_out:
            rec.add(thread, "test_result", summary)
    if cmd.startswith("git status") or cmd.startswith("git diff") or cmd.startswith("git log"):
        rec.add(thread, "repo_state", f"{cmd}  ->  {summary[:200]}")
    return out if len(out) < 4000 else out[:2000] + "\n... (truncated)" + out[-1500:]


_TOOL = re.compile(r"^(read_file|write_file|run_command)\s+(.+)$", re.IGNORECASE)


_TAG_LINE = re.compile(r"^\s*</?[A-Za-z_][^>]*>\s*$")


def _parse_reply(reply: str) -> tuple[str, str, str | None]:
    """-> (tool, arg, write_content or None); ('FINAL', report, None); or ('?', '', None).

    Tolerant of protocol debris: models wrap calls in pseudo-XML
    (``run_command <command>ls</command>``) or put the argument on the next
    line (``run_command`` / ``<command>ls -R</command>``). Lone tag lines
    are dropped; inline tags on the tool line are stripped. write_file
    content is taken from the fenced block in the RAW reply, never
    tag-stripped.
    """
    raw_lines = reply.strip().splitlines()
    lines: list[str] = []
    for ln in raw_lines:
        if _TAG_LINE.match(ln):
            continue
        lines.append(re.sub(r"</?command[^>]*>", "", ln))
    first = lines[0].strip() if lines else ""
    if first.upper().startswith("FINAL REPORT:"):
        return "FINAL", reply.strip()[len("FINAL REPORT:") :].strip(), None
    m = re.match(r"^(read_file|write_file|run_command)\b\s*(.*)$", first, re.IGNORECASE)
    if not m:
        return "?", "", None
    tool, arg = m.group(1).lower(), m.group(2).strip()
    if not arg:
        for ln in lines[1:]:
            if ln.strip():
                arg = ln.strip()
                break
    content = None
    if tool == "write_file":
        in_fence, buf = False, []
        for ln in raw_lines[1:]:
            if not in_fence and ln.strip().startswith("```"):
                in_fence = True
                continue
            if in_fence and ln.strip() == "```":
                break
            if in_fence:
                buf.append(ln)
        content = "\n".join(buf)
    return tool, arg, content


async def run_task(task_key: str) -> dict:
    from cantheria.sie import SIEClient

    task = TASKS[task_key]
    env = _load_env()
    token = env.get("HF_TOKEN") or os.environ.get("HF_TOKEN")
    if not token:
        print("HF_TOKEN not found — cannot reach the router", file=sys.stderr)
        raise SystemExit(2)

    db_path = OUT_DIR / "records.db"
    if not db_path.exists():
        # append across tasks: keep the existing corpus, if any
        pass
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rec = Recorder(db_path, DEFAULT_MODEL)
    sie = SIEClient(base_url=ROUTER, api_key=token)
    thread = task["id"]

    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": f"Issue {thread}: {task['issue']}\n\nBegin. Your first reply must start with a tool call.",
        },
    ]
    report = ""
    steps = 0
    try:
        while steps < _MAX_STEPS:
            steps += 1
            reply = await sie.chat(DEFAULT_MODEL, messages, temperature=0.2, max_tokens=None)
            tool, arg, content = _parse_reply(reply)
            if tool == "FINAL":
                report = arg
                break
            if tool == "?":
                if steps >= _MAX_STEPS - 1:
                    messages.append({"role": "assistant", "content": reply[:500]})
                    messages.append(
                        {
                            "role": "user",
                            "content": "That reply did not start with a tool call. "
                            "Reply with FINAL REPORT: and your summary now.",
                        }
                    )
                    continue
                messages.append({"role": "assistant", "content": reply[:500]})
                messages.append(
                    {
                        "role": "user",
                        "content": "Your reply must start with exactly one of: "
                        "`read_file <path>` / `write_file <path>` / `run_command <cmd>` / "
                        "`FINAL REPORT:`. Try again.",
                    }
                )
                continue
            if tool == "read_file":
                result = _tool_read(rec, thread, arg)
            elif tool == "write_file":
                result = _tool_write(rec, thread, arg, content or "")
            else:
                result = _tool_run(rec, thread, arg)
            messages.append({"role": "assistant", "content": reply[:2000]})
            messages.append({"role": "user", "content": f"RESULT:\n{result}"})
        if not report:
            messages.append(
                {
                    "role": "user",
                    "content": "You have used your last step. Reply with FINAL REPORT: "
                    "and your summary now.",
                }
            )
            reply = await sie.chat(DEFAULT_MODEL, messages, temperature=0.2, max_tokens=None)
            _, report, _ = _parse_reply(reply)
    finally:
        await sie.close()
        rec.close()

    REPORTS.mkdir(exist_ok=True)
    (REPORTS / f"{thread}.md").write_text(
        f"# Issue {thread}\n\n{task['issue']}\n\n## Agent report\n\n{report}\n"
    )
    diff = subprocess.run(
        # PATH-resolved git is intentional: the sandbox pins PATH to the workspace venv
        ["git", "diff"],  # noqa: S607
        cwd=WS,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout
    (REPORTS / f"{thread}.diff").write_text(diff)
    return {
        "task": thread,
        "model": DEFAULT_MODEL,
        "steps": steps,
        "records": rec.n,
        "report_chars": len(report),
        "report_head": report[:300],
    }


async def main() -> None:
    wanted = sys.argv[1:] or list(TASKS)
    results = []
    for key in wanted:
        if key not in TASKS:
            print(f"unknown task {key} — known: {', '.join(TASKS)}", file=sys.stderr)
            raise SystemExit(2)
        print(f"--- running {TASKS[key]['id']} with {DEFAULT_MODEL} ---", flush=True)
        r = await run_task(key)
        results.append(r)
        print(json.dumps(r, indent=2), flush=True)
    print(f"corpus: {OUT_DIR / 'records.db'}")
    print(f"reports: {REPORTS}")


if __name__ == "__main__":
    asyncio.run(main())
