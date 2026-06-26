#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 VHH v1 

。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def get_file_info(file_path: Path) -> Dict[str, Any]:
    """"""
    if not file_path.exists():
        return {
            "exists": False,
            "size": 0,
            "modified": None,
        }
    
    stat = file_path.stat()
    return {
        "exists": True,
        "size": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
    }


def count_jsonl_lines(file_path: Path) -> int:
    """ JSONL """
    if not file_path.exists():
        return 0
    
    count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        for _ in f:
            count += 1
    return count


def count_csv_rows(file_path: Path) -> int:
    """ CSV （ header）"""
    if not file_path.exists():
        return 0
    
    import csv
    count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)  # Skip header
        for _ in reader:
            count += 1
    return count


def generate_file_inventory(base_dir: Path) -> Dict[str, Any]:
    """"""
    inventory = {
        "version": "vhh_v1",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "base_directory": str(base_dir.relative_to(PROJECT_ROOT)),
        "files": {},
    }
    
    # 
    core_files = {
        "manifest": base_dir / "manifest.json",
        "clean_jsonl": base_dir / "vhh_germline_assets_clean.jsonl",
        "proxy_jsonl": base_dir / "vhh_germline_assets_clean_with_canonical_proxy.jsonl",
    }
    
    for name, path in core_files.items():
        info = get_file_info(path)
        if name.endswith("jsonl"):
            info["record_count"] = count_jsonl_lines(path) if info["exists"] else 0
        inventory["files"][name] = {
            "path": str(path.relative_to(PROJECT_ROOT)),
            **info,
        }
    
    # Cluster 
    clusters_dir = base_dir / "clusters"
    cluster_files = {
        "cdr1_assignments": clusters_dir / "cdr1_cluster_assignments.csv",
        "cdr1_summary": clusters_dir / "cdr1_cluster_summary.csv",
        "cdr1_representatives": clusters_dir / "cdr1_representatives.fasta",
        "cdr2_assignments": clusters_dir / "cdr2_cluster_assignments.csv",
        "cdr2_summary": clusters_dir / "cdr2_cluster_summary.csv",
        "cdr2_representatives": clusters_dir / "cdr2_representatives.fasta",
    }
    
    inventory["files"]["clusters"] = {}
    for name, path in cluster_files.items():
        info = get_file_info(path)
        if name.endswith("csv") and "assignments" in name:
            info["row_count"] = count_csv_rows(path) if info["exists"] else 0
        elif name.endswith("csv") and "summary" in name:
            info["row_count"] = count_csv_rows(path) if info["exists"] else 0
        inventory["files"]["clusters"][name] = {
            "path": str(path.relative_to(PROJECT_ROOT)),
            **info,
        }
    
    # QC 
    qc_dir = base_dir / "qc"
    qc_files = {
        "dropped": qc_dir / "vhh_germline_assets_dropped.csv",
        "canonical_proxy_qc": qc_dir / "canonical_proxy_qc.csv",
        "hallmark_distribution": qc_dir / "vhh_hallmark_distribution.csv",
    }
    
    inventory["files"]["qc"] = {}
    for name, path in qc_files.items():
        info = get_file_info(path)
        if name.endswith("csv"):
            info["row_count"] = count_csv_rows(path) if info["exists"] else 0
        inventory["files"]["qc"][name] = {
            "path": str(path.relative_to(PROJECT_ROOT)),
            **info,
        }
    
    # 
    raw_fasta_dir = base_dir / "raw_fasta"
    raw_fasta_files = []
    if raw_fasta_dir.exists():
        for fasta_file in raw_fasta_dir.glob("*.fasta"):
            info = get_file_info(fasta_file)
            raw_fasta_files.append({
                "name": fasta_file.name,
                "path": str(fasta_file.relative_to(PROJECT_ROOT)),
                **info,
            })
    
    inventory["files"]["raw_fasta"] = {
        "directory": str(raw_fasta_dir.relative_to(PROJECT_ROOT)),
        "files": raw_fasta_files,
        "count": len(raw_fasta_files),
    }
    
    return inventory


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
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "file_inventory.json",
        help=" JSON ",
    )
    parser.add_argument(
        "--output_md",
        type=Path,
        default=PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "file_inventory.md",
        help=" Markdown ",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(" VHH v1 ")
    print("=" * 80)
    print()
    
    inventory = generate_file_inventory(args.base_dir)
    
    #  JSON
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=2, ensure_ascii=False)
    print(f"✅  JSON: {args.output}")
    
    #  Markdown
    md_lines = [
        "# VHH v1 ",
        "",
        f": {inventory['generated_at']}",
        f": `{inventory['base_directory']}`",
        "",
        "## ",
        "",
        "|  |  |  |  |  |  |",
        "|------|------|------|------|--------|----------|",
    ]
    
    for name, info in inventory["files"].items():
        if name in ["clusters", "qc", "raw_fasta"]:
            continue
        
        exists = "✅" if info["exists"] else "❌"
        size = f"{info.get('size_mb', 0)} MB" if info["exists"] else "-"
        count = str(info.get("record_count", 0)) if info["exists"] else "-"
        modified = info.get("modified", "-") if info["exists"] else "-"
        
        md_lines.append(
            f"| {name} | `{info['path']}` | {exists} | {size} | {count} | {modified} |"
        )
    
    md_lines.extend([
        "",
        "## Cluster ",
        "",
        "|  |  |  |  |  |  |",
        "|------|------|------|------|------|----------|",
    ])
    
    for name, info in inventory["files"]["clusters"].items():
        exists = "✅" if info["exists"] else "❌"
        size = f"{info.get('size_mb', 0)} MB" if info["exists"] else "-"
        rows = str(info.get("row_count", 0)) if info["exists"] else "-"
        modified = info.get("modified", "-") if info["exists"] else "-"
        
        md_lines.append(
            f"| {name} | `{info['path']}` | {exists} | {size} | {rows} | {modified} |"
        )
    
    md_lines.extend([
        "",
        "## QC ",
        "",
        "|  |  |  |  |  |  |",
        "|------|------|------|------|------|----------|",
    ])
    
    for name, info in inventory["files"]["qc"].items():
        exists = "✅" if info["exists"] else "❌"
        size = f"{info.get('size_mb', 0)} MB" if info["exists"] else "-"
        rows = str(info.get("row_count", 0)) if info["exists"] else "-"
        modified = info.get("modified", "-") if info["exists"] else "-"
        
        md_lines.append(
            f"| {name} | `{info['path']}` | {exists} | {size} | {rows} | {modified} |"
        )
    
    md_lines.extend([
        "",
        "##  (raw_fasta)",
        "",
        f": `{inventory['files']['raw_fasta']['directory']}`",
        f": {inventory['files']['raw_fasta']['count']}",
        "",
    ])
    
    if inventory["files"]["raw_fasta"]["files"]:
        md_lines.append("|  |  |  |  |  |")
        md_lines.append("|--------|------|------|------|----------|")
        for file_info in inventory["files"]["raw_fasta"]["files"]:
            exists = "✅" if file_info["exists"] else "❌"
            size = f"{file_info.get('size_mb', 0)} MB" if file_info["exists"] else "-"
            modified = file_info.get("modified", "-") if file_info["exists"] else "-"
            md_lines.append(
                f"| {file_info['name']} | `{file_info['path']}` | {exists} | {size} | {modified} |"
            )
    else:
        md_lines.append("⚠️ ")
    
    md_lines.append("")
    
    #  Markdown
    with open(args.output_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"✅  Markdown: {args.output_md}")
    
    print()
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)


if __name__ == "__main__":
    main()










