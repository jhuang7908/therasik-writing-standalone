"""
Step 6: Generate final affinity maturation delivery report.

Merges all scoring layers (L1 EvoEF2, L2 AbLang, CMC, L3 OpenMM)
into a single ranked table and outputs a Markdown report.

Usage (from repo root, conda activate affmat):
    python scripts/affinity_maturation/generate_report.py
"""

import csv
from datetime import datetime
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG = yaml.safe_load((SCRIPT_DIR / "config.yaml").read_text(encoding="utf-8"))

OUTPUT_DIR = Path((SCRIPT_DIR / CONFIG["paths"]["output_dir"]).resolve())
WT_SEQ = CONFIG["sequence"]["wt"]
OPENMM_CFG = CONFIG["openmm"]


def load_csv(name: str) -> list[dict]:
    path = OUTPUT_DIR / name
    if not path.exists():
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def safe_float(val) -> float | None:
    if val is None or val == "" or val == "None":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def generate():
    print("=" * 60)
    print("Generating Affinity Maturation Report")
    print("=" * 60)

    l1_data = load_csv("evoef2_scan_results.csv")
    l2_data = load_csv("ablang_scores.csv")
    cmc_data = load_csv("cmc_results.csv")
    combo_data = load_csv("combo_results.csv")
    l3_data = load_csv("openmm_results.csv")

    single_map: dict[str, dict] = {}

    for row in l1_data:
        label = row["mutation"]
        single_map.setdefault(label, {"mutation": label, "type": "single"})
        single_map[label]["evoef2_ddg"] = safe_float(row.get("ddg_bind"))
        single_map[label]["evoef2_pass"] = (
            single_map[label]["evoef2_ddg"] is not None
            and single_map[label]["evoef2_ddg"] < CONFIG["gates_l1"]["ddg_bind_threshold"]
        )

    for row in l2_data:
        label = row["mutation"]
        single_map.setdefault(label, {"mutation": label, "type": "single"})
        single_map[label]["ablang_delta"] = safe_float(row.get("ablang_delta"))
        single_map[label]["ablang_pass"] = row.get("ablang_pass") == "True"

    for row in cmc_data:
        label = row["mutation"]
        single_map.setdefault(label, {"mutation": label, "type": "single"})
        single_map[label]["cmc_pi"] = safe_float(row.get("cmc_pI"))
        single_map[label]["cmc_pass"] = row.get("cmc_pass") == "True"
        single_map[label]["cmc_warnings"] = row.get("cmc_warnings", "")

    combo_map: dict[str, dict] = {}
    for row in combo_data:
        label = row["combo"]
        combo_map[label] = {
            "mutation": label, "type": "combo",
            "evoef2_ddg": safe_float(row.get("ddg_bind")),
            "epistasis": safe_float(row.get("epistasis")),
        }

    l3_map: dict[str, dict] = {}
    for row in l3_data:
        label = row["variant"]
        l3_map[label] = {
            "mmgbsa_bind": safe_float(row.get("mmgbsa_bind")),
            "mmgbsa_ddg": safe_float(row.get("mmgbsa_ddg")),
        }

    all_variants = []
    for label, data in single_map.items():
        if label in l3_map:
            data.update(l3_map[label])
        all_variants.append(data)

    for label, data in combo_map.items():
        if label in l3_map:
            data.update(l3_map[label])
        all_variants.append(data)

    def sort_key(v):
        ddg = v.get("evoef2_ddg")
        return ddg if ddg is not None else 999.0

    all_variants.sort(key=sort_key)

    report = _build_markdown(all_variants)
    report_path = OUTPUT_DIR / "AFFINITY_MATURATION_REPORT.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\nReport: {report_path}")

    merged_csv = OUTPUT_DIR / "merged_scores.csv"
    if all_variants:
        all_keys = set()
        for v in all_variants:
            all_keys.update(v.keys())
        fields = sorted(all_keys)
        fields = ["mutation", "type"] + [f for f in fields if f not in ("mutation", "type")]
        with open(merged_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(all_variants)
        print(f"CSV:    {merged_csv}")

    print(f"\n{'=' * 60}")
    return all_variants


def _build_markdown(variants: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    singles = [v for v in variants if v.get("type") == "single"]
    combos = [v for v in variants if v.get("type") == "combo"]

    md = f"""# VGRW_SR_R2 Virtual Affinity Maturation Report

**Project**: {CONFIG['project']['name']}
**Date**: {now}
**Method**: Structure-driven (HADDOCK3 interface), no MPNN CDR redesign
**WT Sequence**: `{WT_SEQ}`

---

## Summary

| Metric | Value |
|--------|-------|
| Candidate sites | {len(CONFIG['mutations'])} |
| Single-point mutants tested | {len(singles)} |
| Combinations tested | {len(combos)} |
| L1 gate (EvoEF2 ΔΔG) | < {CONFIG['gates_l1']['ddg_bind_threshold']} kcal/mol |
| L2 gate (AbLang Δ) | >= {CONFIG['gates_l2']['delta_logp_min']} |

---

## Single-Point Mutants

| Rank | Mutation | EvoEF2 ΔΔG | AbLang Δ | CMC | L3 MM/GBSA ΔΔG | Verdict |
|------|----------|------------|----------|-----|----------------|---------|
"""
    for i, v in enumerate(singles, 1):
        ddg = v.get("evoef2_ddg")
        ddg_s = f"{ddg:+.2f}" if ddg is not None else "—"
        abl = v.get("ablang_delta")
        abl_s = f"{abl:+.4f}" if abl is not None else "—"
        cmc = "PASS" if v.get("cmc_pass") else ("FAIL" if v.get("cmc_pass") is not None else "—")
        mmgbsa = v.get("mmgbsa_ddg")
        mmgbsa_s = f"{mmgbsa:+.1f}" if mmgbsa is not None else "—"
        all_pass = v.get("evoef2_pass") and v.get("ablang_pass", True) and v.get("cmc_pass", True)
        verdict = "**Recommend**" if all_pass else "Filter"
        md += f"| {i} | {v['mutation']} | {ddg_s} | {abl_s} | {cmc} | {mmgbsa_s} | {verdict} |\n"

    if combos:
        md += f"""
---

## Combination Mutants

| Combination | EvoEF2 ΔΔG | Epistasis | L3 MM/GBSA ΔΔG |
|-------------|------------|-----------|----------------|
"""
        for v in combos:
            ddg = v.get("evoef2_ddg")
            ddg_s = f"{ddg:+.2f}" if ddg is not None else "—"
            epi = v.get("epistasis")
            epi_s = f"{epi:+.2f}" if epi is not None else "—"
            mmgbsa = v.get("mmgbsa_ddg")
            mmgbsa_s = f"{mmgbsa:+.1f}" if mmgbsa is not None else "—"
            md += f"| {v['mutation']} | {ddg_s} | {epi_s} | {mmgbsa_s} |\n"

    md += f"""
---

## Methods

1. **L0 — Structural white-list**: 8 hot-spot sites from HADDOCK3 VHH-HER2 interface analysis (BSA 1524 A^2, 21 VHH contact residues)
2. **L1 — EvoEF2 ComputeBinding**: Single-point ΔΔG scan, gate < {CONFIG['gates_l1']['ddg_bind_threshold']} kcal/mol
3. **L2 — AbLang**: Pseudo-log-likelihood nativeness scoring, gate Δ >= {CONFIG['gates_l2']['delta_logp_min']}
4. **CMC Gate**: pI shift < {CONFIG['gates_cmc']['pi_shift_max']}, no new CDR deamidation sites
5. **L3 — OpenMM MM/GBSA**: AMBER ff14SB + OBC2 implicit solvent, {OPENMM_CFG['minimization_steps']} minimization steps

---

## Files

- `evoef2_scan_results.csv` — L1 raw scores
- `ablang_scores.csv` — L2 nativeness scores
- `cmc_results.csv` — CMC developability
- `combo_results.csv` — Combination + epistasis
- `openmm_results.csv` — L3 MM/GBSA
- `merged_scores.csv` — All layers merged
"""
    return md


if __name__ == "__main__":
    generate()
