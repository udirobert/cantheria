"""Thin async client for the SIE API (OpenAI-compatible surface).

Three verbs cover the whole hackathon:
    embed()   → index the target repo            /v1/embeddings
    chat()    → the hunt loop's reasoning        /v1/chat/completions
    rerank()  → triage candidate findings        /v1/rerank

No SDK dependency — one httpx client keeps the install boring and the
failure modes visible.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx

from cantheria.settings import settings


class SIEError(RuntimeError):
    pass


# Chat models on the managed deployment scale to zero: while no instance is
# up the gateway answers 404, and a burst of concurrent requests against a
# waking model draws 429s. Both are transient — retry with backoff instead of
# burning a chunk on them. 402 (credits) and 4xx request faults stay fatal.
_RETRYABLE = {404, 408, 409, 425, 429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 6


def _retry_delay(resp: httpx.Response, attempt: int) -> float:
    retry_after = resp.headers.get("retry-after")
    if retry_after:
        try:
            return min(float(retry_after), 60.0)
        except ValueError:
            pass
    return min(2.0**attempt + random.random(), 45.0)  # noqa: S311 — jitter, not crypto


class SIEClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        base_url = base_url or settings.base_url
        api_key = api_key or settings.api_key
        if not api_key:
            raise SIEError("SIE_API_KEY is not set — get one at superlinked.com/cloud")
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(_MAX_ATTEMPTS):
            try:
                resp = await self._http.post(path, json=payload)
            except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.ConnectError):
                if attempt == _MAX_ATTEMPTS - 1:
                    raise
                await asyncio.sleep(min(2.0**attempt + random.random(), 45.0))  # noqa: S311
                continue
            if resp.status_code == 402:
                raise SIEError("INSUFFICIENT_CREDITS — ping the Superlinked channel, they top up")
            if resp.status_code in _RETRYABLE and attempt < _MAX_ATTEMPTS - 1:
                await asyncio.sleep(_retry_delay(resp, attempt))
                continue
            resp.raise_for_status()
            return resp.json()
        raise SIEError(f"unreachable — {_MAX_ATTEMPTS} attempts against {path} failed")

    async def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        data = await self._post("/v1/embeddings", {"model": model, "input": texts})
        rows = sorted(data["data"], key=lambda r: r["index"])
        return [r["embedding"] for r in rows]

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> str:
        data = await self._post(
            "/v1/chat/completions",
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        return data["choices"][0]["message"]["content"]

    async def rerank(
        self, model: str, query: str, documents: list[str], top_n: int | None = None
    ) -> list[tuple[int, float]]:
        """Returns (original_index, relevance_score) pairs, best first."""
        payload: dict[str, Any] = {"model": model, "query": query, "documents": documents}
        if top_n:
            payload["top_n"] = top_n
        data = await self._post("/v1/rerank", payload)
        return [(r["index"], r["relevance_score"]) for r in data["results"]]
