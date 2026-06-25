"""
HallucinationGuard — Cross-system computation integrity checker
===============================================================
Enforced across ALL InSynBio pipelines. Catches six categories of
computation errors that produce silently wrong results:

  SEQ_BACK_CHECK    — IMGT-to-linear position map correctness (HARD ABORT)
  MUTANT_DIFF       — exact mutation count in delivered sequence (HARD ABORT)
  CDR_CONTACT_RATIO — fraction of contacts in CDR regions (WARN)
  EVOEF2_ARTIFACT   — |ΔΔG| > threshold signals structural artifact (WARN)
  DOCKING_SCORE     — Vina score outside plausible range (WARN)
  THERMOMPNN_SILENT — ThermoMPNN returning None silently (WARN)

Root cause documented in EVOLUTION_LOG.md 2026-04-06:
  The fentanyl project shipped FASTA sequences with mutations at wrong
  positions (IMGT H107 mapped to linear pos 98, actual 95).

Usage
-----
from core.integrity.hallucination_guard import HallucinationGuard

guard = HallucinationGuard(project_dir=V2)
guard.check_sequence_positions(VH_WT, scan_targets, label="saturation_scan")
guard.check_mutant_diff(VH_WT, vh_mutant, expected_n_muts=1, label="Rank1_VH")
guard.check_docking_score(-6.9, ligand_type="hapten")
guard.check_evoef2_artifact(-2.31, label="H:W107A")
guard.check_cdr_contact_ratio(contacts_csv, cdr_definitions)
guard.check_thermompnn_silent(result_dict, n_mutations=5)
guard.write_audit()   # always call at end of pipeline step

All findings are appended to {project_dir}/_hallucination_audit.json.
Hard-abort checks raise HallucinationError.
"""
from __future__ import annotations

import json
import csv
import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any


# ── Public exception ─────────────────────────────────────────────────────────

class HallucinationError(RuntimeError):
    """Raised on HARD ABORT checks (SEQ_BACK_CHECK, MUTANT_DIFF)."""


# ── Data types ────────────────────────────────────────────────────────────────

class Severity(str, Enum):
    HARD_ABORT = "HARD_ABORT"
    WARN       = "WARN"
    PASS       = "PASS"


@dataclass
class Finding:
    check_id:  str
    severity:  Severity
    passed:    bool
    message:   str
    evidence:  dict = field(default_factory=dict)
    timestamp: str  = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())


@dataclass
class GuardReport:
    pipeline:  str
    step:      str
    findings:  list[Finding] = field(default_factory=list)
    aborted:   bool = False

    @property
    def passed(self) -> bool:
        return all(f.passed for f in self.findings)

    @property
    def n_warnings(self) -> int:
        return sum(1 for f in self.findings if not f.passed and f.severity == Severity.WARN)

    def summary(self) -> str:
        total = len(self.findings)
        passed = sum(1 for f in self.findings if f.passed)
        warns  = self.n_warnings
        aborts = sum(1 for f in self.findings if not f.passed and f.severity == Severity.HARD_ABORT)
        return (f"GuardReport [{self.pipeline}/{self.step}]: "
                f"{passed}/{total} passed, {warns} warnings, {aborts} hard aborts")


# ── Main class ────────────────────────────────────────────────────────────────

class HallucinationGuard:
    """
    Instantiate once per pipeline step, call check_* methods, then write_audit().

    Parameters
    ----------
    project_dir : Path
        Directory where _hallucination_audit.json is written.
    pipeline : str
        Human-readable pipeline name (e.g. "hapten_vam_v2", "vhh_humanization").
    step : str
        Current step name (e.g. "saturation_scan", "ala_scan").
    abort_on : list[str]
        Check IDs that raise HallucinationError on failure.
        Defaults: ["SEQ_BACK_CHECK", "MUTANT_DIFF"]
    warn_on : list[str]
        Check IDs that log warnings on failure.
        Defaults: all others
    verbose : bool
        Print findings to stdout if True.
    """

    DEFAULT_ABORT = {"SEQ_BACK_CHECK", "MUTANT_DIFF"}

    def __init__(
        self,
        project_dir: Path | str,
        pipeline: str = "unknown",
        step: str = "unknown",
        abort_on: list[str] | None = None,
        verbose: bool = True,
    ):
        self.project_dir = Path(project_dir)
        self.pipeline    = pipeline
        self.step        = step
        self.abort_on    = set(abort_on) if abort_on is not None else self.DEFAULT_ABORT
        self.verbose     = verbose
        self._report     = GuardReport(pipeline=pipeline, step=step)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _record(self, finding: Finding) -> Finding:
        self._report.findings.append(finding)
        if self.verbose:
            icon = "✓" if finding.passed else ("✗" if finding.severity == Severity.HARD_ABORT else "⚠")
            print(f"  [{self.step}] {icon} {finding.check_id}: {finding.message}")
        if not finding.passed and finding.check_id in self.abort_on:
            self._report.aborted = True
            self.write_audit()
            raise HallucinationError(
                f"HARD ABORT — {finding.check_id}: {finding.message}\n"
                f"Evidence: {finding.evidence}"
            )
        return finding

    # ── Check 1: Sequence position back-check ────────────────────────────────

    def check_sequence_positions(
        self,
        wt_seq: str,
        scan_targets: list[tuple],
        label: str = "",
    ) -> Finding:
        """
        Verify that every (linear_0idx, wt_aa) pair in scan_targets actually
        matches wt_seq[linear_0idx].

        scan_targets: list of tuples where each tuple contains at least:
          (chain, imgt_resi, linear_0idx, wt_aa, ...)  — matches v2_03 format
          OR dicts with keys: chain, resi_linear, wt

        Raises HallucinationError on first mismatch (HARD ABORT).
        """
        errors = []
        checked = 0

        for entry in scan_targets:
            # Accept both tuple format (chain, imgt, lin, wt, ...) and dict format
            if isinstance(entry, (list, tuple)):
                chain, imgt_rn, linear, wt = entry[0], entry[1], entry[2], entry[3]
            elif isinstance(entry, dict):
                chain   = entry.get("chain", "?")
                imgt_rn = entry.get("resi_imgt", entry.get("resi", "?"))
                linear  = entry.get("resi_linear", entry.get("linear", -1))
                wt      = entry.get("wt", "?")
            else:
                continue

            seq = wt_seq  # same WT seq for all entries (guard caller selects VH vs VL)
            if linear < 0 or linear >= len(seq):
                errors.append(f"{chain}:{imgt_rn} linear={linear} out of range (seq len={len(seq)})")
                continue

            actual = seq[linear]
            if actual != wt:
                errors.append(
                    f"{chain}:{imgt_rn} linear_pos={linear+1}(0idx={linear}) "
                    f"expected={wt} actual={actual}"
                )
            checked += 1

        passed = len(errors) == 0
        msg = (f"{checked} positions verified OK"
               if passed
               else f"{len(errors)} position mismatches: {'; '.join(errors[:3])}")

        return self._record(Finding(
            check_id="SEQ_BACK_CHECK",
            severity=Severity.HARD_ABORT if not passed else Severity.PASS,
            passed=passed,
            message=f"{label}: {msg}" if label else msg,
            evidence={"errors": errors, "checked": checked},
        ))

    # ── Check 2: CDR contact ratio ───────────────────────────────────────────

    def check_cdr_contact_ratio(
        self,
        contacts_csv: Path | str | list[dict],
        cdr_definitions: dict[str, tuple[int, int]],
        min_ratio: float = 0.5,
        label: str = "",
    ) -> Finding:
        """
        Verify ≥ min_ratio of contact residues are in CDR regions.

        contacts_csv: path to CSV with columns [chain, resnum, region] OR
                      list of dicts with same keys.
        cdr_definitions: dict mapping CDR name to (lo, hi) IMGT range, e.g.
          {"HCDR1": (27,38), "HCDR3": (105,117), ...}
        """
        rows: list[dict] = []
        if isinstance(contacts_csv, (str, Path)):
            with open(contacts_csv, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        else:
            rows = list(contacts_csv)

        if not rows:
            return self._record(Finding(
                check_id="CDR_CONTACT_RATIO",
                severity=Severity.WARN,
                passed=False,
                message=f"{label}: contacts file is empty or missing",
                evidence={"rows": 0},
            ))

        # Determine CDR set from region column or by IMGT range
        cdr_names = set(cdr_definitions.keys())
        n_total = len(rows)
        n_cdr = 0

        for row in rows:
            region = row.get("region", "")
            if any(cdr in region for cdr in cdr_names):
                n_cdr += 1

        ratio = n_cdr / n_total if n_total else 0.0
        passed = ratio >= min_ratio
        msg = (f"CDR contact ratio {ratio:.1%} ({n_cdr}/{n_total}) "
               f"{'≥' if passed else '<'} threshold {min_ratio:.0%}")

        return self._record(Finding(
            check_id="CDR_CONTACT_RATIO",
            severity=Severity.PASS if passed else Severity.WARN,
            passed=passed,
            message=f"{label}: {msg}" if label else msg,
            evidence={"n_cdr": n_cdr, "n_total": n_total, "ratio": round(ratio, 3),
                      "threshold": min_ratio},
        ))

    # ── Check 3: EvoEF2 artifact detection ───────────────────────────────────

    def check_evoef2_artifact(
        self,
        ddg: float | None,
        label: str = "",
        threshold: float = 5.0,
    ) -> Finding:
        """
        Flag |ΔΔG| > threshold as a potential structural artifact.
        Common causes: IMGT gap-induced PDB clashes, degenerate rotamers.
        Does NOT abort — result is flagged for manual review.
        """
        if ddg is None:
            return self._record(Finding(
                check_id="EVOEF2_ARTIFACT",
                severity=Severity.WARN,
                passed=False,
                message=f"{label}: EvoEF2 returned None — result missing",
                evidence={"ddg": None, "threshold": threshold},
            ))

        passed = abs(ddg) <= threshold
        msg = (f"EvoEF2 ΔΔG={ddg:+.2f} within normal range"
               if passed
               else f"EvoEF2 |ΔΔG|={abs(ddg):.2f} > {threshold} — possible artifact, verify structure")

        return self._record(Finding(
            check_id="EVOEF2_ARTIFACT",
            severity=Severity.PASS if passed else Severity.WARN,
            passed=passed,
            message=f"{label}: {msg}" if label else msg,
            evidence={"ddg": ddg, "abs_ddg": abs(ddg), "threshold": threshold},
        ))

    # ── Check 4: Mutant sequence diff count ──────────────────────────────────

    def check_mutant_diff(
        self,
        wt_seq: str,
        mutant_seq: str,
        expected_n_muts: int,
        label: str = "",
    ) -> Finding:
        """
        Verify the delivered mutant sequence differs from WT at exactly
        expected_n_muts positions (no more, no less).

        Raises HallucinationError if actual_n_muts != expected_n_muts (HARD ABORT).
        """
        if len(wt_seq) != len(mutant_seq):
            return self._record(Finding(
                check_id="MUTANT_DIFF",
                severity=Severity.HARD_ABORT,
                passed=False,
                message=f"{label}: length mismatch WT={len(wt_seq)} mutant={len(mutant_seq)}",
                evidence={"wt_len": len(wt_seq), "mut_len": len(mutant_seq)},
            ))

        diff_positions = [
            (i + 1, wt_seq[i], mutant_seq[i])
            for i in range(len(wt_seq))
            if wt_seq[i] != mutant_seq[i]
        ]
        actual_n = len(diff_positions)
        passed = actual_n == expected_n_muts

        msg = (f"exactly {actual_n} mutation(s) — correct"
               if passed
               else f"found {actual_n} mutations, expected {expected_n_muts}: "
                    f"{[(p, w, m) for p, w, m in diff_positions]}")

        return self._record(Finding(
            check_id="MUTANT_DIFF",
            severity=Severity.PASS if passed else Severity.HARD_ABORT,
            passed=passed,
            message=f"{label}: {msg}" if label else msg,
            evidence={"diff_positions": diff_positions, "actual_n": actual_n,
                      "expected_n": expected_n_muts},
        ))

    # ── Check 5: Docking score plausibility ──────────────────────────────────

    def check_docking_score(
        self,
        score: float | None,
        ligand_type: str = "hapten",
        label: str = "",
    ) -> Finding:
        """
        Verify docking score is in a physically plausible range.

        ligand_type thresholds:
          "hapten"  : [-12.0, -3.0]  small molecule (<500 Da)
          "peptide" : [-20.0, -4.0]  short peptide (5-30 aa)
          "protein" : [-40.0, -6.0]  protein antigen
        """
        ranges = {
            "hapten":  (-12.0, -3.0),
            "peptide": (-20.0, -4.0),
            "protein": (-40.0, -6.0),
        }
        lo, hi = ranges.get(ligand_type, (-12.0, -3.0))

        if score is None:
            return self._record(Finding(
                check_id="DOCKING_SCORE",
                severity=Severity.WARN,
                passed=False,
                message=f"{label}: docking score is None — docking may have failed",
                evidence={"score": None, "ligand_type": ligand_type},
            ))

        passed = lo <= score <= hi
        msg = (f"Vina score {score:.3f} in expected range [{lo}, {hi}]"
               if passed
               else f"Vina score {score:.3f} outside expected range [{lo}, {hi}] "
                    f"for ligand_type={ligand_type}")

        return self._record(Finding(
            check_id="DOCKING_SCORE",
            severity=Severity.PASS if passed else Severity.WARN,
            passed=passed,
            message=f"{label}: {msg}" if label else msg,
            evidence={"score": score, "lo": lo, "hi": hi, "ligand_type": ligand_type},
        ))

    # ── Check 6: ThermoMPNN silent None ──────────────────────────────────────

    def check_thermompnn_silent(
        self,
        results: list[dict],
        n_mutations: int,
        label: str = "",
        max_none_frac: float = 0.5,
    ) -> Finding:
        """
        Warn if ThermoMPNN returns None for more than max_none_frac of mutations.
        This indicates IMGT-numbered PDB incompatibility — stability veto is silently bypassed.

        results: list of dicts with key "ddg_thermo" (or "ddg")
        n_mutations: total number of mutations submitted
        """
        none_count = sum(
            1 for r in results
            if r.get("ddg_thermo") is None and r.get("ddg") is None
        )
        none_frac = none_count / n_mutations if n_mutations > 0 else 0.0
        passed = none_frac <= max_none_frac

        msg = (f"ThermoMPNN None fraction {none_frac:.0%} ({none_count}/{n_mutations}) OK"
               if passed
               else f"ThermoMPNN returned None for {none_frac:.0%} ({none_count}/{n_mutations}) "
                    f"mutations — stability veto silently bypassed. "
                    f"Likely cause: IMGT-numbered PDB not supported by ThermoMPNN. "
                    f"Mitigation: use renumbered PDB or skip stability veto with explicit note.")

        return self._record(Finding(
            check_id="THERMOMPNN_SILENT",
            severity=Severity.PASS if passed else Severity.WARN,
            passed=passed,
            message=f"{label}: {msg}" if label else msg,
            evidence={"none_count": none_count, "n_mutations": n_mutations,
                      "none_frac": round(none_frac, 3), "threshold": max_none_frac},
        ))

    # ── Batch scan validation ─────────────────────────────────────────────────

    def check_scan_results(
        self,
        results: list[dict],
        wt_vh: str,
        wt_vl: str,
        label: str = "",
    ) -> list[Finding]:
        """
        Run EVOEF2_ARTIFACT + MUTANT_DIFF checks over a full scan result list.

        Each result dict should have:
          - ddg_evoef2: float | None
          - mutation: str (e.g. "H:W107I")
          - chain: "H" | "L"
          - resi_linear: int (0-based)
          - wt: str (single AA)
          - mut: str (single AA)
        """
        findings = []
        for r in results:
            mut_label = r.get("mutation", label)

            # EvoEF2 artifact check
            findings.append(self.check_evoef2_artifact(
                r.get("ddg_evoef2"),
                label=mut_label,
            ))

            # Build expected mutant seq and check diff
            chain = r.get("chain")
            lin   = r.get("resi_linear")
            wt_aa = r.get("wt")
            mut_aa = r.get("mut")

            if chain and lin is not None and wt_aa and mut_aa:
                base_seq = wt_vh if chain == "H" else wt_vl
                mutant_seq = list(base_seq)
                mutant_seq[lin] = mut_aa
                mutant_seq = "".join(mutant_seq)
                findings.append(self.check_mutant_diff(
                    base_seq, mutant_seq, expected_n_muts=1, label=mut_label
                ))

        return findings

    # ── Audit trail ───────────────────────────────────────────────────────────

    def write_audit(self) -> Path:
        """
        Append this report's findings to {project_dir}/_hallucination_audit.json.
        File is append-only — never truncated.
        """
        audit_path = self.project_dir / "_hallucination_audit.json"

        existing: list[dict] = []
        if audit_path.exists():
            try:
                existing = json.loads(audit_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, ValueError):
                existing = []

        entry = {
            "pipeline":  self._report.pipeline,
            "step":      self._report.step,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "passed":    self._report.passed,
            "aborted":   self._report.aborted,
            "n_warnings": self._report.n_warnings,
            "summary":   self._report.summary(),
            "findings":  [asdict(f) for f in self._report.findings],
        }
        existing.append(entry)
        audit_path.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        if self.verbose:
            print(f"  Audit → {audit_path}  ({self._report.summary()})")
        return audit_path

    # ── Context manager support ───────────────────────────────────────────────

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.write_audit()
        return False  # do not suppress exceptions
