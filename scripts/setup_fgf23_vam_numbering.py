#!/usr/bin/env python
"""
FGF23 VAM Step-0: ANARCI CDR numbering → numbering JSON.

Runs ANARCI on 23F1128 VH (chain H) and VL (chain L), maps CDR residues
to PDB sequential positions in the Boltz Model-0 structure, and writes
projects/fgf 23/vam_boltz_scan/FGF23/FGF23_numbering.json

This JSON is consumed by all downstream Stage-2/3/4/5 scripts.

Usage (conda env anarcii):
  conda run -n anarcii python scripts/setup_fgf23_vam_numbering.py
  conda run -n anarcii python scripts/setup_fgf23_vam_numbering.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── Project paths ──────────────────────────────────────────────────────────
PROJECT_DIR = ROOT / "projects/fgf 23"
VAM_DIR     = PROJECT_DIR / "vam_boltz_scan/FGF23"
BOLTZ_PDB   = PROJECT_DIR / "boltz/FGF23/boltz_results_FGF23/predictions/FGF23/FGF23_model_0.pdb"
OUT_JSON    = VAM_DIR / "FGF23_numbering.json"

# ── 23F1128 sequences ──────────────────────────────────────────────────────
VH_SEQ = "EVQLQQSGPELVKPGASVKMSCKASGYTFTTYVMHWVKQKPGQGLEWIGYSNPYNDGTKYNEKFKGKATLTSAKSSSTAYMELSSLTSEDSAVYYCARGSLGMDYWGQGTSVTVSS"
VL_SEQ = "QIVLTQSPAIMSASPGEKVTMTCSASSSISYMHWYQQKPGTSPKRLMYDTSKLASGVPARFSGSGSGTAYSLTISSMEAEDAATYYCHQRNTYTFGGGTKLEIK"

AB_CHAINS = ["H", "L"]   # VH=H, VL=L in Boltz PDB
AG_CHAINS = ["A"]        # FGF23 antigen

AA3 = {
    "ALA":"A","ARG":"R","ASN":"N","ASP":"D","CYS":"C","GLN":"Q","GLU":"E",
    "GLY":"G","HIS":"H","ILE":"I","LEU":"L","LYS":"K","MET":"M","PHE":"F",
    "PRO":"P","SER":"S","THR":"T","TRP":"W","TYR":"Y","VAL":"V",
}


def _parse_pdb_chain(pdb_path: Path, chain_id: str) -> dict[int, str]:
    """Return {pdb_resi: aa_1letter} for a given chain (ATOM records only)."""
    result: dict[int, str] = {}
    seen: set[int] = set()
    for line in pdb_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("ATOM"):
            continue
        if line[21] != chain_id:
            continue
        try:
            resi = int(line[22:26])
        except ValueError:
            continue
        if resi in seen:
            continue
        seen.add(resi)
        result[resi] = AA3.get(line[17:20].strip().upper(), "X")
    return result


def _run_anarci(seq: str, chain_type: str) -> list[tuple[tuple[int, str], str]]:
    """Run ANARCI and return list of ((res_num, icode), aa) pairs (Chothia)."""
    from anarci import anarci
    results, _, _ = anarci(
        [("query", seq)],
        scheme="chothia",
        assign_germline=False,
        allowed_species=None,
    )
    if not results or not results[0]:
        raise RuntimeError(f"ANARCI returned no results for {chain_type}")
    hits = results[0]
    # hits is list of (numbering, alignment_details, query_start, query_end)
    numbering = hits[0][0]
    # numbering is list of ((res_num, ins_code), aa)
    return [(k, aa) for k, aa in numbering if aa != "-"]


def _chothia_cdr_spans() -> dict[str, tuple[int, int]]:
    """Chothia CDR boundary definitions (inclusive)."""
    return {
        "vh_cdr1": (26, 32),
        "vh_cdr2": (52, 56),
        "vh_cdr3": (95, 102),
        "vl_cdr1": (24, 34),
        "vl_cdr2": (50, 56),
        "vl_cdr3": (89, 97),
    }


def build_mutations(
    anarci_rows: list[tuple[tuple[int, str], str]],
    pdb_residues: dict[int, str],
    locus_prefix: str,       # "vh" or "vl"
    pdb_chain: str,          # "H" or "L"
    cdrs: dict[str, tuple[int, int]],
) -> list[dict]:
    """Map ANARCI-numbered CDR residues to PDB sequential residue numbers."""
    muts: list[dict] = []

    # Build sequential index: ANARCI order → pdb_resi (sequential in structure)
    # Both sequences have no gaps vs PDB (Boltz uses sequential numbering),
    # so we match by insertion order.
    anarci_seq   = [aa for (_, _), aa in anarci_rows]
    anarci_nums  = [num for (num, _), _ in anarci_rows]

    # PDB residues come out sorted by pdb_resi
    pdb_sorted   = sorted(pdb_residues.items())   # [(resi, aa), ...]
    pdb_seq_str  = "".join(aa for _, aa in pdb_sorted)
    anarci_seq_str = "".join(anarci_seq)

    if pdb_seq_str != anarci_seq_str:
        # Minor mismatch tolerance: warn and use offset matching
        print(f"  WARNING: ANARCI/PDB sequence mismatch for chain {pdb_chain}:")
        print(f"    ANARCI: {anarci_seq_str[:40]}")
        print(f"    PDB   : {pdb_seq_str[:40]}")

    # Build a Chothia-num → pdb_resi map via aligned position
    chothia_to_pdb: dict[int, int] = {}
    for i, ((ch_num, icode), aa) in enumerate(anarci_rows):
        if i < len(pdb_sorted):
            pdb_resi, pdb_aa = pdb_sorted[i]
            chothia_to_pdb[ch_num] = pdb_resi

    cdr_spans = cdrs
    locus_map = {f"{locus_prefix}_cdr{n}": cdr_spans.get(f"{locus_prefix}_cdr{n}") for n in [1, 2, 3]}

    for locus, span in locus_map.items():
        if span is None:
            continue
        lo, hi = span
        locus_positions = [
            (idx, ch_num, aa)
            for idx, ((ch_num, _), aa) in enumerate(anarci_rows)
            if lo <= ch_num <= hi
        ]
        for pos_idx, (seq_idx, ch_num, aa) in enumerate(locus_positions):
            pdb_resi = chothia_to_pdb.get(ch_num)
            if pdb_resi is None:
                continue
            muts.append({
                "locus":       locus,
                "haddock_chain": pdb_chain,
                "wt":          aa,
                "pdb_resi":    pdb_resi,
                "kabat_pos":   ch_num,
                "imgt_pos":    None,
                "pos_idx":     pos_idx,
                "cli_mutation": f"{pdb_chain}:{pdb_resi}:{aa}:A",
            })

    return muts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print detected CDR positions; do not write JSON.")
    args = parser.parse_args(argv)

    print(f"[FGF23] Boltz PDB: {BOLTZ_PDB}")
    if not BOLTZ_PDB.is_file():
        print(f"ERROR: Boltz PDB not found: {BOLTZ_PDB}", file=sys.stderr)
        return 1

    # 1. Parse PDB sequences per chain
    pdb_H = _parse_pdb_chain(BOLTZ_PDB, "H")
    pdb_L = _parse_pdb_chain(BOLTZ_PDB, "L")
    print(f"[FGF23] PDB chain H: {len(pdb_H)} residues")
    print(f"[FGF23] PDB chain L: {len(pdb_L)} residues")

    # 2. Run ANARCI
    print("[FGF23] Running ANARCI (Chothia) on VH ...")
    rows_H = _run_anarci(VH_SEQ, "VH")
    print(f"[FGF23] ANARCI VH: {len(rows_H)} positions")

    print("[FGF23] Running ANARCI (Chothia) on VL ...")
    rows_L = _run_anarci(VL_SEQ, "VL")
    print(f"[FGF23] ANARCI VL: {len(rows_L)} positions")

    # 3. Build CDR mutation lists
    cdrs = _chothia_cdr_spans()
    muts_H = build_mutations(rows_H, pdb_H, "vh", "H", cdrs)
    muts_L = build_mutations(rows_L, pdb_L, "vl", "L", cdrs)
    all_muts = muts_H + muts_L

    print(f"\n[FGF23] CDR positions detected: {len(all_muts)}")
    for m in all_muts:
        print(f"  {m['locus']:<12} chain={m['haddock_chain']}  pdb_resi={m['pdb_resi']:>3}  "
              f"Chothia={m['kabat_pos']:>3}  wt={m['wt']}")

    if args.dry_run:
        print("\n[FGF23] Dry-run: no JSON written.")
        return 0

    # 4. Write numbering JSON
    VAM_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "clone": "FGF23",
        "antibody_id": "23F1128",
        "vh_seq": VH_SEQ,
        "vl_seq": VL_SEQ,
        "ab_chains": AB_CHAINS,
        "ag_chains": AG_CHAINS,
        "boltz_pdb": str(BOLTZ_PDB.relative_to(ROOT)).replace("\\", "/"),
        "scheme": "chothia",
        "n_cdr_positions": len(all_muts),
        "ala_scan": {"mutations": all_muts},
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\n[FGF23] Written: {OUT_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
