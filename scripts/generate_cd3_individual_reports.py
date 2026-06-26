import json
import os
from pathlib import Path
import sys

# Add workspace root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.vhh.vhh_scaffold_match_and_craft import _build_vhh_residue_map_and_regions

JOB_STORAGE = ROOT / ".job_storage"
PROJECT_DIR = ROOT / "projects" / "CD3_VH2VHH_Batch_20260515"
REPORTS_DIR = PROJECT_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

SAMPLES = [
    ("sp34_murine_vh_blinatumomab", "SP34 (Murine VH)"),
    ("teplizumab_vh_vl", "Teplizumab (Humanized VH)"),
    ("okt3_humanized_scfv_actes", "OKT3 (Humanized VH)"),
    ("otelixizumab_vh_vl", "Otelixizumab (Humanized VH)"),
    ("foralumab_vh_vl", "Foralumab (Humanized VH)"),
    ("visilizumab_vh_vl", "Visilizumab (Humanized VH)"),
]

def get_segments(seq):
    if not seq: return {n: "" for n in ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]}
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

def generate_individual_report(job_suffix, display_name):
    job_id = f"cd3_v2v_{job_suffix}"
    res_path = JOB_STORAGE / job_id / "result.json"
    
    if not res_path.exists():
        print(f"Skipping {job_id}: result.json not found.")
        return

    with open(res_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    orig_seq = data.get("input_sequence", "")
    eng_seq = data.get("converted_sequence", "")
    
    orig_segs = get_segments(orig_seq)
    eng_segs = get_segments(eng_seq)

    md = []
    md.append(f"# VH→VHH : {display_name}")
    md.append(f"\n## §0  (Metadata)")
    md.append(f"*   ****: CD3  VHH ")
    md.append(f"*   ****: 2026-05-16")
    md.append(f"*   **Protocol **: V1.8.9 (SSOT )")
    md.append(f"*   ****: V1.8.9_VH_to_VHH_Conversion")
    md.append(f"*   ****: V3.2 (Console )")
    md.append(f"*   ****: {data.get('feasibility_verdict', 'UNKNOWN')}")

    md.append(f"\n## §1  (Executive Summary)")
    verdict = data.get("feasibility_verdict", "UNKNOWN")
    strategy = data.get("selected_strategy", "—")
    template = data.get("selected_template_id", "N/A")
    md.append(f" VH  VHH 。 **{verdict}**。")
    md.append(f" `{strategy}`， `{template}`。")
    md.append(f" CDR ， Hallmark 。")

    md.append(f"\n## §2  (Sequence Comparison)")
    md.append(f"### 2.1  (Full Sequence)")
    md.append(f"**Original VH**:\n```\n{orig_seq}\n```")
    md.append(f"**Designed VHH**:\n```\n{eng_seq}\n```")

    md.append(f"\n### 2.2  (Segment-by-Segment)")
    md.append("| Region | Original Segment | Designed Segment | Status | Diffs |")
    md.append("| :--- | :--- | :--- | :--- | :--- |")
    for reg in ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]:
        s1 = orig_segs.get(reg, "")
        s2 = eng_segs.get(reg, "")
        
        diffs = []
        s2_display = ""
        for i in range(max(len(s1), len(s2))):
            c1 = s1[i] if i < len(s1) else "-"
            c2 = s2[i] if i < len(s2) else "-"
            if c1 != c2:
                diffs.append(f"{c1}{i+1}{c2}")
                s2_display += f"**{c2}**"
            else:
                s2_display += c2
        
        status = "✅ Match" if not diffs else "⚠️ Modified"
        diff_str = ", ".join(diffs) if diffs else "—"
        md.append(f"| {reg} | `{s1}` | `{s2_display}` | {status} | {diff_str} |")

    md.append(f"\n## §3  (Framework Engineering)")
    md.append(f"### 3.1  (Applied Mutations)")
    muts = data.get("mutations_applied", [])
    if muts:
        for m in muts:
            md.append(f"*   `{m}`")
    else:
        md.append("*    (No mutations applied)")

    md.append(f"\n### 3.2  (Scaffold Matching)")
    md.append(f"*   **Selected Template**: `{template}`")
    md.append(f"*   **Germline Reference**: `{data.get('selected_germline', 'N/A')}`")

    md.append(f"\n## §4  (Structural Assessment)")
    md.append(f"*   **Input pLDDT**: {data.get('input_plddt', 'N/A')}")
    md.append(f"*   **Converted pLDDT**: {data.get('converted_plddt', 'N/A')}")
    md.append(f"#### CDR RMSD (Å):")
    rmsd = data.get("cdr_rmsd", {})
    md.append(f"*   **H1**: {rmsd.get('H1', '—')}")
    md.append(f"*   **H2**: {rmsd.get('H2', '—')}")
    md.append(f"*   **H3**: {rmsd.get('H3', '—')}")

    md.append(f"\n## §5  (Clinical Developability)")
    cmc = data.get("mini_cmc", {})
    md.append(f"| Metric | Value | Threshold | Status |")
    md.append(f"| :--- | :--- | :--- | :--- |")
    md.append(f"| pI | {cmc.get('pI', '—')} | 5.5 - 9.5 | {'✅' if 5.5 < cmc.get('pI', 0) < 9.5 else '⚠️'} |")
    md.append(f"| GRAVY | {cmc.get('GRAVY', '—')} | ≤ 0.1 | {'✅' if cmc.get('GRAVY', 1) <= 0.1 else '⚠️'} |")
    md.append(f"| Instability Index | {cmc.get('instability_index', '—')} | ≤ 40 | {'✅' if cmc.get('instability_index', 100) <= 40 else '⚠️'} |")
    md.append(f"| SAP Proxy | {cmc.get('SAP_proxy', '—')} | ≤ 1.0 | {'✅' if cmc.get('SAP_proxy', 2) <= 1.0 else '⚠️'} |")

    md.append(f"\n### 5.1  (PTM Liabilities)")
    md.append(f"*   **Oxidation**: {', '.join(map(str, cmc.get('oxidation_sites', []))) or 'None'}")
    md.append(f"*   **Deamidation**: {', '.join(map(str, cmc.get('deamidation_sites', []))) or 'None'}")
    md.append(f"*   **Glycosylation**: {', '.join(map(str, cmc.get('glycosylation_sites', []))) or 'None'}")

    md.append(f"\n## §6  (Risk Roadmap)")
    md.append(f"*   **Success Probability**: {data.get('success_probability', 'N/A')}")
    md.append(f"*   **Confidence Band**: {data.get('confidence_band', 'N/A')}")
    md.append(f"*   **Primary Blocker**: {data.get('primary_blocker', 'None')}")
    md.append(f"*   **Recommendation**: {data.get('primary_recommendation', 'Proceed to expression')}")

    md.append(f"\n## §7  (Methodology)")
    md.append(f"*   **Kabat **:  IMGT 39-40 (Kabat H34-35)  CD3 。")
    md.append(f"*   ** CDR2 **:  IMGT 56-74 。")
    md.append(f"*   ****:  Batch Uniqueness Gate (V1.8.9) ，。")

    filename = f"VH2VHH_Report_{job_suffix}.md"
    report_path = REPORTS_DIR / filename
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"Generated: {report_path}")

if __name__ == "__main__":
    for suffix, name in SAMPLES:
        generate_individual_report(suffix, name)
