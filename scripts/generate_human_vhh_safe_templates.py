#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
generate_human_vhh_safe_templates.py

VHH-SAFE Human Framework
Human VH3 scaffoldFR2，VHH-SAFE（A/B/C）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.numbering.imgt_anarcii import imgt_number_anarcii, build_pos_to_aa_map, IMGTNumberingError

INPUT_SCAFFOLDS = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "vh_scaffolds" / "human_vh3_scaffolds.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "vh_scaffolds"
OUTPUT_JSON = OUTPUT_DIR / "human_vh3_vhh_safe_templates.json"
OUTPUT_FASTA = OUTPUT_DIR / "human_vh3_vhh_safe_templates.fasta"


# VHH-SAFE
VHH_SAFE_PLANS = {
    "A": {
        "name": "",
        "description": "44→Q, 45→R",
        "mutations": {
            44: "Q",
            45: "R"
        }
    },
    "B": {
        "name": "",
        "description": "37→Y/S, 44→Q, 45→R, 47→G",
        "mutations": {
            37: "Y",  # Y，SS
            44: "Q",
            45: "R",
            47: "G"
        }
    },
    "C": {
        "name": "VHH",
        "description": "scaffold: 37=Y, 44=Q, 45=R, 47=G",
        "mutations": {
            37: "Y",
            44: "Q",
            45: "R",
            47: "G"
        }
    }
}


def modify_fr2_for_vhh_safe(fr2_seq: str, plan: str) -> Tuple[str, Dict[int, Tuple[str, str]]]:
    """
    FR2VHH-SAFE
    
    Args:
        fr2_seq: FR2
        plan: （'A', 'B', 'C'）
    
    Returns:
        (FR2,  {pos: (aa, aa)})
    """
    if plan not in VHH_SAFE_PLANS:
        raise ValueError(f"Unknown plan: {plan}")
    
    plan_config = VHH_SAFE_PLANS[plan]
    mutations = plan_config["mutations"]
    
    # FR2IMGT，37/44/45/47
    try:
        rows = imgt_number_anarcii(fr2_seq)
        pos_map = build_pos_to_aa_map(rows)
    except IMGTNumberingError:
        # ，（FR239）
        # fallback，
        return fr2_seq, {}
    
    # 
    # FR2IMGT39-55
    pos_to_idx = {}
    for row in rows:
        pos = row.get("pos")
        if pos and 39 <= pos <= 55:
            # 
            # gap，
            pass
    
    # ：FR2IMGT，
    # FR2，FR2
    
    # ：FR2IMGT 39-55，
    # FR2IMGT
    
    # ：FR2，
    # 
    
    modified_seq = list(fr2_seq)
    mutation_log = {}
    
    # FR2
    # ：FR217aa，37/44/45/47FR2
    
    # ，
    # ，FR2
    
    return fr2_seq, {}


def modify_fr2_from_full_framework(full_framework: str, fr1: str, fr2: str, fr3: str, fr4: str, plan: str) -> Tuple[str, Dict[int, Tuple[str, str]]]:
    """
    FR2（）
    
    Args:
        full_framework: （FR1+FR2+FR3+FR4）
        fr1, fr2, fr3, fr4: FR
        plan: 
    
    Returns:
        (FR2, )
    """
    if plan not in VHH_SAFE_PLANS:
        raise ValueError(f"Unknown plan: {plan}")
    
    plan_config = VHH_SAFE_PLANS[plan]
    mutations = plan_config["mutations"]
    
    # IMGT
    try:
        rows = imgt_number_anarcii(full_framework)
        pos_map = build_pos_to_aa_map(rows)
    except IMGTNumberingError as e:
        print(f"  [WARN] IMGT: {e}")
        return fr2, {}
    
    # （FR2）
    # FR2IMGT39-55
    fr2_pos_to_aa = {}
    for pos in range(39, 56):  # 39-55
        if pos in pos_map:
            fr2_pos_to_aa[pos] = pos_map[pos]
    
    # FR2
    modified_fr2 = list(fr2)
    mutation_log = {}
    
    # FR2IMGT
    # FR2gap，
    
    # ：FR2，IMGT
    fr2_rebuilt = ""
    fr2_mutations = {}
    
    for pos in range(39, 56):
        if pos in pos_map:
            original_aa = pos_map[pos]
            
            # 
            if pos in mutations:
                new_aa = mutations[pos]
                # B：S，S
                if plan == "B" and pos == 37 and original_aa == "S":
                    new_aa = "S"
                
                if original_aa != new_aa:
                    fr2_mutations[pos] = (original_aa, new_aa)
                    fr2_rebuilt += new_aa
                else:
                    fr2_rebuilt += original_aa
            else:
                fr2_rebuilt += original_aa
    
    # FR2FR2，
    # FR2
    
    return fr2_rebuilt, fr2_mutations


def build_vhh_safe_templates(scaffolds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    scaffoldVHH-SAFE
    """
    templates = []
    
    for scaffold in scaffolds:
        scaffold_id = scaffold["scaffold_id"]
        consensus = scaffold["consensus"]
        
        fr1 = consensus["fr1"]
        fr2_original = consensus["fr2"]
        fr3 = consensus["fr3"]
        fr4 = consensus["fr4"]
        framework_full = consensus["framework_full"]
        
        # 
        for plan_id, plan_config in VHH_SAFE_PLANS.items():
            try:
                # FR2
                fr2_modified, mutations = modify_fr2_from_full_framework(
                    framework_full, fr1, fr2_original, fr3, fr4, plan_id
                )
                
                # 
                framework_modified = fr1 + fr2_modified + fr3 + fr4
                
                template = {
                    "template_id": f"{scaffold_id}_SAFE_{plan_id}",
                    "source_scaffold": scaffold_id,
                    "safe_plan": plan_id,
                    "plan_name": plan_config["name"],
                    "plan_description": plan_config["description"],
                    "consensus": {
                        "fr1": fr1,
                        "fr2": fr2_modified,
                        "fr3": fr3,
                        "fr4": fr4,
                        "framework_full": framework_modified
                    },
                    "mutations": {
                        f"pos_{pos}": {
                            "original": orig,
                            "modified": new
                        }
                        for pos, (orig, new) in mutations.items()
                    },
                    "n_members": scaffold.get("n_members", 0)
                }
                
                templates.append(template)
                
            except Exception as e:
                print(f"  [WARN]  {scaffold_id} {plan_id}: {e}")
                continue
    
    return templates


def write_templates_json(templates: List[Dict[str, Any]], path: Path):
    """JSON"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(templates, f, indent=2, ensure_ascii=False)


def write_templates_fasta(templates: List[Dict[str, Any]], path: Path):
    """FASTA"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for template in templates:
            tid = template["template_id"]
            plan = template["safe_plan"]
            n = template["n_members"]
            full = template["consensus"]["framework_full"]
            fr1 = template["consensus"]["fr1"]
            fr2 = template["consensus"]["fr2"]
            fr3 = template["consensus"]["fr3"]
            fr4 = template["consensus"]["fr4"]
            
            header = (
                f">{tid} | plan={plan} | n_members={n} | "
                f"fr_len=({len(fr1)},{len(fr2)},{len(fr3)},{len(fr4)})"
            )
            f.write(header + "\n")
            
            # 60aa
            for i in range(0, len(full), 60):
                f.write(full[i:i+60] + "\n")


def main():
    print("=" * 80)
    print("Human VH3 VHH-SAFE")
    print("=" * 80)
    
    print(f"\n[1] Human VH3 scaffolds: {INPUT_SCAFFOLDS}")
    print("-" * 80)
    
    if not INPUT_SCAFFOLDS.exists():
        print(f"[ERROR] : {INPUT_SCAFFOLDS}")
        return 1
    
    with open(INPUT_SCAFFOLDS, encoding="utf-8") as f:
        scaffolds = json.load(f)
    
    print(f"  scaffold: {len(scaffolds)}")
    
    print(f"\n[2] VHH-SAFE（：A/B/C）")
    print("-" * 80)
    
    templates = build_vhh_safe_templates(scaffolds)
    
    print(f"   {len(templates)} （{len(scaffolds)} scaffolds × 3 ）")
    
    # 
    total_mutations = sum(len(t.get("mutations", {})) for t in templates)
    print(f"  : {total_mutations}")
    
    print(f"\n[3] ")
    print("-" * 80)
    
    print(f"  [] JSON: {OUTPUT_JSON}")
    write_templates_json(templates, OUTPUT_JSON)
    
    print(f"  [] FASTA: {OUTPUT_FASTA}")
    write_templates_fasta(templates, OUTPUT_FASTA)
    
    # 
    print(f"\n[4] （5）")
    print("-" * 80)
    for template in templates[:5]:
        tid = template["template_id"]
        plan = template["safe_plan"]
        n_mut = len(template.get("mutations", {}))
        full = template["consensus"]["framework_full"]
        print(f"  {tid}: {plan}, {n_mut}, ={len(full)}aa")
        if template.get("mutations"):
            muts = list(template["mutations"].items())[:3]
            mut_str = ", ".join([f"pos{k.split('_')[1]}:{v['original']}→{v['modified']}" for k, v in muts])
            print(f"    : {mut_str}")
    
    print(f"\n{'='*80}")
    print("VHH-SAFE！")
    print(f"{'='*80}")
    print(f"\n: {OUTPUT_DIR}")
    print(f"  - JSON: {OUTPUT_JSON.name}")
    print(f"  - FASTA: {OUTPUT_FASTA.name}")
    
    return 0


if __name__ == "__main__":
    exit(main())


















