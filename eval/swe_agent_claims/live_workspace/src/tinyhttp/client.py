"""Client-side glue: split a raw response and decode its body."""

from __future__ import annotations

from tinyhttp.headers import read_headers
from tinyhttp.parser import CRLF, parse_chunked

CRLFCRLF = b"\r\n\r\n"


def parse_response(response: bytes) -> tuple[bytes, dict[str, str], bytes]:
    """Split a raw HTTP response into (status_line, headers, body).

    A ``Transfer-Encoding: chunked`` response gets its body decoded via
    :func:`parse_chunked` before it is returned.
    """
    head, _, body = response.partition(CRLFCRLF)
    lines = head.split(CRLF)
    status_line = lines[0] if lines else b""
    headers = read_headers(CRLF.join(lines[1:])) if len(lines) > 1 else {}
    encoding = next(
        (v for k, v in headers.items() if k.lower() == "transfer-encoding"),
        "",
    )
    if "chunked" in encoding.lower():
        body = parse_chunked(body)
    return status_line, headers, body
