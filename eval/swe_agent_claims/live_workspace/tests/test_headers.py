from tinyhttp.headers import read_headers


def test_read_headers_basic():
    block = b"Host: example.org\r\nContent-Length: 3\r\n"
    h = read_headers(block)
    assert h["Host"] == "example.org"
    assert h["Content-Length"] == "3"


def test_header_folding():
    # obs-fold: a continuation line joins the previous value (RFC 9112 §5.2)
    block = b"User-Agent: tinyhttp\r\n\t1.2\r\nAccept: text/plain\r\n"
    h = read_headers(block)
    assert h["User-Agent"] == "tinyhttp 1.2"
    assert h["Accept"] == "text/plain"
