"""Central configuration — everything overridable by env var.

SIE is the model backend: embeddings + rerank + chat, all OpenAI-compatible.
    SIE_API_KEY   sk-sie-...   (https://superlinked.com/cloud)
    SIE_BASE_URL  default https://api.superlinked.com

A local, gitignored `.env` is loaded if present (real env vars win), so
`cantheria scan` works right after `cp .env.example .env`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_BASE_URL = "https://api.superlinked.com"


def _load_dotenv(path: Path | None = None) -> None:
    env = path or Path.cwd() / ".env"
    if not env.is_file():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.split("#")[0].strip().strip("'\""))


_load_dotenv()

EMBED_MODEL = os.environ.get("CANTHERIA_EMBED_MODEL", "Qwen/Qwen3-Embedding-4B")
CHAT_MODEL = os.environ.get("CANTHERIA_CHAT_MODEL", "Qwen/Qwen3.8-27B-FP8")
RERANK_MODEL = os.environ.get("CANTHERIA_RERANK_MODEL", "Qwen/Qwen3-Reranker-4B")


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    base_url: str = field(default_factory=lambda: os.environ.get("SIE_BASE_URL", DEFAULT_BASE_URL))
    api_key: str = field(default_factory=lambda: os.environ.get("SIE_API_KEY", ""))
    sandbox_cpus: int = field(default_factory=lambda: _int_env("CANTHERIA_SANDBOX_CPUS", 2))
    sandbox_mem_mb: int = field(default_factory=lambda: _int_env("CANTHERIA_SANDBOX_MEM_MB", 512))
    sandbox_wall_s: int = field(default_factory=lambda: _int_env("CANTHERIA_SANDBOX_WALL_S", 20))
    # "deny" (default) jails network egress out of PoCs; "allow" is the escape
    # hatch for a finding that can only be proved by a callback. See sandbox.py.
    sandbox_network: str = field(
        default_factory=lambda: os.environ.get("CANTHERIA_SANDBOX_NETWORK", "deny").strip().lower()
    )
    quarantine_threshold: float = 0.5  # confidence below this never reaches a report

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


settings = Settings()
