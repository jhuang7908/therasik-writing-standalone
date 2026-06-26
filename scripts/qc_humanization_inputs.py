#!/usr/bin/env python3
"""
qc_humanization_inputs.py — /

：
（ AF2 ）， VH/VL 。
"，"。

：
1.  (、)
2.  (Cys23, Trp41, Cys104 )
3.  (ABARCII )
4.  (VH  VH，VL  VL)
5.  ()
6. [HallucinationGuard V1.0] SEQ_BACK_CHECK —  IMGT- (HARD ABORT)

：
python scripts/qc_humanization_inputs.py --vh "QVQL..." --vl "DIVM..."

python scripts/qc_humanization_inputs.py --fasta input.fasta
"""

import argparse
import sys
import re
from pathlib import Path

_SUITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SUITE_ROOT))

# Try to import anarcii via shim or directly
try:
    from anarcii import Anarcii
except ImportError:
    print("Error: anarcii not installed. QC requires ABARCII/ABARCII.")
    sys.exit(1)

try:
    from core.integrity.hallucination_guard import HallucinationGuard, HallucinationError
    _GUARD_AVAILABLE = True
except ImportError:
    _GUARD_AVAILABLE = False

def check_sequence_basic(seq, chain_type):
    """Basic string checks."""
    seq = seq.upper().strip()
    if not seq:
        return False, "Empty sequence"
    
    # Length check
    if len(seq) < 80:
        return False, f"Sequence too short ({len(seq)} < 80)"
    if len(seq) > 160:
        return False, f"Sequence too long ({len(seq)} > 160)"
        
    # Illegal chars (B, J, O, U, X, Z are technically ambiguous or non-standard, allow X?)
    # Usually X is allowed but flagged. Let's forbid J, O, U, Numbers.
    if re.search(r"[JOU0-9]", seq):
        return False, "Contains illegal characters (J, O, U, digits)"
        
    return True, seq

def check_conserved_residues(numbering, chain_type):
    """Check key conserved residues (IMGT numbering)."""
    # IMGT: Cys 23 (1st-CYS), Trp 41 (CONSERVED-TRP), Cys 104 (2nd-CYS)
    # Note: ABARCII numbering output format: ((num, ins), aa, index)
    
    # Build map: pos -> aa
    pos_map = {}
    for (num, ins), aa, _ in numbering:
        key = f"{num}{ins}".strip()
        pos_map[key] = aa
        
    missing = []
    
    # Cys 23 (IMGT 23)
    if pos_map.get("23") != "C":
        missing.append("Cys23 (1st-CYS)")
        
    # Trp 41 (IMGT 41) - VH usually W, VL usually W (sometimes F/Y in rare cases)
    if pos_map.get("41") not in ["W", "F", "Y"]:
        missing.append("Trp41 (Conserved-TRP)")
        
    # Cys 104 (IMGT 104)
    if pos_map.get("104") != "C":
        missing.append("Cys104 (2nd-CYS)")
        
    if missing:
        return False, f"Missing conserved residues: {', '.join(missing)}"
        
    return True, "OK"

def _build_imgt_linear_scan_targets(numbering: list, seq: str) -> list[tuple]:
    """Build (linear_idx, expected_aa) tuples for known conserved IMGT positions.

    Uses the ABARCII numbering output to map IMGT position numbers to 0-indexed
    linear positions in the raw sequence. This is the source of truth used by
    HallucinationGuard.check_sequence_positions().

    Conserved anchors checked:
      IMGT 23  → Cys (1st-CYS)
      IMGT 41  → Trp/Phe/Tyr (Conserved-TRP)
      IMGT 104 → Cys (2nd-CYS)
    """
    anchor_imgt = {"23": "C", "41": None, "104": "C"}  # None = any W/F/Y accepted
    targets = []
    linear_idx = 0
    for (num, ins), aa, _ in numbering:
        if not aa or not aa.isalpha():
            continue
        key = f"{num}{ins}".strip()
        if key in anchor_imgt:
            expected = anchor_imgt[key]
            if expected is None:
                expected = aa  # accept whatever is at pos 41 (W/F/Y all valid)
            targets.append((linear_idx, expected))
        linear_idx += 1
    return targets


def run_qc(vh_seq, vl_seq, project_dir: Path | None = None):
    print("Running QC on Inputs...", flush=True)
    engine = Anarcii()

    guard = None
    if _GUARD_AVAILABLE and project_dir is not None:
        guard = HallucinationGuard(
            project_dir=project_dir,
            pipeline="vhvl_humanization",
            step="qc_humanization_inputs",
        )

    # 1. VH Check
    if vh_seq:
        ok, msg = check_sequence_basic(vh_seq, "H")
        if not ok:
            print(f"❌ VH Basic Check Failed: {msg}")
            return False
        vh_seq = msg  # cleaned

        # Numbering
        res = engine.number([("VH", vh_seq)], scheme="imgt")
        if not res or not res.get("VH"):
            print("❌ VH Numbering Failed: ABARCII could not align sequence.")
            return False

        vh_res = res["VH"]
        chain_type = vh_res.get("chain_type", "?")
        if chain_type != "H":
            print(f"❌ VH Chain Mismatch: Input labeled VH but identified as {chain_type} chain.")
            return False

        # Conserved residues
        ok, msg = check_conserved_residues(vh_res["numbering"], "H")
        if not ok:
            print(f"❌ VH Conserved Check Failed: {msg}")
            return False

        # ── HallucinationGuard: SEQ_BACK_CHECK ───────────────────────────────
        # Verify that IMGT-numbered conserved positions map to the correct
        # linear indices in the raw VH sequence. HARD ABORT on mismatch.
        if guard is not None:
            try:
                scan_targets = _build_imgt_linear_scan_targets(vh_res["numbering"], vh_seq)
                guard.check_sequence_positions(vh_seq, scan_targets, label="VH_conserved_anchors")
            except HallucinationError as e:
                print(f"❌ [HallucinationGuard] VH SEQ_BACK_CHECK HARD ABORT: {e}")
                guard.write_audit()
                return False
        # ─────────────────────────────────────────────────────────────────────

        print("✅ VH Sequence: PASS")

    # 2. VL Check
    if vl_seq:
        ok, msg = check_sequence_basic(vl_seq, "L")
        if not ok:
            print(f"❌ VL Basic Check Failed: {msg}")
            return False
        vl_seq = msg  # cleaned

        # Numbering
        res = engine.number([("VL", vl_seq)], scheme="imgt")
        if not res or not res.get("VL"):
            print("❌ VL Numbering Failed: ABARCII could not align sequence.")
            return False

        vl_res = res["VL"]
        chain_type = vl_res.get("chain_type", "?")
        if chain_type not in ["K", "L"]:
            print(f"❌ VL Chain Mismatch: Input labeled VL but identified as {chain_type} chain.")
            return False

        # Conserved residues
        ok, msg = check_conserved_residues(vl_res["numbering"], "L")
        if not ok:
            print(f"❌ VL Conserved Check Failed: {msg}")
            return False

        # ── HallucinationGuard: SEQ_BACK_CHECK ───────────────────────────────
        if guard is not None:
            try:
                scan_targets = _build_imgt_linear_scan_targets(vl_res["numbering"], vl_seq)
                guard.check_sequence_positions(vl_seq, scan_targets, label="VL_conserved_anchors")
            except HallucinationError as e:
                print(f"❌ [HallucinationGuard] VL SEQ_BACK_CHECK HARD ABORT: {e}")
                guard.write_audit()
                return False
        # ─────────────────────────────────────────────────────────────────────

        print("✅ VL Sequence: PASS")

    if guard is not None:
        guard.write_audit()

    return True

def main():
    parser = argparse.ArgumentParser(description="QC Humanization Inputs")
    parser.add_argument("--vh", help="VH sequence string")
    parser.add_argument("--vl", help="VL sequence string")
    parser.add_argument("--fasta", help="FASTA file containing VH and VL (headers must contain 'VH'/'Heavy' or 'VL'/'Light')")
    parser.add_argument("--project_dir", help="Project directory for HallucinationGuard audit log (optional)")

    args = parser.parse_args()

    vh = args.vh
    vl = args.vl

    if args.fasta:
        from Bio import SeqIO
        for record in SeqIO.parse(args.fasta, "fasta"):
            h = record.description.lower()
            if "vh" in h or "heavy" in h:
                vh = str(record.seq)
            elif "vl" in h or "light" in h or "vk" in h:
                vl = str(record.seq)

    if not vh and not vl:
        print("Error: No sequences provided. Use --vh/--vl or --fasta.")
        sys.exit(1)

    project_dir = Path(args.project_dir) if args.project_dir else None
    success = run_qc(vh, vl, project_dir=project_dir)
    if not success:
        print("\n⛔ QC FAILED. Do not proceed to structure modeling.")
        sys.exit(1)
    else:
        print("\n✨ QC PASSED. Inputs are valid antibody variable domains.")
        sys.exit(0)

if __name__ == "__main__":
    main()
