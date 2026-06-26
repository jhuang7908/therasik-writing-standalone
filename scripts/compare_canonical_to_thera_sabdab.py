#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scripts/compare_canonical_to_thera_sabdab.py

Compares canonical class distributions between the framework library and Thera-SAbDab therapeutics.
Calculates Jensen-Shannon Divergence (JSD) and coverage stats.
"""

import sys
import yaml
import json
import math
import argparse
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Set

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]

def load_yaml(path: Path) -> Any:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def kl_divergence(p: List[float], q: List[float]) -> float:
    """Calculate KL divergence D(P || Q)"""
    return sum(p[i] * math.log2(p[i] / q[i]) for i in range(len(p)) if p[i] > 0)

def calculate_jsd(p_dist: Dict[str, float], q_dist: Dict[str, float]) -> float:
    """Calculate Jensen-Shannon Divergence (JSD) in bits"""
    all_keys = sorted(list(set(p_dist.keys()) | set(q_dist.keys())))
    if not all_keys:
        return 0.0
        
    p = [p_dist.get(k, 0.0) for k in all_keys]
    q = [q_dist.get(k, 0.0) for k in all_keys]
    
    # Normalize to sums of 1
    sum_p = sum(p)
    sum_q = sum(q)
    if sum_p == 0 or sum_q == 0:
        return 1.0 # Maximum divergence if one distribution is empty
        
    p = [x / sum_p for x in p]
    q = [x / sum_q for x in q]
    
    m = [(p[i] + q[i]) / 2 for i in range(len(p))]
    
    return 0.5 * kl_divergence(p, m) + 0.5 * kl_divergence(q, m)

def get_framework_canonical_data(vh_yaml: Path, vl_yaml: Path) -> Dict[str, List[str]]:
    """Extracts canonical classes from framework YAMLs"""
    vh_data = load_yaml(vh_yaml)
    vl_data = load_yaml(vl_yaml)
    
    classes = {"H1": [], "H2": [], "L1": [], "L2": [], "L3": []}
    
    for entry in vh_data.get('frameworks', []):
        canon = entry.get('canonical', {})
        if canon.get('status') == 'ASSIGNED_BY_TOOL':
            if 'cdr1' in canon: classes['H1'].append(canon['cdr1']['class'])
            if 'cdr2' in canon: classes['H2'].append(canon['cdr2']['class'])
            
    for entry in vl_data.get('frameworks', []):
        canon = entry.get('canonical', {})
        if canon.get('status') == 'ASSIGNED_BY_TOOL':
            if 'cdr1' in canon: classes['L1'].append(canon['cdr1']['class'])
            if 'cdr2' in canon: classes['L2'].append(canon['cdr2']['class'])
            if 'cdr3' in canon: classes['L3'].append(canon['cdr3']['class'])
            
    return classes

def get_thera_canonical_data(tsv_path: Path) -> Dict[str, List[str]]:
    """
    Extracts canonical classes from Thera tool output TSV.
    P0 Contract: TSV must have exactly 4 columns: id, cdr, class, confidence.
    """
    df = pd.read_csv(tsv_path, sep='\t')
    
    # P0: Required columns = 4 (minimal contract)
    required = ["id", "cdr", "class", "confidence"]
    for col in required:
        if col not in df.columns:
            raise RuntimeError(f"CRITICAL: Thera canonical TSV {tsv_path.name} missing required column: {col}. Minimal contract requires: {required}")
    
    classes = {"H1": [], "H2": [], "L1": [], "L2": [], "L3": []}
    
    for _, row in df.iterrows():
        # P0: id normalization (consistent with assign script)
        full_id = str(row['id']).split('|')[0].strip()
        cdr = str(row['cdr']).upper()
        if cdr in classes:
            classes[cdr].append(str(row['class']))
            
    return classes

def check_thera_sequences(path: Path):
    """Verify that the Thera-SAbDab metadata file contains sequence columns"""
    if path.suffix.lower() == '.xlsx':
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)
        
    vh_cols = {"VH", "Heavy", "Heavy sequence", "VH sequence"}
    vl_cols = {"VL", "Light", "Light sequence", "VL sequence"}
    
    has_vh = any(c in df.columns for c in vh_cols)
    has_vl = any(c in df.columns for c in vl_cols)
    
    if not (has_vh or has_vl):
        raise RuntimeError(f"CRITICAL: Missing VH/VL sequences in Thera-SAbDab export: {path.name}")
    
    print(f"✅ Thera-SAbDab sequence validation OK: {path.name}")

def main():
    parser = argparse.ArgumentParser(description="Compare framework library canonical distribution to Thera-SAbDab")
    parser.add_argument("--framework_vh_yaml", required=True)
    parser.add_argument("--framework_vl_yaml", required=True)
    parser.add_argument("--thera_csv_or_xlsx", required=True)
    parser.add_argument("--thera_canonical_tsv", required=True)
    parser.add_argument("--run_id", default=datetime.now().strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--out_dir", help="Output directory for comparison results")
    
    args = parser.parse_args()
    
    if args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        out_dir = PROJECT_ROOT / "output" / "framework_library" / "canonical" / "compare_thera"
    
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Validation
    check_thera_sequences(Path(args.thera_csv_or_xlsx))
    
    # 2. Data Extraction
    fw_classes = get_framework_canonical_data(Path(args.framework_vh_yaml), Path(args.framework_vl_yaml))
    thera_classes = get_thera_canonical_data(Path(args.thera_canonical_tsv))
    
    # 3. Statistics
    # P0: Strict comparison only for H1/H2/L1/L2; L3 is caution-only
    STRICT_CDRS = ["H1", "H2", "L1", "L2"]
    CAUTION_CDRS = ["L3"]
    ALL_CDRS = STRICT_CDRS + CAUTION_CDRS
    
    coverage_data = []
    jsd_data_strict = []  # Only for STRICT_CDRS
    jsd_data_caution = []  # For CAUTION_CDRS (if needed)
    fw_freqs = []
    thera_freqs = []
    
    for cdr in ALL_CDRS:
        fw_list = fw_classes[cdr]
        th_list = thera_classes[cdr]
        
        fw_set = set(fw_list)
        th_set = set(th_list)
        covered = fw_set & th_set
        
        is_caution = cdr in CAUTION_CDRS
        
        coverage_data.append({
            "CDR": cdr,
            "framework_unique_classes": len(fw_set),
            "thera_unique_classes": len(th_set),
            "covered_classes": len(covered),
            "coverage_ratio": len(covered) / len(th_set) if th_set else 0.0,
            "caution": is_caution
        })
        
        # Frequencies for JSD
        fw_dist = {cls: fw_list.count(cls) / len(fw_list) for cls in fw_set} if fw_list else {}
        th_dist = {cls: th_list.count(cls) / len(th_list) for cls in th_set} if th_list else {}
        
        # Append to detailed frequency reports (with caution flag)
        for cls, freq in fw_dist.items():
            fw_freqs.append({"CDR": cdr, "Class": cls, "Frequency": freq, "Count": fw_list.count(cls), "caution": is_caution})
        for cls, freq in th_dist.items():
            thera_freqs.append({"CDR": cdr, "Class": cls, "Frequency": freq, "Count": th_list.count(cls), "caution": is_caution})
            
        # P0: JSD Calculation ONLY for STRICT_CDRS (H1/H2/L1/L2)
        if cdr in STRICT_CDRS:
            if fw_dist and th_dist:
                val_jsd = calculate_jsd(fw_dist, th_dist)
                jsd_data_strict.append({"CDR": cdr, "JS_Divergence": val_jsd})
            else:
                jsd_data_strict.append({"CDR": cdr, "JS_Divergence": "N/A"})
        elif cdr in CAUTION_CDRS:
            # L3: caution, not included in strict JSD
            jsd_data_caution.append({"CDR": cdr, "JS_Divergence": "N/A (caution, not in strict comparison)"})
            
    # 4. Save CSVs
    pd.DataFrame(coverage_data).to_csv(out_dir / "canonical_coverage_summary.csv", index=False)
    pd.DataFrame(fw_freqs).to_csv(out_dir / "canonical_frequency_framework.csv", index=False)
    pd.DataFrame(thera_freqs).to_csv(out_dir / "canonical_frequency_thera.csv", index=False)
    # P0: canonical_distribution_distance.csv only contains STRICT_CDRS
    pd.DataFrame(jsd_data_strict).to_csv(out_dir / "canonical_distribution_distance.csv", index=False)
    # Optional: caution table (if L3 data exists)
    if jsd_data_caution:
        pd.DataFrame(jsd_data_caution).to_csv(out_dir / "canonical_distribution_distance_caution.csv", index=False)
    
    # 5. Markdown Report
    report_path = out_dir / "REPORT_canonical_compare.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Framework vs Thera-SAbDab Canonical Distribution Comparison\n\n")
        f.write(f"- Run ID: {args.run_id}\n")
        f.write(f"- Timestamp: {datetime.now().isoformat()}\n\n")
        
        f.write("> **Mandatory Disclaimer**: synthetic CDR3 placeholder, do not interpret H3/L3.\n\n")
        
        f.write("## 1. Comparison Boundaries (Fixed Declaration)\n")
        f.write("- **Strict comparison**: H1, H2, L1, L2 (Validated North classes, included in JSD)\n")
        f.write("- **L3**: caution, not included in strict JSD\n")
        f.write("- **H3**: no canonical classification\n\n")
        
        f.write("## 2. Coverage Summary\n")
        f.write("| CDR | Lib Unique | Thera Unique | Covered | Ratio |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        for row in coverage_data:
            f.write(f"| {row['CDR']} | {row['framework_unique_classes']} | {row['thera_unique_classes']} | {row['covered_classes']} | {row['coverage_ratio']:.2%} |\n")
            
        f.write("\n## 3. Distribution Distance (JSD) - Strict Comparison Only\n")
        f.write("Calculates Jensen-Shannon Divergence between distributions (lower is closer). **Only H1/H2/L1/L2 are included.**\n\n")
        f.write("| CDR | JSD (bits) |\n")
        f.write("| --- | --- |\n")
        for row in jsd_data_strict:
            jsd_val = row['JS_Divergence']
            if isinstance(jsd_val, float):
                f.write(f"| {row['CDR']} | {jsd_val:.4f} |\n")
            else:
                f.write(f"| {row['CDR']} | {jsd_val} |\n")
        
        if jsd_data_caution:
            f.write("\n### L3 (Caution - Not in Strict JSD)\n")
            f.write("L3 canonical classes are recorded but excluded from strict distribution comparison due to synthetic CDR3 placeholder.\n")
            for row in jsd_data_caution:
                f.write(f"- {row['CDR']}: {row['JS_Divergence']}\n")
                
        f.write("\n## 4. Top Classes Comparison (H1 example)\n")
        h1_fw = sorted([x for x in fw_freqs if x['CDR'] == 'H1'], key=lambda x: x['Frequency'], reverse=True)[:5]
        h1_th = sorted([x for x in thera_freqs if x['CDR'] == 'H1'], key=lambda x: x['Frequency'], reverse=True)[:5]
        
        f.write("\n### Framework Library (Top 5)\n")
        for x in h1_fw: f.write(f"- {x['Class']}: {x['Frequency']:.1%}\n")
        f.write("\n### Thera-SAbDab (Top 5)\n")
        for x in h1_th: f.write(f"- {x['Class']}: {x['Frequency']:.1%}\n")

    print(f"✅ Comparison complete. Results saved to: {out_dir}")
    print(f"✅ Report: {report_path.relative_to(PROJECT_ROOT)}")

if __name__ == "__main__":
    main()
