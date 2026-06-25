"""One-off completeness report for confirmed 70; run: python scripts/_report_confirmed70_completeness.py"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

SUITE = Path(__file__).resolve().parents[1]


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
    thera = SUITE / "data/thera_sabdab/TheraSAbDab_SeqStruc_OnlineDownload.xlsx"
    df = pd.read_excel(thera, engine="openpyxl")
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


def main() -> None:
    df70 = pd.read_csv(SUITE / "data/thera_sabdab/out/confirmed70_human_humanized_germline_ada.csv")
    names = df70["antibody_name"].astype(str).tolist()

    thera_rows = load_thera_index()
    blob = json.loads(
        (SUITE / "data/ADA_reliable_package/final_three_files/confirmed_ada.json").read_text(encoding="utf-8")
    )
    ada_by_name = {e["antibody_name"]: e for e in blob["entries"]}

    struct_cols = ["100% SI Structure", "99% SI Structure", "95-98% SI Structure"]
    cond_cols = ["Conditions Approved", "Conditions Active", "Conditions Discontinued"]
    phase_col = "Highest_Clin_Trial (Feb '25)"

    rows: list[tuple] = []
    for name in names:
        k1, k2 = norm(name), bio_strip(name)
        trow = None
        for k in (k1, k2):
            if k and k in thera_rows:
                trow = thera_rows[k]
                break
        ada = ada_by_name.get(name, {})
        rows.append((name, trow, ada))

    def count(pred):
        return sum(1 for name, t, a in rows if pred(t, a))

    print("=== Confirmed 70 field completeness ===\n")
    print(f"N = {len(rows)}")

    print("\n-- Match / identity --")
    print(f"Thera row matched: {count(lambda t, a: t is not None)}")
    print(f"confirmed_ada.json has ada_value_display: {count(lambda t, a: bool(a.get('ada_value_display')))}")

    print("\n-- Thera clinical / listing fields --")
    print(f"Target: {count(lambda t, a: t is not None and nonempty(t.get('Target')))}")
    print(f"Highest_Clin_Trial: {count(lambda t, a: t is not None and nonempty(t.get(phase_col)))}")
    print(
        f"Any conditions col: {count(lambda t, a: t is not None and any(nonempty(t.get(c)) for c in cond_cols))}"
    )

    print("\n-- Sequences (Thera) --")
    print(f"HeavySequence: {count(lambda t, a: t is not None and nonempty(t.get('HeavySequence')))}")
    print(f"LightSequence: {count(lambda t, a: t is not None and nonempty(t.get('LightSequence')))}")
    hb = "HeavySequence(ifbispec)"
    lb = "LightSequence(ifbispec)"
    print(
        f"Heavy OR bispec heavy: {count(lambda t, a: t is not None and (nonempty(t.get('HeavySequence')) or nonempty(t.get(hb))))}"
    )

    print("\n-- Structure (Thera PDB/SI refs vs local atlas) --")
    print(
        f"Thera SI field (any of 3 cols): {count(lambda t, a: t is not None and any(nonempty(t.get(c)) for c in struct_cols))}"
    )

    sup = pd.read_csv(SUITE / "data/thera_sabdab/out/confirmed70_structure_atlas_supplement.csv")
    n_pdb = int(sup["atlas_structure_relpath"].fillna("").astype(str).str.len().gt(0).sum())
    print(f"Local/atlas pdb path (supplement script): {n_pdb}/70")
    print("atlas_structure_source counts:")
    print(sup["atlas_structure_source"].value_counts().to_string())
    print()

    print("-- Germline (confirmed70 CSV: 842 INN and/or IMGT aa_translated; OGRDB from ABARCII CSV) --")
    has_vh = df70["vh_germline"].fillna("").astype(str).str.strip() != ""
    has_vl = df70["vl_germline"].fillna("").astype(str).str.strip() != ""
    print(f"vh_germline non-empty: {int(has_vh.sum())}")
    print(f"vl_germline non-empty: {int(has_vl.sum())}")
    print(f"both VH+VL: {int((has_vh & has_vl).sum())}")
    n_842 = int(df70["germline_source"].astype(str).str.startswith("842_assignment").sum())
    n_imgt = int((df70["germline_source"] == "imgt_aa_translated_primary").sum())
    n_ogrdb = int((df70["germline_source"] == "ogrdb_fr_fallback_only").sum())
    print(f"germline_source 842*: {n_842}  imgt_aa_translated_primary: {n_imgt}  ogrdb_fr_fallback_only: {n_ogrdb}")
    if "vh2_germline" in df70.columns:
        h2 = df70["vh2_germline"].fillna("").astype(str).str.strip() != ""
        print(f"vh2_germline non-empty (bispecific arm2): {int(h2.sum())}")

    an = pd.read_csv(SUITE / "data/thera_sabdab/out/anarcii_numbering_70.csv")
    print("\n-- ABARCII --")
    print(f"chain rows: {len(an)}; numbered_ok: {int(an['numbered_ok'].sum())}")
    print(f"drugs in file: {an['drug'].nunique()} (expect 70 unique names as drugs)")

    notes_dose = 0
    for name, t, a in rows:
        if t is None:
            continue
        n = str(t.get("Notes", "") or "")
        ada_s = str(a.get("ada_value_display", "") or "")
        if re.search(r"\b\d+\s*mg\b|\bmg/kg\b", n + ada_s, re.I):
            notes_dose += 1
    print("\n-- Clinical dose (no dedicated column) --")
    print(f"Thera Notes OR ada_value_display mentions mg (regex): {notes_dose}/70")

    print("\n-- Gap lists --")
    no_target = [name for name, t, a in rows if t is None or not nonempty(t.get("Target"))]
    no_phase = [name for name, t, a in rows if t is None or not nonempty(t.get(phase_col))]
    no_cond = [
        name for name, t, a in rows if t is None or not any(nonempty(t.get(c)) for c in cond_cols)
    ]
    print(f"No Target: {no_target}")
    print(f"No Highest_Clin_Trial: {no_phase}")
    print(f"No any condition: {no_cond}")
    print(
        "No 842 row (IMGT primary on Thera seq):",
        df70[df70["germline_source"] == "imgt_aa_translated_primary"]["antibody_name"].tolist(),
    )
    print(
        "No classic LightSequence:",
        [name for name, t, a in rows if t is not None and not nonempty(t.get("LightSequence"))],
    )


if __name__ == "__main__":
    main()
