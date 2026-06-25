"""
IntegrityReporter: emit unified JSON, CSV, and Markdown reports.

Outputs:
  reports/site_integrity_report.json   machine-readable full findings
  reports/site_integrity_report.csv    spreadsheet-friendly flat table
  reports/site_integrity_summary.md    human-readable release summary

Exit code semantics (returned by .exit_code()):
  0  all findings resolved or overridden (or only INFO/LOW remain)
  1  one or more HIGH or MEDIUM unresolved findings
"""
from __future__ import annotations

import csv
import json
import textwrap
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .repairs import Repair
from .validators import Finding, Severity


class IntegrityReporter:
    """Collect findings and repairs, then emit reports."""

    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    # ── public ────────────────────────────────────────────────────────────
    def write(
        self,
        findings: list[Finding],
        repairs: list[Repair],
        run_metadata: dict | None = None,
    ) -> None:
        self._write_json(findings, repairs, run_metadata)
        self._write_csv(findings)
        self._write_markdown(findings, repairs, run_metadata)

    def exit_code(self, findings: list[Finding]) -> int:
        """Return 1 if any unresolved HIGH or MEDIUM finding exists."""
        for f in findings:
            if f.is_overridden or f.is_auto_repaired:
                continue
            if f.severity in (Severity.HIGH, Severity.MEDIUM):
                return 1
        return 0

    # ── JSON ──────────────────────────────────────────────────────────────
    def _write_json(
        self,
        findings: list[Finding],
        repairs: list[Repair],
        meta: dict | None,
    ) -> None:
        now = datetime.now(tz=timezone.utc).isoformat()
        payload = {
            "generated_at": now,
            "metadata": meta or {},
            "summary": self._summary_counts(findings),
            "findings": [f.as_dict() for f in findings],
            "repairs": [
                {
                    "repair_type": r.repair_type,
                    "file_path": r.file_path,
                    "json_path": r.json_path,
                    "old_value": r.old_value[:200],
                    "new_value": r.new_value[:200],
                    "rationale": r.rationale,
                    "applied": r.applied,
                }
                for r in repairs
            ],
        }
        out = self.reports_dir / "site_integrity_report.json"
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[report] {out}")

    # ── CSV ───────────────────────────────────────────────────────────────
    def _write_csv(self, findings: list[Finding]) -> None:
        out = self.reports_dir / "site_integrity_report.csv"
        fieldnames = [
            "check_id",
            "severity",
            "entity_type",
            "value",
            "file_path",
            "json_path",
            "message",
            "detail",
            "is_auto_repaired",
            "repaired_value",
            "is_overridden",
            "override_reason",
        ]
        with out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames)
            w.writeheader()
            for f in findings:
                row = f.as_dict()
                row["value"] = str(row["value"])[:300]
                row["detail"] = str(row["detail"])[:500]
                w.writerow({k: row[k] for k in fieldnames})
        print(f"[report] {out}")

    # ── Markdown ──────────────────────────────────────────────────────────
    def _write_markdown(
        self,
        findings: list[Finding],
        repairs: list[Repair],
        meta: dict | None,
    ) -> None:
        now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        counts = self._summary_counts(findings)
        applied = [r for r in repairs if r.applied]
        pending = [r for r in repairs if not r.applied]

        lines: list[str] = [
            "# Site Integrity Pipeline — Summary",
            "",
            f"**Generated**: {now}",
            "",
        ]

        if meta:
            lines += [
                "## Run Parameters",
                "",
                *[f"- **{k}**: {v}" for k, v in meta.items()],
                "",
            ]

        lines += [
            "## Finding Counts",
            "",
            f"| Severity | Total | Unresolved | Auto-repaired | Overridden |",
            f"|----------|-------|------------|---------------|------------|",
        ]
        for sev in ("HIGH", "MEDIUM", "LOW", "INFO"):
            total = counts[sev]["total"]
            unresolved = counts[sev]["unresolved"]
            repaired = counts[sev]["repaired"]
            overridden = counts[sev]["overridden"]
            lines.append(f"| {sev} | {total} | {unresolved} | {repaired} | {overridden} |")
        lines.append("")

        # Unresolved HIGH
        unresolved_high = [
            f for f in findings
            if f.severity == Severity.HIGH
            and not f.is_overridden
            and not f.is_auto_repaired
        ]
        if unresolved_high:
            lines += [
                "## Unresolved HIGH Severity Findings",
                "",
                "These must be resolved before deployment.",
                "",
            ]
            for f in unresolved_high[:50]:
                lines += [
                    f"### `{f.check_id}` — {f.entity_type}: `{str(f.value)[:80]}`",
                    f"- **File**: `{f.file_path}`",
                    f"- **Path**: `{f.json_path}`",
                    f"- **Message**: {f.message}",
                ]
                if f.detail:
                    lines.append(f"- **Detail**: {f.detail[:300]}")
                lines.append("")
            if len(unresolved_high) > 50:
                lines.append(f"*(… and {len(unresolved_high) - 50} more — see CSV for full list)*\n")

        # Unresolved MEDIUM
        unresolved_med = [
            f for f in findings
            if f.severity == Severity.MEDIUM
            and not f.is_overridden
            and not f.is_auto_repaired
        ]
        if unresolved_med:
            lines += [
                "## Unresolved MEDIUM Severity Findings",
                "",
            ]
            for f in unresolved_med[:30]:
                lines.append(
                    f"- `{f.check_id}` | `{str(f.value)[:60]}` | `{f.file_path}` — {f.message[:200]}"
                )
            if len(unresolved_med) > 30:
                lines.append(f"*(… and {len(unresolved_med) - 30} more)*")
            lines.append("")

        # Applied repairs
        if applied:
            lines += [
                "## Auto-Repairs Applied",
                "",
                f"**{len(applied)} repair(s) applied automatically.**",
                "",
            ]
            by_type = Counter(r.repair_type for r in applied)
            for rtype, cnt in by_type.most_common():
                lines.append(f"- `{rtype}`: {cnt}")
            lines.append("")

        # Pending repairs (dry-run or not applicable)
        if pending:
            lines += [
                "## Pending Repairs (dry-run / not applied)",
                "",
            ]
            for r in pending[:20]:
                lines.append(
                    f"- `{r.repair_type}` in `{r.file_path}` ({r.json_path}): "
                    f"`{str(r.old_value)[:60]}` → `{str(r.new_value)[:60]}` — {r.rationale}"
                )
            if len(pending) > 20:
                lines.append(f"*(… and {len(pending) - 20} more)*")
            lines.append("")

        # Gate status
        unresolved_blocking = [
            f for f in findings
            if f.severity in (Severity.HIGH, Severity.MEDIUM)
            and not f.is_overridden
            and not f.is_auto_repaired
        ]
        if unresolved_blocking:
            lines += [
                "## Pre-Deploy Gate: BLOCKED",
                "",
                f"**{len(unresolved_blocking)} unresolved HIGH/MEDIUM finding(s) must be addressed.**",
                "",
                "Run with `--apply` to auto-repair safe issues, then re-run to confirm.",
                "",
            ]
        else:
            lines += [
                "## Pre-Deploy Gate: PASS",
                "",
                "No unresolved HIGH or MEDIUM findings. Safe to proceed with deployment.",
                "",
            ]

        out = self.reports_dir / "site_integrity_summary.md"
        out.write_text("\n".join(lines), encoding="utf-8")
        print(f"[report] {out}")

    # ── helpers ───────────────────────────────────────────────────────────
    @staticmethod
    def _summary_counts(findings: list[Finding]) -> dict:
        counts: dict = {
            sev: {"total": 0, "unresolved": 0, "repaired": 0, "overridden": 0}
            for sev in ("HIGH", "MEDIUM", "LOW", "INFO")
        }
        for f in findings:
            sev = f.severity.value
            if sev not in counts:
                counts[sev] = {"total": 0, "unresolved": 0, "repaired": 0, "overridden": 0}
            counts[sev]["total"] += 1
            if f.is_auto_repaired:
                counts[sev]["repaired"] += 1
            elif f.is_overridden:
                counts[sev]["overridden"] += 1
            else:
                counts[sev]["unresolved"] += 1
        return counts
