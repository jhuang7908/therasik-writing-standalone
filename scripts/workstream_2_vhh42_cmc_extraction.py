#!/usr/bin/env python3
"""
Workstream 2: Compute CMC metrics for VHH42 (39 clinical + 3 SAbDab humanized).

Reads from data/vhh_39_clinical_atlas/master_table.csv and ImmuneBuilder PDB structures.
Outputs:
  1. data/vhh_clinical_39_union/vhh42_cmc_metrics.csv (per-sequence CMC table)
  2. Updated data/reference/VHH42_reference_stats_v1.json (with per_antibody section)
"""

import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

import numpy as np

try:
    from Bio.SeqUtils.ProtParam import ProteinAnalysis
    from Bio.PDB import PDBParser
except ImportError:
    print("Error: BioPython required. Install with: pip install biopython")
    sys.exit(1)

# Project root
SUITE_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = SUITE_ROOT / "data"
VHH_ATLAS_ROOT = DATA_ROOT / "vhh_39_clinical_atlas"
VHH_UNION_ROOT = DATA_ROOT / "vhh_clinical_39_union"
REFERENCE_ROOT = DATA_ROOT / "reference"

# Input/output files
MASTER_TABLE = VHH_ATLAS_ROOT / "master_table.csv"
CMC_OUTPUT_CSV = VHH_UNION_ROOT / "vhh42_cmc_metrics.csv"
VHH42_STATS_JSON = REFERENCE_ROOT / "VHH42_reference_stats_v1.json"

# Three humanized camelid VHH (Database B / structural union), frozen in:
#   data/vhh_clinical_39_union/vhh42_sabdab_supplement.json
SABDAB_SUPPLEMENT = VHH_UNION_ROOT / "vhh42_sabdab_supplement.json"


def compute_sequence_metrics(sequence: str) -> Dict[str, float]:
    """Compute sequence-level CMC metrics using BioPython."""
    try:
        pa = ProteinAnalysis(sequence)
        return {
            "pI": round(pa.isoelectric_point(), 2),
            "GRAVY": round(pa.gravy(), 4),
            "instability_index": round(pa.instability_index(), 2),
            "net_charge_pH7": round(pa.charge_at_pH(7), 2),
            "molecular_weight_Da": round(pa.molecular_weight(), 1),
            "free_cys": sequence.count("C"),
            "deamidation_sites": (sequence.count("NG") + sequence.count("NQ")),
            "isomerization_sites": sequence.count("DP"),
        }
    except Exception as e:
        print(f"[Warning] Sequence metrics failed: {e}", file=sys.stderr)
        return {}


def compute_patch_metrics(sequence: str) -> Dict[str, Any]:
    """
    Compute hydrophobic/charge patch metrics.
    Simplified version: scan for high-hydrophobicity and high-charge windows.
    """
    # Simplified hydrophobicity scale (Kyte-Doolittle)
    HYDRO = {
        'A': 1.8, 'C': 2.5, 'D': -3.5, 'E': -3.5, 'F': 2.8, 'G': -0.4,
        'H': -3.2, 'I': 4.5, 'K': -3.9, 'L': 3.8, 'M': 1.9, 'N': -3.5,
        'P': -1.6, 'Q': -3.5, 'R': -4.5, 'S': -0.8, 'T': -0.7, 'V': 4.2,
        'W': -0.9, 'Y': -1.3,
    }
    
    CHARGE_POS = {'K', 'R', 'H'}
    CHARGE_NEG = {'D', 'E'}
    
    hydro_max_window = 0.0
    charge_max_window = 0.0
    agg_motifs = 0
    
    # Hydrophobic window (9 AA, Kyte-Doolittle > 1.5 mean)
    for i in range(len(sequence) - 9):
        window = sequence[i:i+9]
        window_hydro = np.mean([HYDRO.get(aa, 0) for aa in window])
        if window_hydro > 1.5:
            hydro_max_window = max(hydro_max_window, window_hydro)
    
    # Charge patch (7 AA, imbalance > 3)
    for i in range(len(sequence) - 7):
        window = sequence[i:i+7]
        pos_count = sum(1 for aa in window if aa in CHARGE_POS)
        neg_count = sum(1 for aa in window if aa in CHARGE_NEG)
        if abs(pos_count - neg_count) >= 3:
            charge_max_window = max(charge_max_window, float(abs(pos_count - neg_count)))
    
    # Simple aggregation propensity check: VLFIWT hotspots
    AGG_AA = {'V', 'L', 'F', 'I', 'W', 'T'}
    for i in range(len(sequence) - 5):
        window = sequence[i:i+6]
        if sum(1 for aa in window if aa in AGG_AA) >= 5:
            agg_motifs += 1
    
    return {
        "hydro_patch_max9": round(hydro_max_window, 3),
        "charge_patch_max7": round(charge_max_window, 2),
        "agg_motifs": agg_motifs,
    }


def extract_fr3_metrics_from_pdb(pdb_path: str) -> Dict[str, Any]:
    """
    Extract FR3 packing metrics from ImmuneBuilder PDB (if available).
    Falls back to vhh_fr3_vernier_metrics.json if PDB is not accessible.
    """
    result = {
        "fr3_contact_fraction": 0.0,
        "fr3_buried_mean": 0.0,
        "fr3_pack_atom_mean": 0.0,
        "pdb_status": "not_computed",
    }
    
    # Try to load from pre-computed vhh_fr3_vernier_metrics.json
    metrics_file = VHH_UNION_ROOT / "vhh_fr3_vernier_metrics.json"
    if metrics_file.exists():
        try:
            with open(metrics_file, encoding='utf-8') as f:
                all_metrics = json.load(f)
                vhh_summaries = {m['name']: m for m in all_metrics.get('vhh_summary', [])}
                # Will be looked up by VHH name later
                return None  # Signal to fetch from pre-computed data
        except Exception:
            pass
    
    return result


def load_vhh_fr3_metrics() -> Dict[str, Dict[str, Any]]:
    """Load all pre-computed FR3 metrics keyed by VHH name."""
    metrics_file = VHH_UNION_ROOT / "vhh_fr3_vernier_metrics.json"
    result = {}
    
    if metrics_file.exists():
        try:
            with open(metrics_file, encoding='utf-8') as f:
                all_metrics = json.load(f)
                for item in all_metrics.get('vhh_summary', []):
                    name = item.get('name', '')
                    result[name] = {
                        "fr3_contact_fraction": item.get('fr3_contact_fraction', 0.0),
                        "fr3_buried_mean": item.get('fr3_buried_mean', 0.0),
                        "fr3_pack_atom_mean": item.get('fr3_pack_atom_total_mean', 0.0),
                    }
        except Exception as e:
            print(f"[Warning] Could not load FR3 metrics: {e}", file=sys.stderr)
    
    return result


def read_sabdab_humanized_vhh() -> List[Dict[str, str]]:
    """
    Read 3 SAbDab / Database-B humanized VHH sequences (frozen JSON manifest).
    """
    if not SABDAB_SUPPLEMENT.exists():
        return []
    with open(SABDAB_SUPPLEMENT, encoding="utf-8") as f:
        data = json.load(f)
    out: List[Dict[str, str]] = []
    for e in data.get("entries") or []:
        name = (e.get("id") or "").strip()
        seq = (e.get("sequence") or "").strip()
        if not name or not seq:
            continue
        out.append({
            "name": name,
            "sequence": seq,
            "structure_path": (e.get("pdb_model") or "").strip(),
        })
    return out


def compute_cmc_for_all_vhh(fr3_metrics: Dict[str, Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Main processing: compute CMC metrics for all 39 clinical + 3 SAbDab VHH.
    Returns: (list of CMC records, list of VHH names)
    """
    
    results = []
    vhh_names = []
    
    # 1. Read 39 clinical VHH from master_table.csv
    print("[Info] Reading VHH clinical atlas...")
    if not MASTER_TABLE.exists():
        print(f"[Error] Master table not found: {MASTER_TABLE}", file=sys.stderr)
        return results, vhh_names
    
    with open(MASTER_TABLE, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('Name', '').strip()
            sequence = row.get('Sequence', '').strip()
            
            if not name or not sequence:
                continue
            
            # Compute metrics
            seq_metrics = compute_sequence_metrics(sequence)
            patch_metrics = compute_patch_metrics(sequence)
            fr3_data = fr3_metrics.get(name, {
                "fr3_contact_fraction": 0.0,
                "fr3_buried_mean": 0.0,
                "fr3_pack_atom_mean": 0.0,
            })
            
            record = {
                "name": name,
                "sequence": sequence,
                "seq_len": len(sequence),
                "origin": "clinical",
                **seq_metrics,
                **patch_metrics,
                **fr3_data,
                "cmc_flags": [],  # TODO: populate with flags like "hydro_patch_high", etc.
            }
            
            results.append(record)
            vhh_names.append(name)
            print(f"  ✓ {name}: pI={seq_metrics.get('pI', 'N/A')}, GRAVY={seq_metrics.get('GRAVY', 'N/A')}")
    
    # 2. Add 3 SAbDab humanized VHH (if available)
    print("[Info] Adding SAbDab humanized VHH...")
    sabdab_list = read_sabdab_humanized_vhh()
    for sabdab_record in sabdab_list:
        name = sabdab_record.get('name', '')
        sequence = sabdab_record.get('sequence', '').strip()
        
        if not name or not sequence:
            continue
        
        seq_metrics = compute_sequence_metrics(sequence)
        patch_metrics = compute_patch_metrics(sequence)
        fr3_data = fr3_metrics.get(name, {
            "fr3_contact_fraction": 0.0,
            "fr3_buried_mean": 0.0,
            "fr3_pack_atom_mean": 0.0,
        })
        
        record = {
            "name": name,
            "sequence": sequence,
            "seq_len": len(sequence),
            "origin": "SAbDab_humanized",
            **seq_metrics,
            **patch_metrics,
            **fr3_data,
            "cmc_flags": [],
        }
        
        results.append(record)
        vhh_names.append(name)
        print(f"  ✓ {name} (SAbDab): pI={seq_metrics.get('pI', 'N/A')}, GRAVY={seq_metrics.get('GRAVY', 'N/A')}")
    
    return results, vhh_names


def write_cmc_csv(records: List[Dict[str, Any]]) -> None:
    """Write CMC metrics to CSV."""
    if not records:
        print("[Warning] No records to write", file=sys.stderr)
        return
    
    fieldnames = [
        "name", "sequence", "seq_len",
        "pI", "GRAVY", "instability_index", "net_charge_pH7", "molecular_weight_Da",
        "free_cys", "deamidation_sites", "isomerization_sites",
        "hydro_patch_max9", "charge_patch_max7", "agg_motifs",
        "fr3_contact_fraction", "fr3_buried_mean", "fr3_pack_atom_mean",
        "cmc_flags", "origin"
    ]
    
    CMC_OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    
    with open(CMC_OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, restval='')
        writer.writeheader()
        for rec in records:
            # Flatten cmc_flags list
            rec_copy = rec.copy()
            rec_copy['cmc_flags'] = '; '.join(rec_copy.get('cmc_flags', []))
            rec_copy['origin'] = rec_copy.get('origin', 'clinical')
            writer.writerow(rec_copy)
    
    print(f"[Info] Wrote CMC metrics to: {CMC_OUTPUT_CSV}")


def update_vhh42_reference_stats(records: List[Dict[str, Any]]) -> None:
    """Update VHH42_reference_stats_v1.json with per-antibody section."""
    
    if not VHH42_STATS_JSON.exists():
        print(f"[Warning] VHH42 reference stats not found: {VHH42_STATS_JSON}", file=sys.stderr)
        return
    
    with open(VHH42_STATS_JSON, encoding='utf-8') as f:
        stats = json.load(f)
    
    # Add per_antibody section
    per_ab = []
    for rec in records:
        per_ab.append({
            "name": rec.get('name', ''),
            "pI": rec.get('pI', None),
            "GRAVY": rec.get('GRAVY', None),
            "instability_index": rec.get('instability_index', None),
            "net_charge_pH7": rec.get('net_charge_pH7', None),
            "hydro_patch_max9": rec.get('hydro_patch_max9', None),
            "charge_patch_max7": rec.get('charge_patch_max7', None),
            "agg_motifs": rec.get('agg_motifs', None),
            "fr3_contact_fraction": rec.get('fr3_contact_fraction', None),
            "fr3_buried_mean": rec.get('fr3_buried_mean', None),
            "fr3_pack_atom_mean": rec.get('fr3_pack_atom_mean', None),
        })
    
    stats['per_antibody'] = per_ab
    stats['_meta']['per_antibody_count'] = len(per_ab)
    
    with open(VHH42_STATS_JSON, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)
    
    print(f"[Info] Updated VHH42_reference_stats_v1.json with {len(per_ab)} entries")


def main():
    print("=" * 70)
    print("Workstream 2: VHH42 CMC Metrics Extraction")
    print("=" * 70)
    
    # Load pre-computed FR3 metrics
    print("[Info] Loading pre-computed FR3 metrics...")
    fr3_metrics = load_vhh_fr3_metrics()
    print(f"  ✓ Loaded FR3 data for {len(fr3_metrics)} VHH")
    
    # Compute CMC for all VHH
    print("[Info] Computing CMC metrics...")
    records, names = compute_cmc_for_all_vhh(fr3_metrics)
    print(f"  ✓ Computed metrics for {len(records)} VHH")
    
    if not records:
        print("[Error] No records computed", file=sys.stderr)
        return 1
    
    # Write outputs
    print("[Info] Writing outputs...")
    write_cmc_csv(records)
    update_vhh42_reference_stats(records)
    
    print()
    print("✓ Workstream 2 Complete")
    print(f"  - Output CSV: {CMC_OUTPUT_CSV}")
    print(f"  - Updated: {VHH42_STATS_JSON}")
    print()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
