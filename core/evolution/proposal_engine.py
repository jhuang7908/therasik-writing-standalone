"""
proposal_engine.py — Convert Signals into governed outputs.

Two output channels:
  1. EVOLUTION_LOG.md  — append-only OBSERVATION or PROPOSAL entries
  2. Project-level     — suggestions.json + summary.md under output/evolution/

The engine consults GovernancePolicy to determine whether a signal
triggers an OBSERVATION (safe to log) or a PROPOSAL (needs owner approval).
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import List, Optional

from core.evolution.governance_policy import GovernancePolicy, ProposalLevel
from core.evolution.signal_analyzer import Signal

_SUITE_ROOT = Path(__file__).resolve().parents[2]
_EVOLUTION_LOG = _SUITE_ROOT / "docs" / "EVOLUTION_LOG.md"
_APPEND_MARKER = "<!-- APPEND NEW ENTRIES ABOVE THIS LINE -->"
_OUTPUT_DIR = _SUITE_ROOT / "output" / "evolution"


class ProposalEngine:
    """Generates governed text from analyzed Signals."""

    def __init__(
        self,
        policy: Optional[GovernancePolicy] = None,
        evolution_log_path: Optional[str | Path] = None,
        output_dir: Optional[str | Path] = None,
    ):
        self._policy = policy or GovernancePolicy()
        self._log_path = Path(evolution_log_path) if evolution_log_path else _EVOLUTION_LOG
        self._out_dir = Path(output_dir) if output_dir else _OUTPUT_DIR
        self._out_dir.mkdir(parents=True, exist_ok=True)

    def process(self, signals: List[Signal], dry_run: bool = False) -> dict:
        """Process all signals, generate outputs, and return a summary.

        Parameters
        ----------
        signals : list[Signal]
            Output from SignalAnalyzer.analyze().
        dry_run : bool
            If True, generate text but do not write to any file.

        Returns
        -------
        dict with keys: observations, proposals, suggestions_path, log_entries_count
        """
        observations: List[str] = []
        proposals: List[str] = []
        suggestions: List[dict] = []

        for sig in signals:
            level = self._determine_level(sig)
            entry_text = self._format_log_entry(sig, level)

            if level == ProposalLevel.PROPOSAL:
                proposals.append(entry_text)
            else:
                observations.append(entry_text)

            suggestions.append({
                "signal_id": sig.signal_id,
                "level": level.value,
                "title": sig.title,
                "severity": sig.severity,
                "occurrence_count": sig.occurrence_count,
                "affected_projects": sig.affected_projects[:10],
                "suggested_action": sig.suggested_action,
                "affected_paths": sig.affected_paths,
            })

        if not dry_run and (observations or proposals):
            self._append_to_evolution_log(observations + proposals)
            self._write_suggestions(suggestions)

        return {
            "observations": len(observations),
            "proposals": len(proposals),
            "total_signals": len(signals),
            "suggestions_path": str(self._out_dir / "suggestions.json"),
            "dry_run": dry_run,
        }

    def _determine_level(self, sig: Signal) -> ProposalLevel:
        """Use governance policy + severity to pick OBSERVATION vs PROPOSAL."""
        path_level = self._policy.required_level(sig.affected_paths)

        if path_level == ProposalLevel.PROPOSAL:
            return ProposalLevel.PROPOSAL
        if sig.severity == "action_needed":
            return ProposalLevel.PROPOSAL

        return ProposalLevel.OBSERVATION

    def _format_log_entry(self, sig: Signal, level: ProposalLevel) -> str:
        """Format a single EVOLUTION_LOG.md entry from a Signal."""
        today = date.today().isoformat()
        entry_type = f"[{level.value}]"
        projects_str = ", ".join(sig.affected_projects[:5])
        if len(sig.affected_projects) > 5:
            projects_str += f" (+{len(sig.affected_projects) - 5} more)"

        paths_str = ", ".join(f"`{p}`" for p in sig.affected_paths[:5]) if sig.affected_paths else "N/A"

        lines = [
            f"### {entry_type} {today} \u2014 {sig.title}",
            f"- **\u6765\u6e90\u6848\u4f8b:** {projects_str}",
            f"- **\u89c2\u5bdf:** {sig.description}",
        ]
        if sig.suggested_action:
            lines.append(f"- **\u5efa\u8bae:** {sig.suggested_action}")
        lines.append(f"- **\u5f71\u54cd\u8303\u56f4:** {paths_str}")

        status = "PROPOSED" if level == ProposalLevel.PROPOSAL else "LOGGED"
        lines.append(f"- **\u72b6\u6001:** {status}")
        lines.append(f"- **\u4fe1\u53f7\u5f3a\u5ea6:** {sig.occurrence_count} \u6b21\u51fa\u73b0\uff0c\u4e25\u91cd\u7ea7\u522b {sig.severity}")
        lines.append("")

        return "\n".join(lines)

    def _append_to_evolution_log(self, entries: List[str]) -> None:
        """Insert entries above the append marker in EVOLUTION_LOG.md."""
        if not self._log_path.exists():
            return

        content = self._log_path.read_text(encoding="utf-8")
        marker_idx = content.find(_APPEND_MARKER)
        if marker_idx == -1:
            return

        block = "\n".join(entries) + "\n---\n\n"
        new_content = content[:marker_idx] + block + content[marker_idx:]
        self._log_path.write_text(new_content, encoding="utf-8")

    def _write_suggestions(self, suggestions: List[dict]) -> None:
        """Write project-level suggestions JSON and summary Markdown."""
        json_path = self._out_dir / "suggestions.json"
        json_path.write_text(
            json.dumps(suggestions, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        md_path = self._out_dir / "summary.md"
        lines = [
            "# InSynBio Self-Evolution \u2014 Signal Summary",
            "",
            f"Generated: {date.today().isoformat()}",
            f"Total signals: {len(suggestions)}",
            "",
        ]
        for s in suggestions:
            level_icon = "\u26a0\ufe0f" if s["level"] == "PROPOSAL" else "\u2139\ufe0f"
            lines.append(f"### {level_icon} {s['title']}")
            lines.append(f"- Level: **{s['level']}**  |  Severity: {s['severity']}  |  Count: {s['occurrence_count']}")
            lines.append(f"- Action: {s['suggested_action']}")
            if s["affected_projects"]:
                lines.append(f"- Projects: {', '.join(s['affected_projects'][:5])}")
            lines.append("")

        md_path.write_text("\n".join(lines), encoding="utf-8")


def run_evolution_cycle(dry_run: bool = False) -> dict:
    """One-shot convenience: load events -> analyze -> propose.

    Can be called from CLI or integrated into post-pipeline hooks.
    """
    from core.evolution.run_event import RunEventStore
    from core.evolution.signal_analyzer import SignalAnalyzer

    store = RunEventStore()
    analyzer = SignalAnalyzer(store)
    signals = analyzer.analyze()

    engine = ProposalEngine()
    return engine.process(signals, dry_run=dry_run)
