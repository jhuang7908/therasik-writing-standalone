#!/usr/bin/env python3
"""
70 drugs = confirmed ADA ∩ TheraSAbDab with Genetics in {fully human, humanised} (27+43).

Germline:
  1) Prefer data/humanization_assay/842_antibody_germline_assignment.csv (INN match).
  2) If missing, primary alleles come from IMGT **aa_translated** (Homo_sapiens) via
     core.resources.germline_resources.vh_identity_imgt / vl_identity_imgt on Thera sequences.
  3) OGRDB-based columns (vh_identity_ogrdb, …) remain from anarcii_numbering_70.csv
     after scripts/fill_anarcii_ogrdb_germlines.py (FR match vs human OGRDB cache).
  4) Bispecific arm2: IMGT on HeavySequence(ifbispec) / LightSequence(ifbispec) when present;
     else OGRDB columns from ABARCII row.
  5) Naive-blood V-gene **population usage priors** (relative weights, κ/λ global VL):
     core.resources.germline_population_usage — see data/germlines/population_usage/README.md

Outputs:
  data/thera_sabdab/out/confirmed70_human_humanized_germline_ada.csv
  data/thera_sabdab/out/confirmed70_germline_ada_summary.txt
"""
from __future__ import annotations

import csv
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))

from core.resources.germline_resources import vh_identity_imgt, vl_identity_imgt
from core.resources.germline_population_usage import (
    population_usage_reference_note,
    population_usage_vh,
    population_usage_vl,
    v_gene_from_allele,
)

from scripts.build_confirmed70_sequences_full import OZORALIZUMAB_ALB8_VHH_AA

OUT_DIR = SUITE / "data/thera_sabdab/out"
GERM842 = SUITE / "data/humanization_assay/842_antibody_germline_assignment.csv"
ABARCII_CSV = OUT_DIR / "anarcii_numbering_70.csv"
CONFIRMED = SUITE / "data/ADA_reliable_package/final_three_files/confirmed_ada.json"
THERA = SUITE / "data/thera_sabdab/TheraSAbDab_SeqStruc_OnlineDownload.xlsx"
GEN_COL = "Genetics (Bispecifics delimited with semicolon)"


def norm(s: object) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    t = str(s).strip().lower()
    t = re.sub(r"\s+", "", t)
    t = re.sub(r"[-_/]", "", t)
    return t


def bio_strip(s: object) -> str:
    base = norm(s)
    m = re.match(r"^([a-z]{6,})([a-z]{4})$", base)
    if m and len(m.group(1)) >= 8:
        return m.group(1)
    return base


def classify_genetics(g: object) -> str | None:
    if g is None or (isinstance(g, float) and pd.isna(g)):
        return None
    s = str(g).strip()
    if not s or s.lower() in ("na", "nan"):
        return None
    low = s.lower()
    has_gh = "genetically human" in low
    has_hum = "humanised" in low or "humanized" in low
    has_chi = "chimeric" in low
    has_mur = "murine" in low
    if has_mur and not has_hum and not has_gh and not has_chi:
        return "murine"
    if has_hum:
        return "humanized"
    if has_chi:
        return "chimeric_only"
    if has_gh and not has_hum and not has_chi:
        return "fully_human"
    return "other"


def first_pct(s: object) -> float | None:
    if not s:
        return None
    m = re.search(r"(\d+\.?\d*)\s*%", str(s))
    return float(m.group(1)) if m else None


def gene_family(allele: str) -> str:
    """IGHV3-23*04 -> IGHV3-23"""
    if not allele:
        return ""
    return allele.split("*")[0]


def load_thera_index() -> dict[str, pd.Series]:
    df = pd.read_excel(THERA, engine="openpyxl")
    by_key: dict[str, list] = defaultdict(list)
    for _, row in df.iterrows():
        t = row["Therapeutic"]
        if pd.isna(t):
            continue
        by_key[norm(t)].append(row)
        alt = row.get("Alternative Therapeutic Names", "")
        if pd.isna(alt):
            continue
        for part in re.split(r"[;|,/\n]+", str(alt)):
            p = part.strip()
            if p and p.lower() not in ("na", "nan"):
                by_key[norm(p)].append(row)
    return {k: v[0] for k, v in by_key.items() if v}


def load_germ842() -> dict[str, dict]:
    out: dict[str, dict] = {}
    with GERM842.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            out[norm(row["ab_id"])] = row
    return out


def _clean_allele(s: object) -> str:
    t = str(s or "").strip()
    return "" if not t or t.lower() == "unknown" else t


def clean_imgt_aa(x: object) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    s = str(x).strip().upper()
    s = re.sub(r"[^ACDEFGHIKLMNPQRSTVWY]", "", s)
    if len(s) < 8:
        return ""
    return s


def _imgt_vh_fields(seq: str) -> tuple[str, str, str]:
    """(allele, identity as 0–1 string or '', search_db relpath)."""
    if len(seq) < 20:
        return "", "", ""
    r = vh_identity_imgt(seq, "Homo_sapiens")
    if not r:
        return "", "", ""
    name = str(r.get("closest_vh_germline") or "").strip()
    if not name or name.lower() == "unknown":
        return "", "", ""
    pct = float(r.get("vh_germline_identity_pct") or 0)
    db = str(r.get("germline_search_db", "") or "")
    return name, f"{round(pct / 100.0, 4):.4f}".rstrip("0").rstrip("."), db


def _fmt_pop_f(x: float) -> str:
    if x != x:  # NaN
        return ""
    return f"{round(float(x), 6):.6f}".rstrip("0").rstrip(".")


def _pop_vh_cols(gene: str) -> tuple[str, str]:
    f, r = population_usage_vh(str(gene or "").strip())
    return _fmt_pop_f(f), _fmt_pop_f(r)


def _pop_vl_cols(gene: str) -> tuple[str, str]:
    _fl, fg, _rl, rg = population_usage_vl(str(gene or "").strip())
    return _fmt_pop_f(fg), _fmt_pop_f(rg)


def _imgt_vl_fields(seq: str) -> tuple[str, str, str, str]:
    """(allele, identity 0–1, locus IGKV|IGLV|'', vl_search_db)."""
    if len(seq) < 20:
        return "", "", "", ""
    r = vl_identity_imgt(seq, "Homo_sapiens")
    if not r:
        return "", "", "", ""
    name = str(r.get("closest_vl_germline") or "").strip()
    if not name or name.lower() == "unknown":
        return "", "", "", ""
    pct = float(r.get("vl_germline_identity_pct") or 0)
    loc = str(r.get("vl_germline_locus", "") or "")
    db = str(r.get("germline_vl_search_db", "") or "")
    return name, f"{round(pct / 100.0, 4):.4f}".rstrip("0").rstrip("."), loc, db


def load_anarcii_by_drug() -> dict[str, dict[str, object]]:
    """Norm(drug) → arm1/2 germline alleles + OGRDB identity % (as 0–100 float from CSV)."""
    if not ABARCII_CSV.is_file():
        return {}
    df = pd.read_csv(ABARCII_CSV)
    out: dict[str, dict[str, object]] = {}
    for drug, g in df.groupby(df["drug"].astype(str)):

        def pick(arm: str, labels: tuple[str, ...]) -> tuple[str, float]:
            r = g[(g["arm"] == arm) & (g["chain_label"].isin(labels))]
            if r.empty:
                return "", 0.0
            row = r.iloc[0]
            gl = _clean_allele(row.get("germline_anarcii", ""))
            try:
                pct = float(row.get("germline_anarcii_pct", 0) or 0)
            except (TypeError, ValueError):
                pct = 0.0
            return gl, pct

        vh, vp = pick("arm1", ("VH",))
        vl, lp = pick("arm1", ("VL",))
        vh2, v2p = pick("arm2", ("VH2",))
        vl2, l2p = pick("arm2", ("VL2", "VL"))
        vh3, v3p = pick("arm3", ("VH3",))
        out[norm(drug)] = {
            "vh": vh,
            "vh_pct": vp,
            "vl": vl,
            "vl_pct": lp,
            "vh2": vh2,
            "vh2_pct": v2p,
            "vl2": vl2,
            "vl2_pct": l2p,
            "vh3": vh3,
            "vh3_pct": v3p,
        }
    return out


def main() -> None:
    blob = json.loads(CONFIRMED.read_text(encoding="utf-8"))
    entries = {e["antibody_name"]: e for e in blob["entries"]}
    thera_rows = load_thera_index()
    germ_by = load_germ842()
    anarcii_by = load_anarcii_by_drug()

    rows_out: list[dict] = []
    for name, e in entries.items():
        k1, k2 = norm(name), bio_strip(name)
        trow = None
        for k in (k1, k2):
            if k and k in thera_rows:
                trow = thera_rows[k]
                break
        if trow is None:
            continue
        gcls = classify_genetics(trow[GEN_COL])
        if gcls not in ("fully_human", "humanized"):
            continue

        ada_str = e.get("ada_value_display") or ""
        p = first_pct(ada_str)
        g = germ_by.get(k1) or germ_by.get(k2)
        arc = anarcii_by.get(k1) or anarcii_by.get(k2) or {}

        h1 = clean_imgt_aa(trow.get("HeavySequence", ""))
        l1 = clean_imgt_aa(trow.get("LightSequence", ""))
        h2 = clean_imgt_aa(trow.get("HeavySequence(ifbispec)", ""))
        l2 = clean_imgt_aa(trow.get("LightSequence(ifbispec)", ""))
        h3 = OZORALIZUMAB_ALB8_VHH_AA if norm(name) == "ozoralizumab" else ""

        vh_im_n, vh_im_id, vh_im_db = _imgt_vh_fields(h1)
        vl_im_n, vl_im_id, vl_im_loc, vl_im_db = _imgt_vl_fields(l1)
        vh2_im_n, vh2_im_id, vh2_im_db = _imgt_vh_fields(h2)
        vl2_im_n, vl2_im_id, vl2_im_loc, vl2_im_db = _imgt_vl_fields(l2)
        vh3_im_n, vh3_im_id, vh3_im_db = _imgt_vh_fields(h3)

        vh_gl_842 = str((g or {}).get("vh_germline", "") or "").strip()
        vl_gl_842 = str((g or {}).get("vl_germline", "") or "").strip()
        vh_id_842 = str((g or {}).get("vh_identity", "") or "").strip()
        vl_id_842 = str((g or {}).get("vl_identity", "") or "").strip()

        if g:
            vh_gl = vh_gl_842
            vl_gl = vl_gl_842
        else:
            vh_gl = vh_im_n or str(arc.get("vh", "") or "")
            vl_gl = vl_im_n or str(arc.get("vl", "") or "")

        vh_pct = float(arc.get("vh_pct", 0) or 0)
        vl_pct = float(arc.get("vl_pct", 0) or 0)
        vh_id_o = round(vh_pct / 100, 4) if arc.get("vh") else ""
        vl_id_o = round(vl_pct / 100, 4) if arc.get("vl") else ""

        vh2_gl = (vh2_im_n or str(arc.get("vh2", "") or "")) if h2 else ""
        vl2_gl = (vl2_im_n or str(arc.get("vl2", "") or "")) if l2 else ""
        vh2_pct = float(arc.get("vh2_pct", 0) or 0)
        vl2_pct = float(arc.get("vl2_pct", 0) or 0)
        vh2_id_o = round(vh2_pct / 100, 4) if arc.get("vh2") else ""
        vl2_id_o = round(vl2_pct / 100, 4) if arc.get("vl2") else ""

        vh3_gl = (vh3_im_n or str(arc.get("vh3", "") or "")) if h3 else ""
        vh3_pct = float(arc.get("vh3_pct", 0) or 0)
        vh3_id_o = round(vh3_pct / 100, 4) if h3 and arc.get("vh3") else ""

        vh_gene = str(gene_family(vh_gl) or "").strip() or v_gene_from_allele(vh_gl)
        vl_gene = str(gene_family(vl_gl) or "").strip() or v_gene_from_allele(vl_gl)
        vh2_gene = v_gene_from_allele(vh2_gl) if vh2_gl else ""
        vl2_gene = v_gene_from_allele(vl2_gl) if vl2_gl else ""
        vh3_gene = v_gene_from_allele(vh3_gl) if vh3_gl else ""

        vh_pf, vh_pr = _pop_vh_cols(vh_gene)
        vl_pf, vl_pr = _pop_vl_cols(vl_gene)
        vh2_pf, vh2_pr = _pop_vh_cols(vh2_gene) if vh2_gene else ("", "")
        vl2_pf, vl2_pr = _pop_vl_cols(vl2_gene) if vl2_gene else ("", "")
        vh3_pf, vh3_pr = _pop_vh_cols(vh3_gene) if vh3_gene else ("", "")

        if g:
            gsrc = "842_assignment_by_inn"
            if vh2_gl or vl2_gl:
                gsrc = "842_assignment_plus_arm2"
        elif vh_im_n or vl_im_n:
            gsrc = "imgt_aa_translated_primary"
        elif vh_gl or vl_gl or vh2_gl or vl2_gl:
            gsrc = "ogrdb_fr_fallback_only"
        else:
            gsrc = "not_in_842"

        rows_out.append(
            {
                "antibody_name": name,
                "thera_genetics_class": gcls,
                "ada_value_display": ada_str,
                "ada_first_pct": p if p is not None else "",
                "vh_germline": vh_gl,
                "vl_germline": vl_gl,
                "vh_family": gene_family(vh_gl),
                "vl_family": gene_family(vl_gl),
                "vh_identity_842": vh_id_842,
                "vl_identity_842": vl_id_842,
                "vh_identity_ogrdb": vh_id_o,
                "vl_identity_ogrdb": vl_id_o,
                "vh2_germline": vh2_gl,
                "vl2_germline": vl2_gl,
                "vh2_identity_ogrdb": vh2_id_o,
                "vl2_identity_ogrdb": vl2_id_o,
                "vh_germline_imgt": vh_im_n,
                "vl_germline_imgt": vl_im_n,
                "vh_identity_imgt": vh_im_id,
                "vl_identity_imgt": vl_im_id,
                "vl_germline_locus_imgt": vl_im_loc,
                "imgt_search_db_vh": vh_im_db,
                "imgt_search_db_vl": vl_im_db,
                "vh2_germline_imgt": vh2_im_n,
                "vl2_germline_imgt": vl2_im_n,
                "vh2_identity_imgt": vh2_im_id,
                "vl2_identity_imgt": vl2_im_id,
                "vl2_germline_locus_imgt": vl2_im_loc,
                "vh3_germline": vh3_gl,
                "vh3_identity_ogrdb": vh3_id_o,
                "vh3_germline_imgt": vh3_im_n,
                "vh3_identity_imgt": vh3_im_id,
                "imgt_search_db_vh3": vh3_im_db,
                "vh_pop_naive_usage_frac": vh_pf,
                "vh_pop_rarity_neglog10": vh_pr,
                "vl_pop_naive_usage_frac_global": vl_pf,
                "vl_pop_rarity_global_neglog10": vl_pr,
                "vh2_pop_naive_usage_frac": vh2_pf,
                "vh2_pop_rarity_neglog10": vh2_pr,
                "vl2_pop_naive_usage_frac_global": vl2_pf,
                "vl2_pop_rarity_global_neglog10": vl2_pr,
                "vh3_pop_naive_usage_frac": vh3_pf,
                "vh3_pop_rarity_neglog10": vh3_pr,
                "population_usage_reference": population_usage_reference_note(),
                "germline_source": gsrc,
                "heavy_seq_len": len(h1),
                "light_seq_len": len(l1),
                "vh3_seq_len": len(h3),
            }
        )

    rows_out.sort(key=lambda r: (r["thera_genetics_class"], r["antibody_name"]))
    assert len(rows_out) == 70, f"expected 70 rows, got {len(rows_out)}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "confirmed70_human_humanized_germline_ada.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)

    # Aggregate VH families (numeric ADA only)
    by_vh: dict[str, list[float]] = defaultdict(list)
    by_vl: dict[str, list[float]] = defaultdict(list)
    for r in rows_out:
        if r["germline_source"] not in (
            "842_assignment_by_inn",
            "842_assignment_plus_arm2",
            "imgt_aa_translated_primary",
        ):
            continue
        p = r["ada_first_pct"]
        if p == "" or p is None:
            continue
        fv, lv = r["vh_family"], r["vl_family"]
        if fv:
            by_vh[fv].append(float(p))
        if lv:
            by_vl[lv].append(float(p))

    def summarize(by: dict[str, list[float]], min_n: int) -> list[tuple]:
        out = []
        for g, vals in by.items():
            if len(vals) < min_n:
                continue
            out.append((g, len(vals), statistics.median(vals), statistics.mean(vals)))
        out.sort(key=lambda x: x[2])
        return out

    n_842 = sum(1 for r in rows_out if r["germline_source"].startswith("842_assignment"))
    n_imgt_pri = sum(1 for r in rows_out if r["germline_source"] == "imgt_aa_translated_primary")
    n_ogrdb_only = sum(1 for r in rows_out if r["germline_source"] == "ogrdb_fr_fallback_only")
    lines = [
        "70 drugs: confirmed ADA + TheraSAbDab Genetics in {Genetically human, Humanised}",
        f"Germline: 842 CSV (INN) primary: {n_842}/70; IMGT aa_translated primary (no 842 row): {n_imgt_pri}/70.",
        f"  OGRDB FR-match only (IMGT miss / short seq): {n_ogrdb_only}/70.",
        "  IMGT: core.resources.germline_resources vh_identity_imgt / vl_identity_imgt (Homo_sapiens).",
        "  OGRDB columns: run scripts/fill_anarcii_ogrdb_germlines.py after ABARCII.",
        "",
        "VH families with n>=3 (842 + IMGT-primary rows), sorted by median first ADA %:",
    ]
    for g, n, med, mean in summarize(by_vh, 3):
        lines.append(f"  {g:12s}  n={n}  median={med:.2f}%  mean={mean:.2f}%")

    lines += ["", "VL families with n>=3 (842 + IMGT-primary rows), sorted by median first ADA %:"]
    for g, n, med, mean in summarize(by_vl, 3):
        lines.append(f"  {g:12s}  n={n}  median={med:.2f}%  mean={mean:.2f}%")

    lines += [
        "",
        "VH families with n==2 (lowest median first — exploratory only):",
    ]
    for g, n, med, mean in summarize(by_vh, 2):
        if n == 2:
            lines.append(f"  {g:12s}  n={n}  median={med:.2f}%  mean={mean:.2f}%")

    imgt_pri = [r["antibody_name"] for r in rows_out if r["germline_source"] == "imgt_aa_translated_primary"]
    ogrdb_only = [r["antibody_name"] for r in rows_out if r["germline_source"] == "ogrdb_fr_fallback_only"]
    lines += [
        "",
        "IMGT aa_translated primary (no 842 INN row; alleles from N-term match vs IMGT human IGHV/IGKV/IGLV):",
        "  " + (", ".join(imgt_pri) if imgt_pri else "(none)"),
        "",
        "OGRDB FR-match only (no usable IMGT hit; VH/VL from ABARCII+OGRDB):",
        "  " + (", ".join(ogrdb_only) if ogrdb_only else "(none)"),
        "",
        "CAUTION: ADA varies by indication, assay, regimen; germline-ADA correlation is hypothesis-generating only.",
    ]

    summary_path = OUT_DIR / "confirmed70_germline_ada_summary.txt"
    summary_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {csv_path}")
    print(f"Wrote {summary_path}")
    print("\n".join(lines[:25]))


if __name__ == "__main__":
    main()
