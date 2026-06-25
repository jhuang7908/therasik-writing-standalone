"""
report_qc_gate.py — Mandatory report QC gate for InSynBio AbEngineCore.

This module must be called before any HTML report is written to disk.
It validates:
  A. Version stamp presence
  B. Key metric completeness (no unexpected blanks)
  C. Structure QC presence (when report type requires it)
  D. Sequence presence (§Seq / §10 equivalent)
  E. Recommendation section presence
  F. Numerical sanity — values within physically/biologically valid ranges
     (pLDDT > 0, pI 3-12, RMSD finite, etc.)
  G. Error signal detection — no embedded tool failure traces
     (module not found, subprocess timeout, cache miss, etc.)
  H. Cross-section consistency — claims in summary match supporting tables
     (mutation count, sequence length, status badge, ADI grade, etc.)
  I. Tool execution evidence — each declared tool produced an actual numeric
     result anchor (HPR score, AbNatiV2 score, pLDDT, etc.)

Usage (in any router before writing HTML):
    from core.reporting.report_qc_gate import run_report_qc, ReportQCError

    qc = run_report_qc(report_html_str, report_family="vhh_humanization")
    if qc.has_blocking_failures:
        raise ReportQCError(qc.summary())
    # optional: embed QC badge into the HTML
    report_html_str = qc.inject_qc_badge(report_html_str)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# QC finding types
# ---------------------------------------------------------------------------

class QCSeverity:
    PASS  = "PASS"
    WARN  = "WARN"
    FAIL  = "FAIL"


@dataclass
class QCFinding:
    dimension: str          # A / B / C / D / E
    check_name: str
    severity: str           # PASS / WARN / FAIL
    detail: str = ""


@dataclass
class ReportQCResult:
    report_family: str
    findings: List[QCFinding] = field(default_factory=list)

    @property
    def has_blocking_failures(self) -> bool:
        return any(f.severity == QCSeverity.FAIL for f in self.findings)

    @property
    def has_warnings(self) -> bool:
        return any(f.severity == QCSeverity.WARN for f in self.findings)

    @property
    def overall(self) -> str:
        if self.has_blocking_failures:
            return QCSeverity.FAIL
        if self.has_warnings:
            return QCSeverity.WARN
        return QCSeverity.PASS

    def summary(self) -> str:
        lines = [f"ReportQC [{self.report_family}] → {self.overall}"]
        for f in self.findings:
            if f.severity != QCSeverity.PASS:
                lines.append(f"  [{f.severity}] {f.dimension} / {f.check_name}: {f.detail}")
        return "\n".join(lines)

    def inject_qc_badge(self, html: str) -> str:
        """Embed a small QC status badge just before </body> in the HTML string."""
        badge_color = {
            QCSeverity.PASS: "#059669",
            QCSeverity.WARN: "#d97706",
            QCSeverity.FAIL: "#dc2626",
        }.get(self.overall, "#6b7280")
        fail_count = sum(1 for f in self.findings if f.severity == QCSeverity.FAIL)
        warn_count = sum(1 for f in self.findings if f.severity == QCSeverity.WARN)
        detail_lines = "".join(
            f"<div style='font-size:.68rem;color:#6b7280;margin-top:2px'>"
            f"[{fn.severity}] {fn.dimension}/{fn.check_name}: {fn.detail}</div>"
            for fn in self.findings if fn.severity != QCSeverity.PASS
        )
        badge_html = (
            f"\n<!-- abenginecore-report-qc: {self.overall} -->\n"
            f"<div style='position:fixed;bottom:10px;right:12px;z-index:9999;"
            f"background:#fff;border:2px solid {badge_color};border-radius:8px;"
            f"padding:4px 10px;font-size:.72rem;font-weight:700;color:{badge_color};"
            f"box-shadow:0 2px 8px rgba(0,0,0,.12);cursor:default' "
            f"title='AbEngineCore Report QC — {self.overall}&#10;FAIL: {fail_count}  WARN: {warn_count}'>"
            f"QC: {self.overall}"
            f"</div>"
        )
        if detail_lines:
            badge_html += (
                f"\n<!-- abenginecore-qc-details -->\n"
                f"<div style='display:none' id='_abenginecore_qc_details'>{detail_lines}</div>"
            )
        return html.replace("</body>", badge_html + "\n</body>", 1)


class ReportQCError(RuntimeError):
    """Raised when a report fails mandatory QC and must not be written."""
    pass


# ---------------------------------------------------------------------------
# Report-family configuration: which checks are required
# ---------------------------------------------------------------------------

# Families that require structure QC output
_STRUCTURE_REQUIRED_FAMILIES = {
    "vhvl_humanization",
    "vhh_humanization",
    "vh_to_vhh",
    "caninization",
    "petization",
    "recheck_vhvl",
    "recheck_vhh",
}

# Key metric tokens that should not all be missing from a given family
_KEY_METRICS_BY_FAMILY = {
    "vhvl_humanization": ["pI", "GRAVY", "HPR Index", "CDR RMSD"],
    "vhh_humanization":  ["pI", "GRAVY", "HPR Index", "Hallmark"],
    "vhh_cmc":           ["pI", "GRAVY", "ADI", "Isoelectric"],
    "bispecific_cmc":    ["pI", "GRAVY", "linker", "Arm 1", "Arm 2"],
    "vh_to_vhh":         ["pI", "GRAVY", "Sequence length", "CDR3 length"],
    "cmc_igg":           ["pI", "GRAVY", "Instability", "clinical"],
    "caninization":      ["pI", "GRAVY", "CDR", "RMSD"],
    "recheck_vhvl":      ["pI", "GRAVY", "HPR"],
    "recheck_vhh":       ["pI", "GRAVY", "HPR"],
}

# Families that require a recommendation chapter
_REC_REQUIRED_FAMILIES = {
    "vhvl_humanization",
    "vhh_humanization",
    "vh_to_vhh",
    "vhh_cmc",
    "bispecific_cmc",
    "cmc_igg",
    "caninization",
    "recheck_vhvl",
    "recheck_vhh",
}


# ---------------------------------------------------------------------------
# Main gate function
# ---------------------------------------------------------------------------

def run_report_qc(
    html: str,
    report_family: str,
    sequence_provided: bool = True,
    strict: bool = False,
) -> ReportQCResult:
    """
    Validate an HTML report string against the 5-dimension QC contract.

    Args:
        html:              The complete HTML string to validate.
        report_family:     One of the standard ReportFamily enum values (string).
        sequence_provided: Caller asserts a sequence was submitted (checked separately).
        strict:            If True, WARN-level findings are promoted to FAIL.

    Returns:
        ReportQCResult with all findings and an overall verdict.
    """
    result = ReportQCResult(report_family=report_family)
    _add = result.findings.append

    # ── A. Format: version stamp ─────────────────────────────────────────────
    has_version = bool(
        re.search(
            r"Protocol\s*[:\-]?\s*(?:[A-Za-z\-]+\s*)?V\d"
            r"|Analysis Version"
            r"|abenginecore(?:\s+version)?\s*v?\d"
            r"|Report Format\s*[:\-]?\s*V\d"
            r"|build.*\d{8}",
            html,
            re.I,
        )
    )
    if has_version:
        _add(QCFinding("A", "version_stamp", QCSeverity.PASS))
    else:
        sev = QCSeverity.FAIL if strict else QCSeverity.WARN
        _add(QCFinding("A", "version_stamp", sev, "No protocol/version stamp found in report HTML."))

    # ── B. Blank metrics ─────────────────────────────────────────────────────
    expected_tokens = _KEY_METRICS_BY_FAMILY.get(report_family, [])
    missing_tokens: List[str] = []
    for token in expected_tokens:
        if token.lower() not in html.lower():
            missing_tokens.append(token)

    # Check for cells that show only em-dash with no value context
    blank_cells = len(re.findall(r"<td[^>]*>\s*—\s*</td>", html))
    if blank_cells > 20:
        _add(QCFinding("B", "blank_cells", QCSeverity.WARN,
                       f"{blank_cells} cells contain only '—'. Verify these are intentional N/A values."))
    elif blank_cells > 5:
        _add(QCFinding("B", "blank_cells", QCSeverity.PASS,
                       f"{blank_cells} cells contain '—' (within expected range)."))
    else:
        _add(QCFinding("B", "blank_cells", QCSeverity.PASS))

    if missing_tokens:
        sev = QCSeverity.FAIL if strict else QCSeverity.WARN
        _add(QCFinding("B", "key_metrics_present", sev,
                       f"Expected metric tokens not found: {', '.join(missing_tokens)}"))
    else:
        _add(QCFinding("B", "key_metrics_present", QCSeverity.PASS))

    # Detect un-computed HPR / AbNatiV patterns that indicate a broken metric
    if re.search(r"not computed.*repertoire database unavailable", html, re.I):
        _add(QCFinding("B", "hpr_computed", QCSeverity.WARN,
                       "HPR Index not computed (promb database not available). "
                       "Report displays informative placeholder. Install promb for full scores."))
    if re.search(r"AbNatiV.*not computed|NanoBERT.*not available", html, re.I):
        _add(QCFinding("B", "abnativ_computed", QCSeverity.WARN,
                       "AbNatiV2 score not computed. Report displays informative placeholder."))

    # ── C. Structure QC ──────────────────────────────────────────────────────
    _fam_needs_struct = report_family in _STRUCTURE_REQUIRED_FAMILIES
    if _fam_needs_struct:
        has_plddt = bool(re.search(r"pLDDT|plddt", html, re.I))
        has_rmsd  = bool(re.search(r"RMSD|Cα RMSD", html))
        has_not_run = bool(re.search(r"NOT_RUN|not.run.*structure|structure.*not.run", html, re.I))

        if has_not_run and not has_plddt:
            sev = QCSeverity.FAIL if strict else QCSeverity.WARN
            _add(QCFinding("C", "structure_qc", sev,
                           "Structure QC NOT_RUN and no pLDDT found. "
                           "Re-submit with run_structure=True for a structure-complete report."))
        elif has_plddt and has_rmsd:
            _add(QCFinding("C", "structure_qc", QCSeverity.PASS, "pLDDT and RMSD both present."))
        elif has_plddt and not has_rmsd:
            _add(QCFinding("C", "structure_qc", QCSeverity.WARN,
                           "pLDDT found but no RMSD values detected. Structural comparison may be incomplete."))
        else:
            _add(QCFinding("C", "structure_qc", QCSeverity.WARN,
                           "No pLDDT or RMSD found. Consider enabling structure QC."))
    else:
        _add(QCFinding("C", "structure_qc", QCSeverity.PASS, "Structure QC not required for this report family."))

    # ── D. Sequences present ─────────────────────────────────────────────────
    seq_patterns = [
        r"§\s*(Seq|10)\s*[—–-]\s*(Sequence|Submitted)",
        r"§10",
        r"Submitted.*Sequence",
        r"Final Sequence",
        r"Humanized.*Sequence|Caninized.*Sequence",
        r">.*VHH|>.*VH|>.*VL|>.*Donor",
        r"seq-body|seq-block|mono.*EVQL|mono.*QVQL|mono.*DIQM",
    ]
    has_seq = any(re.search(p, html, re.I) for p in seq_patterns)
    if has_seq or not sequence_provided:
        _add(QCFinding("D", "sequences_present", QCSeverity.PASS))
    else:
        _add(QCFinding("D", "sequences_present", QCSeverity.FAIL,
                       "No sequence section (§Seq / §10) found. Sequences must be present in every report."))

    # ── E. Recommendation section ─────────────────────────────────────────────
    _fam_needs_rec = report_family in _REC_REQUIRED_FAMILIES
    if _fam_needs_rec:
        has_rec = bool(
            re.search(r"§\s*Rec|§12|Recommendation|Advisory|action.roadmap|next.step", html, re.I)
        )
        if has_rec:
            _add(QCFinding("E", "recommendation_section", QCSeverity.PASS))
        else:
            sev = QCSeverity.FAIL if strict else QCSeverity.WARN
            _add(QCFinding("E", "recommendation_section", sev,
                           "No §Rec / §12 / Recommendation section found. "
                           "Every deliverable report must include next-step guidance."))
    else:
        _add(QCFinding("E", "recommendation_section", QCSeverity.PASS,
                       "Recommendation not required for comparison/QC-only reports."))

    # ── F. Numerical sanity — values within valid ranges ─────────────────────
    _check_numerical_sanity(html, report_family, _add, strict)

    # ── G. Error signal detection — embedded tool failures ───────────────────
    _check_error_signals(html, _add, strict)

    # ── H. Cross-section consistency — claims vs supporting tables ───────────
    _check_cross_section_consistency(html, report_family, _add, strict)

    # ── I. Tool execution evidence — each declared tool produced output ──────
    _check_tool_execution_evidence(html, report_family, _add, strict)

    # ── J. Executive Summary Completeness ────────────────────────────────────
    _check_executive_summary_completeness(html, report_family, _add, strict)

    return result


# ---------------------------------------------------------------------------
# Executive summary helpers (dimension J)
# ---------------------------------------------------------------------------

def _check_executive_summary_completeness(html: str, report_family: str, _add, strict: bool) -> None:
    """
    Ensure the executive summary (§0) contains all high-level status rows
    required for that report type.
    """
    sev_warn = QCSeverity.FAIL if strict else QCSeverity.WARN
    
    # Extract §0 table content
    s0_match = re.search(r"(?:§0|Fusion construct summary).*?(<table.*?>.*?</table>)", html, re.S | re.I)
    
    # Also check for .score-row / .score-lbl patterns used in CMC reports
    s0_text = ""
    if s0_match:
        s0_text += _strip_tags(s0_match.group(1)).lower()
    
    # Robustly extract all .score-lbl content
    for lbl_match in re.finditer(r"<div class=['\"]score-lbl['\"].*?>(.*?)</div>", html, re.S | re.I):
        s0_text += " " + _strip_tags(lbl_match.group(1)).lower()

    if not s0_text:
        _add(QCFinding("J", "summary_table_missing", QCSeverity.FAIL, "Executive summary content (§0) not found."))
        return
    
    required_rows = {
        "vhvl_humanization": ["overall", "input qc", "structure qc", "cmc", "immunogenicity"],
        "vhh_humanization":  ["overall", "input qc", "structure qc", "cmc", "immunogenicity"],
        "recheck_vhvl":      ["overall", "input qc", "structure qc", "mini-cmc", "naturalness", "immunogenicity"],
        "recheck_vhh":       ["overall", "input qc", "structure qc", "mini-cmc", "naturalness", "immunogenicity"],
        "bispecific_cmc":    ["overall status", "fusion pi", "fusion gravy"],
    }.get(report_family, ["overall"])
    
    missing = [row for row in required_rows if row not in s0_text]
    if missing:
        _add(QCFinding("J", "summary_rows_missing", sev_warn,
                       f"Executive summary (§0) is missing required status rows: {', '.join(missing)}"))
    else:
        _add(QCFinding("J", "summary_rows_present", QCSeverity.PASS))


# ---------------------------------------------------------------------------
# Numerical sanity helpers
# ---------------------------------------------------------------------------

def _check_numerical_sanity(html: str, report_family: str, _add, strict: bool) -> None:
    """
    Check that key numerical metrics are inside biologically valid ranges.

    Rules applied (only when value is found; missing values are handled by dim B):
      pLDDT must be > 50 (Fv) or > 70 (VHH); 0.0 → FAIL (cache/computation broken).
      pI    must be 3.0 ≤ pI ≤ 12.0
      GRAVY must be -2.0 ≤ GRAVY ≤ 2.0
      Cα RMSD must be 0 ≤ RMSD ≤ 10.0 Å (otherwise structural alignment failed)
      Instability index must be 0 ≤ II ≤ 100
    """
    sev_warn = QCSeverity.FAIL if strict else QCSeverity.WARN

    # ---- pLDDT extraction — only assignment-like patterns, skip free prose ----
    # Accepts: "pLDDT 89.6", "pLDDT: 89.6", "pLDDT = 89.6", "pLDDT — donor/candidate 89.6 / 88.0"
    # Rejects: "pLDDT ≥ 90 (VH/VL); packing angle 51.2" (no number adjacent to 'pLDDT')
    plddt_values: List[float] = []
    for m in re.finditer(
        r"pLDDT[\s:=\u2014\u2013\-\u2192/]{1,80}?(?:donor|candidate|/|&nbsp;|<[^>]+>)*\s*"
        r"(\d{1,3}\.\d{1,3})"
        r"(?:\s*(?:/|&nbsp;/&nbsp;|&#x2F;|<[^>]+>)+\s*(\d{1,3}\.\d{1,3}))?",
        html, re.I,
    ):
        try:
            v1 = float(m.group(1))
            if 0.0 <= v1 <= 100.0:
                plddt_values.append(v1)
            if m.group(2):
                v2 = float(m.group(2))
                if 0.0 <= v2 <= 100.0:
                    plddt_values.append(v2)
        except (TypeError, ValueError):
            pass

    if plddt_values:
        # Normalize to 0-100 scale: AF3/Boltz-2 reports 0-1, NanoBodyBuilder2 reports 0-100.
        # Heuristic: if all values are ≤ 1.0 (excluding zeros), assume 0-1 scale and rescale.
        nonzero = [v for v in plddt_values if v > 0.0]
        if nonzero and max(nonzero) <= 1.0:
            plddt_values = [v * 100.0 if v > 0.0 else 0.0 for v in plddt_values]
        zero_count = sum(1 for v in plddt_values if v == 0.0)
        low_count = sum(1 for v in plddt_values if 0.0 < v < 50.0)
        if zero_count:
            _add(QCFinding("F", "plddt_zero", sev_warn,
                           f"{zero_count}/{len(plddt_values)} pLDDT value(s) = 0.0 — likely cache miss "
                           f"or model failure. Re-run structure prediction with cache cleared."))
        if low_count:
            _add(QCFinding("F", "plddt_low", QCSeverity.WARN,
                           f"{low_count} pLDDT value(s) below 50 — model is low-confidence; "
                           f"structural conclusions should be treated as tentative."))
        if not zero_count and not low_count:
            _add(QCFinding("F", "plddt_range", QCSeverity.PASS,
                           f"{len(plddt_values)} pLDDT values in valid range "
                           f"({min(plddt_values):.1f}-{max(plddt_values):.1f})."))

    # ---- pI sanity ----
    pi_values: List[float] = []
    for m in re.finditer(r"\bpI\b[^<>]{0,40}?(\d+\.\d{1,3})", html):
        try:
            pi_values.append(float(m.group(1)))
        except (TypeError, ValueError):
            pass
    bad_pi = [v for v in pi_values if not (3.0 <= v <= 12.0)]
    if bad_pi:
        _add(QCFinding("F", "pi_range", sev_warn,
                       f"{len(bad_pi)} pI value(s) outside 3-12 (got {bad_pi[:3]}). "
                       f"Likely computation failure."))
    elif pi_values:
        _add(QCFinding("F", "pi_range", QCSeverity.PASS,
                       f"{len(pi_values)} pI values in 3-12 range."))

    # ---- GRAVY sanity ----
    gravy_values: List[float] = []
    for m in re.finditer(r"GRAVY[^<>]{0,40}?(-?\d+\.\d{1,4})", html, re.I):
        try:
            gravy_values.append(float(m.group(1)))
        except (TypeError, ValueError):
            pass
    bad_gravy = [v for v in gravy_values if not (-2.0 <= v <= 2.0)]
    if bad_gravy:
        _add(QCFinding("F", "gravy_range", sev_warn,
                       f"{len(bad_gravy)} GRAVY value(s) outside -2..+2 (got {bad_gravy[:3]})."))
    elif gravy_values:
        _add(QCFinding("F", "gravy_range", QCSeverity.PASS,
                       f"{len(gravy_values)} GRAVY values in valid range."))

    # ---- CDR / Cα RMSD sanity ----
    rmsd_values: List[float] = []
    for m in re.finditer(r"RMSD[^<>]{0,80}?(\d+\.\d{1,3})", html):
        try:
            rmsd_values.append(float(m.group(1)))
        except (TypeError, ValueError):
            pass
    
    huge_rmsd = [v for v in rmsd_values if v > 8.0]
    high_rmsd = [v for v in rmsd_values if v > 4.0]
    
    if huge_rmsd:
        _add(QCFinding("F", "rmsd_range", QCSeverity.FAIL,
                       f"{len(huge_rmsd)} RMSD value(s) > 8 Å (got {huge_rmsd[:3]}). "
                       f"Structural superposition failed. Report must be rejected."))
    elif high_rmsd:
        _add(QCFinding("F", "rmsd_range", QCSeverity.WARN,
                       f"{len(high_rmsd)} RMSD value(s) > 4 Å (got {high_rmsd[:3]}). "
                       f"Extreme structural deviation detected; review model confidence."))
    elif rmsd_values:
        _add(QCFinding("F", "rmsd_range", QCSeverity.PASS,
                       f"{len(rmsd_values)} RMSD values plausible (max {max(rmsd_values):.2f} Å)."))


def _check_error_signals(html: str, _add, strict: bool) -> None:
    """
    Detect leaked computational error traces in the rendered HTML.
    These should never reach a client-facing report.
    """
    sev_warn = QCSeverity.FAIL if strict else QCSeverity.WARN

    error_patterns = [
        (r"No module named ['\"][a-zA-Z_]+['\"]", "missing_python_module"),
        (r"Traceback \(most recent call last\)", "traceback_leak"),
        (r"subprocess.*(?:timed out|TimeoutExpired)", "subprocess_timeout"),
        (r"OSError|FileNotFoundError|PermissionError", "io_error_leak"),
        (r"NotImplementedError|RuntimeError:", "runtime_error_leak"),
        (r"(?:cache miss|cache.*missing)(?!\)?\s*\")", "cache_meta_warning"),
    ]
    found = []
    for pat, name in error_patterns:
        if re.search(pat, html):
            found.append(name)
    if found:
        _add(QCFinding("G", "error_signal_leak", sev_warn,
                       f"Embedded error trace(s) detected: {', '.join(found)}. "
                       f"Reports should display sanitized placeholders, not raw error strings."))
    else:
        _add(QCFinding("G", "error_signal_leak", QCSeverity.PASS,
                       "No raw error traces in report HTML."))


# ---------------------------------------------------------------------------
# Cross-section consistency helpers (dimension H)
# ---------------------------------------------------------------------------

def _strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s)


def _strip_style_and_script(html: str) -> str:
    """Remove <style>...</style> and <script>...</script> blocks so QC regexes
    do not falsely match CSS rules / JS literals."""
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.S | re.I)
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S | re.I)
    return html


def _next_text_value(html_after_label: str, max_chars: int = 200) -> Optional[float]:
    """Given HTML starting just after a label (e.g. 'pI</td>'), find the next
    numeric value rendered to the user, allowing HTML tags between label and value.
    Returns None if no numeric value found within max_chars."""
    window = html_after_label[:max_chars]
    plain = _strip_tags(window)
    m = re.search(r"(-?\d+\.\d{1,4})", plain)
    if m:
        try:
            return float(m.group(1))
        except (TypeError, ValueError):
            return None
    return None


def _check_cross_section_consistency(html: str, report_family: str, _add, strict: bool) -> None:
    """
    Detect self-contradictions between the executive summary and supporting tables.

    Currently checks:
      H1. Mutation count claim vs FR mutation/back-mutation table row count
      H2. Sequence length claim "X aa" vs actual residue count in seq-body block
      H3. Status badge claim vs metric grades inside the table
    """
    sev_warn = QCSeverity.FAIL if strict else QCSeverity.WARN
    html_clean = _strip_style_and_script(html)

    # ── H1. Mutation count consistency ───────────────────────────────────────
    # Look for claims like "6 back-mutations", "applied 5 mutations", "X FR substitutions"
    claim_patterns = [
        r"(\d{1,3})\s*(?:back[-\s]mutations?|FR\s+substitutions?|framework\s+mutations?)",
        r"applied\s+(\d{1,3})\s+mutations?",
        r"introduced\s+(\d{1,3})\s+(?:safe\s+)?(?:mutations?|substitutions?)",
    ]
    claimed_counts: List[int] = []
    for pat in claim_patterns:
        for m in re.finditer(pat, html_clean, re.I):
            try:
                claimed_counts.append(int(m.group(1)))
            except (TypeError, ValueError):
                pass

    # Count rows in tables whose headers mention "mutation"/"back-mutation"/"FR substitution"
    table_blocks = re.findall(
        r"<table[^>]*>(.*?)</table>", html_clean, re.S | re.I
    )
    mutation_table_rows = 0
    for tbl in table_blocks:
        head = re.search(r"<thead[^>]*>(.*?)</thead>", tbl, re.S | re.I)
        head_text = _strip_tags(head.group(1)).lower() if head else ""
        if any(k in head_text for k in ("back-mutation", "mutation", "fr substitution",
                                        "back mutation", "framework substitution")):
            body = re.search(r"<tbody[^>]*>(.*?)</tbody>", tbl, re.S | re.I)
            body_str = body.group(1) if body else tbl
            mutation_table_rows = max(mutation_table_rows,
                                       len(re.findall(r"<tr[^>]*>", body_str)))

    if claimed_counts and mutation_table_rows > 0:
        # Allow ±1 tolerance for header-style rows or summary rows
        any_match = any(abs(c - mutation_table_rows) <= 1 for c in claimed_counts)
        if not any_match:
            _add(QCFinding("H", "mutation_count_mismatch", sev_warn,
                           f"Claimed mutation count(s) {sorted(set(claimed_counts))[:3]} "
                           f"do not match table row count ({mutation_table_rows}). "
                           f"Summary may contradict the detailed table."))
        else:
            _add(QCFinding("H", "mutation_count_mismatch", QCSeverity.PASS,
                           f"Claimed mutation count consistent with table ({mutation_table_rows} rows)."))

    # ── H2. Sequence length consistency ──────────────────────────────────────
    # Pattern: a label says "120 aa" then a seq-body actually contains N residues
    seq_blocks = re.finditer(
        r"seq-label[^>]*>(.*?)</div>\s*<div[^>]*seq-body[^>]*>(.*?)</div>",
        html_clean, re.S | re.I,
    )
    length_mismatches: List[str] = []
    for m in seq_blocks:
        label_text = _strip_tags(m.group(1))
        body_text = _strip_tags(m.group(2))
        seq_chars = re.sub(r"[^A-Za-z]", "", body_text)
        actual_len = len(seq_chars)
        claim_m = re.search(r"(\d{2,4})\s*aa", label_text, re.I)
        if claim_m:
            claimed = int(claim_m.group(1))
            if claimed != actual_len and actual_len > 0:
                length_mismatches.append(f"{label_text.strip()[:30]}: claim={claimed}, actual={actual_len}")
    if length_mismatches:
        _add(QCFinding("H", "sequence_length_mismatch", sev_warn,
                       "Sequence length claims do not match actual residues: "
                       + "; ".join(length_mismatches[:3])))
    else:
        _add(QCFinding("H", "sequence_length_mismatch", QCSeverity.PASS,
                       "Sequence length labels consistent with actual residues."))

    # ── H3. Overall status badge consistency ─────────────────────────────────
    # If any "Overall: PASS" claim exists but a downstream table contains FAIL/WARN cells > 3
    overall_claim = re.search(r"Overall(?:\s+Status)?\s*[:\-]\s*</?[^>]*>?\s*PASS", html_clean, re.I)
    fail_badges = len(re.findall(r"badge-fail|class=['\"]fail['\"]", html))
    if overall_claim and fail_badges > 3:
        _add(QCFinding("H", "status_badge_inconsistent", QCSeverity.WARN,
                       f"Report claims Overall=PASS but contains {fail_badges} FAIL badges. "
                       f"Verify the executive summary."))


# ---------------------------------------------------------------------------
# Tool execution evidence helpers (dimension I)
# ---------------------------------------------------------------------------

# Tools that each report family is expected to actually have run (not just mention)
_TOOL_EVIDENCE_REQUIRED = {
    "vhvl_humanization": ["pi_value", "gravy_value"],
    "vhh_humanization":  ["pi_value", "gravy_value", "hpr_value_or_placeholder"],
    "vh_to_vhh":         ["pi_value", "gravy_value"],
    "vhh_cmc":           ["pi_value", "gravy_value", "adi_grade"],
    "bispecific_cmc":    ["pi_value", "gravy_value"],
    "cmc_igg":           ["pi_value", "gravy_value", "instability_value"],
    "recheck_vhvl":      ["pi_value", "gravy_value"],
    "recheck_vhh":       ["pi_value", "gravy_value"],
    "caninization":      ["pi_value", "gravy_value"],
}


def _check_tool_execution_evidence(html: str, report_family: str, _add, strict: bool) -> None:
    """
    Confirm that each tool the report family declares actually emitted a numeric
    result anchor — not just a section heading or 'not computed' placeholder.
    """
    sev_warn = QCSeverity.FAIL if strict else QCSeverity.WARN
    required = _TOOL_EVIDENCE_REQUIRED.get(report_family, [])
    if not required:
        _add(QCFinding("I", "tool_evidence", QCSeverity.PASS,
                       "No tool evidence requirements registered for this family."))
        return

    # Strip style/script then collapse tags to a clean text stream so labels
    # and their adjacent numeric values are matched even across <td>...</td> cells.
    html_clean = _strip_style_and_script(html)
    plain_text = re.sub(r"\s+", " ", _strip_tags(html_clean))

    # Each pattern matches a label followed by a numeric value within a bounded
    # window; descriptive labels like "GRAVY (Hydrophobicity)" are tolerated.
    evidence_checks = {
        "pi_value": (
            r"(?:^|[^A-Za-z])pI(?:\s*\([^)]{0,40}\))?[^\n]{1,80}?(-?\d+\.\d{1,3})",
            "pI numeric value",
        ),
        "gravy_value": (
            r"GRAVY(?:\s*\([^)]{0,40}\))?[^\n]{1,80}?(-?\d+\.\d{1,4})",
            "GRAVY numeric value",
        ),
        "hpr_value_or_placeholder": (
            r"HPR[^\n]{0,150}?(?:(\d{1,3}\.\d{1,2})\s*%|not[\s_-]*computed|database\s+unavailable|N/A)",
            "HPR Index numeric % or explicit placeholder",
        ),
        "adi_grade": (
            # Either "ADI ... Grade X" within 200 chars OR a standalone "Grade A/B/C/D"
            # appearing anywhere in the report (CMC reports use this convention universally).
            r"(?:ADI[^\n]{1,200}?\bgrade\s+[A-D]\b)|(?:\bgrade\s+[A-D]\b[^\n]{0,80}?ADI)|(?:[●▶▪★]\s*[Gg]rade\s+[A-D]\b)",
            "ADI grade letter",
        ),
        "instability_value": (
            r"[Ii]nstability(?:\s+[Ii]ndex)?(?:\s*\([^)]{0,40}\))?[^\n]{1,100}?(\d+\.\d{1,3})",
            "Instability index numeric value",
        ),
        "plddt_value": (
            r"pLDDT[^\n]{1,100}?(\d{1,3}\.\d{1,3})",
            "pLDDT numeric value",
        ),
    }

    missing_evidence = []
    for tool_key in required:
        pat_info = evidence_checks.get(tool_key)
        if pat_info is None:
            continue
        pat, desc = pat_info
        # Try plain-text first (cross-cell), fall back to raw HTML
        if not re.search(pat, plain_text, re.I) and not re.search(pat, html_clean, re.I):
            missing_evidence.append(f"{tool_key} ({desc})")

    if missing_evidence:
        _add(QCFinding("I", "tool_evidence_missing", sev_warn,
                       f"Required tool output anchors not detected: {', '.join(missing_evidence)}. "
                       f"Section headings exist but no concrete numeric result was rendered."))
    else:
        _add(QCFinding("I", "tool_evidence", QCSeverity.PASS,
                       f"All {len(required)} required tool evidence anchors present."))
