#!/usr/bin/env python3
"""
Analyze the 39 Clinical VHH structures to design "Human Framework Wardrobes".

Goals:
1.  **Body Measurement (CDR Profiling):** Cluster VHHs by CDR1/2/3 lengths and structural properties.
2.  **Current Clothes (Framework Analysis):** Identify which Human Germlines (IGHV3-23, etc.) are closest to the current VHH frameworks.
3.  **Fitting Room (Vernier Zone):** Analyze the critical residues supporting the CDRs.

Outputs a report suggesting which Human Frameworks are best suited for different "classes" of VHHs.
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import local modules
from data.human_germlines_ref import HUMAN_GERMLINES, VERNIER_POSITIONS

# Use the anarci shim directly from reports/anarci_compat/anarci.py
# Since it's not a package, we load it by path or just mock it if we can't load it.
# Actually, let's just use the shim logic directly or import it if sys.path is right.
sys.path.insert(0, str(PROJECT_ROOT / "reports" / "anarci_compat"))
try:
    import anarci as anarci_module
except ImportError:
    print("Could not import anarci shim. Please ensure reports/anarci_compat/anarci.py exists.")
    sys.exit(1)

DATA_DIR = PROJECT_ROOT / "data" / "vhh_clinical_39_union"
MODELS_DIR = DATA_DIR / "immunebuilder_models"
OUTPUT_REPORT = DATA_DIR / "vhh_wardrobe_analysis.md"


def get_kabat_numbering(sequence):
    """Run ABARCII to get Kabat numbering."""
    try:
        # The shim expects [(id, seq)]
        # It returns (numbered, alignment_details, hit_tables)
        # numbered[0] is the result for the first sequence.
        # numbered[0][0] is the first domain (VH/VL).
        # numbered[0][0][0] is the numbering list [((pos, ins), aa), ...]
        
        # Note: The shim in reports/anarci_compat/anarci.py uses `anarcii` under the hood.
        # We need to make sure `anarci_module.anarci` is called correctly.
        
        # The shim signature: anarci(sequences, scheme="imgt", output=False, allow=None, ...)
        # It returns (numbered, alignment_details, hit_tables)
        
        # We need to pass allow={"H"} or similar if we want to filter, but let's be permissive.
        
        results = anarci_module.anarci(
            [("seq", sequence)], scheme="kabat", output=False
        )
        
        numbered, details, hits = results
        
        if numbered and numbered[0]:
             # The shim returns [[numbering_list]] for the first sequence
             # So numbered[0] is [[numbering_list]]
             # numbered[0][0] is [numbering_list] ?? No, let's check the shim code.
             # Shim line 114: numbered.append([[numbering_list]])
             # So numbered[0] is [[numbering_list]]
             # numbered[0][0] is [numbering_list]
             # numbered[0][0][0] is numbering_list
             
             # Wait, line 114: numbered.append([[numbering_list]])
             # This means for sequence 0: numbered[0] = [[numbering_list]]
             # So numbered[0][0] is [numbering_list]
             # numbered[0][0][0] is numbering_list
             
             # Wait, usually ABARCII returns list of domains.
             # If shim wraps it as [[numbering]], then it implies 1 domain?
             # Let's assume numbered[0][0][0] is the numbering list.
             
             if numbered[0] and numbered[0][0]:
                 numbering = numbered[0][0][0]
                 return numbering, None
             
    except Exception as e:
        print(f"ABARCII Error for {sequence[:10]}...: {e}")
    return None, None


def extract_cdrs_frameworks(numbering):
    """Extract CDR and Framework sequences based on Kabat definition."""
    # Kabat Definitions (Simplified)
    # FR1: 1-25
    # CDR1: 26-35
    # FR2: 36-49
    # CDR2: 50-65
    # FR3: 66-94
    # CDR3: 95-102
    # FR4: 103-113
    
    regions = {
        "FR1": "", "CDR1": "", "FR2": "", "CDR2": "", 
        "FR3": "", "CDR3": "", "FR4": ""
    }
    
    vernier_residues = {}

    for (pos, ins), aa in numbering:
        if aa == "-": continue
        
        # Determine Region
        if pos <= 25: region = "FR1"
        elif pos <= 35: region = "CDR1"
        elif pos <= 49: region = "FR2"
        elif pos <= 65: region = "CDR2"
        elif pos <= 94: region = "FR3"
        elif pos <= 102: region = "CDR3"
        else: region = "FR4"
        
        regions[region] += aa
        
        # Check Vernier
        if pos in VERNIER_POSITIONS:
            vernier_residues[pos] = aa

    return regions, vernier_residues


def calculate_identity(seq1, seq2):
    """Simple sequence identity."""
    matches = sum(a == b for a, b in zip(seq1, seq2))
    length = min(len(seq1), len(seq2))
    return matches / length if length > 0 else 0


def match_human_germline(vhh_frameworks):
    """Find the closest Human Germline Framework."""
    best_germline = None
    best_score = -1
    
    vhh_fr_seq = vhh_frameworks["FR1"] + vhh_frameworks["FR2"] + vhh_frameworks["FR3"]
    
    for name, seq in HUMAN_GERMLINES.items():
        # Quick hack: Human germlines in the dict are full V-regions.
        # We need to extract their frameworks too to be fair, 
        # but for a quick "wardrobe match", aligning the whole V-region (minus CDRs) is okay.
        # Let's just align the whole thing for a rough score, or better, use ABARCII on them too?
        # For speed, let's just do a simple alignment of the VHH FRs against the Germline sequence.
        
        # Actually, let's just use the ABARCII germline assignment if available, 
        # but we want to force match to our specific set of "Good" scaffolds.
        
        score = 0
        # A very rough smith-waterman or just sliding window would be better,
        # but let's assume standard numbering alignment.
        # Let's just count shared kmers or simple identity if lengths matched.
        
        # Better approach: Just compare FR1+FR2+FR3 string to the germline string (removing its CDRs).
        # Since I don't have the germline CDR positions hardcoded, let's just use the full sequence identity
        # as a proxy, knowing CDRs will lower it.
        
        # Refined: We will assume the VHH FRs are the query.
        pass
    
    # Let's use the ABARCII assigned germline for the "Native" match,
    # and then calculate identity to our specific "Wardrobe" set.
    return "IGHV3-23" # Placeholder for now, logic below


def analyze_wardrobe():
    report_lines = []
    report_lines.append("# VHH Wardrobe Analysis: Designing Human Frameworks\n")
    report_lines.append("Analyzing 39 Clinical VHHs to define optimal Human Scaffolds.\n")
    
    # 1. Load Data
    vhh_data = []
    for d in MODELS_DIR.iterdir():
        if d.is_dir() and (d / "meta.json").exists():
            meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
            vhh_data.append(meta)
            
    report_lines.append(f"**Total VHHs Analyzed:** {len(vhh_data)}\n")
    
    # 2. Process each VHH
    cluster_data = defaultdict(list)
    table_rows = []
    
    # Pre-calculate Human Germline Numberings for comparison
    human_germline_numberings = {}
    for name, seq in HUMAN_GERMLINES.items():
        num, _ = get_kabat_numbering(seq)
        if num:
            frs, vernier = extract_cdrs_frameworks(num)
            human_germline_numberings[name] = {"frs": frs, "vernier": vernier, "full": seq}

    for vhh in vhh_data:
        name = vhh.get("name", "Unknown")
        seq = vhh.get("sequence", "")
        
        # ABARCII Analysis
        numbering, germline_info = get_kabat_numbering(seq)
        if not numbering:
            continue
            
        regions, vernier = extract_cdrs_frameworks(numbering)
        
        # Structural "Body" Metrics
        l1 = len(regions["CDR1"])
        l2 = len(regions["CDR2"])
        l3 = len(regions["CDR3"])
        
        # Find best "Wardrobe" (Human Scaffold)
        best_scaffold = "None"
        best_id = -1.0
        
        for h_name, h_data in human_germline_numberings.items():
            matches = 0
            count = 0
            for pos in VERNIER_POSITIONS:
                v_res = vernier.get(pos, "-")
                h_res = h_data["vernier"].get(pos, "-")
                
                if v_res != "-" and h_res != "-":
                    count += 1
                    if v_res == h_res:
                        matches += 1
            
            score = matches / count if count > 0 else 0
            
            if score > best_id:
                best_id = score
                best_scaffold = h_name
        
        # Classify "Body Type"
        body_type = f"L{l1}-L{l2}-L{l3}"
        cluster_data[body_type].append(name)
        
        g_name = "N/A"
        if germline_info and len(germline_info) > 0 and 'germlines' in germline_info[0]:
             g_name = germline_info[0]['germlines'][0]['germline']

        table_rows.append(f"| {name} | {body_type} | {best_scaffold} ({best_id:.1%}) | {g_name} |")


    # 3. Generate Report
    
    report_lines.append("## 1. The 'Body Types' (CDR Length Clusters)")
    report_lines.append("VHHs are grouped by their CDR lengths (L1-L2-L3). This determines the 'shape' of the binding site.\n")
    
    # Sort clusters by frequency
    sorted_clusters = sorted(cluster_data.items(), key=lambda x: len(x[1]), reverse=True)
    
    for body_type, vhhs in sorted_clusters:
        if len(vhhs) > 1:
            report_lines.append(f"- **{body_type}** ({len(vhhs)} VHHs): {', '.join(vhhs[:3])}{'...' if len(vhhs)>3 else ''}")
            
    report_lines.append("\n## 2. The 'Wardrobe' (Best Fitting Human Scaffolds)")
    report_lines.append("Based on Vernier Zone identity (residues supporting the CDRs), here are the best human germline matches.\n")
    report_lines.append("| VHH Name | Body Type (CDR Len) | Best Human Fit (Vernier %) | Original V-Gene |")
    report_lines.append("|---|---|---|---|")
    report_lines.extend(table_rows)
    
    report_lines.append("\n## 3. Humanization Strategy Recommendations")
    report_lines.append("### Strategy A: The 'Universal' Coat (IGHV3-23)")
    report_lines.append("- **Target:** VHHs with standard CDR lengths (e.g., 8-8-X) and high Vernier identity to IGHV3-23.")
    report_lines.append("- **Method:** CDR Grafting onto IGHV3-23. Retain VHH residues at positions 37, 44, 45, 47 (The VHH Tetrad) if solubility drops.")
    
    report_lines.append("\n### Strategy B: The 'Bulky' Coat (IGHV3-53 / IGHV3-66)")
    report_lines.append("- **Target:** VHHs with longer CDR1/2 or specific hydrophobic cores.")
    report_lines.append("- **Method:** Use IGHV3-53/66 which naturally accommodate hydrophobic CDRH3s better.")
    
    OUTPUT_REPORT.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Analysis complete. Report written to: {OUTPUT_REPORT}")


if __name__ == "__main__":
    analyze_wardrobe()
