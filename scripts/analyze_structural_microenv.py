#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
 VHH  (Structural Microenvironment)
: data/vhh_structural_union/vhh_structural_union_index.json
: 
  - data/vhh_structural_microenv/per_entry.json
  - data/vhh_structural_microenv/aggregated.md

:
1.  (IMGT 37 + FR2 hallmark 44/45/47)  SASA ()
2. FR2 hallmark/37 context  5Å  (Neighbor graph)
3. CDR3  FR2  ( CA-CA )
"""

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from Bio.PDB import PDBParser, Selection
from Bio.PDB.NeighborSearch import NeighborSearch
from Bio.PDB.SASA import ShrakeRupley
from Bio.PDB.Polypeptide import is_aa
from Bio.SeqUtils import seq1

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import scripts.anarci_shim  # Ensure ANARCI is available
from anarcii import Anarcii
from core.humanization.kabat_utils import kabat_from_anarcii, cdr_span

INDEX_PATH = REPO / "data" / "vhh_structural_union" / "vhh_structural_union_index.json"
OUT_DIR = REPO / "data" / "vhh_structural_microenv"

# V2.5 alignment:
# - FR2 hallmark positions are IMGT 44/45/47
# - IMGT 37 is retained as CDR1 context residue for four-site display
DISPLAY_POS = [37, 44, 45, 47]


_ANARCII_INST = None
def get_kabat_mapping(sequence: str):
    global _ANARCII_INST
    if _ANARCII_INST is None:
        _ANARCII_INST = Anarcii(seq_type="antibody", mode="accuracy")
    try:
        _ANARCII_INST.number([sequence])
    except Exception as e:
        print("Anarcii error:", e)
        return None
    res = _ANARCII_INST.to_scheme("kabat").get("Sequence 1", {})
    if res.get("error") or res.get("chain_type") != "H":
        return None
    return kabat_from_anarcii(res["numbering"])


def extract_pdb_seq_and_mapping(model, chain_id="H"):
    # Find chain
    cid = chain_id
    if cid not in model:
        cmap = {str(c.id).upper(): c.id for c in model.get_chains()}
        cid = cmap.get(chain_id.upper(), list(model.get_chains())[0].id)
    chain = model[cid]
    
    seq = []
    res_list = []
    for res in chain:
        if res.id[0] != " " or not is_aa(res, standard=True):
            continue
        try:
            seq.append(seq1(res.get_resname()))
            res_list.append(res)
        except Exception:
            pass
    
    sequence = "".join(seq)
    kd = get_kabat_mapping(sequence)
    if not kd:
        return None, None, None, None
        
    # Map Kabat key (pos, ins) to PDB residue
    # Since we numbered the exact sequence extracted from PDB, they align 1:1
    kabat_keys = sorted(kd.keys(), key=lambda x: (x[0], x[1]))
    if len(kabat_keys) != len(res_list):
        # Mismatch, fallback to naive
        return sequence, kd, chain, None
        
    kabat_to_res = {k: r for k, r in zip(kabat_keys, res_list)}
    return sequence, kd, chain, kabat_to_res


def analyze_structure(pdb_path: Path):
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("vhh", str(pdb_path))
    model = structure[0]
    
    seq, kd, chain, kabat_to_res = extract_pdb_seq_and_mapping(model)
    if not kabat_to_res:
        return {"error": "Failed to map Kabat to PDB residues"}
        
    # 1. Compute SASA
    sr = ShrakeRupley()
    sr.compute(model, level="R")
    
    hallmark_sasa = {}
    hallmark_motif = ""
    hallmark_atoms = []
    
    for p in DISPLAY_POS:
        k = (p, "")
        if k in kabat_to_res:
            res = kabat_to_res[k]
            sasa = getattr(res, "sasa", 0.0)
            aa = seq1(res.get_resname())
            hallmark_sasa[str(p)] = {"aa": aa, "sasa": round(sasa, 2)}
            hallmark_motif += aa
            hallmark_atoms.extend(res.get_atoms())
        else:
            hallmark_sasa[str(p)] = {"aa": "-", "sasa": 0.0}
            hallmark_motif += "-"
            
    # 2. Compute 5A Neighbors
    all_atoms = Selection.unfold_entities(model, "A")
    ns = NeighborSearch(all_atoms)
    
    neighbor_res = set()
    for atom in hallmark_atoms:
        close_atoms = ns.search(atom.coord, 5.0)
        for ca in close_atoms:
            neighbor_res.add(ca.get_parent())
            
    # Map neighbor residues back to Kabat
    res_to_kabat = {id(r): k for k, r in kabat_to_res.items()}
    neighbors_kabat = []
    for r in neighbor_res:
        if id(r) in res_to_kabat:
            k = res_to_kabat[id(r)]
            # Exclude the display positions themselves
            if k[0] not in DISPLAY_POS:
                neighbors_kabat.append(f"{k[0]}{k[1]}")
                
    # 3. CDR3 to FR2 distance
    fr2_keys = [k for k in kabat_to_res.keys() if 36 <= k[0] <= 49]
    cdr3_keys = [k for k in kabat_to_res.keys() if 95 <= k[0] <= 102]
    
    fr2_cas = [kabat_to_res[k]["CA"].coord for k in fr2_keys if "CA" in kabat_to_res[k]]
    cdr3_cas = [kabat_to_res[k]["CA"].coord for k in cdr3_keys if "CA" in kabat_to_res[k]]
    
    min_dist = None
    if fr2_cas and cdr3_cas:
        # Pairwise distances
        dists = np.linalg.norm(np.array(cdr3_cas)[:, None, :] - np.array(fr2_cas)[None, :, :], axis=-1)
        min_dist = round(float(np.min(dists)), 2)
        
    return {
        "hallmark_motif": hallmark_motif,
        "hallmark_sasa": hallmark_sasa,
        "neighbors_5A": sorted(neighbors_kabat, key=lambda x: int(x.translate(str.maketrans('','','ABCDEFGHIJKLMNOPQRSTUVWXYZ')))),
        "cdr3_fr2_min_dist_A": min_dist,
        "cdr3_length": len(cdr3_keys)
    }


def main():
    if not INDEX_PATH.is_file():
        print(f"Index not found: {INDEX_PATH}")
        return 1
        
    idx = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    entries = idx.get("clinical_vhh", []) + idx.get("database_b", [])
    
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    results = []
    for ent in entries:
        pdb_rel = ent.get("pdb_model")
        if not pdb_rel:
            continue
        pdb_path = REPO / pdb_rel
        if not pdb_path.is_file():
            continue
            
        print(f"Processing {ent['id']}...", flush=True)
        try:
            res = analyze_structure(pdb_path)
        except Exception as e:
            print(f"  Error: {e}", flush=True)
            continue
        res["id"] = ent["id"]
        res["source_set"] = ent["source_set"]
        results.append(res)
        
    (OUT_DIR / "per_entry.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    
    # Aggregate
    motif_stats = defaultdict(lambda: {"count": 0, "cdr3_lens": [], "min_dists": [], "sasa_sum": 0.0})
    for r in results:
        if "error" in r:
            continue
        m = r["hallmark_motif"]
        st = motif_stats[m]
        st["count"] += 1
        st["cdr3_lens"].append(r["cdr3_length"])
        if r["cdr3_fr2_min_dist_A"] is not None:
            st["min_dists"].append(r["cdr3_fr2_min_dist_A"])
        sasa_total = sum(d["sasa"] for d in r["hallmark_sasa"].values())
        st["sasa_sum"] += sasa_total
        
    md = ["# VHH Structural Microenvironment Analysis\n"]
    md.append(f"Analyzed {len(results)} structures (Clinical + Database B).\n")
    md.append("## Hallmark Motif Aggregation\n")
    md.append("| Motif | Count | Avg CDR3 Len | Avg CDR3-FR2 Dist (Å) | Avg Total SASA (Å²) |")
    md.append("|---|---|---|---|---|")
    
    for m, st in sorted(motif_stats.items(), key=lambda x: -x[1]["count"]):
        avg_cdr3 = sum(st["cdr3_lens"]) / st["count"]
        avg_dist = sum(st["min_dists"]) / len(st["min_dists"]) if st["min_dists"] else float('nan')
        avg_sasa = st["sasa_sum"] / st["count"]
        md.append(f"| **{m}** | {st['count']} | {avg_cdr3:.1f} | {avg_dist:.2f} | {avg_sasa:.1f} |")
        
    (OUT_DIR / "aggregated.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Done. Wrote {OUT_DIR}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
