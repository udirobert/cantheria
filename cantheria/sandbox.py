"""Sandboxed PoC execution.

The canary flies here: we *expect* PoCs to crash, hang, or misbehave, so
execution must never be able to escape, linger, or eat the box.

Layers:
    - fresh temp workdir (repo + PoC files copied in), removed after
    - preexec resource limits: RLIMIT_AS / RLIMIT_CPU / RLIMIT_NPROC
    - new process group; kill the whole group on wall-clock timeout
    - output caps so a spinning printer can't exhaust memory

Not a kernel sandbox — for C we only run sanitizer-instrumented builds the
project itself provides. Enough for a hackathon, honest in the README.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import signal
import sys
import tempfile
from pathlib import Path

from cantheria.schemas import RunResult
from cantheria.settings import settings

MAX_OUTPUT = 64_000


def _apply_limits() -> None:
    import resource

    def clamp(lim: int, want: int) -> None:
        try:
            soft, hard = resource.getrlimit(lim)
            resource.setrlimit(
                lim, (want, min(hard, want + 2) if hard != resource.RLIM_INFINITY else want + 2)
            )
        except (ValueError, OSError):
            pass  # e.g. RLIMIT_NPROC is Linux-only; RLIMIT_AS is unreliable on some macOS builds

    clamp(resource.RLIMIT_CPU, settings.sandbox_wall_s * settings.sandbox_cpus)
    clamp(resource.RLIMIT_FSIZE, 64 * 1024 * 1024)  # no multi-GB core/spill files
    if sys.platform != "darwin":
        # macOS counts RLIMIT_NPROC UID-wide (breaks fork under a desktop
        # session) and RLIMIT_AS is not enforced per-process. There, the wall
        # clock + process-group kill are the backstop; Linux gets the full set.
        clamp(resource.RLIMIT_AS, settings.sandbox_mem_mb * 1024 * 1024)
        clamp(resource.RLIMIT_NPROC, 64)
    os.setpgrp()


async def run_sandboxed(workdir: Path, entry: str, wall_s: int | None = None) -> RunResult:
    wall = wall_s or settings.sandbox_wall_s
    proc = await asyncio.create_subprocess_shell(
        entry,
        cwd=str(workdir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=False,  # we setpgrp in preexec instead
        preexec_fn=_apply_limits,
    )
    timed_out = False
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=wall)
    except TimeoutError:
        timed_out = True
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()
        stdout, stderr = b"", b"timeout"
        await proc.wait()

    out = stdout.decode(errors="replace")[:MAX_OUTPUT]
    err = stderr.decode(errors="replace")[:MAX_OUTPUT]
    rc = proc.returncode if proc.returncode is not None else -9
    signals_found: list[str] = []
    if rc < 0:
        try:
            signals_found.append(signal.Signals(-rc).name)
        except ValueError:
            signals_found.append(f"SIG{-rc}")
    if timed_out:
        signals_found.append("TIMEOUT")
    for marker, name in (
        ("AddressSanitizer", "ASAN"),
        ("LeakSanitizer", "LSAN"),
        ("ThreadSanitizer", "TSAN"),
        ("heap-buffer-overflow", "HEAP_OVERFLOW"),
        ("stack-buffer-overflow", "STACK_OVERFLOW"),
        ("use-after-free", "UAF"),
    ):
        if marker in err or marker in out:
            signals_found.append(name)
    return RunResult(
        ok=(rc == 0 and not timed_out),
        exit_code=rc,
        stdout=out,
        stderr=err,
        signals=signals_found,
        wall_s=wall if timed_out else 0.0,
    )


async def execute_poc(
    repo_root: Path, files: dict[str, str], entry: str, wall_s: int | None = None
):
    """Copy the repo, drop PoC files beside it, run `entry` inside.

    Returns (RunResult, repo_copy_path) — the copy is where tracebacks will
    point, so the oracle attributes frames against it, not the original root.
    """
    with tempfile.TemporaryDirectory(prefix="cantheria-") as tmp:
        work = Path(tmp)
        repo_copy = work / "repo"
        shutil.copytree(
            repo_root,
            repo_copy,
            symlinks=True,
            ignore=shutil.ignore_patterns(".git", "target", "node_modules", "__pycache__"),
        )
        poc_dir = work / "poc"
        poc_dir.mkdir()
        for name, content in files.items():
            dest = poc_dir / name
            if ".." in Path(name).parts:
                raise ValueError(f"PoC file path escapes workdir: {name}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content)
        cmd = f"cd {poc_dir} && {entry}"
        result = await run_sandboxed(work, cmd, wall_s)
        return result, repo_copy.resolve()
