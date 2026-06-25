#!/usr/bin/env python3
"""
： scripts/ pipeline/ core/ ，，
 docs/TOOL_SCRIPT_INDEX.md
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve.parent

# ── （ tools_registry.json）──────────────────────────────────────
REGISTRY_PATH = ROOT / "config" / "tools_registry.json"

# ── ────────────────────────────────────────────
CATEGORY_RULES = [
    (r"^run_",         ""),
    (r"^generate_",    ""),
    (r"^build_",       ""),
    (r"^audit_",       ""),
    (r"^update_",      ""),
    (r"^analyze_",     ""),
    (r"^train_",       ""),
    (r"^export_",      ""),
    (r"^check_",       ""),
    (r"^translate_",   "/"),
    (r"^report_",      ""),
    (r"^md_to_",       ""),
    (r"^validate_",    ""),
    (r"^deploy_",      ""),
    (r"^pivot_",       ""),
    (r"^quick_",       ""),
    (r"^_",            "/（_）"),
]

CORE_MODULE_CATEGORIES = {
    "humanization":   "VH/VL ",
    "immunogenicity": "",
    "integrity":      "（HallucinationGuard）",
    "structure":      "",
    "evaluation":     "CMC/",
    "cmc":            "VHH CMC &  CMC ",
    "car_design":     "CAR-T ",
    "adc_design":     "ADC ",
    "vaccine_design": "",
    "reporting":      "",
    "numbering":      "（Kabat/IMGT/Chothia）",
    "evolution":      "",
    "explain":        "",
    "features":       "",
    "resources":      "/",
    "gates":          "",
    "scoring":        "",
    "segmentation":   "",
    "utils":          "",
    "vhh_scaffolds":  "VHH ",
    "vhh":            "VHH ",
}

PIPELINE_DESCRIPTIONS = {
    "run_mpnn_v2.py":            " ProteinMPNN CDR （V2，）",
    "run_t0_t1_phase1.py":       "De Novo CDR  Phase 1（T0/T1 ）",
    "cluster_and_filter_v2.py":  "MPNN （V2）",
    "rank_phase1_for_p2.py":     "Phase 1 ， Phase 2 ",
    "coord_utils.py":            " PDB Chothia （pipeline ）",
    "run_all_v2.py":             "De Novo CDR （checkpoint/resume）",
}

# ──  ──────────────────────────────────────────
EXTERNAL_TOOL_USE_CASES = {
    "EvoEF2": {
        "": " ΔΔG ",
        "": "（ΔΔG_bind）（ΔΔG_stab）。"
                   " B ，，。"
                   "：PDB  + 。：。",
        "": "、、CMC ",
        "": "Pearson r≈0.50-0.60 vs SKEMPI2 -",
    },
    "PRODIGY": {
        "": " ΔG_bind  Kd ",
        "": "（/） Kd。"
                   " EvoEF2 ，， ΔΔG。",
        "": " ΔΔG（EvoEF2 ）、",
        "": "Pearson r≈0.74 vs PPI ",
    },
    "ThermoMPNN": {
        "": "GNN  ΔΔG  ΔTm ",
        "": "。"
                   " VAM ：ΔΔG_stab > +0.5 kcal/mol 。"
                   " SSM （，~2340 /PDB）。",
        "": "、、",
        "": "Pearson r≈0.75 on FireProt/Megascale",
    },
    "AntiFold": {
        "": " CDR ",
        "": "， CDR （per-residue log-likelihood）。"
                   " ThermoMPNN ：ThermoMPNN ，AntiFold  CDR -。",
        "": "、、",
        "": "Spearman r≈0.52 vs ΔΔG_exp（ benchmark）",
    },
    "ProteinMPNN": {
        "": "（CDR ）",
        "": "，。 De Novo CDR "
                   " CDR 。：， ΔΔG 。",
        "": "、ΔΔG 、",
        "": "（，）",
    },
    "AbLang": {
        "": " / ",
        "": "， log-likelihood。"
                   "：，"
                   " De Novo CDR 。",
        "": "、、",
        "": " vs  ADA；",
    },
    "ESM-IF1": {
        "": " log-likelihood",
        "": "Meta  ESM inverse folding ，。"
                   " AntiFold ，（~30s/PDB CPU）。"
                   " VAM pipeline  AntiFold 。",
        "": "、",
        "": " benchmark，",
    },
    "IgFold": {
        "": "（VH/VL/VHH）",
        "": "（ AlphaFold2， Fv ）。"
                   "，Absci benchmark  PDB，。",
        "": "ΔΔG （ EvoEF2 BuildMutant）、",
        "": "CDR-H3 RMSD≈2.5Å ",
    },
    "EpiScan": {
        "": "- B （+）",
        "": "（/），"
                   "（per-residue ）。"
                   "：- + （.h5）+ （.pickle）。"
                   "：。"
                   " PPI ：-，-、-。"
                   " T （ MHCII ， MHCflurry/IEDB）。",
        "": " PPI 、T 、MHC 、",
        "": "AUC≈0.82 on DB1（162 Ab-Ag ）",
    },
    "LinearDesign": {
        "": "mRNA （ + RNA ）",
        "": " mRNA /。，"
                   "（CAI） RNA （，MFE）。"
                   " vaccine_design ，。",
        "": "、",
        "": "",
    },
    "LinearFold": {
        "": "RNA ",
        "": "O(n)  RNA （ 10x）。"
                   " vaccine_design  mRNA 。",
        "": "、DNA ",
        "": " RNAfold ，",
    },
    "OpenMM_MMGBSA": {
        "": " MM/GBSA ",
        "": " OpenMM （ff14SB + OBC2 ）。"
                   " VAM （~1-3 min/，CPU）。"
                   "（Phase 4），。",
        "": "、",
        "": "； EvoEF2/PRODIGY ",
    },
    "ANARCI": {
        "": " Chothia/IMGT/Kabat ",
        "": "（Kabat/Chothia/IMGT），"
                   "。、CMC 、。"
                   " anarcii conda 。",
        "": "、（ Fv ）",
        "": "，",
    },
    "HADDOCK3": {
        "": "-",
        "": "-，。"
                   "：(1) Scenario A  VAM（AutoDock Vina  HADDOCK3 ）；"
                   "(2) De Novo CDR3 （，）。"
                   "：WSL Ubuntu-22.04， Windows 。",
        "": "、",
        "": "Top-1 （DockQ>0.23）~60-70% - benchmark",
    },
    "MHCflurry": {
        "": "MHC-I （T ）",
        "": " MHC-I （HLA-A/B/C）（IC50 nM）。"
                   "（NeoantigenScanner） pMHC-TCR （EpiDesignCore）。"
                   "： T ， EpiScan（B ）。",
        "": "B （ EpiScan）、MHC-II （ IEDB）",
        "": "AUC≈0.90+ on IEDB benchmark（HLA-A*02:01）",
    },
}


def get_docstring(path: Path) -> str:
    """Extract first meaningful line of module docstring."""
    try:
        txt = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    m = re.search(r'"""(.*?)"""', txt, re.DOTALL)
    if m:
        lines = [l.strip for l in m.group(1).strip.splitlines if l.strip]
        return lines[0][:100] if lines else ""
    m2 = re.search(r"'''(.*?)'''", txt, re.DOTALL)
    if m2:
        lines = [l.strip for l in m2.group(1).strip.splitlines if l.strip]
        return lines[0][:100] if lines else ""
    for line in txt.splitlines[:5]:
        if line.startswith("# ") and not line.startswith("# !/"):
            return line[2:].strip[:100]
    return ""


def classify_script(name: str) -> str:
    for pattern, cat in CATEGORY_RULES:
        if re.match(pattern, name, re.IGNORECASE):
            return cat
    return ""


def has_cli(path: Path) -> bool:
    try:
        txt = path.read_text(encoding="utf-8", errors="ignore")
        return "ArgumentParser" in txt or ("argparse" in txt and "add_argument" in txt)
    except Exception:
        return False


def get_env(path: Path) -> str:
    try:
        txt = path.read_text(encoding="utf-8", errors="ignore").lower
        if "anarcii" in txt or "anarci" in txt:
            return "anarcii"
        if "affmat" in txt or "thermompnn" in txt or "evoef2" in txt:
            return "affmat"
        if "episcan" in txt:
            return "episcan"
        if "lineardesign" in txt or "vaccine" in txt:
            return "vaccine"
    except Exception:
        pass
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# 1. External tools section
# ─────────────────────────────────────────────────────────────────────────────

lines = []
lines.append("# AbEngineCore \n")
lines.append(f"**:** 2026-04-14  \n")
lines.append("**:**  · pipeline  · scripts/ · core/   \n")
lines.append("**:** /、、\n\n")
lines.append("---\n\n")

# ── Part 1:  ──────────────────────────────────────────────────────────
lines.append("## ：（External Tools）\n\n")
lines.append(">  `config/tools_registry.json`； Python API  `core/structure/affinity_energy_toolkit.py`\n\n")

if REGISTRY_PATH.exists:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    tools = registry.get("tools", {})
    env_map = registry.get("conda_env_map", {})

    lines.append("|  | conda  |  |  |  |  |\n")
    lines.append("|--------|-----------|---------|---------|-----------|------|\n")

    for name, info in tools.items:
        env = info.get("conda_env", "?")
        status = info.get("status", "?").split("—")[0].split("(")[0].strip
        uc = EXTERNAL_TOOL_USE_CASES.get(name, {})
        scene = uc.get("", info.get("purpose", ""))[:40]
        detail = uc.get("", "")[:60]
        not_for = uc.get("", "")[:50]
        lines.append(f"| **{name}** | `{env}` | {scene} | {detail} | {not_for} | {status} |\n")

    lines.append("\n### \n\n")
    for name, uc in EXTERNAL_TOOL_USE_CASES.items:
        if name not in tools:
            continue
        info = tools[name]
        lines.append(f"#### {name}\n\n")
        lines.append(f"- **:** {info.get('type', '?')}\n")
        lines.append(f"- **:** `{info.get('conda_env', '?')}`\n")
        lines.append(f"- **:** `{info.get('location') or info.get('entrypoint', '?')}`\n")
        lines.append(f"- **Python API:** `{info.get('python_api', 'N/A')}`\n")
        lines.append(f"- **:** {info.get('status', '?')}\n")
        lines.append(f"- **:** {uc.get('', '')}\n")
        lines.append(f"- **:** {uc.get('', '')}\n")
        lines.append(f"- **:** {uc.get('', '')}\n")
        lines.append(f"- **:** {uc.get('', '')}\n")
        if "benchmark" in info:
            lines.append(f"- **Benchmark:** {info.get('benchmark', '')}\n")
        lines.append("\n")

lines.append("---\n\n")

# ── Part 2: pipeline/  ─────────────────────────────────────────────────
lines.append("## ：Pipeline （pipeline/）\n\n")
lines.append(">  De Novo CDR ，。\n")
lines.append(">  `.cursor/rules/pipeline-coord-discipline.mdc` 。\n\n")

lines.append("|  |  | CLI |  |\n")
lines.append("|------|---------|-----|------|\n")

pipeline_dir = ROOT / "pipeline"
if pipeline_dir.exists:
    for f in sorted(pipeline_dir.glob("*.py")):
        if f.name.startswith("__"):
            continue
        desc = PIPELINE_DESCRIPTIONS.get(f.name, get_docstring(f))
        cli = "✓" if has_cli(f) else ""
        lines.append(f"| `pipeline/{f.name}` | {desc} | {cli} | anarcii/affmat |\n")

lines.append("\n---\n\n")

# ── Part 3: scripts/ （_）──────────────────────────────────────
lines.append("## ：（scripts/，）\n\n")
lines.append("|  |  |  | CLI |  |\n")
lines.append("|------|------|---------|-----|------|\n")

scripts_dir = ROOT / "scripts"
if scripts_dir.exists:
    for f in sorted(scripts_dir.glob("*.py")):
        if f.name.startswith("_") or f.name.startswith("__"):
            continue
        cat = classify_script(f.name)
        doc = get_docstring(f)[:70]
        cli = "✓" if has_cli(f) else ""
        env = get_env(f)
        lines.append(f"| `scripts/{f.name}` | {cat} | {doc} | {cli} | {env} |\n")

lines.append("\n---\n\n")

# ── Part 4: scripts/ （_）──────────────────────────────────────
lines.append("## ： / （scripts/_*.py）\n\n")
lines.append("> ⚠️  `_` ，。。\n\n")
lines.append("|  |  |\n")
lines.append("|------|------|\n")

if scripts_dir.exists:
    for f in sorted(scripts_dir.glob("_*.py")):
        if f.name.startswith("__"):
            continue
        doc = get_docstring(f)[:80] or ""
        lines.append(f"| `scripts/{f.name}` | {doc} |\n")

lines.append("\n---\n\n")

# ── Part 5: core/  ───────────────────────────────────────────────────
lines.append("## ：Core （core/）\n\n")
lines.append("|  |  | / |  |\n")
lines.append("|---------|---------|-----------|------|\n")

core_dir = ROOT / "core"
if core_dir.exists:
    for d in sorted(core_dir.iterdir):
        if not d.is_dir or d.name.startswith(("__", ".")):
            continue
        py_files = list(d.rglob("*.py"))
        if not py_files:
            continue
        cat = CORE_MODULE_CATEGORIES.get(d.name, f"core/{d.name} ")
        # Collect public API from __init__.py or main module
        symbols = []
        init = d / "__init__.py"
        main_mod = core_dir / f"{d.name}.py"
        for src in [init, main_mod]:
            if src.exists:
                try:
                    txt = src.read_text(encoding="utf-8", errors="ignore")
                    m = re.search(r"^__all__\s*=\s*\[(.*?)\]", txt, re.DOTALL | re.MULTILINE)
                    if m:
                        found = re.findall(r'"(\w+)"|\'(\w+)\'', m.group(1))
                        symbols = [a or b for a, b in found][:5]
                        break
                    classes = re.findall(r"^class (\w+)", txt, re.MULTILINE)[:3]
                    if classes:
                        symbols = classes
                        break
                except Exception:
                    pass
        sym_str = ", ".join(f"`{s}`" for s in symbols[:4]) if symbols else "—"
        env = "anarcii" if d.name in ("humanization", "numbering", "cmc", "evaluation") else \
              "affmat" if d.name in ("structure", "integrity") else ""
        lines.append(f"| `core/{d.name}/` | {cat} | {sym_str} | {env} |\n")

lines.append("\n---\n\n")

# ── Part 6:  ───────────────────────────────────────────────
lines.append("## ： → \n\n")
lines.append("|  |  |  |\n")
lines.append("|-----------|---------|--------|\n")
lines.append("| ****（ΔΔG） | EvoEF2 + PRODIGY + OpenMM MM/GBSA | ~~EpiScan~~~~AntiFold~~|\n")
lines.append("| ****（ΔTm） | ThermoMPNN | ~~EvoEF2~~（，）|\n")
lines.append("| ** CDR ** | AntiFold | ~~ThermoMPNN~~（， CDR ）|\n")
lines.append("| ** / ** | AbLang+ ESM-IF1 | ~~EvoEF2~~|\n")
lines.append("| ** B ** | EpiScan | ~~MHCflurry~~（MHC-I，T ）~~IEDB~~（T /MHC）|\n")
lines.append("| **T ** / MHC-I  | MHCflurry | ~~EpiScan~~（B ）|\n")
lines.append("| **MHC-II **（CD4 T ） | IEDB API（`core/immunogenicity/iedb_client.py`） | ~~MHCflurry~~（MHC-I only）|\n")
lines.append("| **De Novo CDR ** | ProteinMPNN（`pipeline/run_mpnn_v2.py`） | ~~EvoEF2~~（，）|\n")
lines.append("| **mRNA ** | LinearDesign | ~~ProteinMPNN~~|\n")
lines.append("| **RNA ** | LinearFold | ~~LinearDesign~~|\n")
lines.append("| ****（ PDB ） | IgFold | ~~HADDOCK3~~（，）|\n")
lines.append("| **-** | HADDOCK3（WSL） | ~~IgFold~~|\n")
lines.append("| ****（Kabat/IMGT/Chothia） | ANARCI（anarcii ） | ~~~~|\n")
lines.append("| **CMC ** | `core/evaluation/evaluator.py`（AbEvaluator） | ~~EvoEF2~~（， CMC）|\n")

lines.append("\n---\n\n")
lines.append("_ `_tmp_gen_script_index.py` ，。_\n")

out_path = ROOT / "docs" / "TOOL_SCRIPT_INDEX.md"
out_path.write_text("".join(lines), encoding="utf-8")
print(f"✅ : {out_path} ({out_path.stat.st_size:,} bytes)")
print(f"  - : {len(EXTERNAL_TOOL_USE_CASES)} ")
scripts_count = len(list((ROOT / 'scripts').glob('*.py'))) if (ROOT / 'scripts').exists else 0
print(f"  - scripts/ : {scripts_count} ")
pipeline_count = len(list((ROOT / 'pipeline').glob('*.py'))) if (ROOT / 'pipeline').exists else 0
print(f"  - pipeline/ : {pipeline_count} ")
