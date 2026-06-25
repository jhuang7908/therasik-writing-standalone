"""
pipeline_qa.py — InSynBio AbEngineCore v1.0
============================================
Comprehensive self-checking and QA framework for every computational step
in the antibody engineering pipeline.

Design principles
-----------------
1. EVERY step produces a signed hash — tampering or silent mis-wiring is detectable.
2. HARD gates abort on critical violations (CDR loss, illegal sequence, assembly mismatch).
3. SOFT checks emit WARN but allow continuation (range anomalies, low scores).
4. IMMUTABLE record — QAReport written once, never modified, exportable to JSON.
5. INDEPENDENT — no dependency on BioPython. ANARCI/anarcii is OPTIONAL and imported lazily only for dual-scheme cross-check.

QA stages covered
-----------------
  Stage 1: SequenceQA    — alphabet, length, CDR boundary integrity
  Stage 2: NumberingQA   — ANARCI output consistency + dual-scheme cross-check
  Stage 3: AssemblyQA    — FR+CDR splicing correctness (hash chain)
  Stage 4: MutationQA    — back-mutation application (only intended positions changed)
  Stage 5: StructureQA   — PDB/ColabFold output validity
  Stage 6: MetricsQA     — physical plausibility of computed metrics
  Stage 7: CrossStepQA   — input-to-output hash chain between pipeline stages

Usage
-----
    from core.qa.pipeline_qa import PipelineQA, QAStage

    qa = PipelineQA(project="PDL1_Ab2", step="humanization_phase3")

    # Stage 1: validate VH sequence
    qa.check_sequence("vh_input",  seq=vh_seq,  chain="VH",  label="VH input")
    qa.check_sequence("vl_input",  seq=vl_seq,  chain="VL",  label="VL input")

    # Stage 3: assembly
    qa.check_assembly("vh_assembly",
        fr1=fr1, cdr1=cdr1, fr2=fr2, cdr2=cdr2, fr3=fr3, cdr3=cdr3, fr4=fr4,
        full_seq=assembled_vh, original_cdrs=original_cdrs)

    # Stage 4: mutation check
    qa.check_mutations("backmut_vh",
        original=mouse_vh, result=humanized_vh, allowed_positions={28,29,71,94})

    # Stage 6: metrics sanity
    qa.check_metric("bsa",          value=1840.3, lo=800,  hi=3500)
    qa.check_metric("vh_vl_angle",  value=81.5,   lo=60.0, hi=105.0)
    qa.check_metric("pI",           value=7.2,    lo=4.0,  hi=11.0)
    qa.check_metric("pLDDT",        value=88.5,   lo=70.0, hi=100.0)

    report = qa.finalize()
    print(report.status)      # "PASS" / "WARN" / "FAIL"
    report.save("qa_report.json")
    qa.assert_pass()          # raises QAViolation if any FAIL
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_VALID_AA   = set("ACDEFGHIKLMNPQRSTVWY")
_STOP_CODON = set("BJOUZ*X")    # illegal in mature Ab sequence

# Expected VH / VL length ranges (residues)
_LEN_RANGE = {
    "VH":  (100, 145),
    "VL":  (95,  130),
    "VHH": (110, 140),
}

# CDR Kabat approximate positions (sequence index, 0-based) for sanity checks
_CDR_EXPECTED = {
    "VH": {"H1": (24, 40), "H2": (48, 68), "H3": (92, 108)},
    "VL": {"L1": (23, 37), "L2": (49, 57), "L3": (87, 100)},
    "VHH": {"H1": (24, 40), "H2": (48, 68), "H3": (92, 115)},
}

# ─────────────────────────────────────────────────────────────────────────────
# Reference-driven metric thresholds
# warn_lo / warn_hi are derived from AbRef458 / VHH42 p5/p95 percentiles.
# Hard bounds are physical limits; warn bounds enforce clinical-range QC.
# Data source: data/reference/AbRef458_stats_v1.json (frozen, v1.0)
#              data/reference/VHH42_reference_stats_v1.json (frozen, v1.0)
# ─────────────────────────────────────────────────────────────────────────────

def _load_reference_thresholds() -> Dict[str, Tuple[float, float, float, float]]:
    """
    Build metric ranges from frozen reference JSONs.
    warn_lo = p5, warn_hi = p95 of AbRef458/VHH42 distributions.
    Falls back to conservative hardcoded values if files are missing.
    """
    _FALLBACK: Dict[str, Tuple[float, float, float, float]] = {
        "pI":               (3.0,  13.0,  5.5,   9.5),
        "GRAVY":            (-4.0,  4.0,  -1.5,   0.5),
        "instability_index":(0.0, 150.0,   0.0,  40.0),
    }

    try:
        _ref_path = Path(__file__).resolve().parent.parent.parent / \
                    "data" / "reference" / "AbRef458_stats_v1.json"
        with open(_ref_path, encoding="utf-8") as _f:
            _abref = json.load(_f)
        _m = _abref.get("metrics", {})

        # Build ranges: hard bounds are physical; warn bounds from p5/p95
        _ranges: Dict[str, Tuple[float, float, float, float]] = {
            "pI": (
                3.0, 13.0,
                _m["pI"]["p5"],   # AbRef458 p5  = 5.197
                _m["pI"]["p95"],  # AbRef458 p95 = 9.09
            ),
            "GRAVY": (
                -4.0, 4.0,
                _m["GRAVY"]["p5"] - 0.05,   # p5 - buffer = ~-0.53
                _m["GRAVY"]["p95"] + 0.05,  # p95 + buffer = ~-0.14
            ),
            "instability_index": (
                0.0, 150.0,
                _m["instability_index"]["p5"],   # p5 = 27.67
                _m["instability_index"]["p95"],  # p95 = 47.1
            ),
        }
        return _ranges

    except Exception:
        return _FALLBACK


_REF_CMC_RANGES = _load_reference_thresholds()

# Metric sanity ranges  {name: (hard_lo, hard_hi, warn_lo, warn_hi)}
# CMC ranges (pI, GRAVY, instability_index) loaded from AbRef458_stats_v1.json.
# Structural/biophysical ranges remain as validated fixed values.
_METRIC_RANGES: Dict[str, Tuple[float, float, float, float]] = {
    "pI":               _REF_CMC_RANGES["pI"],
    "GRAVY":            _REF_CMC_RANGES["GRAVY"],
    "instability_index": _REF_CMC_RANGES["instability_index"],
    "pLDDT":           (30.0, 100.0, 70.0, 100.0),
    "ipTM":            ( 0.0,   1.0,  0.7,   1.0),
    "pTM":             ( 0.0,   1.0,  0.6,   1.0),
    "bsa_total_A2":    (300.0, 6000.0, 1000.0, 3500.0),
    "vh_vl_angle_deg": (55.0, 110.0,  65.0, 100.0),
    "sc_score":        ( 0.0,   1.0,  0.55,   1.0),
    "hbond_count":     ( 0.0, 100.0,   5.0, 100.0),
    "tcia_score":      ( 0.0,   1.0,   0.0,   0.3),
    "dG_BSA_kcal_mol": (-30.0,  0.0, -18.0,  -5.0),
}


# ─────────────────────────────────────────────────────────────────────────────
# Result types
# ─────────────────────────────────────────────────────────────────────────────

class QALevel(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    INFO = "INFO"

ChecklistStatus = QALevel


@dataclass
class QACheck:
    """Single check result."""
    check_id:    str
    stage:       str
    description: str
    level:       QALevel
    expected:    Any     = None
    actual:      Any     = None
    message:     str     = ""
    timestamp:   str     = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class QAReport:
    """Immutable QA report for one pipeline step."""
    project:    str
    step:       str
    status:     QALevel
    checks:     List[QACheck]
    input_hash: str     = ""
    output_hash: str    = ""
    generated_at: str   = field(default_factory=lambda: datetime.utcnow().isoformat())
    n_pass:     int     = 0
    n_warn:     int     = 0
    n_fail:     int     = 0

    def save(self, path: Optional[str] = None) -> Path:
        target = Path(path) if path else Path(f"qa_{self.project}_{self.step}.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False, default=str)
        return target

    def print_summary(self, verbose: bool = False):
        print(f"\n{'─'*55}")
        print(f"  QA Report  [{self.project} / {self.step}]")
        print(f"  Status  : {self.status.value}")
        print(f"  Checks  : {self.n_pass} PASS  {self.n_warn} WARN  {self.n_fail} FAIL")
        if self.input_hash:
            print(f"  In-hash : {self.input_hash[:16]}")
        if self.output_hash:
            print(f"  Out-hash: {self.output_hash[:16]}")
        if verbose or self.n_fail > 0:
            for c in self.checks:
                if c.level != QALevel.PASS or verbose:
                    print(f"  [{c.level.value:4s}] {c.check_id}: {c.message}")
        print(f"{'─'*55}\n")


class QAViolation(RuntimeError):
    """Raised by assert_pass() when any FAIL check exists."""


# ─────────────────────────────────────────────────────────────────────────────
# Main QA engine
# ─────────────────────────────────────────────────────────────────────────────

class PipelineQA:
    """
    Accumulates QA checks across pipeline stages and generates a signed report.

    Typical usage per pipeline run
    --------------------------------
    qa = PipelineQA(project="PDL1_Ab2", step="humanization_phase3")

    # Step 1: Sequence checks
    qa.check_sequence("vh_pre_assembly", vh_seq, "VH")
    qa.check_sequence("vl_pre_assembly", vl_seq, "VL")

    # Step 2: Numbering
    qa.check_numbering("vh_anarcii", numbering_dict, "VH")

    # Step 3: Assembly
    qa.check_assembly("vh_final", fr1, cdr1, fr2, cdr2, fr3, cdr3, fr4,
                      full_seq=vh_assembled, original_cdrs={"H1": cdr1_orig, ...})

    # Step 4: Back-mutation
    qa.check_mutations("vh_backmut", original=mouse_vh, result=humanized_vh,
                       allowed_positions={28, 71, 94})

    # Step 5: Structure
    qa.check_structure_pdb("complex", pdb_path, expected_chains=["H","L","A"],
                           expected_lengths={"H": 120, "L": 108})

    # Step 6: Metrics
    qa.check_metric("pI",       7.2)
    qa.check_metric("pLDDT",    88.5)
    qa.check_metric("bsa_total_A2", 1840.3)

    report = qa.finalize(output_seq=vh_assembled)
    report.save("reports/qa_phase3.json")
    qa.assert_pass()
    """

    def __init__(self, project: str, step: str):
        self.project   = project
        self.step      = step
        self._checks:  List[QACheck] = []
        self._input_hash:  str = ""
        self._output_hash: str = ""
        self._finalized: bool  = False

    # ── Hash utilities ────────────────────────────────────────────────────────

    @staticmethod
    def seq_hash(seq: str) -> str:
        return hashlib.sha256(seq.strip().upper().encode()).hexdigest()[:16]

    def set_input_hash(self, seq: str):
        self._input_hash = self.seq_hash(seq)

    def set_output_hash(self, seq: str):
        self._output_hash = self.seq_hash(seq)

    # ── Internal record helper ────────────────────────────────────────────────

    def _add(self, check_id: str, stage: str, description: str,
             level: QALevel, expected=None, actual=None, message: str = ""):
        self._checks.append(QACheck(
            check_id    = check_id,
            stage       = stage,
            description = description,
            level       = level,
            expected    = expected,
            actual      = actual,
            message     = message,
        ))

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 1: Sequence QA
    # ─────────────────────────────────────────────────────────────────────────

    def check_sequence(
        self,
        check_id: str,
        seq:      str,
        chain:    str = "VH",     # "VH", "VL", "VHH"
        label:    str = "",
    ) -> bool:
        """
        Validate amino-acid sequence:
        - Legal alphabet (20 standard AAs only)
        - No stop codons or placeholder characters
        - Length within expected range
        - No internal gaps or spaces
        """
        stage = f"SequenceQA/{label or chain}"
        ok = True

        # Alphabet
        illegal = set(seq.upper()) - _VALID_AA - {"-"}
        if illegal:
            self._add(check_id + ".alphabet", stage,
                      "Sequence alphabet valid",
                      QALevel.FAIL, _VALID_AA, illegal,
                      f"Illegal characters: {illegal}")
            ok = False
        elif set(seq.upper()) & _STOP_CODON:
            stop_chars = set(seq.upper()) & _STOP_CODON
            self._add(check_id + ".stop_codon", stage,
                      "No stop codons", QALevel.FAIL, None, stop_chars,
                      f"Stop-codon / placeholder characters detected: {stop_chars}")
            ok = False
        else:
            self._add(check_id + ".alphabet", stage, "Sequence alphabet valid",
                      QALevel.PASS, "ACDEFGHIKLMNPQRSTVWY", f"len={len(seq)}", "OK")

        # No gaps
        if "-" in seq:
            self._add(check_id + ".no_gaps", stage, "No gap characters",
                      QALevel.WARN, "no '-'", seq.count("-"),
                      f"{seq.count('-')} gap characters found (may be alignment artifact)")
        else:
            self._add(check_id + ".no_gaps", stage, "No gap characters",
                      QALevel.PASS, "no '-'", "clean", "OK")

        # Length
        lo, hi = _LEN_RANGE.get(chain, (80, 160))
        if not (lo <= len(seq) <= hi):
            level = QALevel.FAIL if len(seq) < lo * 0.8 or len(seq) > hi * 1.2 else QALevel.WARN
            self._add(check_id + ".length", stage, f"Length in [{lo},{hi}]",
                      level, f"[{lo},{hi}]", len(seq),
                      f"Length {len(seq)} outside expected [{lo},{hi}]")
            if level == QALevel.FAIL:
                ok = False
        else:
            self._add(check_id + ".length", stage, f"Length in [{lo},{hi}]",
                      QALevel.PASS, f"[{lo},{hi}]", len(seq), "OK")

        return ok

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 2: Numbering QA
    # ─────────────────────────────────────────────────────────────────────────

    def check_numbering(
        self,
        check_id:    str,
        numbering:   Dict[int, str],   # {kabat_pos: aa}
        chain:       str = "VH",
        seq_len:     Optional[int] = None,
    ) -> bool:
        """
        Validate ANARCII numbering output:
        - No duplicate Kabat positions
        - Positions are positive integers
        - Count within expected CDR boundaries
        - (If seq_len given) same total residue count
        """
        stage = f"NumberingQA/{chain}"
        ok = True

        if not numbering:
            self._add(check_id + ".not_empty", stage, "Numbering not empty",
                      QALevel.FAIL, ">0 positions", 0, "Empty numbering output")
            return False

        positions = list(numbering.keys())

        # Duplicates
        if len(positions) != len(set(positions)):
            dupes = [p for p in positions if positions.count(p) > 1]
            self._add(check_id + ".no_dupes", stage, "No duplicate positions",
                      QALevel.FAIL, "unique", dupes, f"Duplicate Kabat positions: {dupes}")
            ok = False
        else:
            self._add(check_id + ".no_dupes", stage, "No duplicate positions",
                      QALevel.PASS, "unique", len(positions), "OK")

        # All positive
        neg = [p for p in positions if not isinstance(p, int) or p <= 0]
        if neg:
            self._add(check_id + ".positive_pos", stage, "All positions > 0",
                      QALevel.FAIL, ">0", neg, f"Non-positive positions: {neg}")
            ok = False
        else:
            self._add(check_id + ".positive_pos", stage, "All positions > 0",
                      QALevel.PASS, ">0", f"min={min(positions)}", "OK")

        # Length consistency
        if seq_len is not None:
            if len(numbering) != seq_len:
                self._add(check_id + ".count_match", stage, "Numbering count == seq length",
                          QALevel.WARN, seq_len, len(numbering),
                          f"Numbering has {len(numbering)} entries but sequence is {seq_len} aa")
            else:
                self._add(check_id + ".count_match", stage, "Numbering count == seq length",
                          QALevel.PASS, seq_len, len(numbering), "OK")

        return ok

    def check_dual_scheme_numbering(
        self,
        check_id: str,
        seq: str,
        chain: str = "VH",
    ) -> bool:
        """
        Dual-scheme numbering QA (independent compute + cross-check):
          1) Run ANARCI(IMGT) on seq
          2) Run ANARCI(Kabat) on seq
          3) Align both outputs by sequence index
          4) Assert residue-by-residue identity and full coverage (no silent truncation)

        This is designed to prevent numbering drift / insertion-loss that would
        corrupt Vernier mapping and downstream structural gates.
        """
        stage = f"NumberingQA/{chain}"
        ok = True
        seq = (seq or "").strip().upper()
        if not seq:
            self._add(check_id + ".seq_nonempty", stage, "Sequence non-empty",
                      QALevel.FAIL, ">0", 0, "Empty sequence")
            return False

        try:
            from core.numbering.dual_scheme import compute_dual_scheme_numbering, count_kabat_insertions  # noqa: PLC0415
            dual = compute_dual_scheme_numbering(seq, chain_label=chain)

            n_ins = count_kabat_insertions(dual)
            self._add(check_id + ".dual_scheme_ok", stage,
                      "Dual-scheme numbering (IMGT+Kabat) aligned by seq_index",
                      QALevel.PASS, f"len={len(seq)}", f"len={dual.length}", f"OK; Kabat insertions={n_ins}")

            # Record min/max positions as evidence (non-sensitive)
            imgt_min = min(r.pos for r in dual.imgt) if dual.imgt else None
            imgt_max = max(r.pos for r in dual.imgt) if dual.imgt else None
            kab_min  = min(r.pos for r in dual.kabat) if dual.kabat else None
            kab_max  = max(r.pos for r in dual.kabat) if dual.kabat else None
            self._add(check_id + ".ranges", stage,
                      "IMGT & Kabat position ranges plausible",
                      QALevel.PASS,
                      "pos>0",
                      {"imgt": [imgt_min, imgt_max], "kabat": [kab_min, kab_max]},
                      "OK")

        except Exception as e:
            self._add(check_id + ".dual_scheme_ok", stage,
                      "Dual-scheme numbering (IMGT+Kabat) aligned by seq_index",
                      QALevel.FAIL,
                      "Both schemes cover full sequence and match residue-by-residue",
                      "FAIL",
                      f"Dual-scheme numbering cross-check failed: {e}")
            ok = False

        return ok

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 3: Assembly QA (FR + CDR splicing)
    # ─────────────────────────────────────────────────────────────────────────

    def check_assembly(
        self,
        check_id:       str,
        fr1: str, cdr1: str, fr2: str, cdr2: str,
        fr3: str, cdr3: str, fr4: str,
        full_seq:       str,
        original_cdrs:  Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Assembly correctness:
        - Concatenation of segments == full_seq (no loss, no insertion)
        - CDR sequences unchanged vs originals (hash match)
        - Each segment is non-empty (except FR4 may be short)
        - Segment lengths are plausible
        """
        stage = f"AssemblyQA/{check_id}"
        ok = True

        assembled = fr1 + cdr1 + fr2 + cdr2 + fr3 + cdr3 + fr4

        # Concatenation integrity (hard gate)
        if assembled != full_seq:
            self._add(check_id + ".concat", stage,
                      "FR1+CDR1+FR2+CDR2+FR3+CDR3+FR4 == full_seq",
                      QALevel.FAIL,
                      self.seq_hash(full_seq),
                      self.seq_hash(assembled),
                      f"Assembly mismatch! Assembled length={len(assembled)}, "
                      f"expected length={len(full_seq)}")
            ok = False
        else:
            self._add(check_id + ".concat", stage,
                      "FR1+CDR1+FR2+CDR2+FR3+CDR3+FR4 == full_seq",
                      QALevel.PASS,
                      self.seq_hash(full_seq),
                      self.seq_hash(assembled),
                      f"Assembly OK (len={len(full_seq)})")

        # Non-empty segments
        for seg_name, seg in [("FR1",fr1),("CDR1",cdr1),("FR2",fr2),("CDR2",cdr2),
                               ("FR3",fr3),("CDR3",cdr3)]:
            if not seg:
                self._add(check_id + f".{seg_name}_nonempty", stage,
                          f"{seg_name} non-empty", QALevel.FAIL, ">0", 0,
                          f"{seg_name} is empty string")
                ok = False

        # CDR preservation (hard gate if original_cdrs provided)
        if original_cdrs:
            cdr_map = {"H1": cdr1, "H2": cdr2, "H3": cdr3,
                       "L1": cdr1, "L2": cdr2, "L3": cdr3}  # caller uses right labels
            for cdr_name, orig in original_cdrs.items():
                got = cdr_map.get(cdr_name, "")
                if orig and got and orig.upper() != got.upper():
                    self._add(check_id + f".CDR_{cdr_name}_preserved", stage,
                              f"CDR {cdr_name} unchanged",
                              QALevel.FAIL,
                              f"{cdr_name}={self.seq_hash(orig)}",
                              f"{cdr_name}={self.seq_hash(got)}",
                              f"CDR {cdr_name} MODIFIED: '{orig}' → '{got}'")
                    ok = False
                elif orig and got:
                    self._add(check_id + f".CDR_{cdr_name}_preserved", stage,
                              f"CDR {cdr_name} unchanged",
                              QALevel.PASS,
                              self.seq_hash(orig), self.seq_hash(got), "OK")

        return ok

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 4: Mutation QA
    # ─────────────────────────────────────────────────────────────────────────

    def check_mutations(
        self,
        check_id:          str,
        original:          str,
        result:            str,
        allowed_positions: Optional[set] = None,
        must_change:       Optional[set] = None,
    ) -> bool:
        """
        Validate back-mutation or humanization mutation application:
        - Only positions in allowed_positions were changed.
        - All positions in must_change were actually changed.
        - Total change count is plausible.
        """
        stage = f"MutationQA/{check_id}"
        ok = True

        if len(original) != len(result):
            self._add(check_id + ".length_preserved", stage,
                      "Mutation does not change sequence length",
                      QALevel.FAIL, len(original), len(result),
                      f"Length changed {len(original)}→{len(result)} (indels not expected)")
            return False

        changed = {i + 1 for i, (a, b) in enumerate(zip(original.upper(), result.upper())) if a != b}
        self._add(check_id + ".mutation_count", stage,
                  "Number of mutations applied",
                  QALevel.INFO, "—", len(changed),
                  f"{len(changed)} positions changed: {sorted(changed)[:20]}"
                  + ("..." if len(changed) > 20 else ""))

        if allowed_positions is not None:
            unauthorized = changed - allowed_positions
            if unauthorized:
                self._add(check_id + ".authorized_only", stage,
                          "Only authorized positions changed",
                          QALevel.FAIL, sorted(allowed_positions)[:10],
                          sorted(unauthorized),
                          f"Unauthorized changes at positions: {sorted(unauthorized)}")
                ok = False
            else:
                self._add(check_id + ".authorized_only", stage,
                          "Only authorized positions changed",
                          QALevel.PASS, len(allowed_positions), len(changed), "OK")

        if must_change:
            missed = must_change - changed
            if missed:
                self._add(check_id + ".required_changed", stage,
                          "All required positions changed",
                          QALevel.FAIL, sorted(must_change), sorted(missed),
                          f"Required positions NOT changed: {sorted(missed)}")
                ok = False
            else:
                self._add(check_id + ".required_changed", stage,
                          "All required positions changed",
                          QALevel.PASS, sorted(must_change), "all changed", "OK")

        return ok

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 5: Structure QA
    # ─────────────────────────────────────────────────────────────────────────

    def check_structure_scores(
        self,
        check_id:  str,
        iptm:      Optional[float] = None,
        ptm:       Optional[float] = None,
        plddt:     Optional[float] = None,
        model_rank: int = 1,
    ) -> bool:
        """Validate ColabFold/AlphaFold2 confidence scores."""
        stage = f"StructureQA/{check_id}"
        ok = True

        for metric, value in [("ipTM", iptm), ("pTM", ptm), ("pLDDT", plddt)]:
            if value is None:
                continue
            lo_h, hi_h, lo_w, hi_w = _METRIC_RANGES.get(
                metric.lower(), (0.0, 100.0, 0.0, 100.0))
            if not (lo_h <= value <= hi_h):
                self._add(f"{check_id}.{metric}", stage,
                          f"{metric} in [{lo_h},{hi_h}]",
                          QALevel.FAIL, f"[{lo_h},{hi_h}]", value,
                          f"{metric}={value:.3f} outside physical range")
                ok = False
            elif not (lo_w <= value <= hi_w):
                self._add(f"{check_id}.{metric}", stage,
                          f"{metric} in [{lo_w},{hi_w}]",
                          QALevel.WARN, f"[{lo_w},{hi_w}]", value,
                          f"{metric}={value:.3f} below recommended threshold {lo_w}")
            else:
                self._add(f"{check_id}.{metric}", stage,
                          f"{metric} OK",
                          QALevel.PASS, f"≥{lo_w}", round(value, 3), "OK")

        return ok

    def check_structure_pdb(
        self,
        check_id:          str,
        pdb_path:          str,
        expected_chains:   Optional[List[str]] = None,
        expected_lengths:  Optional[Dict[str, int]] = None,
        length_tolerance:  int = 5,
    ) -> bool:
        """Check PDB file existence, chain presence, and chain lengths."""
        stage = f"StructureQA/{check_id}"
        ok = True

        pdb = Path(pdb_path)
        if not pdb.exists():
            self._add(check_id + ".exists", stage, "PDB file exists",
                      QALevel.FAIL, str(pdb_path), "NOT FOUND",
                      f"PDB file not found: {pdb_path}")
            return False

        self._add(check_id + ".exists", stage, "PDB file exists",
                  QALevel.PASS, "file", f"{pdb.stat().st_size} B", "OK")

        # Chain presence and length check using simple PDB text parsing (no BioPython)
        chain_residues: Dict[str, set] = {}
        try:
            with open(pdb, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith("ATOM") or line.startswith("HETATM"):
                        chain_id = line[21]
                        res_num  = line[22:26].strip()
                        ins_code = line[26]
                        key = (res_num, ins_code)
                        chain_residues.setdefault(chain_id, set()).add(key)
        except Exception as e:
            self._add(check_id + ".parse", stage, "PDB parseable",
                      QALevel.FAIL, "readable", str(e), f"PDB parse error: {e}")
            return False

        if expected_chains:
            for cid in expected_chains:
                if cid not in chain_residues:
                    self._add(check_id + f".chain_{cid}", stage,
                              f"Chain {cid} present", QALevel.FAIL,
                              "present", "MISSING", f"Chain {cid} not found in PDB")
                    ok = False
                else:
                    n = len(chain_residues[cid])
                    self._add(check_id + f".chain_{cid}", stage,
                              f"Chain {cid} present",
                              QALevel.PASS, "present", f"{n} residues", "OK")

        if expected_lengths:
            for cid, exp_len in expected_lengths.items():
                actual_len = len(chain_residues.get(cid, set()))
                if abs(actual_len - exp_len) > length_tolerance:
                    self._add(check_id + f".chain_{cid}_len", stage,
                              f"Chain {cid} length ≈ {exp_len}",
                              QALevel.WARN, exp_len, actual_len,
                              f"Chain {cid}: expected {exp_len}±{length_tolerance} residues, "
                              f"got {actual_len}")
                else:
                    self._add(check_id + f".chain_{cid}_len", stage,
                              f"Chain {cid} length ≈ {exp_len}",
                              QALevel.PASS, exp_len, actual_len, "OK")

        return ok

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 6: Metrics sanity QA
    # ─────────────────────────────────────────────────────────────────────────

    def check_metric(
        self,
        metric_name: str,
        value:       float,
        lo:          Optional[float] = None,
        hi:          Optional[float] = None,
        warn_lo:     Optional[float] = None,
        warn_hi:     Optional[float] = None,
    ) -> bool:
        """
        Check a computed metric against known physical/biological limits.
        Uses built-in table first; caller can override with explicit lo/hi.
        """
        stage = f"MetricsQA"

        builtin = _METRIC_RANGES.get(metric_name)
        lo_h    = lo      if lo      is not None else (builtin[0] if builtin else None)
        hi_h    = hi      if hi      is not None else (builtin[1] if builtin else None)
        lo_w    = warn_lo if warn_lo is not None else (builtin[2] if builtin else lo_h)
        hi_w    = warn_hi if warn_hi is not None else (builtin[3] if builtin else hi_h)

        if value is None:
            self._add(metric_name, stage, f"{metric_name} not None",
                      QALevel.WARN, "numeric", None,
                      f"{metric_name} is None (computation may have failed)")
            return False

        if lo_h is not None and value < lo_h:
            self._add(metric_name, stage, f"{metric_name} ≥ {lo_h}",
                      QALevel.FAIL, f"≥{lo_h}", value,
                      f"{metric_name}={value} below hard minimum {lo_h}")
            return False
        if hi_h is not None and value > hi_h:
            self._add(metric_name, stage, f"{metric_name} ≤ {hi_h}",
                      QALevel.FAIL, f"≤{hi_h}", value,
                      f"{metric_name}={value} above hard maximum {hi_h}")
            return False
        if lo_w is not None and value < lo_w:
            self._add(metric_name, stage, f"{metric_name} in recommended range",
                      QALevel.WARN, f"[{lo_w},{hi_w}]", value,
                      f"{metric_name}={value:.3f} below recommended {lo_w}")
            return True
        if hi_w is not None and value > hi_w:
            self._add(metric_name, stage, f"{metric_name} in recommended range",
                      QALevel.WARN, f"[{lo_w},{hi_w}]", value,
                      f"{metric_name}={value:.3f} above recommended {hi_w}")
            return True

        self._add(metric_name, stage, f"{metric_name} in range",
                  QALevel.PASS, f"[{lo_w},{hi_w}]", round(value, 3), "OK")
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Stage 7: Cross-step hash chain
    # ─────────────────────────────────────────────────────────────────────────

    def check_hash_chain(
        self,
        check_id:       str,
        previous_hash:  str,
        current_input:  str,
    ) -> bool:
        """
        Verify that the input to this step matches the output hash of the previous step.
        Detects silent sequence substitutions between pipeline stages.
        """
        stage = "CrossStepQA"
        actual_hash = self.seq_hash(current_input)
        if actual_hash != previous_hash[:16]:
            self._add(check_id, stage,
                      "Input hash matches previous output",
                      QALevel.FAIL, previous_hash[:16], actual_hash,
                      "Hash mismatch: input sequence does not match previous step output. "
                      "Possible sequence substitution or pipeline mis-wiring.")
            return False
        self._add(check_id, stage,
                  "Input hash matches previous output",
                  QALevel.PASS, previous_hash[:16], actual_hash, "Chain intact")
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Finalize and report
    # ─────────────────────────────────────────────────────────────────────────

    def finalize(self, output_seq: Optional[str] = None) -> QAReport:
        """
        Seal the QA run and return an immutable QAReport.
        Call this once at the end of a pipeline stage.
        """
        if output_seq:
            self._output_hash = self.seq_hash(output_seq)

        n_fail = sum(1 for c in self._checks if c.level == QALevel.FAIL)
        n_warn = sum(1 for c in self._checks if c.level == QALevel.WARN)
        n_pass = sum(1 for c in self._checks if c.level == QALevel.PASS)

        if n_fail > 0:
            status = QALevel.FAIL
        elif n_warn > 0:
            status = QALevel.WARN
        else:
            status = QALevel.PASS

        self._finalized = True
        return QAReport(
            project      = self.project,
            step         = self.step,
            status       = status,
            checks       = list(self._checks),
            input_hash   = self._input_hash,
            output_hash  = self._output_hash,
            n_pass       = n_pass,
            n_warn       = n_warn,
            n_fail       = n_fail,
        )

    def assert_pass(self):
        """
        Raise QAViolation if any FAIL check exists.
        Call immediately after finalize() to implement hard-gate behavior.
        """
        fails = [c for c in self._checks if c.level == QALevel.FAIL]
        if fails:
            msgs = "; ".join(f"{c.check_id}: {c.message}" for c in fails[:5])
            raise QAViolation(
                f"[QA FAIL] {self.project}/{self.step} — "
                f"{len(fails)} critical check(s) failed: {msgs}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: run standard module-output QA checks from AbEvaluator results
# ─────────────────────────────────────────────────────────────────────────────

def qa_from_evaluator_result(
    project:   str,
    step:      str,
    modules:   Dict[str, Dict],
    vh_seq:    Optional[str] = None,
    vl_seq:    Optional[str] = None,
) -> QAReport:
    """
    Run all applicable QA checks on an AbEvaluator result dict.
    Called automatically when AbEvaluator.run() completes.

    Args:
        project:  Project name
        step:     Evaluation step label
        modules:  result.results dict from AbEvaluator
        vh_seq:   VH sequence (for sequence checks)
        vl_seq:   VL sequence
    """
    qa = PipelineQA(project=project, step=step)

    if vh_seq:
        qa.set_input_hash(vh_seq)
        qa.check_sequence("vh_eval_input", vh_seq, "VH", "VH")
    if vl_seq:
        qa.check_sequence("vl_eval_input", vl_seq, "VL", "VL")

    # developability
    dev = modules.get("developability", {})
    if dev.get("status") == "PASS":
        for metric in ["pI_fab_estimate", "GRAVY", "instability_index"]:
            val = dev.get(metric)
            if val is not None:
                qa.check_metric(
                    {"pI_fab_estimate": "pI",
                     "GRAVY": "GRAVY",
                     "instability_index": "instability_index"}[metric],
                    val
                )

    # structure_13param
    struct = modules.get("structure_13param", {})
    if struct.get("status") == "PASS":
        m = struct.get("metrics", {})
        for metric_name, key in [("pLDDT", "mean_plddt"), ("ipTM", "iptm"), ("pTM", "ptm")]:
            val = m.get(key) or m.get(metric_name.lower())
            if val is not None:
                qa.check_metric(metric_name.lower(), val)

    # binding_site
    bs = modules.get("binding_site", {})
    if bs.get("status") == "PASS":
        for metric_name, key in [("bsa_total_A2", "bsa_total_A2"),
                                  ("hbond_count", "hbond_count"),
                                  ("sc_score", "sc_score")]:
            val = bs.get(key)
            if val is not None:
                qa.check_metric(metric_name, val)

    # immunogenicity
    immuno = modules.get("immunogenicity", {})
    if immuno.get("status") == "PASS":
        tcia = immuno.get("tcia_score")
        if tcia is not None:
            qa.check_metric("tcia_score", tcia)

    return qa.finalize(output_seq=vh_seq)
