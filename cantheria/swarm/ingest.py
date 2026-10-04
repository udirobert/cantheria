"""Loaders — external corpora → normalized `records` rows.

The AI Village dataset is gated; these loaders are written against the
documented schema and pick fields defensively (`_pick` tries a ladder of
column names). Every row keeps its original dict in `raw` — nothing the
source recorded is lost on the way in.

File shapes (documented):
  chat_messages.jsonl.gz      {id, created_at, sender/agent, content, room}
  events.jsonl.gz             {id, created_at, agent?, data: {actionType, ...}}
  computer_use_sessions       {id, created_at, agent, session_goal}
  agent_memories.jsonl.gz     {id, created_at, agent, content/memory}
  summaries.jsonl.gz          {id, created_at, agent?, content/summary, scope}
  agents.jsonl.gz             {id, name, model, goal, ...}           → kind=agent
  village_goals / agent_goals {id/name, description, start/end}      → kind=goal
  village-transcript.json     single JSON: chat events, human-readable
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from cantheria.swarm.corpus import COLS, Corpus, record_id, ts_unix

VILLAGE_EPOCH_UNIX = 1743523200.0  # 2025-04-01 00:00 UTC — village day 1 is Apr 2 PT


def _pick(row: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        v = row.get(k)
        if v is not None and v != "":
            return v
    return None


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as f:  # noqa: SIM115
        for line in f:
            line = line.strip()
            if line:
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        yield obj
                except json.JSONDecodeError:
                    continue


def _village_uri(ts: float | None, day: Any = None) -> str:
    """Deep-link receipt into the live village UI. Day numbering skips most
    weekends in the dataset's own convention, so when the row carries no day
    field we approximate by counting weekdays since the village began."""
    if ts is None:
        return ""
    ms = int(ts * 1000)
    if day is None:
        from datetime import UTC, datetime

        d0 = datetime(2025, 4, 2, tzinfo=UTC).date()
        d = datetime.fromtimestamp(ts, UTC).date()
        if d < d0:
            return ""
        delta = (d - d0).days + 1
        weeks, rem = divmod(delta, 7)
        day = weeks * 5 + min(rem, 5)
    return f"https://theaidigest.org/village?day={day}&time={ms}"


_CONTENT_CAP = 20000


def _ts_norm(v: Any) -> str | None:
    """'2025-12-29 18:49:21.291984' → '2025-12-29T18:49:21.291984' so the ts
    column sorts and window-compares as ISO text."""
    if v is None or v == "":
        return None
    s = str(v).strip()
    return s.replace(" ", "T", 1) if len(s) > 10 and s[10] == " " else s


def _slim(raw: dict[str, Any]) -> dict[str, Any]:
    """Keep the raw row but drop the known multi-KB blobs — model `output`
    envelopes, SDK message bodies, and text already promoted into the
    `content` column. Provenance stays; the payload bloat doesn't."""
    r = dict(raw)
    for k in ("output", "agent_messages", "content", "memory", "text", "session_goal"):
        r.pop(k, None)
    if isinstance(r.get("data"), dict):
        d = dict(r["data"])
        for k in ("output", "content"):
            d.pop(k, None)
        r["data"] = d
    return r


def _row(corpus: str, raw: dict[str, Any], *, kind: str, content: str, **kw) -> dict[str, Any]:
    ts = _ts_norm(kw.pop("ts", None) or _pick(raw, "created_at", "timestamp", "ts", "time", "date"))
    unix = ts_unix(ts) or (float(ts) if isinstance(ts, int | float) else None)
    return dict(
        zip(
            COLS,
            (  # fmt: off
                record_id(corpus, raw, content),
                corpus,
                ts,
                unix,
                kw.pop("agent_id", None),
                kw.pop("thread", None),
                kind,
                content[:_CONTENT_CAP],
                kw.pop("parent_id", None),
                kw.pop("source_uri", ""),
                raw,
            ),
            strict=True,
        )
    )


def _uuid_map(directory: Path, stem: str, key: str, val: str) -> dict[str, str]:
    """uuid → display name for a dimension table (agents, chat_rooms)."""
    path = next(directory.glob(f"{stem}.jsonl*"), None)
    out: dict[str, str] = {}
    if path:
        for r in _iter_jsonl(path):
            if r.get(key) and r.get(val):
                out[str(r[key])] = str(r[val])
    return out


def ingest_aivillage(directory: Path, corpus: Corpus) -> dict[str, int]:
    """Load the AI Village tables against the real export schema (SCHEMA.md).

    `computer_use_turns` is intentionally lazy — 1.16M rows of citation
    depth, loaded on demand for the time span an audit actually needs.
    Agent/room UUIDs resolve to display names via the dimension tables so
    probes and claims work in the same vocabulary the site uses.
    """
    counts: dict[str, int] = {}
    names = _uuid_map(directory, "agents", "id", "name")
    rooms = _uuid_map(directory, "chat_rooms", "id", "name")

    def who(uuid: Any) -> str | None:
        return names.get(str(uuid), str(uuid) if uuid else None)

    def uri(r: dict[str, Any]) -> str:
        return _village_uri(ts_unix(_ts_norm(r.get("created_at"))))

    def each(stem: str, map_row) -> None:
        path = next(directory.glob(f"{stem}.jsonl*"), None)
        if path:
            n = corpus.insert(map_row(r) for r in _iter_jsonl(path))
            counts[stem] = counts.get(stem, 0) + n

    # --- chat_messages: the clean chat record --------------------------
    def chat(r):
        speaker = r.get("agent_speaker_id") or r.get("user_speaker_id")
        return _row(
            "aivillage",
            _slim(r),
            kind="chat",
            content=str(r.get("content") or ""),
            agent_id=who(speaker)
            if r.get("speaker_type") == "agent"
            else (f"user:{speaker}" if speaker else "user"),
            thread=rooms.get(str(r.get("room_id")), str(r.get("room_id") or "")),
            parent_id=str(r.get("room_id") or ""),
            source_uri=uri(r),
        )

    each("chat_messages", chat)

    # --- events: the canonical timeline --------------------------------
    def event(r):
        d = r.get("data") if isinstance(r.get("data"), dict) else {}
        at = d.get("actionType") or "?"
        agent = who(d.get("speakerId") or d.get("agentId"))
        content = _pick(
            d,
            "content",
            "summary",
            "answerToQuery",
            "sessionGoal",
            "nextSessionGoal",
            "query",
            "speakerName",
        )
        if content is None:
            content = json.dumps({k: v for k, v in d.items() if k != "output"}, default=str)[
                :_CONTENT_CAP
            ]
        else:
            content = str(content)
        room = d.get("roomId") or ""
        return _row(
            "aivillage",
            _slim(r),
            kind="event",
            content=f"[{at}] {content}",
            agent_id=agent,
            thread=rooms.get(str(room), str(room) if room else None),
            parent_id=str(d.get("messageId") or d.get("computerUseSessionId") or ""),
            source_uri=uri(r),
        )

    each("events", event)

    # --- computer_use_sessions: stated goals ---------------------------
    def session(r):
        return _row(
            "aivillage",
            _slim(r),
            kind="session",
            content=str(_pick(r, "session_goal", "short_displayed_session_goal") or ""),
            agent_id=who(r.get("agent_id")),
            thread=str(r.get("id") or ""),
            source_uri=uri(r),
        )

    each("computer_use_sessions", session)

    # --- agent_memories: agent-written claims, audit fodder ------------
    def memory(r):
        return _row(
            "aivillage",
            _slim(r),
            kind="memory",
            content=str(r.get("content") or ""),
            agent_id=who(r.get("agent_id")),
            source_uri=uri(r),
        )

    each("agent_memories", memory)

    # --- summaries: the primary audit target ---------------------------
    def summary(r):
        target = r.get("summary_target") or r.get("summary_date") or ""
        return _row(
            "aivillage",
            _slim(r),
            kind="summary",
            content=str(r.get("content") or ""),
            thread=f"{r.get('type')}:{target}",
            agent_id=str(r.get("generated_by") or ""),
            source_uri=uri(r),
            ts=_pick(r, "summary_date", "created_at"),
        )

    each("summaries", summary)

    # --- dimension tables ----------------------------------------------
    def agent_dim(r):
        return _row(
            "aivillage",
            _slim(r),
            kind="agent",
            content=json.dumps(
                {k: r.get(k) for k in ("name", "model_string", "goal", "is_participating")},
                default=str,
            ),
            agent_id=str(r.get("name") or r.get("id") or ""),
        )

    each("agents", agent_dim)

    def goal(r):
        return _row(
            "aivillage",
            _slim(r),
            kind="goal",
            content=str(_pick(r, "goal", "description", "name") or ""),
            agent_id=who(r.get("agent_id")),
            ts=_pick(r, "start_time", "created_at"),
        )

    each("village_goals", goal)
    each("agent_goals", goal)

    def room(r):
        return _row(
            "aivillage",
            _slim(r),
            kind="room",
            content=str(r.get("name") or ""),
            thread=str(r.get("name") or ""),
        )

    each("chat_rooms", room)

    # --- claude_code stream: the Claude Agent SDK agent ----------------
    def cc_msg(r):
        c = r.get("content")
        text = c if isinstance(c, str) else json.dumps(c, default=str)
        return _row(
            "aivillage",
            _slim(r),
            kind="chat",
            content=text,
            agent_id=who(r.get("agent_id")),
            thread=str(r.get("sdk_session_id") or ""),
            source_uri=uri(r),
        )

    each("claude_code_messages", cc_msg)

    def cc_session(r):
        return _row(
            "aivillage",
            _slim(r),
            kind="session",
            content=str(r.get("sdk_session_id") or ""),
            agent_id=who(r.get("agent_id")),
            thread=str(r.get("sdk_session_id") or ""),
        )

    each("claude_code_sessions", cc_session)

    return counts


def ingest_aivillage_turns(directory: Path, corpus: Corpus) -> dict[str, int]:
    """Load `computer_use_turns` — 1.16M rows of action-level trajectory.

    Lazy by design (see ingest_aivillage): call this only when an audit
    needs turn-level evidence. agent_id resolves through the sessions
    table; `agent_messages` (raw model envelopes) and bulky `output` are
    slimmed — content keeps the executed action + a short result tail.
    """
    names = _uuid_map(directory, "agents", "id", "name")
    sess_agent: dict[str, str] = {}
    spath = next(directory.glob("computer_use_sessions.jsonl*"), None)
    if spath:
        for r in _iter_jsonl(spath):
            if r.get("id"):
                sess_agent[str(r["id"])] = names.get(
                    str(r.get("agent_id")), str(r.get("agent_id") or "")
                )

    def turn(r: dict[str, Any]) -> dict[str, Any]:
        act = r.get("agent_action") if isinstance(r.get("agent_action"), dict) else {}
        at = act.get("action") or ("talk" if not act else "?")
        detail = act.get("command") or act.get("text") or act.get("coordinate") or ""
        out = str(r.get("output") or "")[:300]
        err = str(r.get("error") or "")[:200]
        content = f"[{at}] {detail}".rstrip()
        if out:
            content += f" → {out}"
        if err:
            content += f" !{err}"
        sid = str(r.get("session_id") or "")
        return _row(
            "aivillage",
            _slim(r),
            kind="turn",
            content=content,
            agent_id=sess_agent.get(sid) or None,
            thread=sid or None,
            parent_id=sid or None,
            source_uri=_village_uri(ts_unix(_ts_norm(r.get("created_at")))),
        )

    path = next(directory.glob("computer_use_turns.jsonl*"), None)
    if not path:
        return {}
    return {"computer_use_turns": corpus.insert(turn(r) for r in _iter_jsonl(path))}


def ingest_collusion(path: Path, corpus: Corpus) -> dict[str, int]:
    """The German-wiki dump (~18k posts): files may be a single jsonl, a
    directory of page dumps, or per-page exports. Map to kind=post."""
    files = [path] if path.is_file() else sorted(path.glob("**/*.json*"))

    def rows() -> Iterator[dict[str, Any]]:
        for f in files:
            if f.suffix == ".json" and not f.name.endswith(".jsonl"):
                data = json.loads(f.read_text())
                items = data if isinstance(data, list) else [data]
                yield from _map_posts(items, f.name)
            else:
                yield from _map_posts(_iter_jsonl(f), f.name)

    def _map_posts(items: Iterable[Any], fname: str) -> Iterator[dict[str, Any]]:
        for r in items:
            if not isinstance(r, dict):
                continue
            text = _pick(r, "content", "text", "body", "diff", "new_text") or ""
            yield _row(
                "collusion",
                r,
                kind="post",
                content=str(text)[:20000],
                agent_id=_pick(r, "agent", "editor", "author", "user", "username"),
                thread=_pick(r, "page", "page_title", "title", "wiki", "site"),
                ts=_pick(r, "timestamp", "created_at", "edited_at", "time", "ts"),
                source_uri=str(_pick(r, "url", "uri", "permalink") or f"file:{fname}"),
            )

    return {"post": corpus.insert(rows())}


def ingest_swarmtraces(path: Path, corpus: Corpus) -> dict[str, int]:
    """SwarmTraces payload JSONL — decoded payloads from the HF intrusion."""

    def rows() -> Iterator[dict[str, Any]]:
        for r in _iter_jsonl(path):
            payload = _pick(r, "payload", "content", "decoded", "script", "text") or ""
            yield _row(
                "swarmtraces",
                r,
                kind="payload",
                content=str(payload)[:20000],
                agent_id=_pick(r, "agent", "agent_id", "run_id"),
                thread=_pick(r, "chain", "chain_id", "url_chain"),
                ts=_pick(r, "timestamp", "created_at", "ts", "time"),
                source_uri=str(_pick(r, "url", "uri", "source") or ""),
            )

    return {"payload": corpus.insert(rows())}


def ingest_claims(path: Path) -> list[dict[str, Any]]:
    """Claims file for audit mode: jsonl (one claim dict per line) or a
    text/markdown doc (extracted by the model downstream — returned raw).

    A jsonl row is already an atomic claim when it has `claim`/`text`; a row
    that is a whole summary document stays a document for extract.py.
    """
    if path.suffix in {".jsonl", ".gz"} or path.name.endswith(".jsonl.gz"):
        return list(_iter_jsonl(path))
    return [{"document": path.read_text(), "source_doc": path.name}]


LOADERS = {
    "aivillage": ingest_aivillage,
    "aivillage-turns": ingest_aivillage_turns,
    "collusion": ingest_collusion,
    "swarmtraces": ingest_swarmtraces,
}
