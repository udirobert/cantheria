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
import json
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
# A 429 is a RATE LIMIT, not a flaky gateway: the request was rejected
# before it ran, so it costs no credits and the answer is unchanged. Give
# it more attempts (and honour Retry-After) than a 5xx gets — a run that
# dies on a rate limit has measured nothing, and reporting that as a
# verdict is worse than reporting it as a failure.
_MAX_ATTEMPTS_RATE_LIMITED = 12


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
        max_attempts = _MAX_ATTEMPTS
        for attempt in range(max_attempts):
            try:
                resp = await self._http.post(path, json=payload)
            except (httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout):
                if attempt == max_attempts - 1:
                    raise
                await asyncio.sleep(min(2.0**attempt + random.random(), 45.0))  # noqa: S311
                continue
            if resp.status_code == 402:
                raise SIEError("INSUFFICIENT_CREDITS — ping the Superlinked channel, they top up")
            if resp.status_code in _RETRYABLE and attempt < max_attempts - 1:
                if resp.status_code == 429 and max_attempts == _MAX_ATTEMPTS:
                    # a rate limit deserves the longer budget
                    max_attempts = _MAX_ATTEMPTS_RATE_LIMITED
                await asyncio.sleep(_retry_delay(resp, attempt))
                continue
            resp.raise_for_status()
            try:
                return resp.json()
            except json.JSONDecodeError:
                # some OpenAI-compatible gateways stream or append junk on
                # transient faults — a 200 with an unparseable body is a
                # failed attempt, not a fatal one
                if attempt < _MAX_ATTEMPTS - 1:
                    await asyncio.sleep(_retry_delay(resp, attempt))
                    continue
                raise SIEError(
                    f"undecodable response from {path} after {_MAX_ATTEMPTS} attempts"
                ) from None
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
        max_tokens: int | None = 2048,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        try:
            data = await self._post("/v1/chat/completions", payload)
        except httpx.HTTPStatusError as exc:
            # Some OpenAI-compatible gateways reject the legacy max_tokens
            # field outright (gemma-4 on the HF router 400s on it, with or
            # without a value). Retry once without it rather than dying —
            # the call is already bounded by the endpoint's own cap.
            if (
                exc.response is not None
                and exc.response.status_code == 400
                and "max_tokens" in payload
            ):
                payload.pop("max_tokens")
                data = await self._post("/v1/chat/completions", payload)
            else:
                raise
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
