"""Thin async client for the SIE API (OpenAI-compatible surface).

Three verbs cover the whole hackathon:
    embed()   → index the target repo            /v1/embeddings
    chat()    → the hunt loop's reasoning        /v1/chat/completions
    rerank()  → triage candidate findings        /v1/rerank

No SDK dependency — one httpx client keeps the install boring and the
failure modes visible.
"""

from __future__ import annotations

from typing import Any

import httpx

from cantheria.settings import settings


class SIEError(RuntimeError):
    pass


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
        resp = await self._http.post(path, json=payload)
        if resp.status_code == 402:
            raise SIEError("INSUFFICIENT_CREDITS — ping the Superlinked channel, they top up")
        resp.raise_for_status()
        return resp.json()

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
