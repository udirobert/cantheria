from tinyhttp.parser import parse_chunked


def test_chunked_length():
    # two chunks, 5 content bytes; the framing CRLFs are not content
    body = b"3\r\nabc\r\n2\r\nde\r\n0\r\n\r\n"
    assert parse_chunked(body) == b"abcde"


def test_single_chunk():
    body = b"4\r\nword\r\n0\r\n\r\n"
    assert parse_chunked(body) == b"word"


def test_chunked_terminates():
    # the zero-size chunk ends the body
    body = b"2\r\nhi\r\n0\r\n\r\n"
    assert parse_chunked(body) == b"hi"


def test_chunk_extension_ignored():
    body = b"3;n=1\r\nabc\r\n0\r\n\r\n"
    assert parse_chunked(body) == b"abc"
