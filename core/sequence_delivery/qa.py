"""
sequence_delivery.qa — Sequence Quality Assurance.

Checks performed:
  1. Length: expected vs actual (AA and/or DNA)
  2. Stop codons: presence and position in DNA
  3. GC content: warn if < 40% or > 65% (CHO expression risk)
  4. Diff vs reference: per-residue mismatch list + summary
  5. FR4 patterns: VH WGQGT…VSS / VL FGQGTK…K motifs
  6. No ambiguous AA (X, B, Z, U) in delivery sequences
  7. SP prefix check: sequence starts with expected SP
  8. DNA encodes expected AA (back-translation round-trip)

All check functions return a QAResult with status PASS/WARN/FAIL.
run_all_checks() returns a QAReport aggregating all results.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional
from .codon_optimizer import gc_content, _build_codon_to_aa


# ── Status ─────────────────────────────────────────────────────────────────
PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"


@dataclass
class QAResult:
    check: str
    status: str        # PASS / WARN / FAIL
    message: str
    details: list[str] = field(default_factory=list)


@dataclass
class QAReport:
    chain_name: str
    results: list[QAResult] = field(default_factory=list)

    @property
    def overall(self) -> str:
        statuses = [r.status for r in self.results]
        if FAIL in statuses:
            return FAIL
        if WARN in statuses:
            return WARN
        return PASS

    def summary(self) -> str:
        lines = [f"=== QA Report: {self.chain_name} | Overall: {self.overall} ==="]
        for r in self.results:
            lines.append(f"  [{r.status}] {r.check}: {r.message}")
            for d in r.details[:5]:
                lines.append(f"         {d}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "chain_name": self.chain_name,
            "overall": self.overall,
            "checks": [
                {"check": r.check, "status": r.status,
                 "message": r.message, "details": r.details}
                for r in self.results
            ],
        }


# ── Known FR4 motifs ───────────────────────────────────────────────────────
_VH_FR4_PATTERNS = [
    r"WGQGT[A-Z]{1,3}TVSS",   # WGQGTSVTVSS (dog) / WGQGTLVTVSS (human)
    r"WGQGT[A-Z]{1,3}TVTV",   # variant
]
_VL_FR4_PATTERNS = [
    r"FGQGTK[A-Z]{1,4}K",     # FGQGTKVELK (dog) / FGQGTKLEIK (human)
    r"FGGGTKV",                # kappa variant
]

# ── Known SP sequences (IgH, IgK common) ──────────────────────────────────
KNOWN_SIGNAL_PEPTIDES: dict[str, str] = {
    "Human_IgH":   "MEFGLSWVFLVAILKGVQC",
    "Human_IgK":   "MDMRVPAQLLGLLLLWFPGSRC",
    "Human_IgK_alt": "METDTLLLWVLLLWVPGSTGD",
    "Mouse_IgH":   "MGWSCIILFLVATATGVHS",
}


# ── Individual checks ──────────────────────────────────────────────────────

def check_length(seq: str, expected_len: Optional[int], *, label: str = "AA length") -> QAResult:
    actual = len(seq)
    if expected_len is None:
        return QAResult(label, PASS, f"Length {actual} aa (no expected length specified)")
    diff = actual - expected_len
    if diff == 0:
        return QAResult(label, PASS, f"Length {actual} aa — matches expected")
    status = WARN if abs(diff) <= 3 else FAIL
    return QAResult(label, status,
                    f"Length {actual} aa, expected {expected_len} aa (Δ={diff:+d})")


def check_stop_codon_dna(dna: str) -> QAResult:
    """Verify terminal stop codon and no internal stops."""
    dna = dna.upper()
    STOPS = {"TAA", "TAG", "TGA"}
    if len(dna) % 3 != 0:
        return QAResult("Stop codon", FAIL,
                        f"DNA length {len(dna)} not divisible by 3")
    codons = [dna[i:i+3] for i in range(0, len(dna), 3)]
    internal_stops = [i for i, c in enumerate(codons[:-1]) if c in STOPS]
    last = codons[-1]
    last_ok = last in STOPS
    issues = []
    if internal_stops:
        issues = [f"Internal stop at codon {i+1}: {codons[i]}" for i in internal_stops]
        return QAResult("Stop codon", FAIL,
                        f"{len(internal_stops)} internal stop(s) found", issues)
    if not last_ok:
        return QAResult("Stop codon", WARN,
                        f"Terminal codon '{last}' is not a stop codon")
    return QAResult("Stop codon", PASS,
                    f"Terminal stop '{last}' present, no internal stops")


def check_gc_content(dna: str, low: float = 0.40, high: float = 0.65) -> QAResult:
    gc = gc_content(dna)
    pct = round(gc * 100, 1)
    if gc < low:
        return QAResult("GC content", WARN,
                        f"GC {pct}% — below {low*100:.0f}% (possible instability in CHO)")
    if gc > high:
        return QAResult("GC content", WARN,
                        f"GC {pct}% — above {high*100:.0f}% (possible hairpin risk)")
    return QAResult("GC content", PASS, f"GC {pct}% — within acceptable range")


def check_ambiguous_aa(aa_seq: str) -> QAResult:
    ambig = re.findall(r"[XBZUO]", aa_seq.upper())
    if ambig:
        return QAResult("Ambiguous AA", FAIL,
                        f"{len(ambig)} ambiguous residue(s): {set(ambig)}")
    return QAResult("Ambiguous AA", PASS, "No ambiguous residues")


def check_sp_prefix(full_aa: str, sp_aa: str, sp_name: str = "") -> QAResult:
    label = f"SP prefix ({sp_name})" if sp_name else "SP prefix"
    if full_aa.upper().startswith(sp_aa.upper()):
        return QAResult(label, PASS,
                        f"SP '{sp_aa[:12]}…' found at N-terminus")
    found = full_aa[:len(sp_aa) + 4]
    return QAResult(label, FAIL,
                    f"Expected SP not found",
                    [f"Expected: {sp_aa}", f"Got:      {found}"])


def check_fr4_pattern(aa_seq: str, chain: str = "HC") -> QAResult:
    """Check for VH or VL FR4 canonical motif anywhere in the sequence."""
    label = f"FR4 pattern ({chain})"
    patterns = _VH_FR4_PATTERNS if chain.upper() in ("HC", "VH", "H") else _VL_FR4_PATTERNS
    for p in patterns:
        m = re.search(p, aa_seq.upper())
        if m:
            return QAResult(label, PASS,
                            f"FR4 motif '{m.group()}' found at position {m.start()}–{m.end()-1}")
    return QAResult(label, WARN,
                    "No canonical FR4 motif detected — verify manually if non-standard format")


def check_diff_vs_reference(
    seq: str,
    reference: str,
    *,
    ref_label: str = "reference",
    strip_sp: Optional[str] = None,
) -> QAResult:
    """Compare seq to reference (AA or DNA), report per-position diffs.

    Args:
        seq:       sequence to check.
        reference: reference sequence (must be same length after optional SP strip).
        ref_label: label for the reference in the report.
        strip_sp:  if given, strip this SP prefix from *seq* before comparing.
    """
    s = seq
    if strip_sp:
        if not s.upper().startswith(strip_sp.upper()):
            return QAResult("Diff vs ref", FAIL,
                            f"Cannot strip SP '{strip_sp[:10]}…' from seq (prefix mismatch)")
        s = s[len(strip_sp):]

    # Trim to reference length for Fv-level comparison
    cmp_len = min(len(s), len(reference))
    s_cmp = s[:cmp_len].upper()
    r_cmp = reference[:cmp_len].upper()

    diffs = [(i, s_cmp[i], r_cmp[i]) for i in range(cmp_len) if s_cmp[i] != r_cmp[i]]

    if len(s) != len(reference):
        extra = f" (length mismatch: seq {len(s)} vs ref {len(reference)}, compared first {cmp_len})"
    else:
        extra = ""

    if not diffs:
        return QAResult("Diff vs ref", PASS,
                        f"Identical to {ref_label}{extra}")
    detail = [f"pos {i+1}: seq={a} ref={b}" for i, a, b in diffs[:20]]
    status = PASS if len(diffs) <= 5 else WARN
    return QAResult("Diff vs ref", status,
                    f"{len(diffs)} difference(s) vs {ref_label}{extra}", detail)


def check_round_trip(aa_seq: str, dna: str) -> QAResult:
    """Translate dna back to AA and compare to aa_seq."""
    from .codon_optimizer import _build_codon_to_aa
    table = _build_codon_to_aa()
    dna_up = dna.upper()
    if len(dna_up) % 3 != 0:
        return QAResult("Round-trip", FAIL, f"DNA length not divisible by 3")
    codons = [dna_up[i:i+3] for i in range(0, len(dna_up), 3)]
    translated = "".join(table.get(c, "X") for c in codons).rstrip("*")
    expected = aa_seq.upper().rstrip("*")
    if translated == expected:
        return QAResult("Round-trip", PASS,
                        "DNA back-translates correctly to AA")
    diffs = [(i, translated[i], expected[i])
             for i in range(min(len(translated), len(expected)))
             if translated[i] != expected[i]]
    return QAResult("Round-trip", FAIL,
                    f"{len(diffs)} mismatch(es) in round-trip translation",
                    [f"pos {i+1}: DNA→{a} AA→{b}" for i, a, b in diffs[:10]])


# ── Aggregate report ───────────────────────────────────────────────────────

def run_all_checks(
    chain_name: str,
    full_aa: str,
    *,
    dna: Optional[str] = None,
    reference_fv: Optional[str] = None,
    reference_label: str = "reference",
    sp: Optional[str] = None,
    sp_name: str = "",
    chain_type: str = "HC",
    expected_aa_len: Optional[int] = None,
) -> QAReport:
    """Run the full QA battery for one assembled chain.

    Args:
        chain_name:     display name.
        full_aa:        complete AA sequence (with SP if present).
        dna:            optional CHO-optimized DNA (if None, DNA checks skipped).
        reference_fv:   optional reference Fv AA to diff against (SP stripped first).
        reference_label: label for the reference in the diff report.
        sp:             signal peptide AA sequence (for SP-prefix check).
        sp_name:        display name for the SP.
        chain_type:     "HC" or "LC" (for FR4 pattern).
        expected_aa_len: expected full-length AA count.
    """
    report = QAReport(chain_name=chain_name)

    # 1. Ambiguous AA
    report.results.append(check_ambiguous_aa(full_aa))

    # 2. Length
    report.results.append(check_length(full_aa, expected_aa_len))

    # 3. SP prefix
    if sp:
        report.results.append(check_sp_prefix(full_aa, sp, sp_name))

    # 4. FR4 pattern
    report.results.append(check_fr4_pattern(full_aa, chain_type))

    # 5. Diff vs reference Fv
    if reference_fv:
        report.results.append(
            check_diff_vs_reference(full_aa, reference_fv,
                                    ref_label=reference_label,
                                    strip_sp=sp)
        )

    # 6. DNA checks
    if dna:
        report.results.append(check_stop_codon_dna(dna))
        report.results.append(check_gc_content(dna))
        report.results.append(check_round_trip(full_aa.rstrip("*"), dna))

    return report
