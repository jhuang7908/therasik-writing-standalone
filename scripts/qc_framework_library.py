#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Quality Control (QC) for Framework Library.

Analyzes VH/VL framework YAML files and produces a QC report.
Checks for data completeness, traceability, and structural integrity.
"""

import sys
import os
import yaml
import csv
from pathlib import Path
from typing import Any, Dict, List, Set

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

def load_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_qc():
    vh_path = PROJECT_ROOT / "core" / "data" / "framework_library" / "vh_frameworks.yaml"
    vl_path = PROJECT_ROOT / "core" / "data" / "framework_library" / "vl_frameworks.yaml"
    canon_path = PROJECT_ROOT / "core" / "data" / "framework_library" / "canonical_envelopes.yaml"
    fr4_path = PROJECT_ROOT / "core" / "data" / "framework_library" / "fr4_j_segments.yaml"

    vh_data = load_yaml(vh_path)
    vl_data = load_yaml(vl_path)
    canon_data = load_yaml(canon_path)
    fr4_data = load_yaml(fr4_path)

    qc_results = []
    
    # Process VH
    vh_results = analyze_chain("VH", vh_data)
    qc_results.extend(vh_results)
    
    # Process VL
    vl_results = analyze_chain("VL", vl_data)
    qc_results.extend(vl_results)

    # FR4 Summary
    fr4_summary = analyze_fr4(fr4_data)

    # Generate outputs
    generate_qc_table(qc_results)
    generate_qc_report(vh_results, vl_results, fr4_summary)

def analyze_chain(chain: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not data:
        return []
    
    entries = data.get("frameworks", []) or data.get("entries", [])
    results = []
    
    for e in entries:
        fw_id = e.get("framework_id") or e.get("germline", "unknown")
        family = e.get("family", "unknown")
        
        # Check FR sequence
        fr_seq = e.get("fr_sequence_fr1_fr3", "TODO")
        has_fr = fr_seq != "TODO" and bool(fr_seq)
        
        # Check canonical
        canon = e.get("canonical", {})
        cdr1_class = canon.get("cdr1", {}).get("class", "TODO")
        cdr2_class = canon.get("cdr2", {}).get("class", "TODO")
        has_canon = cdr1_class != "TODO" and cdr2_class != "TODO"
        
        # Check traceability (source_trace or evidence)
        # source_trace: {source_file, fasta_header, sha256 or sha256_sequence}
        st = e.get("source_trace", {})
        has_sha = bool(st.get("sha256")) or bool(st.get("sha256_sequence"))
        has_trace = bool(st.get("source_file")) and bool(st.get("fasta_header")) and has_sha
        
        # Check evidence (alternative)
        evidence = e.get("evidence", [])
        has_evidence = len(evidence) > 0
        
        # Check numbering evidence (positions_map or numbering_maps)
        has_numbering = "numbering_maps" in e or "numbering_evidence" in e or "positions_map" in e
        
        # Check maps (vernier/hallmark)
        has_vernier = "vernier_map" in e
        has_hallmark = "hallmark_map" in e
        
        results.append({
            "framework_id": fw_id,
            "chain": chain,
            "family": family,
            "has_fr": has_fr,
            "has_canon": has_canon,
            "has_trace": has_trace or has_evidence,
            "has_numbering": has_numbering,
            "has_vernier": has_vernier,
            "has_hallmark": has_hallmark
        })
        
    return results

def analyze_fr4(data: Dict[str, Any]) -> Dict[str, Any]:
    if not data:
        return {"available": [], "missing": ["hJH4", "hJH6", "hJK1", "hJK2", "hJL2_3"]}
    
    entries = data.get("entries", [])
    available = [e.get("id") for e in entries if e.get("id")]
    required = ["hJH4", "hJH6", "hJK1", "hJK2", "hJL2_3"]
    missing = [r for r in required if r not in available]
    
    return {
        "available": available,
        "missing": missing
    }

def generate_qc_table(results: List[Dict[str, Any]]):
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "framework_library_qc_table.csv"
    
    if not results:
        return

    keys = results[0].keys()
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(results)
    
    print(f"[INFO] QC Table written to {csv_path}")

def generate_qc_report(vh_results: List[Dict[str, Any]], vl_results: List[Dict[str, Any]], fr4_summary: Dict[str, Any]):
    report_path = PROJECT_ROOT / "docs" / "framework_library_qc_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    lines = []
    lines.append("# Framework Library Quality Control Report")
    lines.append("")
    
    # 1. Summary Counts
    lines.append("## 1. Summary Counts")
    lines.append("")
    lines.append("| Chain | Count | Families | FR Seq (%) | Canonical (%) |")
    lines.append("|-------|-------|----------|------------|---------------|")
    
    for name, results in [("VH", vh_results), ("VL", vl_results)]:
        if not results:
            lines.append(f"| {name} | 0 | 0 | 0.0% | 0.0% |")
            continue
        
        count = len(results)
        families = len(set(r["family"] for r in results))
        fr_pct = (sum(1 for r in results if r["has_fr"]) / count) * 100
        canon_pct = (sum(1 for r in results if r["has_canon"]) / count) * 100
        lines.append(f"| {name} | {count} | {families} | {fr_pct:.1f}% | {canon_pct:.1f}% |")
    
    lines.append("")
    
    # 2. Detailed Checks
    lines.append("## 2. Detailed Checks")
    lines.append("")
    lines.append("| Chain | Traceability (%) | Numbering (%) | Vernier/Hallmark (%) |")
    lines.append("|-------|------------------|---------------|----------------------|")
    
    for name, results in [("VH", vh_results), ("VL", vl_results)]:
        if not results:
            lines.append(f"| {name} | 0.0% | 0.0% | 0.0% |")
            continue
        
        count = len(results)
        trace_pct = (sum(1 for r in results if r["has_trace"]) / count) * 100
        num_pct = (sum(1 for r in results if r["has_numbering"]) / count) * 100
        vh_pct = (sum(1 for r in results if r["has_vernier"] or r["has_hallmark"]) / count) * 100
        lines.append(f"| {name} | {trace_pct:.1f}% | {num_pct:.1f}% | {vh_pct:.1f}% |")
    
    lines.append("")
    
    # 3. FR4/J Availability
    lines.append("## 3. FR4/J Parts Availability")
    lines.append("")
    lines.append(f"- **Available:** {', '.join(fr4_summary['available']) or 'None'}")
    if fr4_summary['missing']:
        lines.append(f"- **Missing:** <span style='color:red'>{', '.join(fr4_summary['missing'])}</span>")
    else:
        lines.append("- **Missing:** None")
    
    lines.append("")
    
    # 4. Top Blockers
    lines.append("## 4. Top Blockers")
    lines.append("")
    blockers = []
    
    total_results = vh_results + vl_results
    if not total_results:
        blockers.append("- **Critical:** No framework data found in YAML files.")
    else:
        total_count = len(total_results)
        missing_fr = total_count - sum(1 for r in total_results if r["has_fr"])
        if missing_fr > 0:
            blockers.append(f"- **Missing Sequences:** {missing_fr}/{total_count} ({ (missing_fr/total_count)*100:.1f}%) entries are missing FR1-FR3 sequences (set to TODO).")
        
        missing_canon = total_count - sum(1 for r in total_results if r["has_canon"])
        if missing_canon > 0:
            blockers.append(f"- **Missing Canonical:** {missing_canon}/{total_count} ({ (missing_canon/total_count)*100:.1f}%) entries have incomplete canonical classes.")
            
        missing_trace = total_count - sum(1 for r in total_results if r["has_trace"])
        if missing_trace > 0:
            blockers.append(f"- **Traceability:** {missing_trace}/{total_count} ({ (missing_trace/total_count)*100:.1f}%) entries lack traceability info (sha256/source).")
            
        if fr4_summary['missing']:
            blockers.append(f"- **FR4/J Parts:** Required segments {', '.join(fr4_summary['missing'])} are missing.")

    if not blockers:
        lines.append("- No major blockers identified. Framework library is ready for production.")
    else:
        for b in blockers:
            lines.append(b)
            
    lines.append("")
    lines.append("---")
    lines.append(f"*Report generated by qc_framework_library.py*")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"[INFO] QC Report written to {report_path}")

if __name__ == "__main__":
    run_qc()
