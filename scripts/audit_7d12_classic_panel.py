#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
7D12 Classic Panel 
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

def audit_classic_panel(json_path: Path):
    """Classic Panel JSON"""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    
    results = {
        "gate": data.get("gate", {}),
        "classic_panel": data.get("classic_panel", []),
        "cdr_features": data.get("cdr_features", {}),
        "canonical_compatibility": data.get("canonical_compatibility", {}),
        "canonical_profiles": data.get("canonical_profiles", {}),
    }
    
    # 1. Gate
    gate = results["gate"]
    print("=== Gate Analysis ===")
    print(f"Pass level: {gate.get('pass_level')}")
    print(f"Flags: {gate.get('flags', [])}")
    print(f"CDR3 len: {gate.get('metrics', {}).get('cdr3_len')}")
    print(f"Best FR identity: {gate.get('metrics', {}).get('best_fr_identity')}")
    print()
    
    # 2. Panel
    panel = results["classic_panel"]
    scaffolds = set()
    j_regions = set()
    for entry in panel:
        scaffolds.add(entry.get("scaffold_id"))
        j_regions.add(entry.get("j_region_id"))
    
    print("=== Panel Coverage ===")
    print(f"Expected: 4 scaffolds × 2 J regions = 8 entries")
    print(f"Actual: {len(panel)} entries")
    print(f"Scaffolds: {sorted(scaffolds)}")
    print(f"J regions: {sorted(j_regions)}")
    print()
    
    # 3. Hallmark
    print("=== Hallmark Rule Audit ===")
    for entry in panel[:2]:  # 2
        scaffold_id = entry.get("scaffold_id")
        mutations = entry.get("mutations", [])
        hallmark_muts = [m for m in mutations if "HALLMARK" in m.get("rule_id", "")]
        print(f"{scaffold_id}: {len(hallmark_muts)} hallmark mutations")
        for m in hallmark_muts:
            print(f"  Kabat {m.get('numbering', {}).get('kabat')}: {m.get('from_aa')} -> {m.get('to_aa')}")
    print()
    
    # 4. Vernier
    print("=== Vernier Backfill Audit ===")
    vernier_positions = [27, 28, 29, 30, 49, 71, 73, 78, 93, 94]
    for entry in panel[:2]:
        scaffold_id = entry.get("scaffold_id")
        mutations = entry.get("mutations", [])
        vernier_muts = [m for m in mutations if "VERNIER" in m.get("rule_id", "")]
        vernier_pos_found = [m.get("numbering", {}).get("kabat") for m in vernier_muts]
        print(f"{scaffold_id}: {len(vernier_muts)} vernier mutations at positions {vernier_pos_found}")
    print()
    
    # 5. Canonical
    print("=== Canonical Layer Audit ===")
    cdr_features = results["cdr_features"]
    print(f"Query CDR1 len: {cdr_features.get('cdr1_len')}, seq: {cdr_features.get('cdr1_seq')}")
    print(f"Query CDR2 len: {cdr_features.get('cdr2_len')}, seq: {cdr_features.get('cdr2_seq')}")
    compat = results["canonical_compatibility"]
    for sid, info in compat.items():
        print(f"{sid}: risk={info.get('risk_level')}, rationale={info.get('rationale', '')[:50]}")
    print()
    
    return results

if __name__ == "__main__":
    json_path = PROJECT_ROOT / "output" / "regression_test_7d12" / "classic_panel_output" / "vhh_classic_panel.json"
    audit_classic_panel(json_path)


