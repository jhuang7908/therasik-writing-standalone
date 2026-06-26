"""
Compare 7D12-SR (4KRL; recomputed SR sequence) to the 19 *clinical* VHH molecules (Slice-3),
grouped by their *observed clinical humanization strategy* (SR / BM / Native).

User intent:
  - Do NOT compare 7D12 to SR subset percentiles only.
  - Compare 7D12-SR immunogenicity + CMC/developability metrics to the 19 clinical molecules
    (native sequences), stratified by strategy group.

Inputs:
  - output/7D12/7d12_4krl_eval_table.csv (produced by scripts/evaluate_7d12_4krl_variants.py)
  - reports/slice3_vhh_immunogenicity_features.csv (native rows = clinical molecules)
  - reports/slice3_vhh_developability_features_native_sr_bm.csv (native rows = clinical molecules)
  - reports/slice3_vhh_comprehensive_functional_library.csv (clinical strategy labels)

Outputs:
  - output/7D12/7d12_sr_vs_slice3_clinical_by_strategy.csv
  - output/7D12/7d12_sr_vs_slice3_clinical_by_strategy.md
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "output" / "7D12"
OUT_DIR.mkdir(parents=True, exist_ok=True)

EVAL_7D12 = OUT_DIR / "7d12_4krl_eval_table.csv"

SLICE3_IMM = PROJECT_ROOT / "reports" / "slice3_vhh_immunogenicity_features.csv"
SLICE3_DEV = PROJECT_ROOT / "reports" / "slice3_vhh_developability_features_native_sr_bm.csv"
SLICE3_META = PROJECT_ROOT / "reports" / "slice3_vhh_comprehensive_functional_library.csv"

OUT_CSV = OUT_DIR / "7d12_sr_vs_slice3_clinical_by_strategy.csv"
OUT_MD = OUT_DIR / "7d12_sr_vs_slice3_clinical_by_strategy.md"


def norm_strategy(s: str) -> str:
    s = (s or "").strip()
    if s.startswith("SR"):
        return "SR"
    if s.startswith("BM"):
        return "BM"
    if s.startswith("Native"):
        return "Native"
    return "Unknown"


def summarize(series: pd.Series) -> dict[str, float]:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return {
            "n": 0.0,
            "min": np.nan,
            "p25": np.nan,
            "median": np.nan,
            "p75": np.nan,
            "max": np.nan,
            "mean": np.nan,
        }
    return {
        "n": float(len(s)),
        "min": float(s.min()),
        "p25": float(s.quantile(0.25)),
        "median": float(s.median()),
        "p75": float(s.quantile(0.75)),
        "max": float(s.max()),
        "mean": float(s.mean()),
    }


def main() -> None:
    missing = [p for p in (EVAL_7D12, SLICE3_IMM, SLICE3_DEV, SLICE3_META) if not p.exists()]
    if missing:
        raise RuntimeError("Missing required inputs:\n" + "\n".join(f"- {p}" for p in missing))

    # 1) 7D12-SR row (recomputed)
    df_7 = pd.read_csv(EVAL_7D12)
    if "variant" not in df_7.columns:
        raise RuntimeError(f"Unexpected 7D12 eval table columns: {df_7.columns.tolist()}")
    r7 = df_7[df_7["variant"] == "sr"]
    if r7.empty:
        raise RuntimeError("7D12 SR row not found in eval table. Re-run evaluate_7d12_4krl_variants.py")
    r7 = r7.iloc[0].to_dict()
    # 7D12 eval table column name differences vs slice-3 developability table:
    # - slice-3: score, iso_count, hp_max9, cp_max7
    # - 7D12:  dev_score, isoasp_count, hydro_patch_max9, charge_patch_max7
    r7_mapped = dict(r7)
    if "dev_score" in r7_mapped and "score" not in r7_mapped:
        r7_mapped["score"] = r7_mapped["dev_score"]
    if "isoasp_count" in r7_mapped and "iso_count" not in r7_mapped:
        r7_mapped["iso_count"] = r7_mapped["isoasp_count"]
    if "hydro_patch_max9" in r7_mapped and "hp_max9" not in r7_mapped:
        r7_mapped["hp_max9"] = r7_mapped["hydro_patch_max9"]
    if "charge_patch_max7" in r7_mapped and "cp_max7" not in r7_mapped:
        r7_mapped["cp_max7"] = r7_mapped["charge_patch_max7"]

    # 2) Clinical Slice-3 molecules = native rows only, then attach clinical strategy group
    meta = pd.read_csv(SLICE3_META).rename(
        columns={"Drug Name": "antibody_id", "Humanization Strategy": "strategy"}
    )
    meta["strategy_group"] = meta["strategy"].astype(str).map(norm_strategy)

    imm = pd.read_csv(SLICE3_IMM)
    dev = pd.read_csv(SLICE3_DEV)

    imm_c = imm[imm["variant"] == "native"].merge(
        meta[["antibody_id", "strategy", "strategy_group"]], on="antibody_id", how="left"
    )
    dev_c = dev[dev["variant"] == "native"].merge(
        meta[["antibody_id", "strategy", "strategy_group"]], on="antibody_id", how="left"
    )

    # Metrics we compare
    imm_metrics = ["B_total_1pct", "B_total_2pct", "B_breadth_1pct", "B_breadth_2pct", "min_rank"]
    dev_metrics = ["score", "ngly_count", "deamid_count", "iso_count", "ox_m_count", "ox_w_count", "extra_cys_flag", "net_charge", "hydrophobic_frac_global", "hp_max9", "cp_max7"]

    # 3) Group summaries
    rows = []
    for g in ["SR", "BM", "Native"]:
        imm_g = imm_c[imm_c["strategy_group"] == g]
        dev_g = dev_c[dev_c["strategy_group"] == g]

        for m in imm_metrics:
            if m not in imm_g.columns:
                continue
            s = summarize(imm_g[m])
            rows.append({"group": g, "domain": "immuno", "metric": m, **s, "7d12_sr_value": float(r7.get(m, np.nan))})

        for m in dev_metrics:
            if m not in dev_g.columns:
                continue
            s = summarize(dev_g[m])
            v7 = float(r7_mapped.get(m, np.nan))
            rows.append({"group": g, "domain": "developability", "metric": m, **s, "7d12_sr_value": v7})

    df_out = pd.DataFrame(rows)
    df_out.to_csv(OUT_CSV, index=False)

    # 4) Render a compact markdown report (no percentile claims; just distributions + value)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("# 7D12-SR vs 19 Clinical VHHs (Slice-3), stratified by clinical strategy\n\n")
        f.write("## Inputs\n")
        f.write(f"- 7D12 eval: `{EVAL_7D12}` (SR row)\n")
        f.write(f"- Slice-3 immunogenicity: `{SLICE3_IMM}` (native rows only)\n")
        f.write(f"- Slice-3 developability: `{SLICE3_DEV}` (native rows only)\n")
        f.write(f"- Clinical strategy labels: `{SLICE3_META}`\n\n")

        f.write("## 7D12-SR key values (recomputed)\n\n")
        f.write(
            f"- Immuno: B_total_1pct={int(r7['B_total_1pct'])}, B_total_2pct={int(r7['B_total_2pct'])}, "
            f"B_breadth_1pct={int(r7['B_breadth_1pct'])}, min_rank={float(r7['min_rank']):.3g}\n"
        )
        f.write(f"- Developability: dev_score={int(r7['dev_score'])}, dev_risk_tier={r7['dev_risk_tier']}\n\n")

        f.write("## Grouped clinical distributions (min / P25 / median / P75 / max / mean) with 7D12-SR value\n\n")
        # Keep columns stable & readable
        show_cols = ["group", "domain", "metric", "n", "min", "p25", "median", "p75", "max", "mean", "7d12_sr_value"]
        f.write(df_out[show_cols].to_markdown(index=False) + "\n")

        f.write("\n## Interpretation guide (for \"developability\" and \"safety\" preview)\n\n")
        f.write("- Lower is better: `B_total_1pct`, `B_total_2pct`, `B_breadth_*`, `ngly_count`, `extra_cys_flag`, `hp_max9` (hydrophobic patch), `cp_max7` (charge patch magnitude)\n")
        f.write("- Higher is better: `score` (Slice-3 dev score; compare to 7D12 `dev_score`)\n")
        f.write("- This is an **in silico** comparison; clinical ADA/CMC outcomes require experimental validation.\n")

    print(f"Wrote: {OUT_CSV}")
    print(f"Wrote: {OUT_MD}")


if __name__ == "__main__":
    main()

