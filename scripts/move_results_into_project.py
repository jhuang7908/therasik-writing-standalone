#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
move_results_into_project.py

：

（ result_v2.json, result_v2_report.txt）

（ v2_cmc_repair/）。

：

    python scripts/move_results_into_project.py --name EGFR_7D12_VHH --v2 result_v2.json --report result_v2_report.txt
"""

import argparse
from pathlib import Path
import shutil


DEFAULT_BASE_DIR = Path(__file__).resolve().parent.parent


def move_file(src: Path, dst: Path):
    if not src.exists():
        print(f"[WARN] ，：{src}")
        return False

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    print(f"[OK] ：{src.name} → {dst}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Move result files into a project directory.")
    parser.add_argument("--name", "-n", required=True, help="， EGFR_7D12_VHH")
    parser.add_argument("--base-dir", "-b", default=str(DEFAULT_BASE_DIR), help="（：）")

    parser.add_argument("--v1", help=" v1_framework_engineering/ ")
    parser.add_argument("--v2", help=" v2_cmc_repair/ ")
    parser.add_argument("--report", help=" v2_cmc_repair/ ")
    parser.add_argument("--v3", help=" v3_immunogenicity/ ")

    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()
    project_root = base_dir / "projects" / args.name

    if not project_root.exists():
        raise SystemExit(f"[ERROR] ：{project_root}")

    print(f"Project root: {project_root}")

    #  v1 
    if args.v1:
        src = Path(args.v1).resolve()
        dst = project_root / "v1_framework_engineering" / src.name
        move_file(src, dst)

    #  v2 
    if args.v2:
        src = Path(args.v2).resolve()
        dst = project_root / "v2_cmc_repair" / src.name
        move_file(src, dst)

    #  v2 
    if args.report:
        src = Path(args.report).resolve()
        dst = project_root / "v2_cmc_repair" / src.name
        move_file(src, dst)

    #  v3 
    if args.v3:
        src = Path(args.v3).resolve()
        dst = project_root / "v3_immunogenicity" / src.name
        move_file(src, dst)

    print("\n[Done] 。")


if __name__ == "__main__":
    main()























