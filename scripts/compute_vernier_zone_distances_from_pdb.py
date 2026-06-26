#!/usr/bin/env python3
"""
Compute VHH Vernier zone positions and their distances to CDRs from a PDB structure.

Definition used (structure-based):
- Number the VHH chain with ANARCII (IMGT scheme) using the repo wrapper
  `core.numbering.imgt_anarcii.imgt_number_anarcii_indexed`.
- Define CDRs by IMGT ranges:
    CDR1: 27-38
    CDR2: 56-65
    CDR3: 105-117
- Define Vernier zone as framework residues (non-CDR) whose minimum heavy-atom distance
  to any CDR residue is <= cutoff (default 5.0 Å).

Outputs JSON + Markdown.

Usage:
  python scripts/compute_vernier_zone_distances_from_pdb.py ^
    --pdb projects/anti_HSA_VHH/structures/8Z8V.pdb ^
    --chain B ^
    --out_dir projects/anti_HSA_VHH ^
    --cutoff 5.0
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys

from Bio.PDB import PDBParser, is_aa
from Bio.SeqUtils import seq1

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.numbering.imgt_anarcii import imgt_number_anarcii_indexed


@dataclass(frozen=True)
class ImgtPos:
    pos: int
    ins: str  # insertion code, usually ' ' or 'A'...

    def __str__(self) -> str:
        ins = "" if self.ins.strip() == "" else self.ins.strip()
        return f"{self.pos}{ins}"


IMGT_CDR_RANGES = {
    "CDR1": (27, 38),
    "CDR2": (56, 65),
    "CDR3": (105, 117),
}

IMGT_REGION_RANGES = {
    "FR1": (1, 26),
    "CDR1": (27, 38),
    "FR2": (39, 55),
    "CDR2": (56, 65),
    "FR3": (66, 104),
    "CDR3": (105, 117),
    "FR4": (118, 128),
}


def region_of_pos(pos: int) -> str:
    for name, (a, b) in IMGT_REGION_RANGES.items():
        if a <= pos <= b:
            return name
    return "OTHER"


def extract_chain_sequence_and_residues(pdb_path: Path, chain_id: str) -> Tuple[str, List]:
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure(pdb_path.stem, str(pdb_path))
    model = next(structure.get_models())
    chain = model[chain_id]

    residues = [r for r in chain.get_residues() if is_aa(r, standard=True)]
    # Ensure we only keep residues with CA for stable ordering
    residues = [r for r in residues if "CA" in r]

    aas: List[str] = []
    kept_res: List = []
    for r in residues:
        try:
            aas.append(seq1(r.resname))
        except Exception:
            continue
        kept_res.append(r)

    seq = "".join(aas)
    return seq, kept_res


def min_heavy_atom_distance(res_a, res_b) -> float:
    min_d = float("inf")
    for a in res_a.get_atoms():
        if getattr(a, "element", None) == "H":
            continue
        for b in res_b.get_atoms():
            if getattr(b, "element", None) == "H":
                continue
            d = (a.coord - b.coord)
            dist = float((d * d).sum() ** 0.5)
            if dist < min_d:
                min_d = dist
    return min_d


def build_imgt_annotation(seq: str) -> Tuple[Dict[int, Dict], Dict[int, ImgtPos]]:
    """
    Returns:
      - seq_idx -> {pos, ins, aa}
      - seq_idx -> ImgtPos
    """
    numbered = imgt_number_anarcii_indexed(seq)
    rows = numbered["rows"]
    seq_idx_map: Dict[int, Dict] = {}
    seq_idx_to_imgt: Dict[int, ImgtPos] = {}
    for r in rows:
        si = r["seq_idx"]
        ip = ImgtPos(int(r["pos"]), str(r.get("ins_code", " ")))
        seq_idx_map[int(si)] = {"imgt_pos": ip.pos, "ins": ip.ins, "aa": r["aa"]}
        seq_idx_to_imgt[int(si)] = ip
    return seq_idx_map, seq_idx_to_imgt


def is_cdr_pos(pos: int) -> Optional[str]:
    for cdr_name, (a, b) in IMGT_CDR_RANGES.items():
        if a <= pos <= b:
            return cdr_name
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdb", required=True)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--cutoff", type=float, default=5.0)
    args = ap.parse_args()

    pdb_path = Path(args.pdb)
    chain_id = str(args.chain)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cutoff = float(args.cutoff)

    seq, residues = extract_chain_sequence_and_residues(pdb_path, chain_id)
    seq_idx_map, seq_idx_to_imgt = build_imgt_annotation(seq)

    # Build CDR index lists (by sequence index/residue index, they align 1:1)
    cdr_indices: Dict[str, List[int]] = {"CDR1": [], "CDR2": [], "CDR3": []}
    fr_indices: List[int] = []

    for i in range(len(residues)):
        ip = seq_idx_to_imgt.get(i)
        if ip is None:
            continue
        cdr_name = is_cdr_pos(ip.pos)
        if cdr_name:
            cdr_indices[cdr_name].append(i)
        else:
            fr_indices.append(i)

    def min_dist_to_cdr(i: int, cdr_name: str) -> float:
        mind = float("inf")
        for j in cdr_indices[cdr_name]:
            d = min_heavy_atom_distance(residues[i], residues[j])
            if d < mind:
                mind = d
        return mind

    results: List[Dict] = []
    vernier: List[Dict] = []

    for i in fr_indices:
        ip = seq_idx_to_imgt.get(i)
        if ip is None:
            continue
        aa = seq[i] if 0 <= i < len(seq) else "?"
        region = region_of_pos(ip.pos)

        d1 = min_dist_to_cdr(i, "CDR1") if cdr_indices["CDR1"] else float("inf")
        d2 = min_dist_to_cdr(i, "CDR2") if cdr_indices["CDR2"] else float("inf")
        d3 = min_dist_to_cdr(i, "CDR3") if cdr_indices["CDR3"] else float("inf")
        dmin = min(d1, d2, d3)
        nearest = "CDR1" if dmin == d1 else ("CDR2" if dmin == d2 else "CDR3")

        r = residues[i]
        pdb_resseq = int(r.id[1])
        pdb_icode = (r.id[2].strip() if isinstance(r.id[2], str) else "")

        row = {
            "imgt": str(ip),
            "imgt_pos": ip.pos,
            "imgt_ins": ip.ins,
            "region": region,
            "aa": aa,
            "seq_idx": i,
            "pdb_resseq": pdb_resseq,
            "pdb_icode": pdb_icode or None,
            "min_dist_to_cdr1_A": d1,
            "min_dist_to_cdr2_A": d2,
            "min_dist_to_cdr3_A": d3,
            "min_dist_to_any_cdr_A": dmin,
            "nearest_cdr": nearest,
        }
        results.append(row)
        if dmin <= cutoff:
            vernier.append(row)

    # Sort outputs by IMGT position then insertion
    def sort_key(x: Dict) -> Tuple[int, str]:
        return (int(x["imgt_pos"]), str(x.get("imgt_ins", " ")))

    results_sorted = sorted(results, key=sort_key)
    vernier_sorted = sorted(vernier, key=sort_key)

    payload = {
        "pdb": str(pdb_path),
        "chain": chain_id,
        "sequence_length": len(seq),
        "cutoff_A": cutoff,
        "cdr_ranges_imgt": IMGT_CDR_RANGES,
        "counts": {
            "cdr1_n": len(cdr_indices["CDR1"]),
            "cdr2_n": len(cdr_indices["CDR2"]),
            "cdr3_n": len(cdr_indices["CDR3"]),
            "framework_n": len(fr_indices),
            "vernier_n": len(vernier_sorted),
        },
        "vernier_zone": vernier_sorted,
        "all_framework_distances": results_sorted,
    }

    json_out = out_dir / f"vernier_zone_distances_{pdb_path.stem}_{chain_id}.json"
    json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    md_out = out_dir / f"Vernier_zone_CDR_{pdb_path.stem}_{chain_id}.md"
    md: List[str] = []
    md.append("# Vernier zone  CDR （）\n\n")
    md.append(f"- **PDB**: `{pdb_path.as_posix()}`\n")
    md.append(f"- **Chain**: `{chain_id}`\n")
    md.append(f"- ****: {cutoff:.2f} Å（CDR）\n")
    md.append(f"- **VHH（）**: {len(seq)} aa\n\n")
    md.append("## \n\n")
    md.append(
        f"- **CDR1/2/3 **: {payload['counts']['cdr1_n']} / {payload['counts']['cdr2_n']} / {payload['counts']['cdr3_n']}\n"
    )
    md.append(f"- ****: {payload['counts']['framework_n']}\n")
    md.append(f"- **Vernier （≤{cutoff:.2f}Å）**: {payload['counts']['vernier_n']}\n\n")

    md.append("## Vernier zone （ IMGT ）\n\n")
    md.append("| IMGT |  |  | CDR | (Å) |\n")
    md.append("|---:|:---:|:---:|:---:|---:|\n")
    for r in vernier_sorted:
        md.append(
            f"| {r['imgt']} | {r['region']} | {r['aa']} | {r['nearest_cdr']} | {r['min_dist_to_any_cdr_A']:.2f} |\n"
        )

    md.append("\n## \n\n")
    md.append("- Vernier zone ****：CDR、CDR/。\n")
    md.append("- /，（ 4Å  6Å）。\n")

    md_out.write_text("".join(md), encoding="utf-8")

    print(f"Wrote:\n- {json_out}\n- {md_out}")


if __name__ == "__main__":
    main()

