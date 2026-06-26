import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.vhh.vhh_scaffold_match_and_craft import _build_vhh_residue_map_and_regions

PROJECT_DIR = ROOT / "projects" / "CD3_VH2VHH_Batch_20260515"
JOB_STORAGE = ROOT / ".job_storage"

SAMPLES = [
    ("sp34_murine_vh_blinatumomab", "SP34 (Murine VH)"),
    ("teplizumab_vh_vl", "Teplizumab (Humanized IgG)"),
    ("visilizumab_vh_vl", "Visilizumab (Humanized IgG)"),
    ("otelixizumab_vh_vl", "Otelixizumab (Humanized IgG)"),
    ("foralumab_vh_vl", "Foralumab (Full Human IgG)"),
    ("okt3_humanized_scfv_actes", "OKT3 (Humanized scFv)"),
]

def get_segments(seq):
    if not seq: return {n: "" for name in ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]}
    rmap, regions = _build_vhh_residue_map_and_regions(seq)
    ordered = getattr(rmap, "_ordered_rows", [])
    segments = {}
    for name in ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]:
        if name not in regions:
            segments[name] = ""
            continue
        lo, hi = regions[name]
        res = [aa for (pos, ins, aa) in ordered if lo <= pos <= hi]
        segments[name] = "".join(res)
    return segments

def select_candidates(candidates):
    # Seq 1: Conservative (Framework Preserving)
    cons = next((c for c in candidates if "keep_framework" in c.get("strategy", "")), candidates[-1])
    
    # Seq 2: Balanced (Top Graft by Identity)
    grafts = [c for c in candidates if c.get("strategy") == "cdr_graft_to_scaffold"]
    balanced = max(grafts, key=lambda x: x.get("framework_identity", 0)) if grafts else candidates[0]
    
    # Seq 3: Optimized (Top by Clinical Score)
    optimized = max(candidates, key=lambda x: x.get("clinical_score", 0))
    
    return [
        ("Seq 1 (Conservative)", cons),
        ("Seq 2 (Balanced)", balanced),
        ("Seq 3 (Optimized)", optimized)
    ]

def generate_report():
    md = []
    md.append("# ：CD3  VHH  (V3.2)")
    md.append(f"****: 2026-05-16")
    md.append("****: V1.8.9 (SSOT ： CDR2  + Kabat )")
    md.append("\n## 1. ")
    md.append("*   **Seq 1 (Conservative)**: ****。 VH ， Hallmark/Stealth 。。")
    md.append("*   **Seq 2 (Balanced)**: ****。 VHH  CDR ，。")
    md.append("*   **Seq 3 (Optimized)**: ****。 AbEvaluator （、、pI ）。")
    md.append("*   **Kabat **:  Kabat H34-35 (IMGT 39-40)， CD3 。")

    for job_suffix, display_name in SAMPLES:
        job_id = f"cd3_v2v_{job_suffix}"
        res_path = JOB_STORAGE / job_id / "result.json"
        
        if not res_path.exists():
            continue
            
        with open(res_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        orig_seq = data.get("input_sequence", "")
        orig_segs = get_segments(orig_seq)
        candidates = data.get("candidates", [])
        
        if not candidates: continue
        
        selected = select_candidates(candidates)
        
        md.append(f"\n---\n\n## 2. {display_name}")
        
        for label, cand in selected:
            eng_seq = cand.get("sequence", "")
            eng_segs = get_segments(eng_seq)
            score = cand.get("clinical_score", 0)
            delta = cand.get("abnativ_delta", 0)
            
            md.append(f"\n### {label}")
            md.append(f"*   ****: `{cand.get('strategy')}` (: `{cand.get('template_id', 'N/A')}`)")
            md.append(f"*   ****: Clinical Score: **{score}**, AbNatiV Δ: **{delta:.4f}**")
            md.append(f"\n**Sequence:**")
            md.append(f"```\n{eng_seq}\n```")
            
            md.append("\n** (vs Original VH):**")
            md.append("| Region | Original Segment | Designed Segment | Status | Diffs |")
            md.append("| :--- | :--- | :--- | :--- | :--- |")
            
            for reg in ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]:
                s1 = orig_segs[reg]
                s2 = eng_segs[reg]
                
                diff_list = []
                if len(s1) == len(s2):
                    for i, (a, b) in enumerate(zip(s1, s2)):
                        if a != b:
                            diff_list.append(f"{a}{i+1}{b}")
                else:
                    diff_list = ["Length Mismatch"]
                    
                status = "✅" if s1 == s2 else "⚠️"
                diff_str = ", ".join(diff_list) if diff_list and diff_list[0] != "Length Mismatch" else ("-" if not diff_list else "Len Diff")
                
                s2_display = ""
                if len(s1) == len(s2):
                    for a, b in zip(s1, s2):
                        if a != b:
                            s2_display += f"**{b}**"
                        else:
                            s2_display += b
                else:
                    s2_display = f"**{s2}**"
                    
                md.append(f"| {reg} | `{s1}` | `{s2_display}` | {status} | {diff_str} |")

    report_path = PROJECT_DIR / "Client_Report_Final_v3.md"
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    
    print(f"Report generated: {report_path}")

if __name__ == "__main__":
    generate_report()
