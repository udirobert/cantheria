"""Header field parsing for tinyhttp."""

from __future__ import annotations


def read_headers(data: bytes) -> dict[str, str]:
    """Parse a header block into a field-name -> value mapping.

    obs-fold continuation lines (a leading SP/HTAB) are joined onto the
    previous field's value, per RFC 9112 §5.2.
    """
    headers: dict[str, str] = {}
    last_name: str | None = None

    for raw in data.split(b"\r\n"):
        if not raw:
            continue

        if raw[0:1] in (b" ", b"\t"):
            if last_name is not None:
                # obs-fold: join with a single space
                headers[last_name] += " " + raw.strip().decode("latin-1")
            continue

        name, sep, value = raw.partition(b":")
        if sep:
            last_name = name.strip().decode("latin-1")
            headers[last_name] = value.strip().decode("latin-1")
        else:
            # Invalid header line, ignore or handle as needed
            last_name = None

    return headers
