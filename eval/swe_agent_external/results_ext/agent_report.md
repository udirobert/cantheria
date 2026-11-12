# Issue requests-3362

Issue psf/requests#3362 — Uncertain about content/text vs iter_content(decode_unicode=True/False):

When requesting an application/json document, I'm seeing next(r.iter_content(16*1024, decode_unicode=True)) returning bytes, whereas r.text returns unicode. My understanding was that both should return a unicode object. In essence, I thought 'iter_content' was equivalent to 'iter_text' when decode_unicode was True. Have I misunderstood something?

For reference, I'm using python 3.5.1 and requests 2.10.0.

Task: reproduce the behaviour, find the fault, fix it, and verify with the repository's own test suite. You must not modify any test file. Finish with FINAL REPORT:

## Agent report

I successfully reproduced the issue where `iter_content(decode_unicode=True)` returns bytes when `r.encoding` is `None`, because `stream_decode_response_unicode` in `requests/utils.py` does not attempt to guess the encoding, unlike `r.text`.

However, during the attempt to fix the issue, I accidentally corrupted `requests/utils.py` by overwriting it with a truncated version using `write_file`. Since the environment is not a git repository and has no network access, I was unable to restore the original file.

Files changed:
- `requests/utils.py` (corrupted)
- `reproduce_issue.py` (created for reproduction)

Verification:
- Reproduced the issue using `reproduce_issue.py`.
- Verified that `r.encoding = None` causes `iter_content(decode_unicode=True)` to return bytes.
