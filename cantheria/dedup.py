"""One bug, one report.

Points are awarded for *valid vulnerabilities*, and the reviewers manually
check each one. So the shape of the output matters as much as its count: a
team that files the same path-traversal twelve times gets twelve rejections and
a reputation for noise, and the maintainer stops reading.

But the merge rule has to be deliberately conservative, because the failure
mode of merging is silent and expensive — fold two genuinely distinct bugs
together and one of them never gets reported, which loses a point that was
already *won*. Chunking by symbol makes that a live risk: a parser and a
path-joiner living 20 lines apart is exactly the case a wide window destroys.

So we merge only on:
    same vuln_class, AND
    either the same symbol, or the same file within `LINE_WINDOW` lines.

Anything looser — same title, similar embedding, "clearly the same root cause
two modules away" — is a judgement call we are not entitled to make at the cost
of a point. Those stay as separate findings and let triage rank them.

What merging is *for*, besides tidiness: N independent chunks producing the same
crash is corroborating evidence, not duplication. Each was a separate hypothesis
draw with its own PoC and its own kill-chain run. That's the one place where
redundancy earns more confidence, so it's kept as a count rather than thrown
away.
"""

from __future__ import annotations

from cantheria.schemas import Finding

LINE_WINDOW = 12  # same-file merges must be this close; a symbol is ~never wider
CORROBORATION_BUMP = 0.05  # per extra independent detection, capped


def _signature(f: Finding) -> tuple | None:
    """Normalized crash identity — ClusterFuzz's "crash state", cheaply.

    The signal set (SIGSEGV, ASAN:heap-buffer-overflow, ...) plus the top
    target frames, with line numbers stripped. Two PoCs that die the same way
    in the same place are the same bug regardless of which chunk hypothesized
    them; identical signals in *different* frames are not.
    """
    for r in f.runs:
        if not r.ok and (r.signals or r.target_frames):
            frames = tuple(fr.rsplit(":", 1)[0] for fr in r.target_frames[:2])
            return (tuple(sorted(s for s in r.signals if s != "TIMEOUT")), frames)
    return None


def _same_bug(a: Finding, b: Finding) -> bool:
    if a.vuln_class != b.vuln_class:
        return False  # two different defects can share a function
    sa, sb = _signature(a), _signature(b)
    if sa is not None and sa == sb:
        return True  # same crash state, same frames — same bug
    la, lb = a.location, b.location
    if la is None or lb is None or la.file != lb.file:
        return False
    if la.symbol and lb.symbol and la.symbol == lb.symbol:
        return True
    if la.line is None or lb.line is None:
        return False
    return abs(la.line - lb.line) <= LINE_WINDOW


def cluster(findings: list[Finding]) -> list[list[Finding]]:
    """Group findings that are the same bug; best representative first."""
    groups: list[list[Finding]] = []
    for f in sorted(findings, key=lambda x: (-x.confidence, x.id)):
        for group in groups:
            if _same_bug(group[0], f):
                group.append(f)
                break
        else:
            groups.append([f])
    return [sorted(g, key=lambda x: (-x.confidence, x.id)) for g in groups]


def dedup(findings: list[Finding]) -> list[Finding]:
    """Collapse each cluster onto its representative, recording the merge."""
    out: list[Finding] = []
    for group in cluster(findings):
        rep, *rest = group
        if rest:
            rep.raw["merged_from"] = [
                {
                    "id": f.id,
                    "line": f.location.line if f.location else None,
                    "confidence": round(f.confidence, 3),
                }
                for f in rest
            ]
            rep.raw["corroboration"] = len(group)
            # Independent detections of the same crash are evidence. Bump, cap,
            # and never past 1.0 — this raises a score, it does not confirm one.
            rep.confidence = min(1.0, rep.confidence + CORROBORATION_BUMP * (len(group) - 1))
            # Carry over any PoC the representative lacks but a twin proved with.
            if (rep.poc is None or not rep.poc.files) and rest[0].poc and rest[0].poc.files:
                rep.poc = rest[0].poc
        out.append(rep)
    return sorted(out, key=lambda f: (-f.confidence, f.id))
