#!/usr/bin/env python3
"""
Analyze the 39 Clinical VHH structures to design "Human Framework Wardrobes".
UPDATED: Uses IMGT numbering for accurate VHH CDR3 extraction.

Goals:
1.  **Body Measurement (CDR Profiling):** Cluster VHHs by CDR1/2/3 lengths (IMGT).
2.  **Current Clothes (Framework Analysis):** Identify which Human Germlines are closest.
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
# Add shim path
sys.path.insert(0, str(PROJECT_ROOT / "reports" / "anarci_compat"))

try:
    import anarci as anarci_module
except ImportError:
    print("Could not import anarci shim.")
    sys.exit(1)

from data.human_germlines_ref import HUMAN_GERMLINES

DATA_DIR = PROJECT_ROOT / "data" / "vhh_clinical_39_union"
MODELS_DIR = DATA_DIR / "immunebuilder_models"
OUTPUT_REPORT = DATA_DIR / "vhh_wardrobe_analysis_imgt.md"


def get_imgt_numbering(sequence):
    """Run ABARCII to get IMGT numbering."""
    try:
        # Force IMGT scheme
        results = anarci_module.anarci(
            [("seq", sequence)], scheme="imgt", output=False
        )
        numbered, _, _ = results
        if numbered and numbered[0] and numbered[0][0]:
             return numbered[0][0][0]
    except Exception as e:
        print(f"ABARCII Error: {e}")
    return None


def extract_imgt_regions(numbering):
    """Extract CDR and Framework sequences based on IMGT definition."""
    # IMGT Definitions
    # FR1: 1-26
    # CDR1: 27-38
    # FR2: 39-55
    # CDR2: 56-65
    # FR3: 66-104 (C is 104)
    # CDR3: 105-117
    # FR4: 118-128 (W/F is 118)
    
    regions = {
        "FR1": "", "CDR1": "", "FR2": "", "CDR2": "", 
        "FR3": "", "CDR3": "", "FR4": ""
    }
    
    # We need to count residues, not just positions, to get accurate lengths.
    # Numbering is list of ((pos, ins), aa)
    
    for (pos, ins), aa in numbering:
        if aa == "-": continue
        
        if pos <= 26: region = "FR1"
        elif pos <= 38: region = "CDR1"
        elif pos <= 55: region = "FR2"
        elif pos <= 65: region = "CDR2"
        elif pos <= 104: region = "FR3"
        elif pos <= 117: region = "CDR3"
        else: region = "FR4"
        
        regions[region] += aa

    return regions


def analyze_wardrobe():
    report_lines = []
    report_lines.append("# VHH Wardrobe Analysis (IMGT Definition)\n")
    report_lines.append("Analyzing 39 Clinical VHHs using IMGT numbering for accurate CDR3 slicing.\n")
    
    # 1. Load Data
    vhh_data = []
    for d in MODELS_DIR.iterdir():
        if d.is_dir() and (d / "meta.json").exists():
            meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
            vhh_data.append(meta)
            
    report_lines.append(f"**Total VHHs Analyzed:** {len(vhh_data)}\n")
    
    # 2. Process Human Germlines
    human_refs = {}
    for name, seq in HUMAN_GERMLINES.items():
        num = get_imgt_numbering(seq)
        if num:
            regs = extract_imgt_regions(num)
            human_refs[name] = regs

    # 3. Process VHHs
    cluster_data = defaultdict(list)
    table_rows = []
    
    for vhh in vhh_data:
        name = vhh.get("name", "Unknown")
        seq = vhh.get("sequence", "")
        
        numbering = get_imgt_numbering(seq)
        if not numbering:
            continue
            
        regions = extract_imgt_regions(numbering)
        
        # Lengths
        l1 = len(regions["CDR1"])
        l2 = len(regions["CDR2"])
        l3 = len(regions["CDR3"])
        
        # Find best Framework Match (FR1+FR2+FR3 Identity)
        best_scaffold = "None"
        best_id = -1.0
        
        vhh_fr = regions["FR1"] + regions["FR2"] + regions["FR3"]
        
        for h_name, h_regs in human_refs.items():
            h_fr = h_regs["FR1"] + h_regs["FR2"] + h_regs["FR3"]
            
            # Simple identity
            # Note: Lengths might differ. Use alignment-free or simple truncation?
            # Since we are using IMGT, the gaps should be aligned if we used the alignment output,
            # but here we just have strings.
            # Let's use Levenshtein or just simple match count on min length.
            
            min_len = min(len(vhh_fr), len(h_fr))
            matches = sum(a==b for a,b in zip(vhh_fr[:min_len], h_fr[:min_len]))
            score = matches / max(len(vhh_fr), len(h_fr)) # Penalize length diff
            
            if score > best_id:
                best_id = score
                best_scaffold = h_name
        
        body_type = f"L{l1}-L{l2}-L{l3}"
        cluster_data[body_type].append(name)
        
        table_rows.append(f"| {name} | {body_type} | {best_scaffold} ({best_id:.1%}) |")

    # 4. Generate Report
    report_lines.append("## 1. CDR Length Clusters (IMGT: CDR1-CDR2-CDR3)")
    sorted_clusters = sorted(cluster_data.items(), key=lambda x: len(x[1]), reverse=True)
    
    for body_type, vhhs in sorted_clusters:
        report_lines.append(f"- **{body_type}** ({len(vhhs)}): {', '.join(vhhs[:3])}{'...' if len(vhhs)>3 else ''}")
        
    report_lines.append("\n## 2. Framework Match (FR1+FR2+FR3 Identity)")
    report_lines.append("| VHH Name | Body Type | Best Human Scaffold |")
    report_lines.append("|---|---|---|")
    report_lines.extend(table_rows)
    
    OUTPUT_REPORT.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Analysis complete. Report: {OUTPUT_REPORT}")

if __name__ == "__main__":
    analyze_wardrobe()
