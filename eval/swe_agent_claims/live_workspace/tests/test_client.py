from tinyhttp.client import parse_response


def test_read_body_chunked():
    raw = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n3\r\nabc\r\n2\r\nde\r\n0\r\n\r\n"
    status, headers, body = parse_response(raw)
    assert status == b"HTTP/1.1 200 OK"
    assert body == b"abcde"
