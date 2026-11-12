"""Small shared helpers."""

from __future__ import annotations


def header_get(headers: dict[str, str], name: str) -> str | None:
    """Case-insensitive header lookup."""
    low = name.lower()
    for k, v in headers.items():
        if k.lower() == low:
            return v
    return None


def content_length(headers: dict[str, str]) -> int | None:
    """Content-Length as an int, when present and well-formed."""
    raw = header_get(headers, "Content-Length")
    if raw is None:
        return None
    try:
        return int(raw.strip())
    except ValueError:
        return None
