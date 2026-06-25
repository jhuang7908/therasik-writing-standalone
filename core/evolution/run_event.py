"""
run_event.py — Unified RunEvent schema and persistent store.

Every CLI / pipeline run produces one RunEvent.  The EventCollector
normalizes heterogeneous outputs into this schema so that the
SignalAnalyzer can detect recurring patterns across projects.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_SUITE_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_STORE = _SUITE_ROOT / "output" / "evolution" / "run_events.jsonl"


@dataclass
class RunEvent:
    """Single normalized observation from a project pipeline run."""

    project_id: str
    family: str                         # vhvl_humanization, vhh_cmc, vam, car_design, ...
    entrypoint: str                     # script path or class name
    timestamp: str = ""

    # EvidenceGate snapshot
    ada_tier: str = "NOT_CHECKED"       # TIER1 | TIER2 | TIER3 | NOT_FOUND | OFFLINE | NOT_CHECKED
    ada_value: Optional[str] = None
    needs_disclaimer: bool = False
    target: str = ""

    # Run outcome
    exit_code: Optional[int] = None
    status: str = "unknown"             # ok | fail | warn | skipped
    n_pass: int = 0
    n_warn: int = 0
    n_fail: int = 0

    # Report output
    report_generated: bool = False
    has_traceability: bool = False

    # Knowledge enrichment
    pubmed_hits: int = 0
    pdb_hits: int = 0
    knowledge_offline: bool = False

    # Free-form tags for signal detection
    tags: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> RunEvent:
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in known}
        return cls(**filtered)


class RunEventStore:
    """Append-only JSONL store for RunEvents.

    V1 uses a flat JSONL file under ``output/evolution/``.
    Each line is one JSON-serialized RunEvent.
    """

    def __init__(self, path: Optional[str | Path] = None):
        self._path = Path(path) if path else _DEFAULT_STORE
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def append(self, event: RunEvent) -> None:
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(event.to_json() + "\n")

    def load_all(self) -> List[RunEvent]:
        if not self._path.exists():
            return []
        events: List[RunEvent] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(RunEvent.from_dict(json.loads(line)))
            except Exception:
                continue
        return events

    def count(self) -> int:
        if not self._path.exists():
            return 0
        return sum(1 for line in self._path.read_text(encoding="utf-8").splitlines() if line.strip())
