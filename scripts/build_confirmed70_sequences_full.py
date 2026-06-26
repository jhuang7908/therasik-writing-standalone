#!/usr/bin/env python3
"""
Per-drug amino-acid sequences for the confirmed-70 panel (Thera + atlas fallbacks).

- Standard mAb: HeavySequence / LightSequence from TheraSAbDab.
- Bispecific Ig-like: includes HeavySequence(ifbispec) / LightSequence(ifbispec).
- Tarlatamab: adds scFv full sequence from scfv_52_atlas (VH-linker-VL) for convenience.
- Ozoralizumab: two anti-TNFα VHH arms from Thera; third domain = ALB8 anti-HSA VHH
  from PDB 8Z8V chain B (SEQRES, aa 1–117; experimental His×6 tag in deposit excluded).

Output: data/thera_sabdab/out/confirmed70_sequences_full.csv
Reads:  confirmed70_human_humanized_germline_ada.csv, Thera xlsx, scfv_52 master_table (optional)
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

SUITE = Path(__file__).resolve().parents[1]
LIST70 = SUITE / "data/thera_sabdab/out/confirmed70_human_humanized_germline_ada.csv"
THERA = SUITE / "data/thera_sabdab/TheraSAbDab_SeqStruc_OnlineDownload.xlsx"
SCFV52 = SUITE / "data/scfv_52_atlas/master_table.csv"
ABARCII = SUITE / "data/thera_sabdab/out/anarcii_numbering_70.csv"
OUT = SUITE / "data/thera_sabdab/out/confirmed70_sequences_full.csv"

# ALB8 albumin-binding VHH (central domain of trivalent ozoralizumab). Source: PDB 8Z8V
# chain B SEQRES; title "ALB8(VHH) domain of ozoralizumab" + PMID 39083975 / BBRC 2024.
# Deposit includes C-terminal HHHHHH (purification); excluded here for drug-relevant VHH.
OZORALIZUMAB_ALB8_VHH_AA = (
    "EVQLVESGGGLVQPGNSLRLSCAASGFTFSSFGMSWVRQAPGKGLEWVSSISGSGSDTLYADSVKGRFTISRDNAKTT"
    "LYLQMNSLRPEDTAVYYCTIGGSLSRSSQGTLVTVSSTS"
)


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


def clean_aa(x: object) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    s = str(x).strip()
    if len(s) < 8 or s.lower() in ("nan", "na", "none"):
        return ""
    return s


def load_scfv_full() -> dict[str, str]:
    if not SCFV52.is_file():
        return {}
    out: dict[str, str] = {}
    with SCFV52.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            aid = str(row.get("antibody_id", "")).strip()
            seq = clean_aa(row.get("full_sequence", ""))
            if aid and seq:
                out[norm(aid)] = seq
    return out


def anarcii_keys_for_drug(drug: str) -> str:
    if not ABARCII.is_file():
        return ""
    df = pd.read_csv(ABARCII)
    sub = df[df["drug"].astype(str) == drug]["anarcii_key"].astype(str).tolist()
    return ";".join(sub)


def main() -> None:
    df70 = pd.read_csv(LIST70)
    thera_ix = load_thera_index()
    scfv_full = load_scfv_full()

    rows: list[dict[str, str]] = []
    for name in df70["antibody_name"].astype(str):
        k1, k2 = norm(name), bio_strip(name)
        trow = None
        for k in (k1, k2):
            if k and k in thera_ix:
                trow = thera_ix[k]
                break
        if trow is None:
            raise SystemExit(f"Thera row missing for {name}")

        fmt = str(trow.get("Format", "") or "")
        h1 = clean_aa(trow.get("HeavySequence"))
        l1 = clean_aa(trow.get("LightSequence"))
        h2 = clean_aa(trow.get("HeavySequence(ifbispec)"))
        l2 = clean_aa(trow.get("LightSequence(ifbispec)"))

        scfv = scfv_full.get(k1) or scfv_full.get(k2) or ""

        vhh1, vhh2, vhh3 = "", "", ""
        notes = ""
        if "ozoralizumab" in name.lower():
            vhh1, vhh2 = h1, h2
            vhh3 = OZORALIZUMAB_ALB8_VHH_AA
            notes = (
                "Layout TNF30–(G4S)9–ALB8–(G4S)9–TNF30 (reviews: PMC11055793; PMID 38681878). "
                "Thera export: heavy col1 = anti-TNFα VHH; heavy col2 = ALB8 through 115 aa (missing "
                "C-terminal TS vs full domain). vhh3 = full ALB8 anti-HSA 117 aa from PDB 8Z8V chain B "
                "(PMID 39083975; crystal His6 tag excluded). Second anti-TNFα arm may match col1 if "
                "TNF30 is duplicated. Cross-check WHO INN / JP SmPC / US8703131 SEQ IDs."
            )
        elif h2 and not l1:
            vhh1, vhh2 = h1, h2
            notes = "Two heavy-domain arms from Thera; no classical light chain in export."

        src = "TheraSAbDab_SeqStruc_OnlineDownload.xlsx"
        if scfv and name == "Tarlatamab":
            src += "; scfv_52_atlas master_table.csv full_sequence"
        if "ozoralizumab" in name.lower():
            src += "; PDB 8Z8V chain B (ALB8 VHH) PMID 39083975"

        rows.append(
            {
                "antibody_name": name,
                "thera_format": fmt,
                "arm1_heavy_aa": h1,
                "arm1_light_aa": l1,
                "arm2_heavy_aa": h2,
                "arm2_light_aa": l2,
                "scfv_full_aa_atlas": scfv if name == "Tarlatamab" else "",
                "vhh1_aa": vhh1,
                "vhh2_aa": vhh2,
                "vhh3_aa": vhh3,
                "sequence_notes": notes,
                "sequence_sources": src,
                "imgt_annotation_file": "data/thera_sabdab/out/anarcii_numbering_70.csv",
                "anarcii_keys": anarcii_keys_for_drug(name),
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {OUT} ({len(rows)} rows).")


if __name__ == "__main__":
    main()
