#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 VHH v1 

：
1. 
2. Hallmark 
3. 
"""

from __future__ import annotations

import argparse
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_hallmark_distribution(csv_path: Path) -> Dict[str, Any]:
    """ hallmark """
    if not csv_path.exists():
        return {}
    
    stats = {
        "label_counts": {},
        "score_stats": {},
    }
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 4 and row[0] in ["vhh_like", "vh_like", "ambiguous"]:
                label = row[0]
                count = int(row[2]) if row[2].isdigit() else 0
                percentage = row[3].replace("%", "") if len(row) > 3 else "0"
                stats["label_counts"][label] = {
                    "count": count,
                    "percentage": percentage,
                }
    
    return stats


def generate_summary_report(base_dir: Path, output_path: Path) -> None:
    """"""
    report_lines = [
        "# VHH v1 ",
        "",
        f": {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 1. ",
        "",
    ]
    
    # 
    core_files = {
        "manifest.json": base_dir / "manifest.json",
        "vhh_germline_assets_clean.jsonl": base_dir / "vhh_germline_assets_clean.jsonl",
        "vhh_germline_assets_clean_with_canonical_proxy.jsonl": base_dir / "vhh_germline_assets_clean_with_canonical_proxy.jsonl",
    }
    
    report_lines.append("### ")
    report_lines.append("")
    report_lines.append("|  |  |  |  |")
    report_lines.append("|------|------|------|--------|")
    
    for name, path in core_files.items():
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            if name.endswith(".jsonl"):
                count = sum(1 for _ in open(path, "r", encoding="utf-8"))
            else:
                count = "-"
            report_lines.append(f"| {name} | ✅ | {size_mb:.2f} MB | {count} |")
        else:
            report_lines.append(f"| {name} | ❌ | - | - |")
    
    report_lines.append("")
    
    # Hallmark 
    hallmark_csv = base_dir / "qc" / "vhh_hallmark_distribution.csv"
    if hallmark_csv.exists():
        stats = load_hallmark_distribution(hallmark_csv)
        report_lines.extend([
            "## 2. VHH Hallmark ",
            "",
            "|  |  |  |",
            "|------|------|--------|",
        ])
        
        for label, info in stats.get("label_counts", {}).items():
            report_lines.append(
                f"| {label} | {info['count']} | {info['percentage']}% |"
            )
        report_lines.append("")
    else:
        report_lines.extend([
            "## 2. VHH Hallmark ",
            "",
            "⚠️ ， `analyze_vhh_hallmark_distribution.py`",
            "",
        ])
    
    # 
    report_lines.extend([
        "## 3. ",
        "",
    ])
    
    checks = []
    
    #  1: VHH clean 
    clean_jsonl = base_dir / "vhh_germline_assets_clean.jsonl"
    if clean_jsonl.exists():
        count = sum(1 for _ in open(clean_jsonl, "r", encoding="utf-8"))
        checks.append(("VHH clean ", count >= 1, f"PASS: {count} "))
    else:
        checks.append(("VHH clean ", False, "FAIL: "))
    
    #  2: Hallmark 
    if clean_jsonl.exists():
        with open(clean_jsonl, "r", encoding="utf-8") as f:
            first_line = f.readline()
            if first_line:
                record = json.loads(first_line)
                has_hallmark = "vhh_hallmark" in record
                checks.append(("Hallmark ", has_hallmark, "PASS" if has_hallmark else "FAIL"))
            else:
                checks.append(("Hallmark ", False, "FAIL: "))
    else:
        checks.append(("Hallmark ", False, "FAIL: "))
    
    #  3: Canonical proxy 
    proxy_jsonl = base_dir / "vhh_germline_assets_clean_with_canonical_proxy.jsonl"
    if proxy_jsonl.exists():
        with open(proxy_jsonl, "r", encoding="utf-8") as f:
            first_line = f.readline()
            if first_line:
                record = json.loads(first_line)
                has_proxy = "canonical_proxy_cdr1" in record and "canonical_proxy_cdr2" in record
                checks.append(("Canonical proxy ", has_proxy, "PASS" if has_proxy else "FAIL"))
            else:
                checks.append(("Canonical proxy ", False, "FAIL: "))
    else:
        checks.append(("Canonical proxy ", False, "FAIL: "))
    
    #  4: QC CSV 
    qc_csv = base_dir / "qc" / "canonical_proxy_qc.csv"
    checks.append(("QC CSV ", qc_csv.exists(), "PASS" if qc_csv.exists() else "FAIL: "))
    
    report_lines.append("|  |  |  |")
    report_lines.append("|--------|------|------|")
    for check_name, passed, message in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        report_lines.append(f"| {check_name} | {status} | {message} |")
    
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("## ")
    report_lines.append("")
    report_lines.append("1. : `python scripts/generate_vhh_v1_file_inventory.py`")
    report_lines.append("2.  Hallmark : `python scripts/analyze_vhh_hallmark_distribution.py`")
    report_lines.append("3.  Scaffold  Debug: `python scripts/generate_scaffold_ranking_debug_vhh.py --input_json <stage1_result.json>`")
    report_lines.append("")
    
    # 
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    
    print("=" * 80)
    print("VHH v1 ")
    print("=" * 80)
    print()
    print(":")
    for check_name, passed, message in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}: {message}")
    print()
    print(f"✅ : {output_path}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description=" VHH v1 "
    )
    parser.add_argument(
        "--base_dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1",
        help="VHH v1 ",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "summary_report.md",
        help=" Markdown ",
    )
    
    args = parser.parse_args()
    
    generate_summary_report(args.base_dir, args.output)


if __name__ == "__main__":
    main()










