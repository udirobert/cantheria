"""Chat backend selection — SIE by default, any OpenAI-compatible endpoint
(Featherless, a local sie-server, a LiteLLM shim in front of anything) by env:

    CANTHERIA_CHAT_BASE_URL   e.g. https://api.featherless.ai/v1
                              ("/v1" suffix optional — normalized away)
    CANTHERIA_CHAT_API_KEY    key for that endpoint
    FEATHERLESS_API_KEY       shorthand: implies the featherless base URL
    CANTHERIA_CHAT_MODEL      model name on whichever backend is active

SIEClient is already a plain OpenAI-compatible HTTP client, so the fallback
is the same class pointed elsewhere — the failure modes and retry discipline
stay identical. Backend choice: explicit CANTHERIA_CHAT_* wins, then
FEATHERLESS_API_KEY, then SIE.
"""

from __future__ import annotations

import os

from cantheria.settings import CHAT_MODEL, settings
from cantheria.sie import SIEClient

FEATHERLESS_BASE_URL = "https://api.featherless.ai/v1"
# SIE's default model lives on Superlinked; the fallback default is a
# strong open instruct that exists on featherless's catalog. Override with
# CANTHERIA_CHAT_MODEL either way.
FALLBACK_CHAT_MODEL = "Qwen/Qwen3-32B"


def _alt_key() -> str:
    return os.environ.get("CANTHERIA_CHAT_API_KEY") or os.environ.get("FEATHERLESS_API_KEY", "")


def _alt_base() -> str:
    explicit = os.environ.get("CANTHERIA_CHAT_BASE_URL", "").strip()
    if explicit:
        return explicit
    return FEATHERLESS_BASE_URL if _alt_key() else ""


def using_alt_backend() -> bool:
    return bool(_alt_base() and _alt_key())


def chat_configured() -> bool:
    """True when *some* chat backend is reachable — alt endpoint or SIE."""
    return using_alt_backend() or settings.configured


def make_chat() -> SIEClient:
    """One client, whichever endpoint is configured. SIEClient already
    implements the OpenAI-compatible surface with the retry/backoff the
    cold-start catalog needs; the fallback is the same class, other URL."""
    if using_alt_backend():
        base = _alt_base().rstrip("/")
        if base.endswith("/v1"):
            base = base[: -len("/v1")]  # SIEClient joins /v1/... itself
        return SIEClient(base_url=base, api_key=_alt_key())
    return SIEClient()


def chat_model() -> str:
    """Model for the active backend. CANTHERIA_CHAT_MODEL wins either way;
    the SIE default is meaningless on a different catalog."""
    if os.environ.get("CANTHERIA_CHAT_MODEL"):
        return CHAT_MODEL
    return FALLBACK_CHAT_MODEL if using_alt_backend() else CHAT_MODEL
