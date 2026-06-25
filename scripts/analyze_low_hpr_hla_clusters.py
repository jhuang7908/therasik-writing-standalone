#!/usr/bin/env python3
"""Overlay local HPR regions with HLA-II risk peptide clusters in ADA records.

This is an internal analysis script. It uses:
- HPR local score: fraction of human-OAS-covered 9-mers inside each 15-mer.
- HLA-II risk: `core.immunogenicity.mhcii_analyzer.MHCII_Analyzer`.
- Positional clusters: overlapping HIGH/MEDIUM 15-mers on the same chain.

Default HLA-II mode is offline heuristic (`use_iedb=False`) to keep the run
reproducible and avoid live API dependency. The output should be treated as a
screening analysis, not a clinical immunogenicity conclusion.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from core.humanization.hpr_index import _hpr_db  # noqa: E402
from core.immunogenicity.mhcii_analyzer import MHCII_Analyzer  # noqa: E402


BAD_VALUES = {"", "nan", "none", "true", "false", "0", "115"}
RISK_LEVELS = {"HIGH", "MEDIUM"}


def is_real_seq(value: object) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    return len(text) > 10 and text.lower() not in BAD_VALUES


def clean_sequence(seq: object, chain: str) -> str:
    if not is_real_seq(seq):
        return ""
    text = re.sub(r"[^A-Za-z]", "", str(seq)).upper()
    if chain == "H":
        for motif in ("ASTKGPSVF", "TVSSASTK", "RTVAAPSVF"):
            idx = text.find(motif)
            if idx > 90:
                return text[:idx]
    else:
        for motif in ("RTVAAPSVF", "TVAAPSVF", "FGQGTKVEIKRTV"):
            idx = text.find(motif)
            if idx > 85:
                return text[:idx]
    return text


def local_hpr_15mer(peptide: str, db: object) -> float:
    if len(peptide) < 9:
        return np.nan
    total = len(peptide) - 8
    found = sum(1 for i in range(total) if db.contains(peptide[i : i + 9]))
    return round(found / total, 4)


def make_positional_clusters(epitopes: Iterable[dict]) -> list[dict]:
    rows = sorted(epitopes, key=lambda e: (e["chain"], int(e["start"])))
    clusters: list[dict] = []
    current: dict | None = None
    for ep in rows:
        start = int(ep["start"])
        end = int(ep["start"]) + len(ep["peptide"]) - 1
        if current is None or ep["chain"] != current["chain"] or start > current["end"] + 1:
            if current is not None:
                clusters.append(current)
            current = {
                "chain": ep["chain"],
                "start": start,
                "end": end,
                "n_peptides": 1,
                "best_rank": float(ep["best_rank"]),
                "max_strong": int(ep["n_strong"]),
                "max_alleles_hit": int(ep["n_alleles_hit"]),
                "risk_levels": {ep["risk"]},
                "top_peptide": ep["peptide"],
            }
        else:
            current["end"] = max(int(current["end"]), end)
            current["n_peptides"] += 1
            current["risk_levels"].add(ep["risk"])
            if float(ep["best_rank"]) < float(current["best_rank"]):
                current["best_rank"] = float(ep["best_rank"])
                current["top_peptide"] = ep["peptide"]
            current["max_strong"] = max(int(current["max_strong"]), int(ep["n_strong"]))
            current["max_alleles_hit"] = max(int(current["max_alleles_hit"]), int(ep["n_alleles_hit"]))
    if current is not None:
        clusters.append(current)

    for cl in clusters:
        cl["risk_levels"] = ",".join(sorted(cl["risk_levels"]))
        cl["start_1based"] = int(cl.pop("start")) + 1
        cl["end_1based"] = int(cl.pop("end")) + 1
    return clusters


def corr(x: pd.Series, y: pd.Series) -> dict[str, float | int | None]:
    valid = x.notna() & y.notna()
    x = x[valid].astype(float)
    y = y[valid].astype(float)
    if len(x) < 3 or x.nunique() < 2 or y.nunique() < 2:
        return {"n": int(len(x)), "spearman_rho": None, "spearman_p": None}
    res = stats.spearmanr(x, y)
    return {"n": int(len(x)), "spearman_rho": round(float(res.statistic), 4), "spearman_p": round(float(res.pvalue), 6)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv",
        default="data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv",
    )
    parser.add_argument(
        "--out-dir",
        default="data/immunogenicity_knowledge_base/reports/hpr_hla_cluster_analysis",
    )
    parser.add_argument("--iedb", action="store_true", help="Use live IEDB if configured; default is offline heuristic.")
    args = parser.parse_args()

    csv_path = (REPO / args.csv).resolve()
    out_dir = (REPO / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(csv_path)
    numeric = df[["vh_seq", "vl_seq"]].notna().any(axis=1) & df["ada_first_pct"].notna()
    data = df[numeric & df["hpr_combined_score"].notna()].copy()

    db = _hpr_db()

    # Derive cohort thresholds from all 15-mers in the 221-record analysis set.
    local_scores: list[float] = []
    for _, row in data.iterrows():
        for seq, chain in [(clean_sequence(row.get("vh_seq"), "H"), "H"), (clean_sequence(row.get("vl_seq"), "L"), "L")]:
            if not seq:
                continue
            for i in range(len(seq) - 14):
                local_scores.append(local_hpr_15mer(seq[i : i + 15], db))
    q25 = round(float(np.quantile(local_scores, 0.25)), 4)
    q75 = round(float(np.quantile(local_scores, 0.75)), 4)

    per_record: list[dict] = []
    cluster_rows: list[dict] = []
    peptide_rows: list[dict] = []

    for n, (_, row) in enumerate(data.iterrows(), start=1):
        name = str(row["antibody_name"])
        vh = clean_sequence(row.get("vh_seq"), "H")
        vl = clean_sequence(row.get("vl_seq"), "L")
        analyzer = MHCII_Analyzer(vh_seq=vh, vl_seq=vl, use_iedb=bool(args.iedb), n_clusters=5)
        result = analyzer.run(is_vhh=(bool(vh) and not bool(vl)))

        low_all: list[dict] = []
        high_all: list[dict] = []
        low_funnel: list[dict] = []
        high_funnel: list[dict] = []
        n_low_windows = 0
        n_high_windows = 0

        # Count all local-HPR windows, including non-binders.
        for seq, chain in [(vh, "VH"), (vl, "VL")]:
            if not seq:
                continue
            for i in range(len(seq) - 14):
                score = local_hpr_15mer(seq[i : i + 15], db)
                if score <= q25:
                    n_low_windows += 1
                if score >= q75:
                    n_high_windows += 1

        for ep in result.all_epitopes:
            score = local_hpr_15mer(ep.peptide, db)
            hpr_bin = "low" if score <= q25 else ("high" if score >= q75 else "mid")
            epd = {
                "antibody_name": name,
                "chain": ep.chain,
                "start": int(ep.start),
                "start_1based": int(ep.start) + 1,
                "peptide": ep.peptide,
                "region": ep.region,
                "risk": ep.risk,
                "n_alleles_hit": int(ep.n_alleles_hit),
                "n_strong": int(ep.n_strong),
                "best_rank": float(ep.best_rank),
                "best_allele": ep.best_allele,
                "hydrophilicity": round(float(ep.hydrophilicity), 4),
                "is_germline": bool(ep.is_germline),
                "local_hpr_15mer": score,
                "local_hpr_bin": hpr_bin,
            }
            peptide_rows.append(epd)
            if ep.risk in RISK_LEVELS:
                if hpr_bin == "low":
                    low_all.append(epd)
                elif hpr_bin == "high":
                    high_all.append(epd)
                if "FR" in ep.region and ep.hydrophilicity > -0.5 and not ep.is_germline:
                    if hpr_bin == "low":
                        low_funnel.append(epd)
                    elif hpr_bin == "high":
                        high_funnel.append(epd)

        low_all_clusters = make_positional_clusters(low_all)
        high_all_clusters = make_positional_clusters(high_all)
        low_funnel_clusters = make_positional_clusters(low_funnel)
        high_funnel_clusters = make_positional_clusters(high_funnel)

        for scope, clusters in [
            ("low_hpr_all_region", low_all_clusters),
            ("high_hpr_all_region", high_all_clusters),
            ("low_hpr_fr_surface_non_germline", low_funnel_clusters),
            ("high_hpr_fr_surface_non_germline", high_funnel_clusters),
        ]:
            for cid, cl in enumerate(clusters, start=1):
                cluster_rows.append({"antibody_name": name, "scope": scope, "cluster_id": cid, **cl})

        per_record.append(
            {
                "antibody_name": name,
                "ada_first_pct": float(row["ada_first_pct"]),
                "hpr_combined_score": float(row["hpr_combined_score"]),
                "hpr_chain_mode": row.get("hpr_chain_mode"),
                "source_class": row.get("source_class"),
                "mhcii_method": result.method,
                "tcia_score": result.tcia_score,
                "mhcii_risk_level": result.risk_level,
                "n_low_hpr_15mer_windows": n_low_windows,
                "n_high_hpr_15mer_windows": n_high_windows,
                "low_hpr_hla_risk_peptides_all_region": len(low_all),
                "high_hpr_hla_risk_peptides_all_region": len(high_all),
                "low_hpr_hla_clusters_all_region": len(low_all_clusters),
                "high_hpr_hla_clusters_all_region": len(high_all_clusters),
                "low_hpr_hla_risk_peptides_fr_surface": len(low_funnel),
                "high_hpr_hla_risk_peptides_fr_surface": len(high_funnel),
                "low_hpr_hla_clusters_fr_surface": len(low_funnel_clusters),
                "high_hpr_hla_clusters_fr_surface": len(high_funnel_clusters),
            }
        )

        if n % 25 == 0 or n == len(data):
            print(f"Analyzed {n}/{len(data)}")

    per_df = pd.DataFrame(per_record)
    cluster_df = pd.DataFrame(cluster_rows)
    peptide_df = pd.DataFrame(peptide_rows)

    summary = {
        "n_records": int(len(per_df)),
        "hpr_local_q25_threshold": q25,
        "hpr_local_q75_threshold": q75,
        "mhcii_method": "iedb_online_if_available" if args.iedb else "offline_heuristic",
        "low_hpr_windows_total": int(per_df["n_low_hpr_15mer_windows"].sum()),
        "high_hpr_windows_total": int(per_df["n_high_hpr_15mer_windows"].sum()),
        "low_hpr_hla_clusters_all_region_total": int(per_df["low_hpr_hla_clusters_all_region"].sum()),
        "high_hpr_hla_clusters_all_region_total": int(per_df["high_hpr_hla_clusters_all_region"].sum()),
        "low_hpr_hla_clusters_fr_surface_total": int(per_df["low_hpr_hla_clusters_fr_surface"].sum()),
        "high_hpr_hla_clusters_fr_surface_total": int(per_df["high_hpr_hla_clusters_fr_surface"].sum()),
        "low_hpr_cluster_rate_per_100_windows_all_region": round(
            float(per_df["low_hpr_hla_clusters_all_region"].sum()) / max(1, per_df["n_low_hpr_15mer_windows"].sum()) * 100, 4
        ),
        "high_hpr_cluster_rate_per_100_windows_all_region": round(
            float(per_df["high_hpr_hla_clusters_all_region"].sum()) / max(1, per_df["n_high_hpr_15mer_windows"].sum()) * 100, 4
        ),
        "low_hpr_cluster_rate_per_100_windows_fr_surface": round(
            float(per_df["low_hpr_hla_clusters_fr_surface"].sum()) / max(1, per_df["n_low_hpr_15mer_windows"].sum()) * 100, 4
        ),
        "high_hpr_cluster_rate_per_100_windows_fr_surface": round(
            float(per_df["high_hpr_hla_clusters_fr_surface"].sum()) / max(1, per_df["n_high_hpr_15mer_windows"].sum()) * 100, 4
        ),
        "spearman_low_hpr_clusters_all_region_vs_ada": corr(per_df["low_hpr_hla_clusters_all_region"], per_df["ada_first_pct"]),
        "spearman_low_hpr_clusters_fr_surface_vs_ada": corr(per_df["low_hpr_hla_clusters_fr_surface"], per_df["ada_first_pct"]),
        "spearman_low_hpr_clusters_all_region_vs_hpr": corr(per_df["low_hpr_hla_clusters_all_region"], per_df["hpr_combined_score"]),
    }

    per_path = out_dir / "per_record_low_hpr_hla_cluster_counts.csv"
    cluster_path = out_dir / "low_hpr_hla_clusters_detail.csv"
    peptide_path = out_dir / "hla_peptides_with_local_hpr_bins.csv"
    summary_path = out_dir / "low_hpr_hla_cluster_summary.json"

    per_df.to_csv(per_path, index=False)
    cluster_df.to_csv(cluster_path, index=False)
    peptide_df.to_csv(peptide_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(f"Saved: {per_path}")
    print(f"Saved: {cluster_path}")
    print(f"Saved: {peptide_path}")
    print(f"Saved: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
