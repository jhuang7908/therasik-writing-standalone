"""
ChecklistRunner — InSynBio AbEngineCore v1.0
============================================
Executes and tracks the 27-item VH/VL humanization checklist
defined in config/vh_vl_humanization_v490.json.

Design principles:
  - TRACKS, not implements: records evidence that each step was done
  - ENFORCES order: Phase N cannot close until all items are checked
  - BLOCKS on hard failures: raises HardGateError on CDR integrity violations
  - IMMUTABLE config: loads from locked JSON, never writes back to it

Usage:
    from core.humanization import ChecklistRunner

    runner = ChecklistRunner()
    runner.check("1.1", evidence={"cdr_ranges": ..., "canonical": ...})
    runner.phase_complete(1)          # raises if any Phase 1 item unchecked
    runner.check("2.0", evidence={"germline_id": "IGHV3-30*15", "fr4_clean": True})
    ...
    runner.check("4.8", evidence={"cdr_match": True}, hard_gate=True)
    ...
    report = runner.report()
"""

import json
import sys
from dataclasses import dataclass, field


class HardGateError(RuntimeError):
    """Raised by ChecklistRunner when a hard_gate=True check fails.

    Replaces sys.exit(2) so callers (background threads, API workers) can catch
    this as a normal exception instead of terminating the process.
    """
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "vh_vl_humanization_v490.json"


class ChecklistStatus(str, Enum):
    PASS    = "PASS"
    WARN    = "WARN"
    FAIL    = "FAIL"
    SKIPPED = "SKIPPED"
    PENDING = "PENDING"


@dataclass
class ChecklistItem:
    item_id: str
    description: str
    phase: int
    status: ChecklistStatus = ChecklistStatus.PENDING
    evidence: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    timestamp: Optional[str] = None


class ChecklistViolation(RuntimeError):
    """Raised when a must_not_do rule is violated."""


class ChecklistRunner:
    """
    Stateful runner for the VH/VL humanization 27-item checklist.

    Lifecycle:
        runner = ChecklistRunner()
        runner.check("1.1", evidence={...})
        runner.phase_complete(1)
        runner.check("2.0", ...)
        ...
        runner.check("4.8", evidence={"cdr_match": True}, hard_gate=True)
        report = runner.report()
    """

    def __init__(self, config_path: Optional[Path] = None):
        cfg_path = Path(config_path) if config_path else _CONFIG_PATH
        if not cfg_path.exists():
            raise FileNotFoundError(f"Config not found: {cfg_path}")
        with open(cfg_path, encoding="utf-8") as f:
            self._config = json.load(f)

        self._items: Dict[str, ChecklistItem] = {}
        self._current_phase = 1
        self._finalized = False
        self._build_item_registry()

    # ──────────────────────────────────────────────────────────────────────
    # Internal setup
    # ──────────────────────────────────────────────────────────────────────

    def _build_item_registry(self):
        checklist = self._config.get("checklist_v4_4", {})
        phase_map = {
            "phase_1": 1, "phase_2": 2, "phase_3": 3,
            "phase_4": 4, "phase_5": 5,
        }
        for phase_key, phase_num in phase_map.items():
            for desc in checklist.get(phase_key, []):
                item_id = desc.split(" ")[0]
                self._items[item_id] = ChecklistItem(
                    item_id=item_id,
                    description=desc,
                    phase=phase_num,
                )

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def check(
        self,
        item_id: str,
        evidence: Dict[str, Any],
        status: ChecklistStatus = ChecklistStatus.PASS,
        notes: str = "",
        hard_gate: bool = False,
    ) -> ChecklistItem:
        """
        Record the result of a checklist item.

        Args:
            item_id:    e.g. "1.1", "4.8", "5.2b"
            evidence:   dict of computed values proving the step was done
            status:     PASS / WARN / FAIL
            notes:      free-text explanation
            hard_gate:  if True and status==FAIL, raises HardGateError (caught by API workers)

        Returns:
            The updated ChecklistItem.
        """
        if item_id not in self._items:
            raise KeyError(f"Unknown checklist item: '{item_id}'. "
                           f"Valid IDs: {sorted(self._items)}")

        item = self._items[item_id]

        if self._finalized:
            raise RuntimeError("ChecklistRunner is finalized — no further checks allowed.")

        item.status    = ChecklistStatus(status)
        item.evidence  = evidence
        item.notes     = notes
        item.timestamp = datetime.utcnow().isoformat()

        if hard_gate and item.status == ChecklistStatus.FAIL:
            self._abort_hard_gate(item)

        return item

    def phase_complete(self, phase_num: int) -> None:
        """
        Assert all items in `phase_num` have been checked (not PENDING).
        Must be called before starting the next phase.

        Raises:
            RuntimeError  if any Phase N item is still PENDING
            RuntimeError  if any Phase N item has status FAIL (hard failure)
        """
        phase_items = [i for i in self._items.values() if i.phase == phase_num]
        pending = [i.item_id for i in phase_items if i.status == ChecklistStatus.PENDING]
        failed  = [i.item_id for i in phase_items if i.status == ChecklistStatus.FAIL]

        if pending:
            raise RuntimeError(
                f"Phase {phase_num} incomplete — unchecked items: {pending}\n"
                f"All 27 checklist items must be verified before proceeding."
            )
        if failed:
            raise RuntimeError(
                f"Phase {phase_num} has FAIL items: {failed}\n"
                f"Resolve failures before advancing to Phase {phase_num + 1}."
            )

        self._current_phase = phase_num + 1

    def enforce_must_not_do(self, action: str) -> None:
        """
        Check a proposed action against compliance_rules.must_not_do.
        Raises ChecklistViolation if the action is prohibited.

        Args:
            action: plain-text description of the action being taken
        """
        prohibited = self._config.get("compliance_rules", {}).get("must_not_do", [])
        action_lower = action.lower()
        for rule in prohibited:
            rule_lower = rule.lower()
            # Require at least 2 distinct rule keywords to match the action
            # to avoid false positives from single common words
            keywords = [w for w in rule_lower.split() if len(w) > 6]
            matched = sum(1 for kw in keywords if kw in action_lower)
            if matched >= 2:
                raise ChecklistViolation(
                    f"MUST NOT DO violation:\n"
                    f"  Action : {action}\n"
                    f"  Rule   : {rule}\n"
                    f"Refer to config/vh_vl_humanization_v490.json#compliance_rules"
                )

    def status_summary(self) -> Dict[str, int]:
        """Return count of items per status."""
        counts: Dict[str, int] = {s.value: 0 for s in ChecklistStatus}
        for item in self._items.values():
            counts[item.status.value] += 1
        return counts

    def finalize(self) -> None:
        """
        Mark the run as complete. Verifies all 27 items have been checked.
        Call this before report().
        """
        pending = [i.item_id for i in self._items.values()
                   if i.status == ChecklistStatus.PENDING]
        if pending:
            raise RuntimeError(
                f"Cannot finalize — {len(pending)} items still PENDING: {pending}"
            )
        self._finalized = True

    def report(self) -> Dict[str, Any]:
        """
        Generate a structured compliance report dict.
        Call finalize() first.
        """
        if not self._finalized:
            self.finalize()

        phases: Dict[int, List[Dict]] = {1: [], 2: [], 3: [], 4: [], 5: []}
        overall = ChecklistStatus.PASS

        for item in self._items.values():
            phases[item.phase].append({
                "id": item.item_id,
                "description": item.description,
                "status": item.status.value,
                "evidence": item.evidence,
                "notes": item.notes,
                "timestamp": item.timestamp,
            })
            if item.status == ChecklistStatus.FAIL:
                overall = ChecklistStatus.FAIL
            elif item.status == ChecklistStatus.WARN and overall == ChecklistStatus.PASS:
                overall = ChecklistStatus.WARN

        summary = self.status_summary()
        return {
            "abenginecore_version": "1.0.0",
            "checklist_version": self._config.get("version", "unknown"),
            "standard": self._config.get("standard", ""),
            "generated_at": datetime.utcnow().isoformat(),
            "overall_status": overall.value,
            "summary": summary,
            "phases": phases,
            "compliance_rules_applied": True,
        }

    def print_status(self) -> None:
        """Print a compact phase-by-phase status table to stdout."""
        print(f"\n{'─'*60}")
        print(f"  AbEngineCore ChecklistRunner  (config v{self._config.get('version','?')})")
        print(f"{'─'*60}")
        icons = {
            ChecklistStatus.PASS:    "✅",
            ChecklistStatus.WARN:    "⚠️ ",
            ChecklistStatus.FAIL:    "❌",
            ChecklistStatus.SKIPPED: "⏭ ",
            ChecklistStatus.PENDING: "⬜",
        }
        for phase_num in range(1, 6):
            items = [i for i in self._items.values() if i.phase == phase_num]
            statuses = [icons[i.status] for i in items]
            print(f"  Phase {phase_num}  {''.join(statuses)}")
            for item in items:
                if item.status != ChecklistStatus.PASS:
                    print(f"          {icons[item.status]} {item.item_id}: {item.description[:60]}")
        summary = self.status_summary()
        print(f"{'─'*60}")
        print(f"  PASS:{summary['PASS']}  WARN:{summary['WARN']}  "
              f"FAIL:{summary['FAIL']}  PENDING:{summary['PENDING']}")
        print(f"{'─'*60}\n")

    # ──────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────

    def _abort_hard_gate(self, item: ChecklistItem) -> None:
        """Called when a hard_gate check fails. Raises HardGateError (not sys.exit).

        Previously called sys.exit(2) which killed the uvicorn server when triggered
        from a background thread. Now raises HardGateError so API workers can catch
        it and mark the job as failed without crashing the process.
        """
        msg_lines = [
            f"\n{'='*60}",
            f"  HARD GATE FAILURE — AbEngineCore ChecklistRunner",
            f"{'='*60}",
            f"  Item     : {item.item_id}",
            f"  Rule     : {item.description}",
            f"  Evidence : {item.evidence}",
            f"  Notes    : {item.notes}",
            f"\n  Pipeline aborted. Fix the issue and re-run from Phase 1.",
            f"{'='*60}\n",
        ]
        for line in msg_lines:
            print(line, file=sys.stderr)
        raise HardGateError(
            f"Phase {item.item_id} hard gate FAIL: {item.description} | "
            f"evidence={item.evidence}"
        )

    # ──────────────────────────────────────────────────────────────────────
    # Convenience: item access
    # ──────────────────────────────────────────────────────────────────────

    def __getitem__(self, item_id: str) -> ChecklistItem:
        return self._items[item_id]

    def items(self):
        return self._items.values()

    def __repr__(self) -> str:
        s = self.status_summary()
        return (f"ChecklistRunner(v{self._config.get('version','?')}, "
                f"PASS={s['PASS']}, WARN={s['WARN']}, "
                f"FAIL={s['FAIL']}, PENDING={s['PENDING']})")
