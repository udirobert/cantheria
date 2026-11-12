# Issue tinyhttp-0043

Bug report: a header value folded with an obs-fold continuation line (a line starting with a space or tab, RFC 9112 §5.2) loses the folded part. `User-Agent: tinyhttp` followed by a continuation line `\t1.2` should read back as `tinyhttp 1.2`. tests/test_headers.py::test_header_folding documents it. Fix the library; do not modify the tests.

## Agent report

I fixed a bug in `src/tinyhttp/headers.py` where header values folded with an `obs-fold` continuation line (starting with a space or tab) were being ignored. I modified the `read_headers` function to detect lines starting with a space or tab and append their content to the previously parsed header value, as required by RFC 9112 §5.2.

Changes:
- Modified `src/tinyhttp/headers.py`: Updated `read_headers` to track the `last_name` of the header being parsed and handle continuation lines by appending them to the existing value.

Verification:
- Ran `pytest tests/test_headers.py::test_header_folding`, which now passes.
- Ran `pytest tests/test_headers.py` to ensure no regressions in other header tests. Both tests passed.
