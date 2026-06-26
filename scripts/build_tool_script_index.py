#!/usr/bin/env python3
"""
build_tool_script_index.py
==========================
 docs/TOOL_SCRIPT_INDEX.md — AbEngineCore 。

**：**
  - （tools_registry.json ）
  -  scripts/ 
  -  core/ 
  -  audit_codebase_health.py  index 

：
  python scripts/build_tool_script_index.py            #  docs/TOOL_SCRIPT_INDEX.md
  python scripts/build_tool_script_index.py --dry-run  # ，
  python scripts/build_tool_script_index.py --check    #  exit code 1  index 

（，）：
  - config/tools_registry.json        → §1  + §1b 
  - core/**/*.py docstring             → §2 
  - scripts/*.py docstring + argparse → §3-9 
  - pipeline/*.py docstring           → §10 
  - scripts/_*.py                     → §11 （ 60 ）

（）：
  - TOOL_USE_CASES         — 
  - CORE_MODULE_DESCRIPTIONS —  API 
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ── helpers ───────────────────────────────────────────────────────────────────

def _first_docstring(path: Path) -> str:
    import warnings
    try:
        src = path.read_text(encoding="utf-8", errors="ignore")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(src)
        v = ast.get_docstring(tree)
        if v:
            return v.strip().splitlines()[0][:100]
    except Exception:
        pass
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[:12]:
        s = line.strip()
        if s and not s.startswith("#!") and (s.startswith("#") or s.startswith('"""') or s.startswith("'''")):
            clean = s.lstrip("#\"' ").rstrip("\"' ")
            if clean:
                return clean[:100]
    return ""


def _has_cli(path: Path) -> bool:
    try:
        src = path.read_text(encoding="utf-8", errors="ignore")
        return "ArgumentParser" in src or ("argparse" in src and "add_argument" in src)
    except Exception:
        return False


# ── §1 External tools ─────────────────────────────────────────────────────────

TOOL_USE_CASES: dict[str, str] = {
    "EvoEF2": (
        "** ΔG_bind  ΔΔG 。**"
        " - PDB，（kcal/mol）。"
        "  VAM （Tier-1） Hapten VAM /。"
        " ： `tools/EvoEF2_src/` （）。"
        " ****， B 。"
    ),
    "PRODIGY": (
        "** ΔG_bind  Kd 。**"
        " /， EvoEF2 。"
        "  VAM  PRODIGY Rescue（V1.3 ） Phase 3 。"
        " ****。"
    ),
    "ThermoMPNN": (
        "**GNN  ΔΔG  ΔTm （）。**"
        " ， per-residue ΔΔG_stability。"
        "  VAM （ΔΔG > +0.5 → ）。"
        " ****；。"
    ),
    "AntiFold": (
        "** CDR  log-likelihood 。**"
        "  PDB ， CDR 。"
        "  VAM （AntiFold  → -）。"
        "  CDR， ThermoMPNN（）。：affmat，biotite 0.38.0 。"
    ),
    "ProteinMPNN": (
        "**（inverse folding）， CDR 。**"
        "  backbone，。"
        "  De Novo CDR Design pipeline （Phase T0–T2）。"
        " ****， ΔΔG；，。"
    ),
    "AbLang": (
        "**/ log-likelihood 。**"
        " ， per-residue likelihood 。"
        "  VAM （ → ）。"
        "  mean() 。 VH ；VL 。"
    ),
    "ESM-IF1": (
        "** log-likelihood（）。**"
        "  AntiFold （ CDR）。"
        "  30s/PDB（CPU），， AntiFold 。"
        " ： AffinityEnergyToolkit， Absci benchmark。"
    ),
    "IgFold": (
        "**（VH/VL/VHH）， AlphaFold2。**"
        " ， AF2，。"
        " →。"
        " Absci benchmark ；/。"
    ),
    "EpiScan": (
        "**- B /。**"
        " ：- + （3D +  + ）。"
        " ：（per-residue epitope score）。"
        " ****：（B ），"
        " ****-（PPI），"
        " **** T  MHC （ MHCflurry/IEDB）。"
        "  DB1（162 Ab-Ag ）+ DB2（30 ）。"
        "  VAM 、。：episcan。"
    ),
    "OpenMM_MMGBSA": (
        "** MM/GBSA （，）。**"
        " EvoEF2 BuildMutant → PDBFixer  → OpenMM ff14SB+OBC2  →  ΔG_bind。"
        "  1–3 /（CPU）。 VAM Phase 4 。"
        "  854  Absci ； Top-20  MM/GBSA。"
    ),
    "ANARCI": (
        "**（Chothia / IMGT / Kabat / Martin）。**"
        "  VH/VL/VHH ， CDR 。"
        " 、CMC、。"
        " ：anarcii（ affmat ）。"
    ),
    "HADDOCK3": (
        "**-/-（）。**"
        " （ambiguous restraints）++。"
        "  VAM Scenario A（，），"
        "  De Novo CDR Design  CDR3 。"
        "  WSL Ubuntu-22.04（ Windows ）。"
    ),
    "LinearDesign": (
        "**mRNA （ + ）。**"
        " ， mRNA （ CAI ）。"
        " ** vaccine_design **；。"
    ),
    "LinearFold": (
        "**RNA （O(n) ）。**"
        "  mRNA  mRNA （MFE）。"
        " ** vaccine_design **；。"
    ),
}

# ── §2 Core module descriptions ───────────────────────────────────────────────

CORE_MODULE_DESCRIPTIONS: dict[str, str] = {
    "structure/affinity_energy_toolkit.py": (
        "AffinityEnergyToolkit | ** Python API， 6 /**"
        "（EvoEF2/PRODIGY/ThermoMPNN/AntiFold/ESM-IF1/OpenMM MM/GBSA）。"
        "  VAM  Hapten VAM  API ， CLI。"
    ),
    "humanization/engine.py": (
        "HumanizationEngine | VH/VL 。CDR 、、Vernier 。"
        " ：VH_VL_HUMANIZATION_STANDARD_V4.5.1。"
    ),
    "humanization/kabat_utils.py": (
        "KabatUtils | Kabat （get_kabat_numbering/is_in_cdr/sorted_keys）。"
        " CDR 、 identity 。。"
    ),
    "humanization/checklist_runner.py": (
        "ChecklistRunner | VH/VL  V4.4 。"
        "  Phase 1–5 。"
    ),
    "evaluation/evaluator.py": (
        "AbEvaluator | CMC （12 ，15 ）。"
        "  VH/VL/VHH//scFv/。AbRef-458 。"
    ),
    "integrity/hallucination_guard.py": (
        "HallucinationGuard | （6 ）。"
        " SEQ_BACK_CHECK + MUTANT_DIFF ； 4 。"
        "  VAM/Hapten VAM 。"
    ),
    "immunogenicity/ada_risk_scorer.py": (
        "ADAScorer | ADA （ FH/HU ）。"
        "  CLEAN-138 ，V2.1 。"
    ),
    "cmc/bispecific_cmc_engine.py": (
        "compute_fusion_matrix / select_recommendations |  VHH  CMC 。"
        "  pI 、SmartLink™ 、ER 。"
    ),
    "cmc/vhh_cmc_engine.py": (
        "evaluate_single_vhh | VHH CMC （15 ，VHH42 ）。"
        " flag-discrete ADI ；bispecific_cmc_engine 。"
    ),
    "vaccine_design/neoantigen_scanner.py": (
        "NeoantigenScanner | MHC-I  DAI 。"
        " MHCflurry 2.x，CPU-only，。"
    ),
    "car_design/car_designer.py": (
        "CARDesigner | CAR-T/CAR-NK/CAR-M （11 ）。"
        " CART_LIBRARY_V3 ，RuleValidator 。"
    ),
    "adc_design/adc_decision_engine.py": (
        "ADCDecisionEngine | ADC （8 ）。"
        " ADCProposal  schema， FTO 。"
    ),
    "reporting/render.py": (
        "render_pdf / render_html / write_dual_bundle |  API。"
        " ，/。"
    ),
    "reporting/spec.py": (
        "ReportSpec / ReportFamily / CHAPTER_SKELETONS |  family 。"
        " ： 11  family， 130+ 。"
    ),
}

# ── §3-9 Script categorization ────────────────────────────────────────────────

SCRIPT_CATEGORIES: dict[str, dict] = {
    "pipeline_entry": {
        "desc": "（Pipeline Entry Points）",
        "pattern": r"^run_",
        "files": [],
    },
    "audit_check": {
        "desc": "（Audit & Health Checks）",
        "pattern": r"^audit_|^check_|^verify_|^validate_",
        "files": [],
    },
    "build_generate": {
        "desc": "（Build & Generate）",
        "pattern": r"^build_|^generate_|^make_|^create_",
        "files": [],
    },
    "analysis": {
        "desc": "（Analysis & Statistics）",
        "pattern": r"^analyze_|^compare_|^rank_|^score_|^extract_",
        "files": [],
    },
    "report": {
        "desc": "（Report Generation）",
        "pattern": r"report|_pdf|_html",
        "files": [],
    },
    "website": {
        "desc": "（Website Maintenance）",
        "pattern": r"update_|deploy_|sync_|pivot_",
        "files": [],
    },
    "utility": {
        "desc": "（Utility & Support）",
        "pattern": (
            r"^(anarci_shim|structure_metrics|affinity_energy_cli|md_to_pdf|"
            r"report_cli|translate_|alpaca_|run_anarcii|run_bispecific)"
        ),
        "files": [],
    },
    "tmp_underscore": {
        "desc": "/（Temporary — prefix `_`）",
        "pattern": r"^_",
        "files": [],
    },
}


def categorize_script(name: str) -> str:
    for cat, info in SCRIPT_CATEGORIES.items():
        if re.match(info["pattern"], name):
            return cat
    return "utility"


def scan_scripts(scripts_dir: Path) -> dict[str, list[tuple[str, bool, str]]]:
    result: dict[str, list] = {k: [] for k in SCRIPT_CATEGORIES}
    for f in sorted(scripts_dir.glob("*.py")):
        cat = categorize_script(f.stem)
        result[cat].append((f.name, _has_cli(f), _first_docstring(f)))
    return result


def scan_pipeline(pipeline_dir: Path) -> list[tuple[str, bool, str]]:
    if not pipeline_dir.exists():
        return []
    return [
        (f.name, _has_cli(f), _first_docstring(f))
        for f in sorted(pipeline_dir.glob("*.py"))
    ]


# ── Markdown builder ──────────────────────────────────────────────────────────

def build_md() -> str:
    from datetime import date
    lines: list[str] = [
        "# AbEngineCore Tool & Script Index",
        "",
        f"**Generated:** {date.today().isoformat()}  ",
        "**Regenerate:** `python scripts/build_tool_script_index.py`  ",
        "**Root:** `Antibody_Engineer_Suite/`",
        "",
        "> This file is auto-generated. Do not edit manually.",
        "> Re-run the builder whenever tools or scripts are added/removed.",
        "",
        "---",
        "",
        "## Table of Contents",
        "1. [External Tools](#1-external-tools)",
        "2. [Core Python Modules](#2-core-python-modules)",
        "3. [Pipeline Entry Scripts](#3-pipeline-entry-scripts)",
        "4. [Audit & Check Scripts](#4-audit--check-scripts)",
        "5. [Build & Generate Scripts](#5-build--generate-scripts)",
        "6. [Analysis & Statistics Scripts](#6-analysis--statistics-scripts)",
        "7. [Report Generation Scripts](#7-report-generation-scripts)",
        "8. [Website Maintenance Scripts](#8-website-maintenance-scripts)",
        "9. [Utility & Support Scripts](#9-utility--support-scripts)",
        "10. [Pipeline Scripts (pipeline/)](#10-pipeline-scripts)",
        "11. [Temporary Scripts (prefix `_`)](#11-temporary-scripts-prefix-_)",
        "",
        "---",
        "",
        "## 1. External Tools",
        "",
        "Registered in `config/tools_registry.json`."
        " Always invoke via `core/structure/affinity_energy_toolkit.py`.",
        "",
        "| Tool | Conda Env | Status | Brief Use Case |",
        "|------|-----------|--------|----------------|",
    ]

    reg = json.loads((ROOT / "config" / "tools_registry.json").read_text(encoding="utf-8"))
    for name, info in reg["tools"].items():
        env = info.get("conda_env", "?")
        status = info.get("status", "?").split("—")[0].strip()[:30]
        use = TOOL_USE_CASES.get(name, info.get("use_case", info.get("purpose", "")))
        short = use.replace("**", "").split("。")[0][:100]
        lines.append(f"| **{name}** | `{env}` | {status} | {short} |")

    lines += ["", "### Tool Use-Case Details", ""]
    for name, use in TOOL_USE_CASES.items():
        lines.append(f"#### {name}")
        lines.append(use)
        lines.append("")

    # §2 Core modules
    lines += [
        "---", "", "## 2. Core Python Modules", "",
        "| Module | Class / API | Use Case |",
        "|--------|-------------|----------|",
    ]
    for rel, desc in CORE_MODULE_DESCRIPTIONS.items():
        parts = desc.split("|")
        cls = parts[0].strip() if len(parts) > 1 else ""
        use = (" | ".join(parts[1:])).strip() if len(parts) > 1 else desc
        use_short = use.replace("**", "").split("。")[0][:120]
        lines.append(f"| `core/{rel}` | `{cls}` | {use_short} |")

    # §3-9 scripts/
    scripts_dir = ROOT / "scripts"
    categorized = scan_scripts(scripts_dir)

    section_map = [
        ("pipeline_entry", "3. Pipeline Entry Scripts"),
        ("audit_check",    "4. Audit & Check Scripts"),
        ("build_generate", "5. Build & Generate Scripts"),
        ("analysis",       "6. Analysis & Statistics Scripts"),
        ("report",         "7. Report Generation Scripts"),
        ("website",        "8. Website Maintenance Scripts"),
        ("utility",        "9. Utility & Support Scripts"),
    ]
    for cat_key, title in section_map:
        lines += ["", "---", "", f"## {title}", ""]
        files = categorized.get(cat_key, [])
        if files:
            lines += ["| Script | CLI | Description |", "|--------|-----|-------------|"]
            for fname, cli, doc in files:
                lines.append(f"| `{fname}` | {'✓' if cli else ''} | {doc} |")
        else:
            lines.append("_(none)_")

    # §10 pipeline/
    pipeline_files = scan_pipeline(ROOT / "pipeline")
    lines += ["", "---", "", "## 10. Pipeline Scripts (pipeline/)", ""]
    if pipeline_files:
        lines += ["| Script | CLI | Description |", "|--------|-----|-------------|"]
        for fname, cli, doc in pipeline_files:
            lines.append(f"| `{fname}` | {'✓' if cli else ''} | {doc} |")
    else:
        lines.append("_(none)_")

    # §11 tmp
    tmp = categorized.get("tmp_underscore", [])
    lines += [
        "", "---", "", "## 11. Temporary Scripts (prefix `_`)", "",
        f"Total: **{len(tmp)}** files. One-off or data-pipeline scripts not intended for reuse.",
        "Archive after output data is validated.",
        "",
        "| Script | CLI | Description |",
        "|--------|-----|-------------|",
    ]
    for fname, cli, doc in tmp[:60]:
        lines.append(f"| `{fname}` | {'✓' if cli else ''} | {doc} |")
    if len(tmp) > 60:
        lines.append(f"| _(+{len(tmp) - 60} more — omitted)_ | | |")

    lines += [
        "", "---", "",
        "## Notes",
        "- **LOCKED files**: see `docs/ABENGINECORE_GOVERNANCE.md`",
        "- **Tool invocation**: check `config/tools_registry.json` before writing compute code",
        r"- **Coordinate system**: use `pipeline/coord_utils.py` for PDB/linear position mapping",
        r"- **Report output**: `core/reporting/render.py` or `scripts/report_cli.py`",
        r"- **Temporary scripts** (`_*.py`): review and archive after deliverable is confirmed",
        "",
    ]
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate docs/TOOL_SCRIPT_INDEX.md for AbEngineCore"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Print generated content, do not write file")
    parser.add_argument("--check", action="store_true",
                        help="Exit 1 if index is older than this script (needs regeneration)")
    args = parser.parse_args()

    out = ROOT / "docs" / "TOOL_SCRIPT_INDEX.md"

    if args.check:
        import time
        if not out.exists():
            print("STALE: docs/TOOL_SCRIPT_INDEX.md does not exist")
            sys.exit(1)
        script_mtime = Path(__file__).stat().st_mtime
        index_mtime = out.stat().st_mtime
        if index_mtime < script_mtime:
            print("STALE: docs/TOOL_SCRIPT_INDEX.md is older than build_tool_script_index.py")
            sys.exit(1)
        print("OK: docs/TOOL_SCRIPT_INDEX.md is up-to-date")
        sys.exit(0)

    content = build_md()

    if args.dry_run:
        print(content)
        return

    out.write_text(content, encoding="utf-8")
    print(f"Written {len(content):,} chars → {out.relative_to(ROOT)}")
    print("Tip: commit docs/TOOL_SCRIPT_INDEX.md whenever tools or scripts change.")


if __name__ == "__main__":
    main()
