#!/usr/bin/env python3
"""
Recompute germline_anarcii / germline_anarcii_pct in anarcii_numbering_70.csv using
FR1+FR2+FR3 vs **OGRDB** published **human** IG V alleles (same logic as run_anarcii_numbering_70.py).

OGRDB (AIRR) is limited to a small set of species for IG/TR (e.g. human, primate, mouse);
multi-species antibody work in AbEngineCore should use IMGT_V-QUEST_reference_directory +
data/germlines/aa_translated (see core/resources/germline_resources.py).

Downloads JSON caches under data/germlines/ if missing (network).

Usage:
  python scripts/fill_anarcii_ogrdb_germlines.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

SUITE = Path(__file__).resolve().parents[1]
CSV_PATH = SUITE / "data/thera_sabdab/out/anarcii_numbering_70.csv"


def _load_ra70():
    p = SUITE / "scripts/run_anarcii_numbering_70.py"
    spec = importlib.util.spec_from_file_location("run_anarcii_numbering_70", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    ra = _load_ra70()
    df = pd.read_csv(CSV_PATH)
    if not {"fr1", "fr2", "fr3", "chain_type"}.issubset(df.columns):
        raise SystemExit("anarcii_numbering_70.csv missing fr*/chain_type columns")

    print("Loading OGRDB references …")
    germline_ref = ra._load_germline_ref()
    total = sum(len(v) for v in germline_ref.values())
    if total == 0:
        print("ERROR: No germline genes loaded (OGRDB download failed?).", file=sys.stderr)
        sys.exit(1)
    print(f"  Loaded {total} total V-allele AA sequences.")

    gl_a: list[str] = []
    gl_p: list[float] = []
    gl_fam: list[str] = []

    for _, row in df.iterrows():
        ct = str(row.get("chain_type", ""))
        ref_chain = "H" if ct == "H" else ("K" if ct == "K" else "L")
        ref_genes = germline_ref.get(ref_chain, {})
        fr_concat = f'{row.get("fr1", "")}{row.get("fr2", "")}{row.get("fr3", "")}'
        allele, pct = ra._best_germline(fr_concat, ref_genes)
        gl_a.append(allele)
        gl_p.append(pct)
        gl_fam.append(ra._gene_family(allele))

    df["germline_anarcii"] = gl_a
    df["germline_anarcii_pct"] = gl_p
    df["germline_family"] = gl_fam

    # Refresh agreement vs 842 column when both present
    def agree_row(r) -> str:
        ga = str(r.get("germline_842csv", "") or "").strip()
        an = str(r.get("germline_anarcii", "") or "").strip()
        if not ga or an == "unknown":
            return "N/A"
        return str(an.split("*")[0]).upper() == str(ga.split("*")[0]).upper()

    df["germline_agree"] = df.apply(agree_row, axis=1)

    df.to_csv(CSV_PATH, index=False)
    print(f"Updated {CSV_PATH.relative_to(SUITE)} ({len(df)} rows).")


if __name__ == "__main__":
    main()
