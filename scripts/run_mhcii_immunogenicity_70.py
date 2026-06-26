"""
scripts/run_mhcii_immunogenicity_70.py
──────────────────────────────────────
Batch MHC-II T-cell immunogenicity scan for 70 therapeutic antibodies.

Four-layer pipeline per antibody
---------------------------------
  1. Strong antigen detection  – IEDB netMHCIIpan-4.1, DRB1-35 panel, rank ≤ 2.0 %
  2. CDR/FR localization       – ABARCII IMGT
  3. Germline tolerance filter – sigmoid(f_max), full IMGT human V-gene FASTA
     Net immunogenic burden    – Σ allele_weight × (1 − tolerance)
  4. Spatial clustering        – ≥ 3 non-tolerant peptides / 15 aa window

Surface exposure
-----------------
  Primary: freesasa on data/structures/natural/{Name}.pdb  (chain H = VH, chain L = VL)
  Fallback: Parker hydrophilicity scale (sequence-based)

Output
------
  data/thera_sabdab/out/mhcii_immuno_70_summary.csv   – one row per antibody
  data/thera_sabdab/out/mhcii_immuno_70_epitopes.csv  – all strong binder peptides
  data/thera_sabdab/out/mhcii_immuno_70_report.html   – interactive HTML report

Usage
-----
  conda activate anarcii
  python scripts/run_mhcii_immunogenicity_70.py [--panel drb1_35] [--offline]
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

# ── project root on sys.path ──────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.immunogenicity.mhcii_analyzer import MHCII_Analyzer
from core.immunogenicity.surface_immuno import SurfaceImmunogenicity
from core.immunogenicity.ada_risk_scorer import ADAScorer

# ── paths ─────────────────────────────────────────────────────────────────────
SEQ_CSV   = ROOT / "data" / "thera_sabdab" / "out" / "confirmed70_sequences_full.csv"
PDB_DIR   = ROOT / "data" / "structures" / "natural"
OUT_DIR   = ROOT / "data" / "thera_sabdab" / "out"
SUM_CSV   = OUT_DIR / "mhcii_immuno_70_summary.csv"
EPI_CSV   = OUT_DIR / "mhcii_immuno_70_epitopes.csv"
HTML_OUT  = OUT_DIR / "mhcii_immuno_70_report.html"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pick_vh_vl(row: pd.Series):
    vh = str(row.get("arm1_heavy_aa", "") or "").strip()
    vl = str(row.get("arm1_light_aa", "") or "").strip()
    if not vh:
        vh = str(row.get("vhh1_aa", "") or "").strip()
    return vh, vl


def _pdb_path(name: str) -> str | None:
    p = PDB_DIR / f"{name}.pdb"
    return str(p) if p.exists() else None


def _risk_colour(risk: str) -> str:
    return {"HIGH": "#d32f2f", "MEDIUM": "#f57c00", "LOW": "#388e3c"}.get(risk, "#757575")


def _fmt(v, digits: int = 4) -> str:
    try:
        return f"{float(v):.{digits}f}"
    except (TypeError, ValueError):
        return str(v) if v is not None else "—"


# ─────────────────────────────────────────────────────────────────────────────
# HTML builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_html(summary_df: pd.DataFrame, epi_df: pd.DataFrame) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    rows_html = ""
    for _, r in summary_df.iterrows():
        clin   = str(r.get("clinical_ada_risk", "—"))
        risk   = str(r.get("mhcii_risk", "—"))
        surf   = str(r.get("surface_risk", "—"))
        cscore = r.get("clinical_ada_score")
        ccol   = _risk_colour(clin)
        col    = _risk_colour(risk)
        scol   = _risk_colour(surf)
        pdb_icon = "✓" if r.get("pdb_used") else "—"
        score_bar = ""
        if cscore is not None:
            pct = min(int(float(cscore) * 100), 100)
            bar_col = _risk_colour(clin)
            score_bar = (f'<div style="width:{pct}px;height:8px;'
                         f'background:{bar_col};border-radius:4px;display:inline-block"></div>'
                         f' {_fmt(cscore, 3)}')
        rows_html += f"""
        <tr>
          <td>{r['antibody']}</td>
          <td style="color:{ccol};font-weight:700;background:#fff3e0">{clin}</td>
          <td>{score_bar}</td>
          <td style="color:{col}">{risk}</td>
          <td>{r.get('n_strong_binders','—')}</td>
          <td>{r.get('n_clusters','—')}</td>
          <td>{_fmt(r.get('raw_immunogenic_burden'), 4)}</td>
          <td><strong>{_fmt(r.get('net_immunogenic_burden'), 4)}</strong></td>
          <td style="color:{scol};font-weight:700">{surf}</td>
          <td>{r.get('n_hydrophilic_patches','—')}</td>
          <td>{_fmt(r.get('frac_exposed_vh'), 3)}</td>
          <td>{_fmt(r.get('frac_exposed_vl'), 3)}</td>
          <td style="color:#388e3c">{pdb_icon}</td>
          <td style="font-size:11px">{r.get('flags','')}</td>
        </tr>"""

    epi_rows = ""
    if not epi_df.empty:
        top = epi_df.nsmallest(60, "percentile_rank")
        for _, e in top.iterrows():
            tol = float(e.get("tolerance", 0) or 0)
            tol_label = "Tolerant" if tol >= 0.9 else "Partial" if tol >= 0.5 else "Foreign"
            tol_col   = {"Tolerant": "#388e3c", "Partial": "#f57c00", "Foreign": "#d32f2f"}[tol_label]
            epi_rows += f"""
        <tr>
          <td>{e.get('antibody','')}</td>
          <td>{e.get('chain','')}</td>
          <td style="font-family:monospace">{e.get('peptide','')}</td>
          <td style="font-family:monospace">{e.get('core9','')}</td>
          <td>{e.get('allele','')}</td>
          <td>{_fmt(e.get('percentile_rank'), 2)}</td>
          <td>{e.get('region','')}</td>
          <td style="color:{tol_col};font-weight:700">{tol_label} ({_fmt(tol, 2)})</td>
          <td>{_fmt(e.get('net_contribution'), 4)}</td>
        </tr>"""

    rc = summary_df.get("clinical_ada_risk", pd.Series()).value_counts().to_dict() if not summary_df.empty else {}
    h = rc.get("HIGH", 0); m = rc.get("MEDIUM", 0); l = rc.get("LOW", 0)
    total = len(summary_df)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>MHC-II Immunogenicity Report – 70 Therapeutic Antibodies</title>
<style>
  body  {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          margin: 32px; background: #fafafa; color: #212121; }}
  h1    {{ color: #1a237e; border-bottom: 2px solid #3f51b5; padding-bottom: 8px; }}
  h2    {{ color: #283593; margin-top: 32px; }}
  .meta {{ color: #757575; font-size: 13px; margin-top: -8px; margin-bottom: 24px; }}
  .card {{ background: #fff; border-radius: 8px; padding: 20px 24px;
           box-shadow: 0 1px 4px rgba(0,0,0,.15); margin-bottom: 24px; }}
  .kpi-row {{ display:flex; gap:20px; flex-wrap:wrap; margin-bottom:24px; }}
  .kpi  {{ background:#fff; border-radius:8px; padding:16px 20px;
           box-shadow:0 1px 4px rgba(0,0,0,.12); text-align:center; min-width:110px; }}
  .kpi .val {{ font-size:30px; font-weight:700; }}
  .kpi .lbl {{ font-size:12px; color:#757575; margin-top:4px; }}
  table {{ border-collapse:collapse; width:100%; font-size:12px; }}
  th    {{ background:#3f51b5; color:#fff; padding:8px 10px; text-align:left; }}
  td    {{ padding:5px 10px; border-bottom:1px solid #e0e0e0; }}
  tr:hover {{ background:#f5f5f5; }}
  .info-box {{ background:#e8eaf6; border-left:4px solid #3f51b5;
               padding:12px 16px; border-radius:4px; margin-bottom:20px; font-size:13px; }}
</style>
</head>
<body>
<h1>MHC-II Immunogenicity Scan — 70 Therapeutic Antibodies</h1>
<p class="meta">Generated: {ts} &nbsp;|&nbsp; Panel: DRB1-35 (36 alleles) &nbsp;|&nbsp;
Method: IEDB netMHCIIpan-4.1 (rank ≤ 2.0 %) &nbsp;|&nbsp; Surface: freesasa / Parker fallback</p>

<div class="info-box">
  <strong>Pipeline (4 layers + surface):</strong><br>
  (1) Strong antigen – IEDB netMHCIIpan-4.1, 15-mer, rank ≤ 2.0 %
  → (2) CDR/FR – ABARCII IMGT
  → (3) Germline tolerance – IMGT human IGHV/IGKV/IGLV FASTA; sigmoid(f_max, k=100, θ=0.005);
  <em>net_burden = Σ allele_weight × (1 − tolerance)</em>
  → (4) Spatial clusters – ≥ 3 non-tolerant peptides / 15 aa window
  + Surface exposure – freesasa chain H/L SASA &gt; 20 Å² (Parker if no PDB)<br>
  <strong>Clinical ADA Risk</strong> = MHC-II Risk amplified by Surface Risk (Aggregation-driven uptake)
</div>

<div class="kpi-row">
  <div class="kpi"><div class="val" style="color:#1a237e">{total}</div><div class="lbl">Antibodies</div></div>
  <div class="kpi"><div class="val" style="color:#d32f2f">{h}</div><div class="lbl">HIGH risk</div></div>
  <div class="kpi"><div class="val" style="color:#f57c00">{m}</div><div class="lbl">MEDIUM risk</div></div>
  <div class="kpi"><div class="val" style="color:#388e3c">{l}</div><div class="lbl">LOW risk</div></div>
</div>

<div class="card">
<h2>Per-Antibody Summary</h2>
<table>
<thead><tr>
  <th>Antibody</th><th>Clinical ADA Risk</th><th>ADA Score [0-1]</th><th>MHC-II Risk</th><th># Strong Binders</th><th># Clusters</th>
  <th>Raw Burden</th><th>Net Burden</th>
  <th>Surface Risk</th><th># Patches</th>
  <th>Frac Exp VH</th><th>Frac Exp VL</th>
  <th>PDB</th><th>Flags</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>
</div>

<div class="card">
<h2>Top 60 Strong Binder Epitopes (by percentile rank)</h2>
<table>
<thead><tr>
  <th>Antibody</th><th>Chain</th><th>15-mer Peptide</th><th>9-mer Core</th>
  <th>HLA Allele</th><th>Rank %</th><th>Region</th>
  <th>Tolerance (sigmoid)</th><th>Net Contribution</th>
</tr></thead>
<tbody>{epi_rows}</tbody>
</table>
</div>

</body>
</html>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Batch MHC-II immunogenicity scan for 70 therapeutic antibodies"
    )
    parser.add_argument("--panel", default="drb1_35")
    parser.add_argument("--rank-strong", type=float, default=2.0,
                        help="Percentile rank threshold for strong binder (default 2.0)")
    parser.add_argument("--offline", action="store_true",
                        help="Skip IEDB API (surface SASA only, for testing)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Process only first N antibodies")
    parser.add_argument("--resume", action="store_true",
                        help="Skip antibodies already in the summary CSV (incremental restart)")
    parser.add_argument("--poll-max", type=int, default=90,
                        help="Max IEDB polls before timeout (default 90 = 7.5 min)")
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Comma-separated antibody names to re-run only; merges into existing summary/epitopes",
    )
    args = parser.parse_args()

    print(f"\n{'='*64}")
    print("  InSynBio MHC-II Immunogenicity Scan — 70 Antibodies")
    print(f"  Panel   : {args.panel}  |  rank ≤ {args.rank_strong} %")
    print(f"  Mode    : {'OFFLINE (SASA + Parker only)' if args.offline else 'ONLINE (IEDB API)'}")
    print(f"{'='*64}\n")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not SEQ_CSV.exists():
        print(f"[ERROR] Sequence file not found: {SEQ_CSV}")
        sys.exit(1)

    df_seqs = pd.read_csv(SEQ_CSV)
    if args.limit:
        df_seqs = df_seqs.head(args.limit)

    only_set: set = set()
    if args.only:
        raw = [x.strip() for x in args.only.split(",") if x.strip()]
        canon = {str(r["antibody_name"]).lower(): str(r["antibody_name"]) for _, r in df_seqs.iterrows()}
        resolved: list[str] = []
        for n in raw:
            key = n.lower()
            if key in canon:
                resolved.append(canon[key])
            else:
                print(f"[WARN] Unknown antibody name (not in sequence CSV): {n!r}")
        only_set = set(resolved)
        df_seqs = df_seqs[df_seqs["antibody_name"].isin(resolved)].copy()
        ord_map = {name: i for i, name in enumerate(resolved)}
        df_seqs["_ord"] = df_seqs["antibody_name"].map(lambda x: ord_map[str(x)])
        df_seqs = df_seqs.sort_values("_ord").drop(columns="_ord")

    total = len(df_seqs)
    print(f"Loaded {total} antibodies\n")

    scorer = ADAScorer()
    print(scorer.params_summary())
    print()

    # ── Resume: load already-completed rows ───────────────────────────────────
    already_done: set = set()
    summary_rows = []
    epitope_rows = []
    if args.only and SUM_CSV.exists():
        prev = pd.read_csv(SUM_CSV, comment="#")
        summary_rows = [r for r in prev.to_dict("records") if r["antibody"] not in only_set]
        if EPI_CSV.exists():
            eprev = pd.read_csv(EPI_CSV)
            epitope_rows = [r for r in eprev.to_dict("records") if r["antibody"] not in only_set]
        print(f"  --only: re-running {len(only_set)} antibodies, keeping {len(summary_rows)} others\n")
    elif args.resume and SUM_CSV.exists():
        prev = pd.read_csv(SUM_CSV, comment="#")
        already_done = set(prev["antibody"].tolist())
        summary_rows = prev.to_dict("records")
        if EPI_CSV.exists():
            epitope_rows = pd.read_csv(EPI_CSV).to_dict("records")
        print(f"  --resume: loaded {len(already_done)} completed rows from {SUM_CSV.name}")
        print(f"  Skipping: {sorted(already_done)}\n")

    # ── Apply --poll-max override ─────────────────────────────────────────────
    import core.immunogenicity.mhcii_analyzer as _mhcii_mod
    _mhcii_mod.IEDB_POLL_MAX = args.poll_max

    for ni, (_, row) in enumerate(df_seqs.iterrows(), start=1):
        name = str(row["antibody_name"])
        vh, vl = _pick_vh_vl(row)
        pdb    = _pdb_path(name)

        if name in already_done:
            print(f"[{ni:2d}/{total}] {name:30s}  SKIP (already done)")
            continue

        if not vh:
            print(f"[{ni:2d}/{total}] {name:30s}  SKIP (no VH)")
            summary_rows.append({
                "antibody": name,
                "clinical_ada_score": None,
                "clinical_ada_risk": "SKIPPED", "mhcii_risk": "SKIPPED", "surface_risk": "SKIPPED",
                "n_strong_binders": 0, "n_clusters": 0,
                "raw_immunogenic_burden": 0.0, "net_immunogenic_burden": 0.0,
                "n_hydrophilic_patches": 0, "flags": "no_vh_sequence",
                "pdb_used": bool(pdb),
            })
            continue

        t0 = time.time()

        # ── MHC-II scan ──────────────────────────────────────────────────────
        mhc = MHCII_Analyzer(
            vh_seq=vh, vl_seq=vl, panel=args.panel,
            rank_strong=args.rank_strong, use_iedb=(not args.offline),
        ).run()

        # ── Surface exposure (primary: freesasa from PDB) ─────────────────
        surf = SurfaceImmunogenicity(
            pdb_path=pdb, vh_seq=vh, vl_seq=vl,
        ).run()

        # ── Clinical ADA score (composite, replaces step-function cascade) ─
        ada_scored = scorer.score(mhc, surf)

        elapsed = time.time() - t0

        # ── Epitope rows ──────────────────────────────────────────────────
        for ep in mhc.get("strong_binders", []):
            epitope_rows.append({
                "antibody": name,
                "chain": ep.get("chain"),
                "peptide": ep.get("peptide"),
                "core9": ep.get("core9"),
                "allele": ep.get("allele"),
                "allele_weight": ep.get("allele_weight"),
                "percentile_rank": ep.get("percentile_rank"),
                "ic50": ep.get("ic50"),
                "region": ep.get("region"),
                "tolerance": ep.get("tolerance"),
                "net_contribution": ep.get("net_contribution"),
                "start": ep.get("start"),
            })

        # ── Summary row ───────────────────────────────────────────────────
        flags = "|".join(mhc.get("flags", []))
        risk      = mhc.get("mhcii_risk", "ERROR")
        surf_risk = surf.get("surface_risk", "—")
        clinical_risk  = ada_scored["clinical_ada_risk"]
        clinical_score = ada_scored["clinical_ada_score"]
        comp = ada_scored["components"]

        summary_rows.append({
            "antibody": name,
            "clinical_ada_score": clinical_score,
            "clinical_ada_risk": clinical_risk,
            "mhcii_risk": risk,
            "surface_risk": surf_risk,
            "score_B_mhcii": comp.get("B_mhcii_burden"),
            "score_S_surface": comp.get("S_surface_exp"),
            "score_C_clusters": comp.get("C_clusters"),
            "score_N_binders": comp.get("N_binders"),
            "n_strong_binders": mhc.get("n_strong_binders", 0),
            "n_clusters": mhc.get("n_clusters", 0),
            "raw_immunogenic_burden": mhc.get("raw_immunogenic_burden", 0.0),
            "net_immunogenic_burden": mhc.get("net_immunogenic_burden", 0.0),
            "n_hydrophilic_patches": surf.get("n_hydrophilic_patches", 0),
            "frac_exposed_vh": surf.get("frac_exposed_vh"),
            "frac_exposed_vl": surf.get("frac_exposed_vl"),
            "mean_sasa_vh": surf.get("mean_sasa_vh"),
            "mean_sasa_vl": surf.get("mean_sasa_vl"),
            "surface_mode": surf.get("mode", "—"),
            "flags": flags,
            "pdb_used": bool(pdb),
            "vh_len": len(vh),
            "vl_len": len(vl),
        })

        risk = mhc.get("mhcii_risk", "?")
        surf_risk = surf.get("surface_risk", "?")
        nb  = mhc.get("n_strong_binders", 0)
        nc  = mhc.get("n_clusters", 0)
        net = mhc.get("net_immunogenic_burden", 0.0)
        mode = "PDB" if pdb else "seq"
        print(
            f"[{ni:2d}/{total}] {name:30s}  "
            f"ADA:{clinical_score:.3f}({clinical_risk:6s})  "
            f"MHC-II:{risk:6s}  Surf:{surf_risk:6s}  "
            f"strong={nb:3d}  clusters={nc}  net={net:.4f}  "
            f"surf={mode}  ({elapsed:.1f}s)"
        )

        # ── Incremental write: flush summary row immediately ──────────────────
        _inc_df = pd.DataFrame(summary_rows)
        _inc_df.to_csv(SUM_CSV, index=False)
        if epitope_rows:
            pd.DataFrame(epitope_rows).to_csv(EPI_CSV, index=False)

    # ── Write outputs ─────────────────────────────────────────────────────────
    sum_df = pd.DataFrame(summary_rows)
    epi_df = pd.DataFrame(epitope_rows)

    # Keep row order aligned with confirmed70_sequences_full.csv
    order_df = pd.read_csv(SEQ_CSV)
    order_map = {str(n): i for i, n in enumerate(order_df["antibody_name"].tolist())}
    if not sum_df.empty and "antibody" in sum_df.columns:
        sum_df["_ord"] = sum_df["antibody"].map(lambda x: order_map.get(str(x), 9999))
        sum_df = sum_df.sort_values("_ord").drop(columns="_ord")
        summary_rows = sum_df.to_dict("records")

    # ── Auto-calibrate if known-ADA antibodies are in the scan ────────────────
    if not sum_df.empty and "clinical_ada_score" in sum_df.columns:
        valid = sum_df[sum_df["clinical_ada_score"].notna()][["antibody", "clinical_ada_score"]]
        if len(valid) >= 5:
            cal_result = scorer.calibrate(valid, save=True)
            if cal_result:
                print(f"\n  Auto-calibration: {cal_result.get('n_antibodies',0)} antibodies matched")
                print(f"    balanced_accuracy = {cal_result.get('balanced_accuracy','—')}")
                print(f"    spearman_r(score vs ADA%) = {cal_result.get('spearman_r','—')}")
                print(f"    optimal thresholds: HIGH≥{cal_result.get('optimal_threshold_high')}, "
                      f"MEDIUM≥{cal_result.get('optimal_threshold_medium')}")

    sum_df.to_csv(SUM_CSV, index=False)
    epi_df.to_csv(EPI_CSV, index=False)
    HTML_OUT.write_text(_build_html(sum_df, epi_df), encoding="utf-8")

    # ── Terminal summary ──────────────────────────────────────────────────────
    print(f"\n{'='*64}")
    print("  DONE")
    print(f"{'='*64}")
    if not sum_df.empty:
        rc = sum_df["clinical_ada_risk"].value_counts()
        print("  Clinical ADA Risk distribution (composite score):")
        for tier in ["HIGH", "MEDIUM", "LOW", "SKIPPED", "ERROR"]:
            if tier in rc:
                print(f"    {tier:8s}: {rc[tier]:3d}")
        valid_scores = sum_df["clinical_ada_score"].dropna()
        if len(valid_scores) > 0:
            print(f"  ADA score range: {valid_scores.min():.3f} – {valid_scores.max():.3f} "
                  f"(mean {valid_scores.mean():.3f})")
        n_pdb = int(sum_df.get("pdb_used", pd.Series([False] * len(sum_df))).sum())
        print(f"\n  PDB structures used : {n_pdb}/{total}")
        if "net_immunogenic_burden" in sum_df.columns:
            valid = sum_df[sum_df["mhcii_risk"].isin(["HIGH","MEDIUM","LOW"])]
            if not valid.empty:
                print(f"  Net burden range    : "
                      f"{valid['net_immunogenic_burden'].min():.4f} – "
                      f"{valid['net_immunogenic_burden'].max():.4f}")
    print(f"\n  Outputs → {OUT_DIR}/")
    print(f"    {SUM_CSV.name}")
    print(f"    {EPI_CSV.name}")
    print(f"    {HTML_OUT.name}")


if __name__ == "__main__":
    main()
