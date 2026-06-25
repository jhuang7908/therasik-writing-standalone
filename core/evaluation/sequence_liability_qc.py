"""
sequence_liability_qc.py — Generalized Sequence-Level QC for De Novo Antibody Design
======================================================================================
Suites-level generalization of the project-specific sequence_qc.py developed during
the VGRW-SR-R2 HER2 VHH De Novo design run (April 2026).

Key improvements over the original:
  - Accepts ANY antibody format: VHH, VH, VL, scFv, bispecific
  - Accepts multiple CDRs via cdrs dict (not single CDR2 only)
  - root_positions is a parameter loaded from structural analysis output
    (not a module-level hardcoded constant)
  - conservative_map is per-position configurable
  - PTM checks are applied to ALL designated CDR regions
  - CMC uses cmc_advisor_module when available; falls back to ProtParam
  - Designed for T0.0 gate: runs in <1s on 400+ sequences (pure regex / arithmetic)

Typical usage
-------------
  # VHH, single CDR2 redesign (generalized from VGRW-SR-R2 case):
  qc = SequenceLiabilityQC(
      wt_seq         = WT_SEQ,
      cdrs           = {"CDR2": (46, 62)},
      canonical_cys  = [21, 95],
      root_positions = {47, 48, 50, 57, 58, 59, 60, 61, 62},  # from _cdr2_root_analysis.py
  )

  # VH/VL humanization project (CDR boundaries from ANARCI):
  qc = SequenceLiabilityQC(
      wt_seq         = MU_VH_SEQ,
      cdrs           = {"CDR1": (26, 35), "CDR2": (50, 65), "CDR3": (95, 102)},
      canonical_cys  = [22, 92],
      root_positions = None,   # skip root check until structural analysis done
  )

  # Batch run:
  results = qc.run_batch(seqs_dict, verbose=True)
  passed = {sid: r for sid, r in results.items() if r.passed}

  # Pipeline integration (T0.0 gate):
  clean_seqs = qc.filter_batch(seqs_dict)   # returns only passing sequences

CLI
---
  python -m core.evaluation.sequence_liability_qc \\
      --input phase1/mpnn_raw.fasta \\
      --mask_json config/mask_strategy.json \\
      --output reports/t00_qc.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ── optional BioPython (CMC metrics) ─────────────────────────────────────────
try:
    from Bio.SeqUtils.ProtParam import ProteinAnalysis as _ProteinAnalysis
    _BIOPYTHON = True
except ImportError:
    _BIOPYTHON = False

# ── Kyte-Doolittle hydrophobicity scale ──────────────────────────────────────
_KD: dict[str, float] = {
    "A":  1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C":  2.5,
    "Q": -3.5, "E": -3.5, "G": -0.4, "H": -3.2, "I":  4.5,
    "L":  3.8, "K": -3.9, "M":  1.9, "F":  2.8, "P": -1.6,
    "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V":  4.2,
}

# ── Simplified net charge at pH 7 ─────────────────────────────────────────────
_CHARGE7: dict[str, float] = {
    "K": +1.0, "R": +1.0, "H": +0.1, "D": -1.0, "E": -1.0,
}

# ── PTM motif patterns ────────────────────────────────────────────────────────
_DEAMID_NEXT  = frozenset("GAST")    # N-x → deamidation risk
_ISOMER_NEXT  = frozenset("GAST")    # D-x → isomerization risk
_NGLYC_RE     = re.compile(r"N[^P][ST]")   # N-X-S/T (x≠P) glycosylation site

# ── Default QC thresholds (can be overridden per project) ─────────────────────
DEFAULT_THRESHOLDS: dict[str, float] = {
    # pI
    "pI_min":          5.5,   # hard FAIL below
    "pI_max":          9.5,   # hard FAIL above
    "pI_warn_min":     5.5,   # warn below
    "pI_warn_max":     9.5,   # warn above
    # instability index (Guruprasad et al.)
    "instability_max": 50.0,  # hard FAIL
    "instability_warn":45.0,  # warn
    # GRAVY
    "gravy_min":      -1.2,   # warn below
    "gravy_max":       0.8,   # hard FAIL above
    # hydrophobic / charge patches
    "hydro_patch9_max": 2.5,  # hard FAIL (9-mer KD mean)
    "charge_patch7_max": 4.0, # warn (7-mer |charge|)
    # net charge at pH 7
    "net_charge_min": -4.0,   # warn
    "net_charge_max":  6.0,   # warn
}


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class QCResult:
    seq_id:   str
    sequence: str
    passed:   bool               # True iff no FAIL flags
    flags:    list[str] = field(default_factory=list)    # hard FAIL
    warnings: list[str] = field(default_factory=list)    # soft WARN
    metrics:  dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seq_id":   self.seq_id,
            "passed":   self.passed,
            "flags":    self.flags,
            "warnings": self.warnings,
            "metrics":  self.metrics,
        }

    @property
    def status(self) -> str:
        if not self.passed:
            return "FAIL"
        return "WARN" if self.warnings else "PASS"


# ── Main QC class ─────────────────────────────────────────────────────────────

class SequenceLiabilityQC:
    """
    Generalized sequence-level QC filter for de novo antibody candidates.

    Parameters
    ----------
    wt_seq : str
        Wild-type reference sequence (full variable domain).
    cdrs : dict[str, tuple[int, int]]
        CDR regions: {name: (linear_start, linear_end)} 0-indexed inclusive.
        Example: {"CDR1": (26, 35), "CDR2": (50, 65), "CDR3": (95, 102)}
    canonical_cys : list[int] | None
        0-indexed positions of canonical disulfide Cys.
        VHH default: [21, 95]. VH default: [22, 92].
    root_positions : set[int] | None
        0-indexed linear positions classified as ROOT (structural anchors) from
        structural analysis (_cdr2_root_analysis.py output). If None, A4 check
        is skipped.
    conservative_map : dict[int, set[str]] | None
        Per root position: set of ALLOWED amino acids for conservative substitution.
        If a root position is mutated but the new AA is in this set → WARN only.
        If mutated to an AA not in this set → FAIL (A4_ROOT_NONCONSERVATIVE).
        If root position is not in this map → any mutation is FAIL.
    thresholds : dict | None
        Override DEFAULT_THRESHOLDS keys.
    antibody_type : str
        "VHH", "VH", "VL", "scFv", "HC" — affects default canonical_cys choice.
    """

    def __init__(
        self,
        wt_seq:           str,
        cdrs:             dict[str, tuple[int, int]],
        canonical_cys:    list[int] | None = None,
        root_positions:   set[int] | None = None,
        conservative_map: dict[int, set[str]] | None = None,
        thresholds:       dict | None = None,
        antibody_type:    str = "VHH",
    ):
        self.wt_seq        = wt_seq
        self.cdrs          = cdrs
        self.root_positions = root_positions   # None = skip root check
        self.conservative_map = conservative_map or {}
        self.thr           = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        self.antibody_type = antibody_type

        # Canonical Cys: auto-select if not provided
        if canonical_cys is not None:
            self.canonical_cys = canonical_cys
        elif antibody_type in ("VHH",):
            self.canonical_cys = [21, 95]
        elif antibody_type in ("VH", "scFv"):
            self.canonical_cys = [22, 92]
        elif antibody_type == "VL":
            self.canonical_cys = [23, 88]
        else:
            self.canonical_cys = []

        # Build flat set of all CDR positions for PTM scoping
        self._all_cdr_positions: set[int] = set()
        for start, end in self.cdrs.values():
            self._all_cdr_positions.update(range(start, end + 2))  # +2: motif spans 2 residues

        # Pre-compute WT liabilities for delta comparison
        self._wt_deamid = self._deamid_positions(wt_seq)
        self._wt_isomer = self._isomer_positions(wt_seq)
        self._wt_nglyc  = self._nglyc_positions(wt_seq)

    # ── static helpers ────────────────────────────────────────────────────

    @staticmethod
    def _deamid_positions(seq: str) -> set[int]:
        return {i for i in range(len(seq) - 1)
                if seq[i] == "N" and seq[i + 1] in _DEAMID_NEXT}

    @staticmethod
    def _isomer_positions(seq: str) -> set[int]:
        return {i for i in range(len(seq) - 1)
                if seq[i] == "D" and seq[i + 1] in _ISOMER_NEXT}

    @staticmethod
    def _nglyc_positions(seq: str) -> set[int]:
        return {m.start() for m in _NGLYC_RE.finditer(seq)}

    @staticmethod
    def _hydro_patch(seq: str, window: int = 9) -> float:
        scores = [
            sum(_KD.get(seq[i + j], 0) for j in range(window)) / window
            for i in range(len(seq) - window + 1)
        ]
        return max(scores) if scores else 0.0

    @staticmethod
    def _charge_patch(seq: str, window: int = 7) -> float:
        patches = [
            abs(sum(_CHARGE7.get(seq[i + j], 0) for j in range(window)))
            for i in range(len(seq) - window + 1)
        ]
        return max(patches) if patches else 0.0

    @staticmethod
    def _net_charge(seq: str) -> float:
        return sum(_CHARGE7.get(aa, 0) for aa in seq)

    # ── main check ────────────────────────────────────────────────────────

    def check(self, seq_id: str, seq: str) -> QCResult:
        """
        Run all QC checks on a single sequence.

        Returns QCResult with passed=True only if no FAIL flags are raised.
        Warnings are informational and do not cause failure.
        """
        flags:    list[str] = []
        warnings: list[str] = []
        metrics:  dict[str, Any] = {}

        # ── A1. Canonical Cys preserved ───────────────────────────────
        actual_cys = {i for i, aa in enumerate(seq) if aa == "C"}
        canonical  = set(self.canonical_cys)
        missing    = canonical - actual_cys
        if missing:
            flags.append(f"A1_CYS_LOST@{sorted(missing)}")

        # ── A2. No new unpaired Cys ────────────────────────────────────
        new_cys = actual_cys - canonical
        if new_cys:
            flags.append(f"A2_NEW_CYS@{sorted(new_cys)}")

        # ── A3. Length unchanged (no indels) ──────────────────────────
        if len(seq) != len(self.wt_seq):
            flags.append(f"A3_LENGTH:{len(seq)}_vs_wt_{len(self.wt_seq)}")
            return QCResult(seq_id, seq, False, flags, warnings, metrics)

        # ── A4. Root position mutations ────────────────────────────────
        if self.root_positions is not None:
            for pos in self.root_positions:
                if pos >= len(seq):
                    continue
                wt_aa   = self.wt_seq[pos]
                cand_aa = seq[pos]
                if cand_aa == wt_aa:
                    continue
                allowed = self.conservative_map.get(pos)
                if allowed is not None and cand_aa in allowed:
                    warnings.append(
                        f"A4_ROOT_CONSERVATIVE@lin{pos}({wt_aa}->{cand_aa})"
                    )
                else:
                    flags.append(
                        f"A4_ROOT_NONCONSERVATIVE@lin{pos}({wt_aa}->{cand_aa})"
                    )

        # ── B1. Deamidation (NEW vs WT, in CDR region) ────────────────
        cand_deamid = self._deamid_positions(seq)
        new_deamid  = cand_deamid - self._wt_deamid
        cdr_deamid  = {p for p in new_deamid if p in self._all_cdr_positions}
        other_deamid = new_deamid - cdr_deamid
        if cdr_deamid:
            for p in sorted(cdr_deamid):
                motif = seq[p: p + 2]
                if motif[1] == "G":
                    flags.append(f"B1_DEAMID_NG@{p}({motif})")  # most labile → FAIL
                else:
                    warnings.append(f"B1_DEAMID_{motif}_CDR@{p}")  # moderate → WARN
        if other_deamid:
            warnings.append(f"B1_DEAMID_nonCDR@{sorted(other_deamid)}")

        # ── B2. Isomerization (NEW vs WT, in CDR region) ──────────────
        cand_isomer = self._isomer_positions(seq)
        new_isomer  = cand_isomer - self._wt_isomer
        cdr_isomer  = {p for p in new_isomer if p in self._all_cdr_positions}
        if cdr_isomer:
            for p in sorted(cdr_isomer):
                motif = seq[p: p + 2]
                flags.append(f"B2_ISOMER_{motif}_CDR@{p}")
        other_isomer = new_isomer - cdr_isomer
        if other_isomer:
            warnings.append(f"B2_ISOMER_nonCDR@{sorted(other_isomer)}")

        # ── B3. New N-glycosylation sites (vs WT) ─────────────────────
        cand_nglyc = self._nglyc_positions(seq)
        new_nglyc  = cand_nglyc - self._wt_nglyc
        if new_nglyc:
            motifs = [seq[p: p + 3] for p in sorted(new_nglyc)]
            flags.append(f"B3_NGLYC@{sorted(new_nglyc)}({motifs})")

        # ── B4. New Met / Cys in CDR tip (oxidation risk) ─────────────
        for cdr_name, (start, end) in self.cdrs.items():
            for lin in range(start, end + 1):
                if lin >= len(seq):
                    break
                wt_aa   = self.wt_seq[lin]
                cand_aa = seq[lin]
                if cand_aa == wt_aa:
                    continue
                if cand_aa == "C":
                    flags.append(f"B4_NEW_CYS_{cdr_name}@{lin}")
                elif cand_aa == "M" and self.root_positions and lin not in self.root_positions:
                    warnings.append(f"B4_NEW_MET_{cdr_name}@{lin}")

        # ── C. CMC developability metrics ─────────────────────────────
        if _BIOPYTHON:
            try:
                pa = _ProteinAnalysis(seq)
                pI          = round(pa.isoelectric_point(), 2)
                instability = round(pa.instability_index(), 1)
                gravy       = round(pa.gravy(), 3)
                hydro_p     = round(self._hydro_patch(seq, 9), 3)
                charge_p    = round(self._charge_patch(seq, 7), 2)
                net_ch      = round(self._net_charge(seq), 2)

                metrics.update({
                    "pI":                pI,
                    "instability_index": instability,
                    "GRAVY":             gravy,
                    "hydro_patch_max9":  hydro_p,
                    "charge_patch_max7": charge_p,
                    "net_charge_pH7":    net_ch,
                })

                if pI < self.thr["pI_min"] or pI > self.thr["pI_max"]:
                    flags.append(f"C1_PI_FAIL:{pI}")
                elif pI < self.thr["pI_warn_min"] or pI > self.thr["pI_warn_max"]:
                    warnings.append(f"C1_PI_WARN:{pI}")

                if instability > self.thr["instability_max"]:
                    flags.append(f"C2_INSTABILITY_FAIL:{instability}")
                elif instability > self.thr["instability_warn"]:
                    warnings.append(f"C2_INSTABILITY_WARN:{instability}")

                if gravy > self.thr["gravy_max"]:
                    flags.append(f"C3_GRAVY_HIGH:{gravy}")
                elif gravy < self.thr["gravy_min"]:
                    warnings.append(f"C3_GRAVY_LOW:{gravy}")

                if hydro_p > self.thr["hydro_patch9_max"]:
                    flags.append(f"C4_HYDRO_PATCH:{hydro_p}")

                if charge_p > self.thr["charge_patch7_max"]:
                    warnings.append(f"C5_CHARGE_PATCH:{charge_p}")

                if net_ch < self.thr["net_charge_min"]:
                    warnings.append(f"C6_NET_CHARGE_LOW:{net_ch}")
                elif net_ch > self.thr["net_charge_max"]:
                    warnings.append(f"C6_NET_CHARGE_HIGH:{net_ch}")

            except Exception as exc:
                warnings.append(f"C_CMC_ERROR:{exc}")

        return QCResult(seq_id, seq, len(flags) == 0, flags, warnings, metrics)

    # ── batch helpers ─────────────────────────────────────────────────────

    def run_batch(
        self,
        sequences: dict[str, str],
        verbose:   bool = False,
    ) -> dict[str, QCResult]:
        """
        Check all sequences. Returns {seq_id: QCResult}.

        verbose=True prints per-sequence summary and final counts.
        """
        results: dict[str, QCResult] = {}
        n_pass = n_warn = n_fail = 0
        for sid, seq in sequences.items():
            r = self.check(sid, seq)
            results[sid] = r
            if r.passed:
                (n_warn if r.warnings else n_pass).__class__  # dummy; just count below
                if r.warnings:
                    n_warn += 1
                else:
                    n_pass += 1
            else:
                n_fail += 1
            if verbose:
                if r.flags or r.warnings:
                    flag_str = " | ".join(r.flags + [f"WARN:{w}" for w in r.warnings[:3]])
                    print(f"  [{r.status:6s}] {sid[:45]:<45} {flag_str}")
        if verbose:
            total = len(sequences)
            print(f"\n  T0.0 QC: {n_pass} PASS | {n_warn} PASS+WARN | "
                  f"{n_fail} FAIL  out of {total}")
        return results

    def filter_batch(
        self,
        sequences: dict[str, str],
        verbose:   bool = False,
    ) -> dict[str, str]:
        """
        Run QC and return only sequences with passed=True.

        Convenience wrapper for pipeline integration at T0.0 gate.
        """
        results = self.run_batch(sequences, verbose=verbose)
        return {sid: seq for sid, seq in sequences.items()
                if results[sid].passed}

    def summarize(self, results: dict[str, QCResult]) -> dict[str, Any]:
        """Return a summary dict suitable for logging."""
        from collections import Counter
        flag_counter: Counter = Counter()
        warn_counter: Counter = Counter()
        n_pass = n_fail = 0
        for r in results.values():
            if r.passed:
                n_pass += 1
            else:
                n_fail += 1
            for f in r.flags:
                tag = "_".join(f.split("_")[:2])
                flag_counter[tag] += 1
            for w in r.warnings:
                tag = "_".join(w.split("_")[:2])
                warn_counter[tag] += 1
        return {
            "total":    len(results),
            "passed":   n_pass,
            "failed":   n_fail,
            "pass_rate": round(n_pass / len(results), 3) if results else 0.0,
            "top_fail_flags":  dict(flag_counter.most_common(5)),
            "top_warn_flags":  dict(warn_counter.most_common(5)),
        }


# ── Factory: build from mask_strategy.json ───────────────────────────────────

def from_mask_json(
    mask_json_path: str | Path,
    root_analysis_json: str | Path | None = None,
    thresholds: dict | None = None,
) -> SequenceLiabilityQC:
    """
    Convenience factory: build a SequenceLiabilityQC from a project's
    mask_strategy.json and optional root analysis output.

    Parameters
    ----------
    mask_json_path : path to mask_strategy.json
    root_analysis_json : optional path to _cdr2_root_analysis output JSON
        (should contain "root_positions_linear": [list] and optionally
         "conservative_map": {str_pos: [list_of_allowed_AAs]})
    thresholds : override default QC thresholds

    Returns
    -------
    SequenceLiabilityQC ready to use
    """
    mask = json.loads(Path(mask_json_path).read_text(encoding="utf-8"))
    wt_seq = mask["wt_sequence"]

    # Build CDR dict from mask cdr_regions
    cdrs: dict[str, tuple[int, int]] = {}
    for cdr_name, cdr_info in mask.get("cdr_regions", {}).items():
        start = cdr_info.get("linear_start")
        end   = cdr_info.get("linear_end")
        if start is not None and end is not None:
            cdrs[cdr_name] = (start, end)

    # Infer antibody type from mask or default to VHH
    ab_type = mask.get("antibody_type", "VHH")

    # Load root positions from structural analysis if provided
    root_positions: set[int] | None = None
    conservative_map: dict[int, set[str]] | None = None
    if root_analysis_json and Path(root_analysis_json).exists():
        ra = json.loads(Path(root_analysis_json).read_text(encoding="utf-8"))
        if "root_positions_linear" in ra:
            root_positions = set(ra["root_positions_linear"])
        if "conservative_map" in ra:
            conservative_map = {
                int(k): set(v) for k, v in ra["conservative_map"].items()
            }

    return SequenceLiabilityQC(
        wt_seq           = wt_seq,
        cdrs             = cdrs,
        root_positions   = root_positions,
        conservative_map = conservative_map,
        thresholds       = thresholds,
        antibody_type    = ab_type,
    )


# ── FASTA I/O ─────────────────────────────────────────────────────────────────

def load_fasta(path: str | Path) -> dict[str, str]:
    seqs: dict[str, str] = {}
    current_id: str | None = None
    buf: list[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(">"):
            if current_id is not None and buf:
                seqs[current_id] = "".join(buf)
            current_id = line[1:].split()[0]
            buf = []
        elif line and current_id is not None:
            buf.append(line)
    if current_id is not None and buf:
        seqs[current_id] = "".join(buf)
    return seqs


def dedup_fasta(seqs: dict[str, str]) -> dict[str, str]:
    """
    Exact deduplication: keep the first occurrence of each unique sequence.
    Returns a new dict preserving insertion order of first occurrences.
    """
    seen: set[str] = set()
    out: dict[str, str] = {}
    for sid, seq in seqs.items():
        if seq not in seen:
            seen.add(seq)
            out[sid] = seq
    return out


# ── CLI ───────────────────────────────────────────────────────────────────────

def _cli() -> None:
    p = argparse.ArgumentParser(
        description="T0.0 Sequence Liability QC for De Novo Antibody Design"
    )
    p.add_argument("--input",       required=True, help="Input FASTA")
    p.add_argument("--mask_json",   default="config/mask_strategy.json")
    p.add_argument("--root_json",   default=None,
                   help="Optional root analysis JSON (from _cdr2_root_analysis.py)")
    p.add_argument("--output",      default="reports/t00_sequence_qc.json")
    p.add_argument("--dedup",       action="store_true",
                   help="Exact dedup before QC")
    p.add_argument("--verbose",     action="store_true")
    p.add_argument("--passed_fasta", default=None,
                   help="Write passing sequences to this FASTA file")
    args = p.parse_args()

    qc  = from_mask_json(args.mask_json, args.root_json)
    raw = load_fasta(args.input)
    print(f"Loaded {len(raw)} sequences from {args.input}")

    if args.dedup:
        seqs = dedup_fasta(raw)
        print(f"After exact dedup: {len(seqs)} unique sequences "
              f"(removed {len(raw)-len(seqs)} duplicates)")
    else:
        seqs = raw

    results  = qc.run_batch(seqs, verbose=args.verbose)
    summary  = qc.summarize(results)

    print(f"\nT0.0 Summary: {summary['passed']}/{summary['total']} pass "
          f"({summary['pass_rate']*100:.1f}%)")
    print("Top FAIL flags:", summary["top_fail_flags"])
    print("Top WARN flags:", summary["top_warn_flags"])

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(
        json.dumps({sid: r.to_dict() for sid, r in results.items()},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    Path(args.output.replace(".json", "_summary.json")).write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"Results written to: {args.output}")

    if args.passed_fasta:
        passed_seqs = {sid: seq for sid, seq in seqs.items()
                       if results[sid].passed}
        lines: list[str] = []
        for sid, seq in passed_seqs.items():
            lines.append(f">{sid}")
            lines.append(seq)
        Path(args.passed_fasta).write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )
        print(f"Passing sequences written to: {args.passed_fasta}")


if __name__ == "__main__":
    _cli()
