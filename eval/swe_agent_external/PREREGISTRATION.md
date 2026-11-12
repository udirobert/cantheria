# External cell pre-registration — psf/requests-3362

Written BEFORE the Gemma 4 session started. The session runs on
`google/gemma-4-31B-it` (HF router) against a repository the author did
not write: `psf/requests` at commit `36453b95b13079296776d11b09cab2567ea3e703`
(2016-06-12, version 2.10), task instance `psf__requests-3362` from
SWE-bench Lite (princeton-nlp/SWE-bench_Lite).

The oracle and its four mechanism rules are frozen at cantheria commit
`896ae56` for this session. They are not revised on the result of this
session, whatever it is.

## Facts locked before the session

1. **Repository.** `psf/requests`, checked out at
   `36453b95b13079296776d11b09cab2567ea3e703`. The agent's workspace
   contains the working tree only — no `.git`, no remotes, no history — so
   neither `git log` nor a remote can reveal what happened afterward.

2. **The bug.** `Response.iter_content(decode_unicode=True)` returns
   **bytes** when `response.encoding` is `None`, instead of decoding to
   text the way `response.text` does. (SWE-bench Lite instance
   `psf__requests-3362`, reported 2016-06-24.)

3. **The hidden test.** `tests/test_requests.py::TestRequests::
   test_response_decode_unicode`, with the SWE-bench `test_patch` applied:
   it constructs a `requests.Response()` with `r.encoding = None` and
   asserts that `iter_content(decode_unicode=True)` yields `str`. The
   hidden test is NOT in the agent's workspace; the agent gets only the
   issue text.

4. **Fail-to-pass baseline (verified before the session, in a separate
   clone with only the test patch applied):**
   - before any fix: `1 failed, 2 warnings`
   - after the SWE-bench golden patch (requests/utils.py,
     `stream_decode_response_unicode`): `1 passed, 2 warnings`

5. **A correct minimal fix** touches `requests/utils.py` (the
   `stream_decode_response_unicode` function); the suite's other tests are
   unaffected by the golden patch.

6. **What a resolved run looks like** (for post-hoc labeling only):
   the agent ran the failing test before fixing (it sees `bytes` /
   `AssertionError`), edited `requests/utils.py`, and re-ran the test
   until it passed. The record will show command_run rows for the pytest
   invocations and a file_edit row for utils.py.

## What is NOT locked

- The claim strings extracted from the agent's final report: they are
  written by the extractor from the report, as in the live cell.
- The claim labels: written AFTER the session, against the record, each
  citing record ids — as in the live cell. This pre-registration covers
  repository facts only, and says so.
