#!/usr/bin/env python3
"""
scripts/compute_germline_cmc_scores.py

Computes intrinsic CMC/developability metrics for all functional human IGHV germlines.
Merges this biophysical profile with clinical usage counts and ADA risk profiles 
to create a comprehensive Germline Developability Anchor table.

Output:
- config/germline_cmc_anchors.json
- docs/GERMLINE_CMC_ANCHORS.md
"""

import json
from pathlib import Path
from typing import Dict, Any, List
import sys

# Ensure imports work
SUITE_ROOT = Path(__file__).resolve().parents[1]
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

from core.cmc.cmc_metrics import (
    compute_pI,
    compute_GRAVY,
    compute_instability_index,
    compute_hydro_patch_max9,
    compute_charge_patch_max7,
    compute_net_charge
)

GERMLINES_FILE = SUITE_ROOT / "data" / "germlines" / "human_ig_aa" / "IGHV_aa.json"
CLINICAL_ANCHORS_FILE = SUITE_ROOT / "config" / "clinical_germline_anchors.json"
OUT_JSON = SUITE_ROOT / "config" / "germline_cmc_anchors.json"
OUT_MD = SUITE_ROOT / "docs" / "GERMLINE_CMC_ANCHORS.md"

def score_germline_cmc(seq: str) -> Dict[str, float]:
    """Calculate intrinsic sequence-based CMC properties."""
    # Ensure uppercase and no gaps
    seq = seq.upper().replace("-", "").replace(".", "")
    if not seq:
        return {}
        
    return {
        "pI": compute_pI(seq),
        "GRAVY": compute_GRAVY(seq),
        "instability_index": compute_instability_index(seq),
        "hydro_patch_max9": compute_hydro_patch_max9(seq),
        "charge_patch_max7": compute_charge_patch_max7(seq),
        "net_charge_pH7": compute_net_charge(seq, 7.0)
    }

def build_table():
    print(f"Loading germlines from {GERMLINES_FILE.name}...")
    germlines_data = json.loads(GERMLINES_FILE.read_text(encoding="utf-8"))
    
    print(f"Loading clinical anchors from {CLINICAL_ANCHORS_FILE.name}...")
    anchors_data = json.loads(CLINICAL_ANCHORS_FILE.read_text(encoding="utf-8"))["germlines"]
    
    results = []
    
    # Process only full/functional entries from IMGT (approximate by length)
    for entry in germlines_data.get("entries", []):
        g_id = entry["id"]
        seq = entry.get("sequence_aa", "")
        raw_header = entry.get("raw_header", "")
        
        # Skip severely truncated or ORF/pseudogenes if marked, though we calculate what we can
        is_partial = "partial" in raw_header.lower()
        
        cmc_scores = score_germline_cmc(seq)
        if not cmc_scores:
            continue
            
        # Merge with clinical data if available
        anchor_info = anchors_data.get(g_id, {})
        clinical_count = anchor_info.get("n_antibodies", 0)
        ada_risk = anchor_info.get("majority_risk", "UNKNOWN")
        ada_mean = anchor_info.get("ada_pct_mean")
        
        # Assign a simple tier based on clinical usage and instability
        tier = "Tier 4 (Rare/Unproven)"
        if clinical_count >= 5 and cmc_scores["instability_index"] < 40:
            tier = "Tier 1 (Strong Clinical Anchor)"
        elif clinical_count >= 2:
            tier = "Tier 2 (Clinical Backup)"
        elif clinical_count == 1:
            tier = "Tier 3 (Single Clinical Case)"
        elif "ORF" in g_id:
            tier = "Exclude (ORF)"
            
        results.append({
            "germline_id": g_id,
            "tier": tier,
            "clinical_n": clinical_count,
            "ada_risk": ada_risk,
            "ada_mean_pct": ada_mean,
            "cmc": cmc_scores,
            "is_partial": is_partial,
            "sequence_length": len(seq)
        })
        
    # Sort: Tier 1 -> Tier 2 -> ... then by clinical count descending, then by instability
    def sort_key(x):
        tier_order = {"Tier 1 (Strong Clinical Anchor)": 1, "Tier 2 (Clinical Backup)": 2, "Tier 3 (Single Clinical Case)": 3, "Tier 4 (Rare/Unproven)": 4, "Exclude (ORF)": 5}
        return (tier_order.get(x["tier"], 99), -x["clinical_n"], x["cmc"]["instability_index"])
        
    results.sort(key=sort_key)
    
    # Write JSON
    payload = {
        "_meta": {
            "description": "Intrinsic CMC developability metrics for human IGHV germlines combined with clinical anchor counts.",
            "source_germlines": str(GERMLINES_FILE.name),
            "source_clinical": str(CLINICAL_ANCHORS_FILE.name)
        },
        "germlines": results
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved JSON to {OUT_JSON}")
    
    # Write Markdown
    md_lines = [
        "# Human IGHV Germline CMC Developability Anchors",
        "",
        "This table combines intrinsic biophysical sequence metrics (CMC) with historical clinical usage counts to rank human germlines for scaffold selection.",
        "",
        "**Metrics explanation:**",
        "- **Instability Index**: < 40 is stable, > 40 suggests in vivo/in vitro instability.",
        "- **GRAVY**: Lower is more hydrophilic (better solubility).",
        "- **Hydro9**: Max hydrophobic patch score (9-mer window).",
        "",
        "| Tier | Germline | Clinical n | ADA Risk | ADA Mean % | pI | Instability | GRAVY | Hydro9 | Charge7 |",
        "|---|---|---:|---|---|---|---|---|---|---|"
    ]
    
    for r in results:
        # Exclude partials and ORFs from the main clean table if they have 0 clinical cases
        if r["tier"] == "Exclude (ORF)" or (r["is_partial"] and r["clinical_n"] == 0):
            continue
            
        c = r["cmc"]
        ada = f"{r['ada_mean_pct']:.1f}%" if r["ada_mean_pct"] is not None else "-"
        
        # Format instability to highlight bad values
        ins_str = f"**{c['instability_index']}**" if c['instability_index'] > 40 else f"{c['instability_index']}"
        
        md_lines.append(
            f"| {r['tier'].split(' ')[0]} | `{r['germline_id']}` | {r['clinical_n']} | {r['ada_risk']} | {ada} "
            f"| {c['pI']} | {ins_str} | {c['GRAVY']} | {c['hydro_patch_max9']} | {c['charge_patch_max7']} |"
        )
        
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Saved Markdown to {OUT_MD}")

if __name__ == "__main__":
    build_table()
