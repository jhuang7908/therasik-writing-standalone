#!/usr/bin/env python3
"""
audit_codebase_health.py
========================
InSynBio AbEngineCore 。

：
  1. core/ （0  .py ）
  2. （anarcii env）
  3. tools_registry.json （BLOCKED / unknown）
  4. scripts/ （）
  5. （）
  6. standards 
  7. projects/ （ report.json  report.md）
  8. TOOL_SCRIPT_INDEX.md （>30  → WARN，）

：
  conda run -n anarcii python scripts/audit_codebase_health.py
  python scripts/audit_codebase_health.py --json  #  JSON 
  python scripts/audit_codebase_health.py --fix   # （： __pycache__）
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]

DATA_ONLY_CORE_DIRS = {"policies", "scaffolds", "schemas"}
DOC_ONLY_CORE_DIRS = {"vhh_humanization"}

# ──────────────────────────────────────────────────────────────────────────────
# Check 1: core/ empty directories
# ──────────────────────────────────────────────────────────────────────────────

IGNORE_CORE_DIRS = {"__pycache__", ".pytest_cache"}


def check_empty_core_dirs() -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    core_dir = ROOT / "core"
    if not core_dir.exists():
        return [{"level": "CRITICAL", "check": "core_dir_missing", "msg": "core/ directory not found"}]
    for d in sorted(core_dir.iterdir()):
        if not d.is_dir() or d.name in IGNORE_CORE_DIRS:
            continue
        py_files = list(d.rglob("*.py"))
        if not py_files:
            all_files = list(d.rglob("*"))
            non_dirs = [f for f in all_files if f.is_file()]
            doc_files = [f for f in non_dirs if f.suffix.lower() in {".md", ".txt", ".rst"}]

            if d.name in DATA_ONLY_CORE_DIRS:
                issues.append({
                    "level": "INFO",
                    "check": "core_data_only_dir",
                    "path": str(d.relative_to(ROOT)),
                    "msg": f"Data-only core dir ({len(non_dirs)} non-Python file(s))",
                    "action": "valid if intended as registry/schema/data support module"
                })
                continue

            if not non_dirs:
                issues.append({
                    "level": "WARN",
                    "check": "empty_core_dir",
                    "path": str(d.relative_to(ROOT)),
                    "msg": f"Truly empty core directory: core/{d.name}/",
                    "action": "restore source from git or remove directory if deprecated"
                })
                continue

            sibling_module = d.with_suffix(".py")
            if d.name in DOC_ONLY_CORE_DIRS and sibling_module.exists():
                issues.append({
                    "level": "INFO",
                    "check": "core_doc_support_dir",
                    "path": str(d.relative_to(ROOT)),
                    "msg": f"Doc/support dir for sibling module {sibling_module.name}",
                    "action": "valid if package docs/cache are intentional"
                })
                continue

            if d.name in DOC_ONLY_CORE_DIRS and len(doc_files) == len(non_dirs):
                issues.append({
                    "level": "WARN",
                    "check": "core_doc_only_dir",
                    "path": str(d.relative_to(ROOT)),
                    "msg": f"Doc-only core dir ({len(non_dirs)} file(s), no Python source)",
                    "action": "restore implementation from git if module is still active"
                })
                continue

            issues.append({
                "level": "WARN",
                "check": "empty_core_dir",
                "path": str(d.relative_to(ROOT)),
                "msg": f"0 Python files in core/{d.name}/ (total files: {len(non_dirs)})",
                "action": "investigate: restore from git or remove if deprecated"
            })
    return issues


# ──────────────────────────────────────────────────────────────────────────────
# Check 2: Critical module imports
# ──────────────────────────────────────────────────────────────────────────────

CRITICAL_MODULES = [
    ("core.humanization.engine", "HumanizationEngine", "anarcii"),
    ("core.humanization.kabat_utils", "get_kabat_numbering", "anarcii"),
    ("core.humanization.checklist_runner", "ChecklistRunner", "anarcii"),
    ("core.evaluation.evaluator", "AbEvaluator", "anarcii"),
    ("core.integrity.hallucination_guard", "HallucinationGuard", "affmat"),
    ("core.structure.affinity_energy_toolkit", "AffinityEnergyToolkit", "affmat"),
    ("core.cmc.bispecific_cmc_engine", "compute_fusion_matrix", "anarcii"),
    ("core.immunogenicity.ada_risk_scorer", "ADAScorer", "anarcii"),
]


def check_critical_imports() -> List[Dict[str, Any]]:
    """Test imports for critical modules (best-effort; may fail if wrong env)."""
    issues: List[Dict[str, Any]] = []
    sys.path.insert(0, str(ROOT))
    for module_path, symbol_name, env in CRITICAL_MODULES:
        # Check if module file exists first
        parts = module_path.split(".")
        mod_file = ROOT / Path(*parts[:-1]) / f"{parts[-1]}.py"
        alt_file = ROOT / Path(*parts) / "__init__.py"
        exists = mod_file.exists() or alt_file.exists()
        if not exists:
            issues.append({
                "level": "CRITICAL",
                "check": "module_file_missing",
                "module": module_path,
                "env": env,
                "msg": f"Source file not found: {mod_file.relative_to(ROOT)}",
                "action": f"restore from git: git checkout HEAD -- {mod_file.relative_to(ROOT)}"
            })
            continue
        # Try import
        try:
            mod = importlib.import_module(module_path)
            if not hasattr(mod, symbol_name):
                issues.append({
                    "level": "WARN",
                    "check": "symbol_missing",
                    "module": module_path,
                    "symbol": symbol_name,
                    "msg": f"Module exists but {symbol_name} not found",
                })
        except Exception as e:
            err_str = str(e)[:120]
            issues.append({
                "level": "WARN",
                "check": "import_error",
                "module": module_path,
                "env": env,
                "msg": f"Import failed (may be env issue if not in {env}): {err_str}",
                "action": f"run in {env} env to verify"
            })
    return issues


# ──────────────────────────────────────────────────────────────────────────────
# Check 3: tools_registry.json status scan
# ──────────────────────────────────────────────────────────────────────────────

def check_tools_registry() -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    registry_path = ROOT / "config" / "tools_registry.json"
    if not registry_path.exists():
        return [{"level": "CRITICAL", "check": "registry_missing", "msg": "config/tools_registry.json not found"}]
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    tools = registry.get("tools", {})
    for name, info in tools.items():
        status = info.get("status", "")
        # Check BLOCKED status
        if "BLOCKED" in status.upper():
            issues.append({
                "level": "WARN",
                "check": "tool_blocked",
                "tool": name,
                "status": status,
                "workaround": info.get("workaround"),
                "action": info.get("workaround") or "check tool documentation"
            })
        # Check missing last_validated
        if "last_validated" not in info:
            issues.append({
                "level": "INFO",
                "check": "missing_last_validated",
                "tool": name,
                "msg": "No last_validated date in registry",
                "action": "add last_validated field after next successful run"
            })
        # Check location exists (for cli/script types)
        if info.get("type") in ("cli_executable", "python_script"):
            loc = info.get("location") or info.get("entrypoint")
            if loc and not loc.startswith(("pip:", "conda", "d:/Users", "WSL")):
                loc_path = ROOT / loc
                if not loc_path.exists():
                    issues.append({
                        "level": "WARN",
                        "check": "tool_location_missing",
                        "tool": name,
                        "path": loc,
                        "msg": f"Tool file/directory not found: {loc}",
                        "action": "verify installation or update registry path"
                    })
    return issues


# ──────────────────────────────────────────────────────────────────────────────
# Check 4: Duplicate/orphan script detection in scripts/
# ──────────────────────────────────────────────────────────────────────────────

VERSION_PATTERN_SUFFIXES = ["_v1", "_v2", "_v3", "_v4", "_v5", "_v6"]


def check_duplicate_scripts() -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    scripts_dir = ROOT / "scripts"
    if not scripts_dir.exists():
        return []
    # Group by base name (strip version suffix)
    groups: Dict[str, List[Path]] = defaultdict(list)
    for f in sorted(scripts_dir.glob("*.py")):
        base = f.stem
        for sfx in VERSION_PATTERN_SUFFIXES:
            if base.endswith(sfx):
                base = base[: -len(sfx)]
                break
        groups[base].append(f)
    for base, files in groups.items():
        if len(files) > 1:
            issues.append({
                "level": "INFO",
                "check": "versioned_scripts",
                "base": base,
                "files": [str(f.relative_to(ROOT)) for f in files],
                "msg": f"{len(files)} version(s) found for '{base}'",
                "action": "keep latest version; archive older versions"
            })
    return issues


# ──────────────────────────────────────────────────────────────────────────────
# Check 5: config files — required keys present
# ──────────────────────────────────────────────────────────────────────────────

CONFIG_REQUIRED_KEYS = {
    "config/tools_registry.json": ["tools", "conda_env_map"],
    "config/tier_system_config.json": ["version", "tier_0_critical", "tier_1_high_priority"],
    "config/vh_vl_humanization_v451.json": ["_meta.version", "cdr_definitions", "framework_selection"],
    "config/vh_vl_humanization_v490.json": ["_meta.version", "cdr_definitions", "framework_selection", "qc_thresholds"],
    "config/hapten_vam_v10.json": ["_meta.version", "environments", "tools"],
}


def _has_key_path(data: Dict[str, Any], key_path: str) -> bool:
    cur: Any = data
    for part in key_path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    return True


def check_config_integrity() -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    for rel_path, required_keys in CONFIG_REQUIRED_KEYS.items():
        cfg_path = ROOT / rel_path
        if not cfg_path.exists():
            issues.append({
                "level": "CRITICAL",
                "check": "config_missing",
                "path": rel_path,
                "msg": f"Config file not found: {rel_path}",
                "action": "restore from git"
            })
            continue
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            for key in required_keys:
                if not _has_key_path(data, key):
                    issues.append({
                        "level": "WARN",
                        "check": "config_key_missing",
                        "path": rel_path,
                        "key": key,
                        "msg": f"Required key '{key}' missing in {rel_path}"
                    })
        except json.JSONDecodeError as e:
            issues.append({
                "level": "CRITICAL",
                "check": "config_parse_error",
                "path": rel_path,
                "msg": f"JSON parse error: {e}",
                "action": "fix JSON syntax"
            })
    return issues


# ──────────────────────────────────────────────────────────────────────────────
# Check 6: standards docs registration
# ──────────────────────────────────────────────────────────────────────────────

EXPECTED_STANDARD_FILES = [
    "docs/VH_VL_HUMANIZATION_STANDARD_V4.4.md",
    "docs/VHH_HUMANIZATION_DESIGN_STANDARD.md",
    "docs/VIRTUAL_AFFINITY_MATURATION_STANDARD.md",
    "docs/CMC_DEVELOPABILITY_STANDARD_V1.1.md",
    "docs/BISPECIFIC_VHH_CMC_STANDARD.md",
    "docs/ADC_DESIGN_STANDARD_V1.0.md",
    "docs/CART_DESIGN_STANDARD_V1.0.md",
    "docs/VACCINE_DESIGN_STANDARD_V1.0.md",
    "docs/HALLUCINATION_GUARD_STANDARD.md",
    "docs/HAPTEN_VAM_STANDARD_V1.0.md",
    "docs/EPIDESIGNCORE_STANDARD_V1.0.md",
    "docs/CANINIZATION_STANDARD_V1.0.md",
    "docs/ADA_RISK_SCORING_STANDARD_V2.1.md",
    "docs/ABENGINECORE_GOVERNANCE.md",
    "docs/STANDARDS_INDEX.md",
    "docs/EVOLUTION_LOG.md",
]


def check_standards_docs() -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    standards_index = ROOT / "docs" / "STANDARDS_INDEX.md"
    standards_index_text = ""
    if standards_index.exists():
        standards_index_text = standards_index.read_text(encoding="utf-8", errors="replace")

    for rel in EXPECTED_STANDARD_FILES:
        p = ROOT / rel
        if not p.exists():
            issues.append({
                "level": "CRITICAL",
                "check": "standard_doc_missing",
                "path": rel,
                "msg": f"Standard document not found: {rel}",
                "action": "restore from git or create"
            })
        elif p.stat().st_size < 200:
            issues.append({
                "level": "WARN",
                "check": "standard_doc_too_small",
                "path": rel,
                "size_bytes": p.stat().st_size,
                "msg": f"Standard doc suspiciously small ({p.stat().st_size} bytes): {rel}"
            })
        elif (
            rel.startswith("docs/")
            and p.name not in {"STANDARDS_INDEX.md", "EVOLUTION_LOG.md"}
            and standards_index_text
            and p.name not in standards_index_text
        ):
            issues.append({
                "level": "WARN",
                "check": "standard_doc_not_indexed",
                "path": rel,
                "msg": f"Standard exists but is not referenced by docs/STANDARDS_INDEX.md",
                "action": "register the standard in STANDARDS_INDEX.md"
            })
    return issues


# ──────────────────────────────────────────────────────────────────────────────
# Check 7: projects/ orphan output dirs (no report.json or report.md)
# ──────────────────────────────────────────────────────────────────────────────

def check_orphan_project_outputs() -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    projects_dir = ROOT / "projects"
    if not projects_dir.exists():
        return []
    count = 0
    for sub in sorted(projects_dir.rglob("*")):
        if not sub.is_dir():
            continue
        # Heuristic: dir has only .fasta / .txt / .pdb files and no report
        children = [f for f in sub.iterdir() if f.is_file()]
        if not children:
            continue
        exts = {f.suffix.lower() for f in children}
        has_report = any(f.name in ("report.json", "report.md") for f in children)
        is_output_dir = bool(exts & {".fasta", ".pdb", ".txt", ".csv"}) and not has_report
        if is_output_dir and not any(f.suffix == ".py" for f in children):
            count += 1
    if count > 0:
        issues.append({
            "level": "INFO",
            "check": "orphan_output_dirs",
            "count": count,
            "msg": f"{count} project output dirs found with no report.json/md",
            "action": "review and add report, or archive"
        })
    return issues


# ──────────────────────────────────────────────────────────────────────────────
# Check 8: TOOL_SCRIPT_INDEX.md staleness
# ──────────────────────────────────────────────────────────────────────────────

INDEX_MAX_AGE_DAYS = 30  # warn if older than this many days


def check_tool_script_index() -> List[Dict[str, Any]]:
    """Warn if docs/TOOL_SCRIPT_INDEX.md is missing or stale (>30 days old)."""
    issues: List[Dict[str, Any]] = []
    index_path = ROOT / "docs" / "TOOL_SCRIPT_INDEX.md"

    if not index_path.exists():
        issues.append({
            "level": "WARN",
            "check": "tool_script_index",
            "path": "docs/TOOL_SCRIPT_INDEX.md",
            "msg": "TOOL_SCRIPT_INDEX.md not found — run: python scripts/build_tool_script_index.py",
            "action": "python scripts/build_tool_script_index.py",
        })
        return issues

    import time
    age_days = (time.time() - index_path.stat().st_mtime) / 86400
    if age_days > INDEX_MAX_AGE_DAYS:
        issues.append({
            "level": "WARN",
            "check": "tool_script_index",
            "path": "docs/TOOL_SCRIPT_INDEX.md",
            "msg": f"TOOL_SCRIPT_INDEX.md is {age_days:.0f} days old (>{INDEX_MAX_AGE_DAYS}d threshold). "
                   "Regenerate after adding new tools/scripts.",
            "action": "python scripts/build_tool_script_index.py",
        })
    else:
        issues.append({
            "level": "INFO",
            "check": "tool_script_index",
            "path": "docs/TOOL_SCRIPT_INDEX.md",
            "msg": f"TOOL_SCRIPT_INDEX.md is up-to-date ({age_days:.0f} days old).",
        })

    # Also check that the build script itself exists
    builder = ROOT / "scripts" / "build_tool_script_index.py"
    if not builder.exists():
        issues.append({
            "level": "WARN",
            "check": "tool_script_index",
            "path": "scripts/build_tool_script_index.py",
            "msg": "build_tool_script_index.py not found — index cannot be regenerated automatically.",
            "action": "restore from git or re-create scripts/build_tool_script_index.py",
        })

    return issues


# ──────────────────────────────────────────────────────────────────────────────
# Summary and main
# ──────────────────────────────────────────────────────────────────────────────

LEVEL_ORDER = {"CRITICAL": 0, "WARN": 1, "INFO": 2}
LEVEL_ICONS = {"CRITICAL": "🔴", "WARN": "🟡", "INFO": "🔵"}


def run_all_checks(verbose: bool = True) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    all_issues: List[Dict[str, Any]] = []
    if verbose:
        print("Running AbEngineCore Health Audit...\n")

    checks = [
        ("1. core/ empty directories", check_empty_core_dirs),
        ("2. critical module imports", check_critical_imports),
        ("3. tools_registry.json status", check_tools_registry),
        ("4. duplicate/versioned scripts", check_duplicate_scripts),
        ("5. config file integrity", check_config_integrity),
        ("6. standards docs registration", check_standards_docs),
        ("7. orphan project output dirs", check_orphan_project_outputs),
        ("8. tool/script index freshness", check_tool_script_index),
    ]

    for label, fn in checks:
        if verbose:
            print(f"  Checking {label}...", end=" ", flush=True)
        issues = fn()
        counts = {lvl: sum(1 for i in issues if i["level"] == lvl) for lvl in ("CRITICAL", "WARN", "INFO")}
        if verbose:
            print(f"🔴{counts['CRITICAL']} 🟡{counts['WARN']} 🔵{counts['INFO']}")
        all_issues.extend(issues)

    totals = {lvl: sum(1 for i in all_issues if i["level"] == lvl) for lvl in ("CRITICAL", "WARN", "INFO")}
    return all_issues, totals


def print_report(issues: List[Dict[str, Any]], totals: Dict[str, int]) -> None:
    print("\n" + "=" * 70)
    print("ABENGINECORE HEALTH AUDIT REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Workspace: {ROOT}")
    print("=" * 70)

    # Group by level
    for level in ("CRITICAL", "WARN", "INFO"):
        level_issues = [i for i in issues if i["level"] == level]
        if not level_issues:
            continue
        icon = LEVEL_ICONS[level]
        print(f"\n{icon} {level} ({len(level_issues)} issues)")
        print("-" * 40)
        for issue in level_issues:
            check = issue.get("check", "?")
            msg = issue.get("msg", "")
            path = issue.get("path", issue.get("module", issue.get("tool", "")))
            print(f"  [{check}]")
            if path:
                print(f"    Path/Target: {path}")
            print(f"    {msg}")
            if "action" in issue:
                print(f"    → Action: {issue['action']}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print(f"  🔴 CRITICAL: {totals['CRITICAL']}")
    print(f"  🟡 WARN:     {totals['WARN']}")
    print(f"  🔵 INFO:     {totals['INFO']}")
    total = sum(totals.values())
    if totals["CRITICAL"] == 0 and totals["WARN"] == 0:
        print("\n  ✅ All critical and warning checks passed!")
    elif totals["CRITICAL"] == 0:
        print(f"\n  ⚠️  No critical issues, but {totals['WARN']} warnings need attention.")
    else:
        print(f"\n  ❌ {totals['CRITICAL']} critical issues require immediate action.")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="AbEngineCore codebase health audit")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix safe issues (clear __pycache__ dirs)",
    )
    args = parser.parse_args()

    if args.fix:
        # Safe auto-fix: remove __pycache__ dirs
        pycache_count = 0
        for p in ROOT.rglob("__pycache__"):
            if p.is_dir():
                import shutil
                shutil.rmtree(p, ignore_errors=True)
                pycache_count += 1
        print(f"Auto-fix: removed {pycache_count} __pycache__ directories")

    issues, totals = run_all_checks(verbose=not args.json)

    if args.json:
        output = {
            "generated": datetime.now().isoformat(),
            "workspace": str(ROOT),
            "summary": totals,
            "issues": issues,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print_report(issues, totals)

    # Exit code: 1 if any CRITICAL, 0 otherwise
    sys.exit(1 if totals["CRITICAL"] > 0 else 0)


if __name__ == "__main__":
    main()
