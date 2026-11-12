"""Request/response body parsing for tinyhttp."""

from __future__ import annotations

CRLF = b"\r\n"


def parse_chunked(data: bytes) -> bytes:
    """Decode a chunked transfer-coding body (RFC 9112 §7.1).

    Each chunk is ``<hex size>[;ext]<CRLF><size bytes><CRLF>``; a zero
    size terminates the body. The CRLF after each chunk's payload is
    framing, not content.
    """
    body = bytearray()
    pos = 0
    while pos < len(data):
        line_end = data.index(CRLF, pos)
        size = int(data[pos:line_end].split(b";")[0], 16)
        if size == 0:
            break
        start = line_end + 2
        body += data[start : start + size]
        pos = start + size + 2
    return bytes(body)
