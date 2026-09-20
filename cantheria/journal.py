"""Append-only journal — every candidate, every run, nothing lost.

Same discipline as redteam/journal.py: the search is only as credible as
its log. If a finding can't be replayed from the journal, it doesn't go
in the report.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from cantheria.schemas import Finding


class Journal:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, finding: Finding, event: str) -> None:
        row = {"event": event, "finding": json.loads(finding.model_dump_json())}
        with self._lock, self.path.open("a") as f:
            f.write(json.dumps(row) + "\n")

    def replay(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]
