#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
create_project.py

 Antibody_Engineer_Suite 。

（）：

    python scripts/create_project.py --name EGFR_7D12_VHH

：

    python scripts/create_project.py --name EGFR_7D12_VHH --base-dir D:/InSynBio-AI-Research/Antibody_Engineer_Suite
"""

import argparse
from pathlib import Path

# ：（ Antibody_Engineer_Suite）
DEFAULT_BASE_DIR = Path(__file__).resolve().parent.parent


PROJECT_SUBDIRS = [
    "raw",
    "v1_framework_engineering",
    "v2_cmc_repair",
    "v3_immunogenicity",
    "final_report",
    "logs",
]


def create_project_structure(base_dir: Path, project_name: str) -> Path:
    """
     base_dir/projects ，。
    。
    """
    projects_root = base_dir / "projects"
    project_root = projects_root / project_name

    created = []

    #  projects 
    if not projects_root.exists():
        projects_root.mkdir(parents=True, exist_ok=True)
        created.append(str(projects_root))

    # 
    if not project_root.exists():
        project_root.mkdir(parents=True, exist_ok=True)
        created.append(str(project_root))

    # 
    for subdir in PROJECT_SUBDIRS:
        sub_path = project_root / subdir
        if not sub_path.exists():
            sub_path.mkdir(parents=True, exist_ok=True)
            created.append(str(sub_path))

    #  raw  README （）
    raw_readme = project_root / "raw" / "README.txt"
    if not raw_readme.exists():
        raw_readme.write_text(
            "/FASTA/JSON， input_sequences.json。\n",
            encoding="utf-8",
        )
        created.append(str(raw_readme))

    #  final_report  README （）
    final_readme = project_root / "final_report" / "README.txt"
    if not final_readme.exists():
        final_readme.write_text(
            "， PDF/Word/Markdown 。\n",
            encoding="utf-8",
        )
        created.append(str(final_readme))

    return project_root


def main():
    parser = argparse.ArgumentParser(
        description="Create a standard project directory for antibody engineering tasks."
    )
    parser.add_argument(
        "--name",
        "-n",
        required=True,
        help="Project name, e.g. EGFR_7D12_VHH or Mouse_PD1.",
    )
    parser.add_argument(
        "--base-dir",
        "-b",
        default=str(DEFAULT_BASE_DIR),
        help=(
            "Base directory of Antibody_Engineer_Suite (default: script parent). "
            "。"
        ),
    )

    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        raise SystemExit(f"[ERROR] base-dir does not exist: {base_dir}")

    project_name = args.name.strip()
    if not project_name:
        raise SystemExit("[ERROR] project name is empty.")

    project_root = create_project_structure(base_dir, project_name)

    print("======================================")
    print(" Project directory created / verified ")
    print("======================================")
    print(f"Base dir:    {base_dir}")
    print(f"Project:     {project_name}")
    print(f"Project root:{project_root}")
    print("")
    print("Subdirectories:")
    for sub in PROJECT_SUBDIRS:
        print(f"  - {project_root / sub}")
    print("")
    print("：")
    print("  -  raw/ （ input_sequences.json）")
    print("  - v1/v2/v3 （result_v1.json / result_v2.json ）")
    print("  -  final_report/ ")


if __name__ == "__main__":
    main()

