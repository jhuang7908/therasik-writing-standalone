#!/usr/bin/env python3
"""
build_cat_production_germline_library_v1.py
===========================================

Builds a structured Cat Scaffold JSON (similar to dog_scaffold_cmc_optimization_tier1_tier2_v1.json)
using downloaded NCBI IGHV candidates and local IMGT IGKV/IGLV data.

It computes Kabat numbering, extracts FR segments, scans for generic CMC liabilities,
and structures the final output.
"""

import json
from pathlib import Path
import sys

# Add suite root to path
SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))

from core.humanization.kabat_utils import get_kabat_numbering, sorted_keys, is_in_cdr
from core.cmc.generic_cmc_scanner import scan_cmc_liabilities

OUT_JSON = SUITE / "data" / "germlines" / "fc_aa" / "cat_scaffold_cmc_optimization_tier1_tier2_v1.json"

VH_FASTA = SUITE / "data" / "germlines" / "fc_aa" / "fc_database" / "cat" / "IGHC_cat_vh_candidates.fasta"
IGKV_JSON = SUITE / "data" / "germlines" / "felis_catus_ig_aa" / "IGKV_aa.json"
IGLV_JSON = SUITE / "data" / "germlines" / "felis_catus_ig_aa" / "IGLV_aa.json"

FR_RANGES = {
    "VH": {"FR1": (1, 25), "FR2": (36, 49), "FR3": (66, 94)},
    "VL": {"FR1": (1, 23), "FR2": (35, 49), "FR3": (57, 88)},
}

def parse_fasta(path: Path):
    if not path.exists(): return []
    seqs = []
    header = ""
    seq = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if header:
                    seqs.append((header, "".join(seq)))
                header = line[1:]
                seq = []
            else:
                seq.append(line)
    if header:
        seqs.append((header, "".join(seq)))
    return seqs

def extract_fr_segments(kd: dict, chain: str):
    fr_seg = {"FR1": "", "FR2": "", "FR3": ""}
    ranges = FR_RANGES["VH" if chain == "VH" else "VL"]
    for name, (lo, hi) in ranges.items():
        seg = ""
        for (pos, ins) in sorted_keys(kd):
            if lo <= pos <= hi and not is_in_cdr(pos, chain):
                seg += kd[(pos, ins)]
        fr_seg[name] = seg
    return fr_seg

def process_sequence(header: str, seq: str, chain: str, locus: str, gene_name: str, tier: str):
    kd = get_kabat_numbering(seq)
    if not kd:
        return None
        
    norm_seq = "".join(kd[k] for k in sorted_keys(kd))
    
    # We only care about FR1-FR3 region for scaffolds
    # Stop before FR4
    max_fr3 = 94 if chain == "VH" else 88
    v_region = "".join(kd[k] for k in sorted_keys(kd) if k[0] <= max_fr3)
    
    fr_segs = extract_fr_segments(kd, chain)
    fr_concat = fr_segs["FR1"] + fr_segs["FR2"] + fr_segs["FR3"]
    
    # Basic generic CMC scan on full V-region
    cmc_full = scan_cmc_liabilities(v_region)
    cmc_fr13 = scan_cmc_liabilities(fr_segs["FR1"] + fr_segs["FR3"])
    
    return {
        "tier": tier,
        "chain": chain,
        "locus": locus,
        "gene": gene_name,
        "raw_header": header,
        "sequence_aa_kabat_norm": norm_seq,
        "fr_segments": fr_segs,
        "fr1_3_concat": fr_segs["FR1"] + fr_segs["FR3"],
        "cmc_full": cmc_full,
        "cmc_fr13_only": cmc_fr13,
        "optimization": {
            "sequence_aa_opt": norm_seq,  # Not doing greedy mutations in V1, just use raw
            "mutations": []
        }
    }

def main():
    rows = []
    
    # 1. Process VH Candidates
    print("Processing VH candidates...")
    sys.stdout.flush()
    vh_seqs = parse_fasta(VH_FASTA)
    unique_vh_fr = set()
    idx = 1
    for h, s in vh_seqs:
        # Remove signal peptides roughly if present (simple heuristic: find typical FR1 start)
        # Most Cat VH start with (D|E|Q)VQL
        start_idx = s.find("EVQL")
        if start_idx == -1: start_idx = s.find("DVQL")
        if start_idx == -1: start_idx = s.find("QVQL")
        if start_idx == -1: start_idx = s.find("QVLL")
        
        core_s = s[start_idx:] if start_idx >= 0 else s
        if len(core_s) < 80: continue
        
        print(f"  -> Processing VH: {h[:30]}... ({len(core_s)} aa)")
        sys.stdout.flush()
        
        entry = process_sequence(h, core_s, "VH", "IGHV", f"IGHV-Cat-{idx:03d}", "tier1")
        if entry:
            # Deduplicate by FR1-3 exact match
            if entry["fr1_3_concat"] not in unique_vh_fr:
                unique_vh_fr.add(entry["fr1_3_concat"])
                rows.append(entry)
                idx += 1
                print(f"     => Added as Tier 1 ({len(unique_vh_fr)} unique so far)")

    # 2. Process IGKV
    print("Processing IGKV...")
    if IGKV_JSON.exists():
        vk_data = json.loads(IGKV_JSON.read_text())
        for e in vk_data.get("entries", []):
            entry = process_sequence(e.get("id",""), e.get("sequence_aa",""), "VL", "IGKV", e.get("id",""), "tier1")
            if entry: rows.append(entry)
            
    # 3. Process IGLV
    print("Processing IGLV...")
    if IGLV_JSON.exists():
        vl_data = json.loads(IGLV_JSON.read_text())
        for e in vl_data.get("entries", []):
            entry = process_sequence(e.get("id",""), e.get("sequence_aa",""), "VL", "IGLV", e.get("id",""), "tier1")
            if entry: rows.append(entry)
            
    # 4. Save
    payload = {
        "artifact_id": "cat_scaffold_cmc_optimization_tier1_tier2_v1",
        "built_at": "2026-04-29",
        "notes": "Generated from NCBI Protein search and IMGT Felis Catus light chains.",
        "rows": rows
    }
    
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(payload, f, indent=2)
        
    print(f"Done! Built {len(rows)} scaffolds ({idx-1} VH, {len(rows)-idx+1} VL). Saved to {OUT_JSON.name}")

if __name__ == "__main__":
    main()
