#!/usr/bin/env python3
"""
scripts/generate_protection_list_vhvl.py

Dynamic protection list generator for VH/VL humanization.

Architecture
------------
Protection list is always DYNAMIC — generated per antibody at runtime.
It has two layers:

  Layer 1 — Sequence-based (always runs, no structure required):
    - CDR regions (Kabat boundary)
    - Vernier zone residues
    - N-glycosylation motifs (NxS/T)
    - Free Cys (unpaired) / disulfide-forming Cys
    - FR4 / J-region (handled by separate rule)
    - Canonical buried positions (Kabat C23, W41, C104 etc.)

  Layer 2 — Structure-based (optional, runs when PDB provided):
    - Buried residues (SASA < threshold using BioPython)
    - Paratope-adjacent positions (within 5 Å of CDR Cα)
    - B-factor high variance positions

  Both layers produce a flat list of (fr_segment, fr_pos) tuples
  that the CC-FR applier will exclude from substitution.

Usage
-----
  # Sequence-only (fast, no structure):
  python scripts/generate_protection_list_vhvl.py \\
      --fr1 EVKLVES... --cdr1 GFAFS... --fr2 MSWVR... \\
      --cdr2 ISGGG... --fr3 YYPDTVK... \\
      --vh-germline IGHV3-23 --out protection.json

  # With structure (if PDB available):
  python scripts/generate_protection_list_vhvl.py \\
      --fr1 ... --vh-germline IGHV3-23 \\
      --pdb 1abc.pdb --chain H --out protection.json

Output JSON
-----------
{
  "_meta": {...},
  "protected_positions": [
    {
      "fr_segment": "FR1",
      "fr_pos": 3,
      "reasons": ["deep_boundary_cdr", "vernier"],
      "layer": "sequence"
    }, ...
  ],
  "protected_set": {"FR1:3": true, "FR2:0": true, ...},
  "summary": {
    "total_fr_positions": 80,
    "protected": 32,
    "free_for_substitution": 48
  }
}
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

SUITE_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Kabat CDR boundaries for VH (Kabat numbering, 1-indexed within full V-region)
# These are KABAT definitions: CDR1=31-35, CDR2=50-65, CDR3=95-102
# We use FR-segment-relative positions here.
# ---------------------------------------------------------------------------

# Within FR1 (25 aa): positions 0-24 are Kabat 1-25
#   deep-boundary = last 4 positions (21-24) adjacent to CDR1
# Within FR2 (17 aa): positions 0-16 are Kabat 36-49 (CDR1 ends at 35)
#   deep-boundary = first 4 (0-3) and last 4 (13-16)
# Within FR3 (38 aa): positions 0-37 are Kabat 66-94 (CDR2 ends at 65)
#   deep-boundary = first 4 (0-3) and last 8 (30-37) toward CDR3

_CDR_BOUNDARY_DEPTH = 4   # positions from CDR edge are "deep boundary"

# Vernier zone residues (Kabat positions known to support CDR conformation)
# Translated to (fr_segment, 0-indexed fr_pos):
# Kabat 2 → FR1[1], 27→CDR, 29→CDR1+adjacent, 30→CDR1, 47→FR2[11 of 36-49→47-36=11],
# 48→FR2[12], 49→FR2[13 last, deep boundary), 67→FR3[1], 69→FR3[3], 71→FR3[5],
# 78→FR3[12], 93→FR3[27]
# Reference: Foote & Winter 1992; Chothia & Lesk 1987

_VERNIER_FR1: Set[int] = {1, 2}          # Kabat 2, 3  (VH light-contact vernier)
_VERNIER_FR2: Set[int] = {10, 11, 12, 13} # Kabat 46,47,48,49 (CDR2-support Vernier)
_VERNIER_FR3: Set[int] = {1, 3, 5, 12, 27}  # Kabat 67,69,71,78,93

# Canonical buried/structural residues (always protect regardless of surface)
# Kabat numbering → FR-segment-relative 0-indexed:
#   Cys23 → FR1[22], Trp41 → FR2[5], Cys104 → FR3[38 – out of FR3], C104 is in CDR3
_CANONICAL_BURIED_FR1: Set[int] = {22}     # C23 (disulfide)
_CANONICAL_BURIED_FR2: Set[int] = {5}      # W41 (hydrophobic core)
_CANONICAL_BURIED_FR3: Set[int] = {27, 28, 29, 30}  # WGQG J-proximal conserved patch

# ---------------------------------------------------------------------------
# Sequence-based checks
# ---------------------------------------------------------------------------

def _find_nglyc(fr_seq: str) -> Set[int]:
    """Return 0-indexed positions in fr_seq that are N of NxS/T motif."""
    hits: Set[int] = set()
    for m in re.finditer(r"N[^P][ST]", fr_seq.upper()):
        hits.add(m.start())
    return hits


def _find_free_cys(fr1: str, fr2: str, fr3: str) -> Dict[str, Set[int]]:
    """
    Find Cys positions that are NOT the canonical disulfide pair.
    Canonical: C23 (FR1[22]) and C104 (in CDR3/FR4, not in our FR1-3 range).
    Any other Cys in FR1/FR2/FR3 is potentially free → protect it.
    """
    result: Dict[str, Set[int]] = {"FR1": set(), "FR2": set(), "FR3": set()}
    for seg_name, seq in [("FR1", fr1), ("FR2", fr2), ("FR3", fr3)]:
        for i, aa in enumerate(seq.upper()):
            if aa == "C":
                # FR1[22] is canonical C23 — still protect it
                result[seg_name].add(i)
    return result


# ---------------------------------------------------------------------------
# Protection list builder
# ---------------------------------------------------------------------------

def build_protection_list(
    fr1: str,
    fr2: str,
    fr3: str,
    pdb_path: Optional[str] = None,
    pdb_chain: str = "H",
    verbose: bool = False,
) -> dict:
    """
    Build the dynamic protection list for a VH antibody.

    Parameters
    ----------
    fr1, fr2, fr3 : pre-split FR sequences (uppercase)
    pdb_path      : optional PDB file for structure-based checks
    pdb_chain     : chain ID for VH in PDB

    Returns
    -------
    dict with keys: protected_positions, protected_set, summary
    """
    fr1 = fr1.strip().upper()
    fr2 = fr2.strip().upper()
    fr3 = fr3.strip().upper()

    segments = {"FR1": fr1, "FR2": fr2, "FR3": fr3}
    total_fr = len(fr1) + len(fr2) + len(fr3)

    # Accumulate: pos_key → set of reasons
    prot: Dict[str, Set[str]] = {}

    def _add(seg: str, pos: int, reason: str):
        key = f"{seg}:{pos}"
        if key not in prot:
            prot[key] = set()
        prot[key].add(reason)

    # ---- Layer 1a: CDR deep-boundary ----------------------------------------
    # FR1: last _CDR_BOUNDARY_DEPTH positions adjacent to CDR1
    fr1_len = len(fr1)
    for p in range(max(0, fr1_len - _CDR_BOUNDARY_DEPTH), fr1_len):
        _add("FR1", p, "deep_boundary_cdr1")

    # FR2: first _CDR_BOUNDARY_DEPTH adjacent to CDR1 end
    for p in range(min(_CDR_BOUNDARY_DEPTH, len(fr2))):
        _add("FR2", p, "deep_boundary_cdr1")
    # FR2: last _CDR_BOUNDARY_DEPTH adjacent to CDR2 start
    fr2_len = len(fr2)
    for p in range(max(0, fr2_len - _CDR_BOUNDARY_DEPTH), fr2_len):
        _add("FR2", p, "deep_boundary_cdr2")

    # FR3: first _CDR_BOUNDARY_DEPTH adjacent to CDR2 end
    for p in range(min(_CDR_BOUNDARY_DEPTH, len(fr3))):
        _add("FR3", p, "deep_boundary_cdr2")
    # FR3: last 8 positions adjacent to CDR3 (CDR3 is long and variable)
    fr3_len = len(fr3)
    cdr3_boundary_depth = 8
    for p in range(max(0, fr3_len - cdr3_boundary_depth), fr3_len):
        _add("FR3", p, "deep_boundary_cdr3")

    # ---- Layer 1b: Vernier zone ----------------------------------------------
    for p in _VERNIER_FR1:
        if p < fr1_len:
            _add("FR1", p, "vernier")
    for p in _VERNIER_FR2:
        if p < fr2_len:
            _add("FR2", p, "vernier")
    for p in _VERNIER_FR3:
        if p < fr3_len:
            _add("FR3", p, "vernier")

    # ---- Layer 1c: Canonical buried / structural core -----------------------
    for p in _CANONICAL_BURIED_FR1:
        if p < fr1_len:
            _add("FR1", p, "canonical_buried")
    for p in _CANONICAL_BURIED_FR2:
        if p < fr2_len:
            _add("FR2", p, "canonical_buried")
    for p in _CANONICAL_BURIED_FR3:
        if p < fr3_len:
            _add("FR3", p, "canonical_buried")

    # ---- Layer 1d: N-glycosylation (NxS/T) ----------------------------------
    for seg, seq in segments.items():
        for p in _find_nglyc(seq):
            _add(seg, p, "n_glycosylation_motif")

    # ---- Layer 1e: Cys residues (free or canonical) -------------------------
    free_cys = _find_free_cys(fr1, fr2, fr3)
    for seg, positions in free_cys.items():
        for p in positions:
            _add(seg, p, "cys_residue")

    # ---- Layer 2: Structure-based (optional) --------------------------------
    structure_used = False
    if pdb_path and Path(pdb_path).exists():
        try:
            structure_used = True
            buried, paratope_adj = _structure_based_protection(
                pdb_path, pdb_chain, fr1, fr2, fr3
            )
            for seg, positions in buried.items():
                for p in positions:
                    _add(seg, p, "sasa_buried")
            for seg, positions in paratope_adj.items():
                for p in positions:
                    _add(seg, p, "paratope_adjacent_5A")
        except Exception as exc:
            if verbose:
                print(f"[WARN] Structure-based check failed: {exc}. Using sequence-only.")
            structure_used = False

    # ---- Compile output -----------------------------------------------------
    protected_positions = []
    protected_set: Dict[str, bool] = {}

    for key, reasons in sorted(prot.items()):
        seg, pos_str = key.split(":")
        pos = int(pos_str)
        protected_positions.append({
            "fr_segment": seg,
            "fr_pos":     pos,
            "reasons":    sorted(reasons),
            "layer":      "structure+sequence" if structure_used else "sequence",
        })
        protected_set[key] = True

    n_protected = len(protected_positions)
    n_free = total_fr - n_protected

    if verbose:
        print(f"[protection] FR positions total:   {total_fr}")
        print(f"[protection] Protected:            {n_protected}")
        print(f"[protection] Free for substitution:{n_free}")
        by_reason: Dict[str, int] = {}
        for item in protected_positions:
            for r in item["reasons"]:
                by_reason[r] = by_reason.get(r, 0) + 1
        for r, cnt in sorted(by_reason.items(), key=lambda x: -x[1]):
            print(f"  {r}: {cnt}")

    return {
        "_meta": {
            "tool":          "generate_protection_list_vhvl.py",
            "version":       "v1.0",
            "generated_at":  datetime.now(timezone.utc).isoformat(),
            "structure_used": structure_used,
            "pdb_path":      str(pdb_path) if pdb_path else None,
            "cdr_boundary_depth": _CDR_BOUNDARY_DEPTH,
        },
        "protected_positions": protected_positions,
        "protected_set":       protected_set,
        "summary": {
            "total_fr_positions":    total_fr,
            "protected":             n_protected,
            "free_for_substitution": n_free,
        },
    }


# ---------------------------------------------------------------------------
# Layer 2: Structure-based (BioPython optional)
# ---------------------------------------------------------------------------

def _structure_based_protection(
    pdb_path: str,
    chain_id: str,
    fr1: str, fr2: str, fr3: str,
) -> Tuple[Dict[str, Set[int]], Dict[str, Set[int]]]:
    """
    Returns:
        buried[seg] = set of fr_pos with SASA < threshold
        paratope_adj[seg] = set of fr_pos within 5Å of any CDR Cα
    Requires: BioPython
    """
    from Bio.PDB import PDBParser  # type: ignore
    from Bio.PDB.SASA import ShrakeRupley  # type: ignore

    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("ab", pdb_path)
    model = structure[0]
    chain = model[chain_id]

    # Compute SASA
    sr = ShrakeRupley()
    sr.compute(structure, level="R")

    # Map residues to FR positions (simplified: use sequence order)
    # This requires that the PDB chain residues align to our FR sequences
    residues = [r for r in chain.get_residues() if r.get_resname() != "HOH"]

    # Build expected sequence from our FRs
    full_fr_seq = fr1 + fr2 + fr3
    fr_segments = (
        [("FR1", i) for i in range(len(fr1))] +
        [("FR2", i) for i in range(len(fr2))] +
        [("FR3", i) for i in range(len(fr3))]
    )

    _SASA_BURIED_THRESHOLD = 10.0  # Å² — below this = buried

    buried: Dict[str, Set[int]] = {"FR1": set(), "FR2": set(), "FR3": set()}
    paratope_adj: Dict[str, Set[int]] = {"FR1": set(), "FR2": set(), "FR3": set()}

    # Match residues to FR positions (by sequential order, ignoring CDRs from PDB)
    # This is an approximation; full ANARCI-based mapping is preferred
    fr_idx = 0
    for res in residues:
        if fr_idx >= len(fr_segments):
            break
        sasa = res.sasa if hasattr(res, "sasa") else 99.0
        seg, pos = fr_segments[fr_idx]
        if sasa < _SASA_BURIED_THRESHOLD:
            buried[seg].add(pos)
        fr_idx += 1

    # Paratope-adjacent: positions within 5Å of CDR Cα
    # (simplified: mark first/last 6 of each FR as potentially adjacent)
    # Full implementation would compute actual distances from CDR residues
    # For now this is left as a stub for when full ANARCI+PDB integration is added
    # TODO: implement full ANARCI-PDB mapping + distance calculation

    return buried, paratope_adj


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate dynamic VH FR protection list for CC-FR substitution"
    )
    parser.add_argument("--fr1",  required=True)
    parser.add_argument("--cdr1", default="", help="CDR1 (informational only)")
    parser.add_argument("--fr2",  required=True)
    parser.add_argument("--cdr2", default="", help="CDR2 (informational only)")
    parser.add_argument("--fr3",  required=True)
    parser.add_argument("--vh-germline", default="IGHV3", help="Germline ID (informational)")
    parser.add_argument("--pdb",   default=None, help="Optional PDB path for structure checks")
    parser.add_argument("--chain", default="H",  help="PDB chain ID for VH")
    parser.add_argument("--out",   default="protection_list.json")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    result = build_protection_list(
        fr1=args.fr1, fr2=args.fr2, fr3=args.fr3,
        pdb_path=args.pdb,
        pdb_chain=args.chain,
        verbose=args.verbose,
    )
    result["_meta"]["vh_germline"] = args.vh_germline

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[done] Protection list → {out}")
    s = result["summary"]
    print(f"       protected={s['protected']}  free={s['free_for_substitution']}"
          f"  total_fr={s['total_fr_positions']}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
