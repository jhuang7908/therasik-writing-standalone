#!/usr/bin/env python3
"""
Join confirmed-70 list with Thera SI-structure columns + local atlas PDB paths.

Resolution order (first hit wins for atlas_structure_relpath):
  1) data/structures/natural/<INN>.pdb
  2) data/structures/engineered/<INN>.pdb
  3) bispecific_75_atlas master_table structure_whole (Emicizumab, Faricimab, Zenocutuzumab, …)
  4) Hard-coded clinical / pipeline models:
       Ozoralizumab -> PDB 8Z8V (HSA + ALB8 VHH; PMID 39083975)
       Tarlatamab   -> multispecific_linker_pipeline esmfold

Reads:
  data/thera_sabdab/out/confirmed70_human_humanized_germline_ada.csv
  data/thera_sabdab/TheraSAbDab_SeqStruc_OnlineDownload.xlsx
Writes:
  data/thera_sabdab/out/confirmed70_structure_atlas_supplement.csv
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

SUITE = Path(__file__).resolve().parents[1]
DEFAULT_70 = SUITE / "data/thera_sabdab/out/confirmed70_human_humanized_germline_ada.csv"
THERA = SUITE / "data/thera_sabdab/TheraSAbDab_SeqStruc_OnlineDownload.xlsx"
BISPEC = SUITE / "data/bispecific_75_atlas/master_table.csv"
OUT_CSV = SUITE / "data/thera_sabdab/out/confirmed70_structure_atlas_supplement.csv"

STRUCT_COLS = ("100% SI Structure", "99% SI Structure", "95-98% SI Structure")

# INN-specific models not under structures/natural|engineered
SPECIAL_PDB: dict[str, tuple[str, str]] = {
    "ozoralizumab": (
        "projects/anti_HSA_VHH/8z8v.pdb",
        "pdb_8z8v_hsa_alb8",
    ),
    "tarlatamab": (
        "data/design_rules/multispecific_linker_pipeline/esmfold_predictions/Tarlatamab.pdb",
        "multispecific_esmfold",
    ),
}


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


def nonempty(x: object) -> bool:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return False
    s = str(x).strip()
    return bool(s) and s.lower() not in ("na", "nan")


def rel_from_suite(abs_or_rel: str) -> str:
    p = Path(abs_or_rel.strip())
    if not p.is_absolute():
        p = (SUITE / p).resolve()
    try:
        return p.resolve().relative_to(SUITE.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def load_bispecific_structure_whole() -> dict[str, str]:
    out: dict[str, str] = {}
    if not BISPEC.is_file():
        return out
    with BISPEC.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            aid = (row.get("antibody_id") or "").strip()
            if not aid:
                continue
            sw = (row.get("structure_whole") or "").strip()
            if sw:
                out[aid.lower()] = sw
    return out


def index_pdb_dir(sub: str) -> dict[str, str]:
    d = SUITE / "data" / "structures" / sub
    m: dict[str, str] = {}
    if not d.is_dir():
        return m
    for p in d.glob("*.pdb"):
        m[p.stem.lower()] = (p.relative_to(SUITE)).as_posix()
    return m


def resolve_atlas_pdb(
    inn_key: str,
    nat: dict[str, str],
    eng: dict[str, str],
    bispec_whole: dict[str, str],
) -> tuple[str, str]:
    if inn_key in nat:
        return nat[inn_key], "structures_natural"
    if inn_key in eng:
        return eng[inn_key], "structures_engineered"
    if inn_key in bispec_whole:
        p = bispec_whole[inn_key]
        if Path(p).is_file():
            return rel_from_suite(p), "bispecific_atlas_structure_whole"
        return rel_from_suite(str(Path(p))), "bispecific_atlas_structure_whole"
    if inn_key in SPECIAL_PDB:
        rel, src = SPECIAL_PDB[inn_key]
        full = SUITE / rel
        if full.is_file():
            return rel, src
    return "", ""


def main() -> None:
    ap = argparse.ArgumentParser(description="Supplement confirmed-70 with atlas PDB paths.")
    ap.add_argument("--input70", type=Path, default=DEFAULT_70)
    ap.add_argument("--output", type=Path, default=OUT_CSV)
    args = ap.parse_args()

    df = pd.read_csv(args.input70)
    thera_rows = load_thera_index()
    bispec_whole = load_bispecific_structure_whole()
    nat = index_pdb_dir("natural")
    eng = index_pdb_dir("engineered")

    rows_out: list[dict[str, str]] = []
    for _, r in df.iterrows():
        name = str(r["antibody_name"])
        k1, k2 = norm(name), bio_strip(name)
        trow = None
        for k in (k1, k2):
            if k and k in thera_rows:
                trow = thera_rows[k]
                break

        si_parts: list[str] = []
        if trow is not None:
            for c in STRUCT_COLS:
                v = trow.get(c)
                if nonempty(v):
                    si_parts.append(f"{c}: {str(v).strip()}")
        thera_si = " | ".join(si_parts)
        thera_flag = "1" if si_parts else ""

        inn_key = k1 or k2 or norm(name)
        rel, src = resolve_atlas_pdb(inn_key, nat, eng, bispec_whole)

        rows_out.append(
            {
                "antibody_name": name,
                "thera_has_si_structure_field": thera_flag,
                "thera_si_structure_text": thera_si,
                "atlas_structure_relpath": rel,
                "atlas_structure_source": src,
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)

    n_thera = sum(1 for x in rows_out if x["thera_has_si_structure_field"])
    n_atlas = sum(1 for x in rows_out if x["atlas_structure_relpath"])
    print(f"Wrote {args.output}")
    print(f"Rows: {len(rows_out)}")
    print(f"Thera SI field non-empty: {n_thera}")
    print(f"Atlas/local PDB resolved: {n_atlas}")
    if n_atlas < len(rows_out):
        miss = [x["antibody_name"] for x in rows_out if not x["atlas_structure_relpath"]]
        print(f"Still missing PDB: {miss}")


if __name__ == "__main__":
    main()
