# tinyhttp

A very small HTTP toolkit: chunked-body decoding, header parsing, and the
client glue over them. Kept deliberately tiny; the tests are the contract.

```
python3 -m pytest tests/ -q
```

Layout: `src/tinyhttp/` (library), `tests/` (pytest). Requires Python 3.10+.

This is the frozen working tree the live Gemma 4 sessions ran against
(sessions tinyhttp-0042 and tinyhttp-0043; the recorded sequence of every
edit, command and test outcome lives in `../records_live.db`). The repo's
`.git` directory was local-only and is not shipped; re-running the agent
loop (`../live.py`) requires `git init && git add -A && git commit` here
first, which reproduces the pre-registered starting state.
