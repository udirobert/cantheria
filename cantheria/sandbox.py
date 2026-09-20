"""Sandboxed PoC execution.

The canary flies here: we *expect* PoCs to crash, hang, or misbehave, so
execution must never be able to escape, linger, or eat the box.

The code being run was written by a model that read a repository we do not
trust, which makes two properties load-bearing rather than cosmetic: the child
must hold no secrets (see `_child_env`), and it must not badly want a network
(see `_confine`).

Layers:
    - fresh temp workdir (repo + PoC files copied in), removed after
    - allowlisted environment; HOME/TMPDIR relocated inside the temp dir
    - preexec resource limits: CPU / FSIZE / (Linux: AS, NPROC)
    - new process group; kill the whole group on wall-clock timeout
    - output caps so a spinning printer can't exhaust memory
    - macOS: seatbelt profile denying network egress, where available

Not a kernel sandbox — a local privilege escape is out of scope, and for C we
only run sanitizer-instrumented builds the project itself provides. Enough for
a hackathon, stated honestly in SECURITY.md.
"""

from __future__ import annotations

import asyncio
import os
import resource
import shutil
import signal
import sys
import tempfile
from pathlib import Path

from cantheria.schemas import RunResult
from cantheria.settings import settings

MAX_OUTPUT = 64_000
_SEATBELT = "(version 1)(allow default)(deny network*)"

# What the most recent _confine() actually enforced. Surfaced by
# `cantheria status` and stamped on every RunResult, because "we isolated it"
# is only worth claiming if we can name the isolation this machine applied.
_CONFINEMENT = "not yet run"


def _child_env(work: Path) -> dict[str, str]:
    """Environment for model-written code: an allowlist, never a denylist.

    A denylist fails the moment anyone adds a second credential to .env — and
    the one guaranteed-present secret is the SIE key, i.e. a metered one that
    someone else pays for if a planted comment talks our PoC into reading it.
    HOME and TMPDIR move inside the throwaway dir so a PoC sent looking for
    `~/.ssh` or `~/.aws/credentials` finds an empty sandbox instead.

    Toolchains are the deliberate exception: Rust/TS targets are un-provable
    without cargo/node. Their *homes* are pointed at the real dirs (toolchains
    are read-only-ish in practice — a PoC that corrupts ~/.cargo corrupts build
    artifacts, not data), and CARGO_TARGET_DIR lands in a shared cache so the
    dep graph is compiled once per machine, not once per PoC run.
    """
    for d in ("home", "tmp"):
        (work / d).mkdir(exist_ok=True)
    real_home = Path(os.environ.get("HOME") or Path.home())
    target_cache = real_home / ".cache" / "cantheria" / "cargo-target"
    try:
        target_cache.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    bin_dir = str(Path(sys.executable).parent)  # `python` must be *our* interpreter
    env = {
        "PATH": os.pathsep.join([bin_dir, os.environ.get("PATH", "")]).rstrip(os.pathsep),
        "HOME": str(work / "home"),
        "TMPDIR": str(work / "tmp"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        "CARGO_HOME": os.environ.get("CARGO_HOME", str(real_home / ".cargo")),
        "RUSTUP_HOME": os.environ.get("RUSTUP_HOME", str(real_home / ".rustup")),
        "CARGO_TARGET_DIR": os.environ.get("CARGO_TARGET_DIR", str(target_cache)),
        "CARGO_NET_OFFLINE": "true",  # deps come from prefetch; never the network
    }
    return env


def _confine(entry: str) -> list[str]:
    """Wrap `entry` to drop network egress, where the platform allows it.

    Denying egress also forecloses the useful *escapes* — pip install, curl of a
    stage-2 payload, a callback proving a blind finding from outside. A real
    blind-SSRF proof does need the listener, and on that day we run with
    CANTHERIA_SANDBOX_NETWORK=allow and accept the trade knowingly, per run.
    """
    global _CONFINEMENT
    if settings.sandbox_network != "deny":
        _CONFINEMENT = "off (CANTHERIA_SANDBOX_NETWORK=allow)"
        return ["/bin/sh", "-c", entry]
    if sys.platform == "darwin" and shutil.which("sandbox-exec"):
        _CONFINEMENT = "seatbelt: deny network*"
        return ["sandbox-exec", "-p", _SEATBELT, "/bin/sh", "-c", entry]
    # Linux wants a netns (`unshare -n`, needs CAP_SYS_ADMIN) or a container
    # run with --network none. Silently pretending we did something is worse
    # than saying so, so the mode lands in every RunResult.
    _CONFINEMENT = f"none ({sys.platform}: no network jail available)"
    return ["/bin/sh", "-c", entry]


def describe_confinement() -> str:
    """What the last run actually enforced — for the CLI summary and journal."""
    return _CONFINEMENT


def _apply_limits() -> None:
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
    argv = _confine(entry)
    proc = await asyncio.create_subprocess_exec(
        *argv,
        cwd=str(workdir),
        env=_child_env(workdir),
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
        confinement=_CONFINEMENT,
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
        # Prefetched deps (node_modules/, target/) are excluded from the copy —
        # they're huge and read-mostly. Link them in so PoCs can build; writes
        # through the link land in the scan's own clone, which is throwaway.
        for heavy in ("node_modules", "target"):
            src = repo_root / heavy
            dst = repo_copy / heavy
            if src.is_dir() and not dst.exists():
                try:
                    dst.symlink_to(src, target_is_directory=True)
                except OSError:
                    pass
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
