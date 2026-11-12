"""External-cell live session: Gemma 4 on a repository the author did not write.

psf/requests @ 36453b95 (SWE-bench Lite instance psf__requests-3362). The
workspace is a working tree with no .git, so no history or remote can
reveal the fix. The oracle is frozen at cantheria 896ae56 — see
PREREGISTRATION.md, committed before this session ran.

Record kinds match the live cell: tool_call | file_edit | command_run |
test_result | repo_state. The agent's final report is the source document
for claim extraction; it never becomes a record.

Usage:
    python3 eval/swe_agent_external/live_ext.py
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
WS = Path(os.environ.get("EXT_WS", "/tmp/reqext_ws"))  # noqa: S108
PY = os.environ.get("EXT_PYTHON", "/tmp/reqext38/bin/python")  # noqa: S108
OUT_DIR = ROOT / "runs" / "swe-agent-ext"
WORKSPACE_VENV = WS / ".venv"
REPORTS = HERE / "ext_reports"
CORPUS = "swe-agent-ext"
ROUTER = "https://router.huggingface.co"
MODEL = "google/gemma-4-31B-it"

ISSUE = (
    "Issue psf/requests#3362 — Uncertain about content/text vs "
    "iter_content(decode_unicode=True/False):\n\n"
    "When requesting an application/json document, I'm seeing "
    "next(r.iter_content(16*1024, decode_unicode=True)) returning bytes, "
    "whereas r.text returns unicode. My understanding was that both should "
    "return a unicode object. In essence, I thought 'iter_content' was "
    "equivalent to 'iter_text' when decode_unicode was True. Have I "
    "misunderstood something?\n\n"
    "For reference, I'm using python 3.5.1 and requests 2.10.0.\n\n"
    "Task: reproduce the behaviour, find the fault, fix it, and verify "
    "with the repository's own test suite. You must not modify any test "
    "file. Finish with FINAL REPORT:"
)

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

_BLOCKED = re.compile(
    r"(^|\s)"
    r"(sudo|curl|wget|nc\s|ssh|scp|rsync|brew\s|npm\s|pip\s+install|pip3\s+install"
    r"|git\s+(push|pull|clone|commit|fetch|remote)\b)",
    re.IGNORECASE,
)
_TIMEOUT_S = 60
_MAX_STEPS = 60
_TAIL = 1500


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
    def __init__(self, db_path: Path, agent: str) -> None:
        from cantheria.swarm.corpus import Corpus

        db_path.parent.mkdir(parents=True, exist_ok=True)
        if db_path.exists():
            db_path.unlink()
        self.db = Corpus(db_path)
        self.agent = agent
        self.n = 0
        self._last_ts = 0.0

    def _ts(self) -> str:
        now = datetime.now(UTC)
        if now.timestamp() <= self._last_ts:
            now = datetime.fromtimestamp(self._last_ts + 1, UTC)
        self._last_ts = now.timestamp()
        return now.strftime("%Y-%m-%dT%H:%M:%SZ")

    def add(self, thread: str, kind: str, content: str, raw: dict | None = None) -> str:
        from cantheria.swarm.corpus import ts_unix as to_unix

        self.n += 1
        rid = f"ext:{self.n:04d}"
        ts = self._ts()
        cols = "record_id, corpus, ts, ts_unix, agent_id, thread, kind, content, parent_id, source_uri, raw"
        with self.db._conn:  # noqa: SLF001
            self.db._conn.execute(  # noqa: SLF001
                f"INSERT INTO records({cols}) VALUES(?,?,?,?,?,?,?,?,?,?,?)",  # noqa: S608
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
                    f"ext://{thread}/{self.n:04d}",
                    json.dumps(raw or {}, default=str),
                ),
            )
        return rid

    def close(self) -> None:
        self.db.build_fts()
        self.db.close()


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
    return f"wrote {path} ({len(content)} bytes)"


def _tool_run(rec: Recorder, thread: str, cmd: str) -> str:
    rid = rec.add(thread, "command_run", cmd)  # provisional
    if _BLOCKED.search(cmd):
        rec.db._conn.execute(  # noqa: SLF001
            "UPDATE records SET content=? WHERE record_id=?",
            (f"{cmd}  ->  refused by sandbox (no network, no commits)", rid),
        )
        rec.db._conn.commit()
        return "command refused by sandbox: network access and git mutations are disabled"
    env = {
        "PATH": f"{WS}/.venv/bin:" + os.environ.get("PATH", ""),
        "PYTHONPATH": str(WS),
        "PYTHONDONTWRITEBYTECODE": "1",
        "HOME": os.environ.get("HOME", "/tmp"),  # noqa: S108
    }
    # the workspace venv is the pinned CPython 3.8 interpreter: the 2016
    # test suite needs <3.10 (collections.MutableMapping) and <=3.12 (cgi)
    run_cmd = [PY, "-m", "pytest"] + _pytest_args(cmd) if "pytest" in cmd else None
    try:
        if run_cmd:
            proc = subprocess.run(
                run_cmd, capture_output=True, text=True, timeout=_TIMEOUT_S, env=env, cwd=WS
            )  # noqa: S603
        else:
            proc = subprocess.run(  # noqa: S602
                cmd, shell=True, capture_output=True, text=True, timeout=_TIMEOUT_S, env=env, cwd=WS
            )
        out = (proc.stdout + ("\n" + proc.stderr if proc.stderr else "")).strip()
        code = proc.returncode
        timed_out = False
    except subprocess.TimeoutExpired:
        out, code, timed_out = f"timeout after {_TIMEOUT_S}s", 124, True
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
    if "pytest" in cmd:
        for line in out.splitlines():
            m = re.match(r"^(FAILED|PASSED|ERROR)\s+(\S+)", line)
            if m:
                rec.add(thread, "test_result", line.strip()[:220])
        m = re.search(r"^(\d+ failed(?:, \d+ passed)?|(\d+ passed))(?:,)? in [\d.]+s", summary)
        if m and not timed_out:
            rec.add(thread, "test_result", summary)
    return out if len(out) < 4000 else out[:2000] + "\n... (truncated)" + out[-1500:]


def _pytest_args(cmd: str) -> list[str]:
    """Pull the pytest invocation out of a shell command (test targets, -x, -q)."""
    m = re.search(r"pytest\s+(.*)$", cmd)
    if not m:
        return []
    return m.group(1).split()


_TOOL = re.compile(r"^(read_file|write_file|run_command)\s+(.+)$", re.IGNORECASE)
_TAG_LINE = re.compile(r"^\s*</?[A-Za-z_][^>]*>\s*$")


def _parse_reply(reply: str) -> tuple[str, str, str | None]:
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
    if tool == "run_command":
        # a heredoc body belongs to the command. The model puts the script
        # on the lines after `cat <<EOF > file` — or inline after the EOF
        # marker on the same line — and sometimes repeats the marker line
        # as the first body line. Rebuild the command as one canonical
        # heredoc, dropping the repeated marker. (This is the defect that
        # cost the first two ext runs.)
        hd = re.match(r"^(cat|tee)\s*<<-?\s*(['\"]?)(\w+)\2\s*(?:[>(]\s*(\S+))?\s*(.*)$", arg)
        if hd:
            delim = hd.group(3)
            target = (hd.group(4) or "f").strip()
            body: list[str] = []
            inline_done = False
            for ln in hd.group(5).splitlines():
                if ln.strip() == delim:
                    inline_done = True
                    break
                if not body and re.match(r"^(cat|tee)\s*<<", ln.strip()):
                    continue
                body.append(ln)
            if not inline_done:
                for ln in raw_lines[1:]:
                    if ln.strip() == delim:
                        break
                    if not body and re.match(r"^(cat|tee)\s*<<", ln.strip()):
                        continue
                    body.append(ln)
            arg = f"cat <<{delim} > {target}\n" + "\n".join(body) + f"\n{delim}"
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


async def run_session() -> dict:
    from cantheria.sie import SIEClient

    env = _load_env()
    token = env.get("HF_TOKEN") or os.environ.get("HF_TOKEN")
    if not token:
        print("HF_TOKEN not found — cannot reach the router", file=sys.stderr)
        raise SystemExit(2)

    db_path = OUT_DIR / "records.db"
    rec = Recorder(db_path, MODEL)
    sie = SIEClient(base_url=ROUTER, api_key=token)
    thread = "requests-3362"
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": f"{ISSUE}\n\nBegin. Your first reply must start with a tool call.",
        },
    ]
    report = ""
    steps = 0
    last_cmd = None
    repeat = 0
    try:
        while steps < _MAX_STEPS:
            steps += 1
            reply = await sie.chat(MODEL, messages, temperature=0.2, max_tokens=None)
            tool, arg, content = _parse_reply(reply)
            if tool == "FINAL":
                report = arg
                break
            if tool == "?":
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
            # anti-loop: Gemma 4 re-runs a deterministic command until the
            # cap when it sees no progress. A deterministic command repeated
            # verbatim yields the same output, so it has no new evidence —
            # nudge it to the next step. This is a session-harness guard,
            # not an oracle change: the frozen mechanism is untouched.
            if tool == "run_command" and arg:
                if arg == last_cmd:
                    repeat += 1
                else:
                    repeat = 1
                    last_cmd = arg
                if repeat >= 3:
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "You have run that exact command several times; it is deterministic, so "
                                "the output will not change. Do not re-run it. Take the next different "
                                "step: if you have found the fault, edit the code with write_file and then "
                                "verify with the test suite; if you are stuck, say so in a one-line note "
                                "and move to a different command."
                            ),
                        }
                    )
                    repeat = 0
        if not report:
            messages.append(
                {"role": "user", "content": "Reply with FINAL REPORT: and your summary now."}
            )
            reply = await sie.chat(MODEL, messages, temperature=0.2, max_tokens=None)
            _, report, _ = _parse_reply(reply)
    finally:
        await sie.close()
        rec.close()

    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "requests-3362.md").write_text(
        f"# Issue requests-3362\n\n{ISSUE}\n\n## Agent report\n\n{report}\n"
    )
    return {
        "task": thread,
        "model": MODEL,
        "steps": steps,
        "records": rec.n,
        "report_chars": len(report),
    }


async def main() -> None:
    print(json.dumps(await run_session(), indent=2))
    print(f"corpus: {OUT_DIR / 'records.db'}")
    print(f"reports: {REPORTS}")


if __name__ == "__main__":
    asyncio.run(main())
