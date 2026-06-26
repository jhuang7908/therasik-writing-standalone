#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Kabat 

 7D12 VHH、VH3 germline  VH3 scaffold  Kabat 。
"""

import argparse
from typing import Dict, List, Tuple, Optional
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_anarcii_numbering(name: str, seq: str, scheme: str) -> Dict[str, Optional[str]]:
    """
    Returns dict: position_label -> AA (None for gap or missing)
    position_label is like '37' or '44A' depending on scheme/insertions.
    """
    try:
        from anarcii import Anarcii
    except ImportError:
        raise ImportError("anarcii package not found. Install with: pip install anarcii")
    
    # Use the same approach as in core/numbering/dual_numbering.py
    anarcii_obj = Anarcii(
        seq_type="antibody",
        mode="accuracy",
        batch_size=32,
        cpu=True,
        ncpu=-1,
        verbose=False,
    )
    
    seq_clean = seq.strip().upper().replace(" ", "").replace("\n", "").replace("\r", "")
    
    # 
    result = anarcii_obj.number(seq_clean)
    
    #  Kabat ，
    if scheme == "kabat":
        result = anarcii_obj.to_scheme('kabat')
    
    # 
    # result : {seq_key: {"numbering": [(pos_info, aa), ...], ...}}
    key = next(iter(result.keys()))
    seq_info = result.get(key, {})
    numbering = seq_info.get("numbering", [])
    
    if not numbering:
        raise ValueError(f"[{name}] ANARCI failed for scheme={scheme}: empty numbering")
    
    pos2aa: Dict[str, Optional[str]] = {}
    for item in numbering:
        if not isinstance(item, tuple) or len(item) < 2:
            continue
        pos_info, aa = item[0], item[1]
        
        if pos_info is None:
            continue
        
        # pos_info is tuple: (pos_num, ins_code)
        if isinstance(pos_info, tuple) and len(pos_info) >= 1:
            pos_num = pos_info[0]
            ins_code = pos_info[1] if len(pos_info) > 1 else ""
            # ：，
            ins_code_clean = ins_code.strip() if ins_code else ""
            label = f"{pos_num}{ins_code_clean}" if ins_code_clean else str(pos_num)
        else:
            label = str(pos_info)
        
        # aa can be '-' for gap
        if aa == "-" or aa is None:
            pos2aa[label] = None
        else:
            pos2aa[label] = str(aa)
    
    return pos2aa


def sorted_kabat_positions(pos_labels: List[str]) -> List[str]:
    """
    Sort Kabat positions like 37, 37A, 37B, 38...
    """
    def key(lbl: str):
        import re
        m = re.match(r"^(\d+)([A-Z]?)$", lbl)
        if not m:
            return (10**9, lbl)
        n = int(m.group(1))
        ins = m.group(2) or ""
        return (n, ins)
    return sorted(set(pos_labels), key=key)


def main():
    ap = argparse.ArgumentParser(
        description=" Kabat （7D12 VHH vs VH3 germline vs VH3 scaffold）"
    )
    ap.add_argument("--seq7d12", required=True, help="7D12 VHH ")
    ap.add_argument("--seq_germ", required=True, help="VH3 germline ")
    ap.add_argument("--seq_scf", required=True, help="VH3 scaffold ")
    ap.add_argument("--name7d12", default="7D12_VHH", help="7D12 ")
    ap.add_argument("--name_germ", default="VH3_germline", help="Germline ")
    ap.add_argument("--name_scf", default="VH3_scaffold", help="Scaffold ")
    ap.add_argument("--out", default="kabat_alignment_3way.md", help=" Markdown ")
    args = ap.parse_args()

    print("=" * 80)
    print(" Kabat ")
    print("=" * 80)
    print()

    # Kabat numbering
    print(f"[1/6]  {args.name7d12}  Kabat ...")
    try:
        kab_7d12 = run_anarcii_numbering(args.name7d12, args.seq7d12, scheme="kabat")
        print(f"  ✅ : {len(kab_7d12)} ")
    except Exception as e:
        print(f"  ❌ : {e}")
        return

    print(f"[2/6]  {args.name_germ}  Kabat ...")
    try:
        kab_germ = run_anarcii_numbering(args.name_germ, args.seq_germ, scheme="kabat")
        print(f"  ✅ : {len(kab_germ)} ")
    except Exception as e:
        print(f"  ❌ : {e}")
        return

    print(f"[3/6]  {args.name_scf}  Kabat ...")
    try:
        kab_scf = run_anarcii_numbering(args.name_scf, args.seq_scf, scheme="kabat")
        print(f"  ✅ : {len(kab_scf)} ")
    except Exception as e:
        print(f"  ❌ : {e}")
        return

    # IMGT numbering (for domain membership cross-check)
    print(f"[4/6]  {args.name7d12}  IMGT ...")
    try:
        imgt_7d12 = run_anarcii_numbering(args.name7d12, args.seq7d12, scheme="imgt")
        print(f"  ✅ : {len(imgt_7d12)} ")
    except Exception as e:
        print(f"  ⚠️  IMGT : {e}（ Kabat ）")
        imgt_7d12 = {}

    print(f"[5/6]  {args.name_germ}  IMGT ...")
    try:
        imgt_germ = run_anarcii_numbering(args.name_germ, args.seq_germ, scheme="imgt")
        print(f"  ✅ : {len(imgt_germ)} ")
    except Exception as e:
        print(f"  ⚠️  IMGT : {e}（ Kabat ）")
        imgt_germ = {}

    print(f"[6/6]  {args.name_scf}  IMGT ...")
    try:
        imgt_scf = run_anarcii_numbering(args.name_scf, args.seq_scf, scheme="imgt")
        print(f"  ✅ : {len(imgt_scf)} ")
    except Exception as e:
        print(f"  ⚠️  IMGT : {e}（ Kabat ）")
        imgt_scf = {}

    all_pos = sorted_kabat_positions(list(kab_7d12.keys()) + list(kab_germ.keys()) + list(kab_scf.keys()))

    def aa(x: Dict[str, Optional[str]], p: str) -> str:
        return x.get(p) if x.get(p) is not None else "-"

    # Simple out-of-domain heuristic:
    # If Kabat has AA at position p but IMGT has no corresponding AA anywhere near (can't map directly),
    # we mark "domain_unknown". For rigorous mapping, use your dual_numbering map.
    # Here we just annotate "Kabat-only" positions.
    def kabat_only_flag(kab_dict: Dict[str, Optional[str]], imgt_dict: Dict[str, Optional[str]], p: str) -> str:
        if kab_dict.get(p) is None:
            return ""
        # IMGT dict doesn't share labels with Kabat; we can't 1:1 map without your mapping table.
        # So we mark Kabat-only positions as "needs_map".
        return "needs_map"

    lines = []
    lines.append("# 3-way Kabat-numbered alignment (7D12 vs VH3 germline vs VH3 scaffold)\n")
    lines.append("## Inputs\n")
    lines.append(f"- **7D12**: {args.name7d12}\n")
    lines.append(f"- **Germline**: {args.name_germ}\n")
    lines.append(f"- **Scaffold**: {args.name_scf}\n")
    lines.append("\n## Kabat position table\n")
    lines.append("| Kabat | 7D12 | Germline | Scaffold | Notes |\n")
    lines.append("|---:|:---:|:---:|:---:|:---|\n")

    for p in all_pos:
        a1 = aa(kab_7d12, p)
        a2 = aa(kab_germ, p)
        a3 = aa(kab_scf, p)
        notes = []
        # highlight hallmark positions
        if p in {"37", "44", "45", "47"}:
            notes.append("**hallmark**")
        # mark gaps
        if a1 == "-" or a2 == "-" or a3 == "-":
            notes.append("gap")
        # mapping reminder
        if p in {"37", "44", "45", "47"}:
            notes.append("verify_kabat→imgt_map")
        # mark differences
        if a1 != a2 or a1 != a3 or a2 != a3:
            notes.append("diff")
        lines.append(f"| {p} | {a1} | {a2} | {a3} | {', '.join(notes) if notes else '-'} |\n")

    lines.append("\n## IMGT sanity checks (domain reconstruction)\n")
    lines.append("- If any sequence fails IMGT reconstruction (Check A), stop and fix segmentation/domain extraction.\n")
    lines.append("- Use your existing dual_numbering mapping to label out-of-domain Kabat residues explicitly.\n")
    lines.append("\n## Hallmark positions summary\n")
    lines.append("| Position | 7D12 | Germline | Scaffold | Status |\n")
    lines.append("|----------|------|----------|----------|--------|\n")
    for p in ["37", "44", "45", "47"]:
        a1 = aa(kab_7d12, p)
        a2 = aa(kab_germ, p)
        a3 = aa(kab_scf, p)
        status = []
        # Check if all are gaps
        if a1 == "-" and a2 == "-" and a3 == "-":
            status.append("all_gap")
        elif a1 == a2 == a3 and a1 != "-":
            status.append("identical")
        elif a1 == a2 and a1 != "-":
            status.append("7d12=germ")
        elif a1 == a3 and a1 != "-":
            status.append("7d12=scf")
        elif a2 == a3 and a2 != "-":
            status.append("germ=scf")
        else:
            status.append("all_diff")
        lines.append(f"| {p} | {a1} | {a2} | {a3} | {', '.join(status)} |\n")

    # 
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = PROJECT_ROOT / out_path

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print()
    print("=" * 80)
    print(f"✅ ！: {out_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()

