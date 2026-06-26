"""
CDR-H3 Conformation Classifier — Proof of Concept

Implements the τ101 / α101 pseudo-dihedral classification metric from:
- Weitzner BD, Dunbrack RL, Gray JJ. "The origin of CDR H3 structural diversity."
  Structure 23, 302-311 (2015).
- Bahrami Dizicheh Z, Chen IL, Koenig P. "VHH CDR-H3 conformation is determined
  by VH germline usage." Communications Biology 6:864 (2023).

Classifies antibody (or VHH) CDR-H3 loops into:
  - Kinked   (0 < α101 < 120° AND 85° < τ101 < 130°)
  - Extended (α101 < -100° AND 100° < τ101 < 145°)
  - Ambiguous (does not match either bucket)

Reads SAbDab-style Chothia-numbered PDB files and reports the angles for the
heavy chain. Used to evaluate whether the V1.6 algorithm should adopt true 3D
geometric classification (replacing the current V1.5 sequence-heuristic at FR2
positions 37/47).

Usage (default test set: 4-5 published PD-1 antibody drugs):
    python scripts/cdr3_conformation_classifier_poc.py

Custom PDB:
    python scripts/cdr3_conformation_classifier_poc.py --pdb path/to/ab.pdb --chain H
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np


# ─────────────────────────────────────────────────────────────────────────────
# Geometry
# ─────────────────────────────────────────────────────────────────────────────

def _dihedral_deg(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray, p4: np.ndarray) -> float:
    """Signed dihedral angle in degrees, range (-180, 180]."""
    b1 = p2 - p1
    b2 = p3 - p2
    b3 = p4 - p3
    n1 = np.cross(b1, b2)
    n2 = np.cross(b2, b3)
    m1 = np.cross(n1, b2 / np.linalg.norm(b2))
    x = np.dot(n1, n2)
    y = np.dot(m1, n2)
    return float(np.degrees(np.arctan2(y, x)))


def _bond_angle_deg(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
    """Cα-Cα-Cα bond angle at p2, in degrees [0, 180]."""
    v1 = p1 - p2
    v2 = p3 - p2
    cos = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
    cos = max(-1.0, min(1.0, cos))
    return float(np.degrees(np.arccos(cos)))


# ─────────────────────────────────────────────────────────────────────────────
# PDB parsing  (no biopython dependency — minimal ATOM record reader)
# ─────────────────────────────────────────────────────────────────────────────

AA3TO1 = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
}


@dataclass
class CaResidue:
    chain: str
    resnum: int
    icode: str
    resname: str
    coord: np.ndarray
    bfactor: float
    chothia_pos: Optional[int] = None
    chothia_icode: str = ""

    @property
    def label(self) -> str:
        return f"{self.resnum}{self.icode.strip()}".strip()

    @property
    def chothia_label(self) -> str:
        if self.chothia_pos is None:
            return "—"
        return f"{self.chothia_pos}{self.chothia_icode}".strip()


def _parse_pdb_ca(pdb_path: Path, chain: str) -> List[CaResidue]:
    """Parse Cα atoms for `chain` from PDB, preserving the file's residue numbering."""
    residues: List[CaResidue] = []
    seen: Dict[Tuple[int, str], CaResidue] = {}
    with pdb_path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if not (line.startswith("ATOM") or line.startswith("HETATM")):
                continue
            if line[12:16].strip() != "CA":
                continue
            if line[21:22] != chain:
                continue
            try:
                resnum = int(line[22:26])
            except ValueError:
                continue
            icode = line[26:27]
            resname = line[17:20].strip()
            try:
                x = float(line[30:38]); y = float(line[38:46]); z = float(line[46:54])
            except ValueError:
                continue
            try:
                bf = float(line[60:66])
            except ValueError:
                bf = 0.0
            r = CaResidue(
                chain=chain, resnum=resnum, icode=icode, resname=resname,
                coord=np.array([x, y, z]), bfactor=bf,
            )
            key = (resnum, icode)
            if key not in seen:
                seen[key] = r
                residues.append(r)
    return residues


def _annotate_chothia(residues: List[CaResidue]) -> List[str]:
    """
    Run ANARCI on the residue 1-letter sequence to obtain Chothia numbering,
    then write back chothia_pos / chothia_icode onto each CaResidue.

    Returns list[str] of warnings.
    """
    warnings: List[str] = []
    seq = "".join(AA3TO1.get(r.resname, "X") for r in residues)
    if "X" in seq or len(seq) < 100:
        warnings.append(f"Sequence has unusual residues or is short ({len(seq)} aa)")
    try:
        from anarcii import Anarcii
    except ImportError:
        warnings.append("anarcii not importable; cannot map to Chothia numbering")
        return warnings

    a = Anarcii(seq_type="antibody", mode="accuracy", verbose=False)
    a.number([seq])
    entry = a.to_scheme("chothia").get("Sequence 1", {})
    if entry.get("error") or entry.get("chain_type") not in ("H",):
        warnings.append(f"ANARCI did not classify as H chain: {entry.get('error') or entry.get('chain_type')}")
        return warnings

    numbering = entry.get("numbering", [])
    # ANARCI returns list of [(pos, icode), aa] for the variable region only.
    # We need to align this back to the PDB residue list. The variable region usually starts
    # at the N-terminus of the chain (PDB residue 1 or close). Use a sliding alignment.
    anarcii_seq = "".join(item[1] for item in numbering if item[1] != "-")
    if not anarcii_seq:
        warnings.append("Empty ANARCI output")
        return warnings

    pdb_seq = seq
    start = pdb_seq.find(anarcii_seq[:30])
    if start < 0:
        # try shorter prefix
        start = pdb_seq.find(anarcii_seq[:20])
    if start < 0:
        warnings.append("Could not align ANARCI output back to PDB sequence")
        return warnings

    j = start
    for (chothia_pos, chothia_icode), aa in numbering:
        if aa == "-":
            continue
        if j >= len(residues):
            break
        if AA3TO1.get(residues[j].resname, "X") != aa:
            warnings.append(f"Mismatch at PDB index {j}: pdb={residues[j].resname} expected={aa}")
            continue
        residues[j].chothia_pos = chothia_pos
        residues[j].chothia_icode = chothia_icode if chothia_icode and chothia_icode != " " else ""
        j += 1
    return warnings


def _find_chothia(residues: List[CaResidue], pos: int, icode: str = "") -> Optional[CaResidue]:
    icode = icode.strip()
    for r in residues:
        if r.chothia_pos == pos and r.chothia_icode.strip() == icode:
            return r
    return None


def _last_chothia_100x(residues: List[CaResidue]) -> Optional[CaResidue]:
    """Return the LAST residue assigned to Chothia position 100 (highest insertion code).

    Sort order: base 100 (empty icode) → 100A → 100B → ... → 100Z.
    Trick: bool(icode != "") makes empty icode sort first (False=0), then by code.
    """
    pos100 = [r for r in residues if r.chothia_pos == 100]
    if not pos100:
        return None
    pos100.sort(key=lambda r: (r.chothia_icode != "", r.chothia_icode))
    return pos100[-1]


# ─────────────────────────────────────────────────────────────────────────────
# τ / α computation + classification
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ConformationResult:
    pdb: str
    label: str
    chain: str
    cdr_h3_length: Optional[int]
    cdr_h3_seq: Optional[str]
    tau_101: Optional[float]                # bond angle Cα(100x_last)-Cα(101)-Cα(102), [0,180]
    alpha_101_A: Optional[float]            # dihedral( 99, 100x_last, 101, 102 ), signed
    alpha_101_B: Optional[float]            # dihedral( 100x_last, 101, 102, 103 ), signed
    classification_A: str                   # using alpha_101_A
    classification_B: str                   # using alpha_101_B
    expected_for_regular: str
    notes: List[str]


def _classify(tau: Optional[float], alpha: Optional[float]) -> str:
    if tau is None or alpha is None:
        return "no_data"
    is_kinked = (0.0 < alpha < 120.0) and (85.0 < tau < 130.0)
    is_extended = (alpha < -100.0) and (100.0 < tau < 145.0)
    if is_kinked and not is_extended:
        return "kinked"
    if is_extended and not is_kinked:
        return "extended"
    return "ambiguous"


def _extract_cdr_h3(residues: List[CaResidue]) -> Tuple[Optional[int], Optional[str]]:
    """Chothia CDR-H3 = positions 95-102 (inclusive of 100A, 100B, ... in order)."""
    cdr = [r for r in residues if r.chothia_pos is not None and 95 <= r.chothia_pos <= 102]
    cdr.sort(key=lambda r: (r.chothia_pos, r.chothia_icode != "", r.chothia_icode))
    if not cdr:
        return None, None
    seq = "".join(AA3TO1.get(r.resname, "X") for r in cdr)
    return len(seq), seq


def classify_pdb(pdb_path: Path, chain: str = "H", label: str = "") -> ConformationResult:
    notes: List[str] = []
    residues = _parse_pdb_ca(pdb_path, chain)
    if not residues:
        return ConformationResult(
            pdb=pdb_path.name, label=label, chain=chain,
            cdr_h3_length=None, cdr_h3_seq=None,
            tau_101=None, alpha_101_A=None, alpha_101_B=None,
            classification_A="no_data", classification_B="no_data",
            expected_for_regular="—",
            notes=[f"No Cα atoms found for chain '{chain}' in {pdb_path.name}"],
        )

    notes.extend(_annotate_chothia(residues))
    if not any(r.chothia_pos is not None for r in residues):
        notes.append("Failed to assign Chothia numbering")
        return ConformationResult(
            pdb=pdb_path.name, label=label, chain=chain,
            cdr_h3_length=None, cdr_h3_seq=None,
            tau_101=None, alpha_101_A=None, alpha_101_B=None,
            classification_A="no_data", classification_B="no_data",
            expected_for_regular="—",
            notes=notes,
        )

    cdr_len, cdr_seq = _extract_cdr_h3(residues)

    r99 = _find_chothia(residues, 99)
    r100_last = _last_chothia_100x(residues)
    r101 = _find_chothia(residues, 101)
    r102 = _find_chothia(residues, 102)
    r103 = _find_chothia(residues, 103)

    needed = {"99": r99, "100x_last": r100_last, "101": r101, "102": r102, "103": r103}
    missing = [k for k, v in needed.items() if v is None]
    if missing:
        notes.append(f"Missing Cα at Chothia: {', '.join(missing)}")
        return ConformationResult(
            pdb=pdb_path.name, label=label, chain=chain,
            cdr_h3_length=cdr_len, cdr_h3_seq=cdr_seq,
            tau_101=None, alpha_101_A=None, alpha_101_B=None,
            classification_A="no_data", classification_B="no_data",
            expected_for_regular="—",
            notes=notes,
        )

    # Weitzner 2015 (Structure 23, 302-311) / Bahrami Dizicheh 2023:
    #   τ101 = pseudo BOND angle at kink: angle( Cα(100x_last), Cα101, Cα102 )    → [0,180°]
    #   α101 = pseudo DIHEDRAL — exact atom tuple is ambiguous in the published abstract.
    # We compute BOTH conventional definitions and report both:
    #   Variant A: dihedral( Cα99, Cα(100x_last), Cα101, Cα102 )   (kink twist, body→bulge)
    #   Variant B: dihedral( Cα(100x_last), Cα101, Cα102, Cα103 ) (kink twist, bulge→FR4)
    # Threshold: kinked (0<α<120 AND 85<τ<130); extended (α<-100 AND 100<τ<145).
    try:
        tau_101 = _bond_angle_deg(r100_last.coord, r101.coord, r102.coord)
        alpha_101_A = _dihedral_deg(r99.coord, r100_last.coord, r101.coord, r102.coord)
        alpha_101_B = _dihedral_deg(r100_last.coord, r101.coord, r102.coord, r103.coord)
    except Exception as e:
        notes.append(f"Angle calc error: {e}")
        return ConformationResult(
            pdb=pdb_path.name, label=label, chain=chain,
            cdr_h3_length=cdr_len, cdr_h3_seq=cdr_seq,
            tau_101=None, alpha_101_A=None, alpha_101_B=None,
            classification_A="no_data", classification_B="no_data",
            expected_for_regular="—",
            notes=notes,
        )

    cls_A = _classify(tau_101, alpha_101_A)
    cls_B = _classify(tau_101, alpha_101_B)

    notes.append(
        f"Cα(99)={r99.label}, "
        f"Cα(100x_last)={r100_last.label}/Chothia{r100_last.chothia_label}, "
        f"Cα(101)={r101.label}, Cα(102)={r102.label}, Cα(103)={r103.label}"
    )

    return ConformationResult(
        pdb=pdb_path.name, label=label, chain=chain,
        cdr_h3_length=cdr_len, cdr_h3_seq=cdr_seq,
        tau_101=round(tau_101, 1),
        alpha_101_A=round(alpha_101_A, 1),
        alpha_101_B=round(alpha_101_B, 1),
        classification_A=cls_A,
        classification_B=cls_B,
        expected_for_regular="kinked (~79% of human VH/VL antibodies, Weitzner 2015)",
        notes=notes,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Default PD-1 antibody test set
# ─────────────────────────────────────────────────────────────────────────────

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
PROJ = WORKSPACE_ROOT / "Antibody_Engineer_Suite" / "projects" / "Reference_Antibodies"

DEFAULT_TESTS: List[Dict[str, str]] = [
    {
        "label":   "Pembrolizumab (Keytruda) — IgG4 humanized [PD-1 complex]",
        "drug":    "Pembrolizumab",
        "pdb_id":  "5JXE",
        "pdb_path": str(PROJ / "Pembrolizumab_Alt_Human_Experimental" / "5JXE.pdb"),
        "chain":   "D",
        "company": "Merck",
    },
    {
        "label":   "Pembrolizumab (full IgG4 crystal, no antigen)",
        "drug":    "Pembrolizumab",
        "pdb_id":  "5DK3",
        "pdb_path": str(PROJ / "Pembrolizumab_Human_Experimental" / "5DK3.pdb"),
        "chain":   "B",
        "company": "Merck",
    },
    {
        "label":   "Pembrolizumab Fv (PD-1 complex, high-res)",
        "drug":    "Pembrolizumab",
        "pdb_id":  "5B8C",
        "pdb_path": str(PROJ / "Pembrolizumab_Human_Experimental" / "5B8C.pdb"),
        "chain":   "B",
        "company": "Merck",
    },
    {
        "label":   "Nivolumab (Opdivo) — IgG4 fully human [PD-1 complex]",
        "drug":    "Nivolumab",
        "pdb_id":  "5WT9",
        "pdb_path": str(PROJ / "Nivolumab_Human_Experimental" / "5WT9.pdb"),
        "chain":   "H",
        "company": "BMS",
    },
    {
        "label":   "Toripalimab (Tuoyi/Loqtorzi) — IgG4 humanized [PD-1 complex]",
        "drug":    "Toripalimab",
        "pdb_id":  "6JBT",
        "pdb_path": str(PROJ / "Toripalimab_Human_Experimental" / "6JBT.pdb"),
        "chain":   "H",
        "company": "Junshi Biosciences",
    },
    {
        "label":   "Tislelizumab (Tevimbra) — IgG4 humanized [PD-1 complex]",
        "drug":    "Tislelizumab",
        "pdb_id":  "7CGW",
        "pdb_path": str(WORKSPACE_ROOT / "7CGW.pdb"),
        "chain":   "H",
        "company": "BeiGene",
    },
]


def _print_table(results: List[Tuple[Dict[str, str], ConformationResult]]) -> None:
    print()
    print("=" * 130)
    print(f"{'Drug':<14} {'PDB':<6} {'CDR-H3':<6} {'τ101°':>8} {'αA(99..)°':>10} {'class-A':<11} "
          f"{'αB(..103)°':>11} {'class-B':<11} {'Sequence':<22}")
    print("-" * 130)
    for meta, res in results:
        cdr_len = res.cdr_h3_length if res.cdr_h3_length is not None else "—"
        tau = f"{res.tau_101:>+8.1f}" if res.tau_101 is not None else f"{'—':>8}"
        aA = f"{res.alpha_101_A:>+10.1f}" if res.alpha_101_A is not None else f"{'—':>10}"
        aB = f"{res.alpha_101_B:>+11.1f}" if res.alpha_101_B is not None else f"{'—':>11}"
        seq = (res.cdr_h3_seq or "")[:22]
        print(f"{meta['drug']:<14} {meta['pdb_id']:<6} {str(cdr_len):<6} {tau} {aA} {res.classification_A:<11} "
              f"{aB} {res.classification_B:<11} {seq:<22}")
    print("=" * 130)


def _print_thresholds() -> None:
    print()
    print("Classification thresholds (Bahrami Dizicheh et al., 2023; Weitzner 2015):")
    print("  KINKED   :  0 < α101 < 120°  AND  85 < τ101 < 130°")
    print("  EXTENDED :  α101 < -100°     AND  100 < τ101 < 145°")
    print("  Reference: ~79% of conventional VH/VL antibodies are KINKED.")
    print()
    print("PoC angle definitions:")
    print("  τ101  = bond angle( Cα(100x_last), Cα101, Cα102 )                [0,180°]")
    print("  α-A   = dihedral( Cα99, Cα(100x_last), Cα101, Cα102 )            signed")
    print("  α-B   = dihedral( Cα(100x_last), Cα101, Cα102, Cα103 )           signed")
    print("  (Both α variants are reported because the published abstract is ambiguous;")
    print("   exact convention will be calibrated in V1.6 against Weitzner 2015 reference data.)")
    print()


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--pdb", type=str, default=None, help="Custom PDB file to classify")
    p.add_argument("--chain", type=str, default="H", help="Chain ID (default H)")
    p.add_argument("--label", type=str, default="custom", help="Custom label for output")
    p.add_argument("--out-json", type=str, default=None, help="Save full JSON output")
    args = p.parse_args(argv)

    if args.pdb:
        path = Path(args.pdb)
        if not path.exists():
            print(f"ERROR: PDB not found: {path}", file=sys.stderr)
            return 2
        res = classify_pdb(path, args.chain, args.label)
        results = [({"drug": args.label, "pdb_id": path.stem,
                    "company": "—", "label": args.label}, res)]
    else:
        results = []
        for meta in DEFAULT_TESTS:
            path = Path(meta["pdb_path"])
            if not path.exists():
                print(f"WARN: skipping {meta['drug']} {meta['pdb_id']} — file not found", file=sys.stderr)
                continue
            res = classify_pdb(path, meta["chain"], meta["label"])
            results.append((meta, res))

    _print_thresholds()
    _print_table(results)

    print()
    print("Notes per case:")
    for meta, res in results:
        print(f"  {meta['drug']} ({meta['pdb_id']}):")
        for n in res.notes:
            print(f"     - {n}")

    if args.out_json:
        out = []
        for meta, res in results:
            row = {"meta": meta, "result": asdict(res)}
            row["result"]["notes"] = list(row["result"]["notes"])
            out.append(row)
        Path(args.out_json).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nFull JSON saved to: {args.out_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
