#!/usr/bin/env python3
"""
Evaluate a multispecific antibody structure against the 84-clinical-antibody benchmark.

Usage:
  python scripts/evaluate_multispecific_structure.py --pdb my_structure.pdb
  python scripts/evaluate_multispecific_structure.py --pdb my_structure.pdb --linker-seq GGGGSGGGGSGGGGS

Logic:
1. Extracts sequence from PDB.
2. Identifies VH/Linker/VL boundaries (by aligning linker sequence).
3. Computes structural metrics (pLDDT, Clashes, Interface Contacts, Linker Geometry).
4. Compares against the distribution of 84 clinical antibodies.
5. Generates a score and diagnostic report with functional impact and recommendations.
"""

import argparse
import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
from Bio.PDB import PDBParser
from Bio.SeqUtils import seq1

# Reference data path
REF_CSV = Path("data/design_rules/multispecific_linker_pipeline/multispecific_84_structure_metrics.csv")

def load_reference_stats():
    if not REF_CSV.exists():
        print(f"Error: Reference data not found at {REF_CSV}")
        sys.exit(1)
    df = pd.read_csv(REF_CSV)
    stats = {
        "plddt_mean": df["mean_plddt"].mean(),
        "plddt_std": df["mean_plddt"].std(),
        "plddt_min_ref": df["mean_plddt"].min(),
        
        "contact_mean": df["contact_vh_vl"].mean(),
        "contact_std": df["contact_vh_vl"].std(),
        "contact_min_ref": df["contact_vh_vl"].min(),
        
        "linker_dist_mean": df["linker_end_to_end_a"].mean(),
        "linker_dist_std": df["linker_end_to_end_a"].std(),
        
        "clash_max_ref": df["clash_total"].max(), # Should be 0
    }
    return stats, df

def get_sequence_from_pdb(pdb_path):
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("target", pdb_path)
    # Assume single chain or first chain
    chain = next(structure.get_chains())
    
    seq = ""
    residues = []
    for res in chain:
        if res.id[0] == " ":
            try:
                aa = seq1(res.get_resname())
                seq += aa
                residues.append(res)
            except:
                pass
    return seq, residues

def find_linker_indices(full_seq, linker_seq):
    # Simple substring search
    start = full_seq.find(linker_seq)
    if start == -1:
        return None, None
    end = start + len(linker_seq)
    return start, end

def compute_metrics(residues, start_idx, end_idx):
    # Indices are 0-based in the residues list
    vh_res = residues[:start_idx]
    linker_res = residues[start_idx:end_idx]
    vl_res = residues[end_idx:]
    
    if not vh_res or not vl_res:
        return None

    # Helper to extract CA coords and B-factors
    def get_data(res_list):
        coords = []
        bfactors = []
        for r in res_list:
            if "CA" in r:
                coords.append(r["CA"].coord)
                bf = r["CA"].bfactor
                # Normalize pLDDT to 0-100
                if bf <= 1.0:
                    bf *= 100.0
                bfactors.append(bf)
        return np.array(coords), np.array(bfactors)

    vh_coords, vh_bf = get_data(vh_res)
    linker_coords, linker_bf = get_data(linker_res)
    vl_coords, vl_bf = get_data(vl_res)
    
    all_bf = np.concatenate([vh_bf, linker_bf, vl_bf]) if len(linker_bf) > 0 else np.concatenate([vh_bf, vl_bf])
    
    # Metrics
    mean_plddt = np.mean(all_bf) if len(all_bf) > 0 else 0
    
    # Clashes (CA < 3.5 A)
    clash_count = 0
    if len(vh_coords) > 0 and len(vl_coords) > 0:
        # VH-VL
        d = np.linalg.norm(vh_coords[:, None, :] - vl_coords[None, :, :], axis=2)
        clash_count += np.sum(d < 3.5)
    if len(vh_coords) > 0 and len(linker_coords) > 0:
        # VH-Linker
        d = np.linalg.norm(vh_coords[:, None, :] - linker_coords[None, :, :], axis=2)
        clash_count += np.sum(d < 3.5)
    if len(linker_coords) > 0 and len(vl_coords) > 0:
        # Linker-VL
        d = np.linalg.norm(linker_coords[:, None, :] - vl_coords[None, :, :], axis=2)
        clash_count += np.sum(d < 3.5)
        
    # Contacts (CA < 8.0 A)
    contact_count = 0
    if len(vh_coords) > 0 and len(vl_coords) > 0:
        d = np.linalg.norm(vh_coords[:, None, :] - vl_coords[None, :, :], axis=2)
        contact_count = np.sum(d < 8.0)
        
    # Linker Distance
    linker_dist = 0.0
    if len(linker_coords) > 1:
        linker_dist = np.linalg.norm(linker_coords[0] - linker_coords[-1])
        
    return {
        "mean_plddt": mean_plddt,
        "clash_total": clash_count,
        "contact_vh_vl": contact_count,
        "linker_end_to_end_a": linker_dist,
        "vh_len": len(vh_res),
        "vl_len": len(vl_res),
        "linker_len": len(linker_res)
    }

def evaluate(metrics, stats):
    score = 100
    report = []
    
    # 1. Clashes
    if metrics["clash_total"] > 0:
        score -= 50
        report.append({
            "metric": "Clashes",
            "value": metrics["clash_total"],
            "status": "FAIL",
            "impact": "Severe structural conflict. The protein is physically impossible or highly strained.",
            "suggestion": "Check linker attachment points. Ensure domains are not forced into overlap. Re-model with a longer linker."
        })
    else:
        report.append({"metric": "Clashes", "value": 0, "status": "PASS", "impact": "None", "suggestion": "None"})

    # 2. Stability (pLDDT)
    # Z-score
    z_plddt = (metrics["mean_plddt"] - stats["plddt_mean"]) / stats["plddt_std"]
    if metrics["mean_plddt"] < 70:
        score -= 30
        status = "FAIL"
        impact = "Low confidence structure. High risk of disorder, aggregation, or proteolysis."
        suggestion = "Check for hydrophobic patches on surface. Consider disulfide stabilization or framework engineering."
    elif z_plddt < -2: # Bottom 2.5% roughly
        score -= 10
        status = "WARNING"
        impact = "Lower stability than clinical benchmarks."
        suggestion = "Review VH/VL pairing preference. Ensure linker is not destabilizing the interface."
    else:
        status = "PASS"
        impact = "Comparable to clinical antibodies."
        suggestion = "None"
        
    report.append({
        "metric": "Global pLDDT",
        "value": f"{metrics['mean_plddt']:.1f} (Ref Mean: {stats['plddt_mean']:.1f})",
        "status": status,
        "impact": impact,
        "suggestion": suggestion
    })

    # 3. Interface Contacts
    z_contact = (metrics["contact_vh_vl"] - stats["contact_mean"]) / stats["contact_std"]
    if metrics["contact_vh_vl"] < 25:
        score -= 20
        status = "FAIL"
        impact = "Loose VH-VL interface. Risk of domain dissociation and reduced antigen binding affinity."
        suggestion = "Linker might be too long or rigid, pulling domains apart. Check interface residues for repulsions."
    elif z_contact < -2:
        score -= 10
        status = "WARNING"
        impact = "Interface looser than average clinical antibody."
        suggestion = "Monitor stability. Consider interface engineering."
    elif z_contact > 3:
        # Too tight? Maybe not bad, but unusual
        status = "NOTE"
        impact = "Very tight interface. Ensure no internal strain."
        suggestion = "None"
    else:
        status = "PASS"
        impact = "Normal VH-VL packing."
        suggestion = "None"
        
    report.append({
        "metric": "VH-VL Contacts",
        "value": f"{metrics['contact_vh_vl']} (Ref Mean: {stats['contact_mean']:.1f})",
        "status": status,
        "impact": impact,
        "suggestion": suggestion
    })

    # 4. Linker Geometry
    # Only evaluate if linker length is similar to reference (15aa)
    # But even for different lengths, end-to-end tells us about domain proximity
    z_dist = (metrics["linker_end_to_end_a"] - stats["linker_dist_mean"]) / stats["linker_dist_std"]
    
    if metrics["linker_end_to_end_a"] > 45: # Very stretched
        score -= 10
        status = "FAIL"
        impact = "Linker fully extended. High strain on termini. May prevent proper Fv assembly."
        suggestion = "Increase linker length or change attachment points."
    elif metrics["linker_end_to_end_a"] < 15: # Very collapsed
        score -= 10
        status = "WARNING"
        impact = "Linker collapsed or looping. May interfere with binding site or cause entanglement."
        suggestion = "Check if linker is interacting with CDRs."
    elif abs(z_dist) > 2.5:
        status = "WARNING"
        impact = "Linker conformation deviates from clinical norm."
        suggestion = "Verify if this geometry is intended for the specific format."
    else:
        status = "PASS"
        impact = "Normal linker extension."
        suggestion = "None"

    report.append({
        "metric": "Linker End-to-End",
        "value": f"{metrics['linker_end_to_end_a']:.1f} A (Ref Mean: {stats['linker_dist_mean']:.1f})",
        "status": status,
        "impact": impact,
        "suggestion": suggestion
    })

    return max(0, score), report

def main():
    parser = argparse.ArgumentParser(description="Evaluate Multispecific Antibody Structure")
    parser.add_argument("--pdb", required=True, help="Path to PDB file")
    parser.add_argument("--linker-seq", default="GGGGSGGGGSGGGGS", help="Linker sequence to identify boundaries")
    args = parser.parse_args()

    print(f"Analyzing {args.pdb}...")
    
    # 1. Load Data
    stats, _ = load_reference_stats()
    
    # 2. Parse PDB
    seq, residues = get_sequence_from_pdb(args.pdb)
    if not seq:
        print("Error: Could not extract sequence from PDB.")
        sys.exit(1)
        
    # 3. Find Linker
    start, end = find_linker_indices(seq, args.linker_seq)
    if start is None:
        print(f"Error: Linker sequence '{args.linker_seq}' not found in PDB sequence.")
        print(f"PDB Sequence: {seq[:50]}...")
        sys.exit(1)
        
    print(f"Linker found at indices {start}-{end} (Len: {end-start})")
    
    # 4. Compute Metrics
    metrics = compute_metrics(residues, start, end)
    if not metrics:
        print("Error: Failed to compute metrics.")
        sys.exit(1)
        
    # 5. Evaluate
    score, report = evaluate(metrics, stats)
    
    # 6. Output
    print("\n" + "="*60)
    print(f"FINAL QUALITY SCORE: {score}/100")
    print("="*60 + "\n")
    
    print(f"{'METRIC':<20} | {'STATUS':<10} | {'VALUE':<20} | {'IMPACT & SUGGESTION'}")
    print("-" * 100)
    
    for item in report:
        print(f"{item['metric']:<20} | {item['status']:<10} | {item['value']:<20} | {item['impact']}")
        if item['suggestion'] != "None":
            print(f"{'':<20} | {'':<10} | {'':<20} | -> Suggestion: {item['suggestion']}")
        print("-" * 100)

if __name__ == "__main__":
    main()
