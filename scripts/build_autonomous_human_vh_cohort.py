"""
build_autonomous_human_vh_cohort.py — InSynBio AbEngineCore
============================================================
Constructs a clean, non-redundant autonomous-human-VH reference cohort
from the local Database A (autonomous_human_vh_db.json, n=138).

Output (new files only, no LOCKED files modified):
  data/reference/AutonomousHumanVH_Cohort_v1.json
  data/reference/AutonomousHumanVH_Cohort_v1.csv

Pipeline:
  1. Load Database A (138 entries).
  2. Flag nanobody/VHH contamination by keyword + camelid hallmark signature.
  3. Strip signal-peptide prefix; isolate VH domain via ANARCII.
  4. Deduplicate by V-region (Kabat 1-113) SHA1 hash.
  5. Re-compute Kabat residues at 18, 37, 44, 45, 47, 50, 68, 89, 94.
  6. Annotate CDR3 length (Kabat 95-102) and compactness if available.
  7. Write cohort JSON + CSV.

Cohort ID: autonomous_human_vh_v1_0_2026-05-14
"""

from __future__ import annotations

import collections
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd
from anarcii import Anarcii

ROOT = Path(__file__).resolve().parents[1]

# ── input ──────────────────────────────────────────────────────────────────
DB_A_PATH = ROOT / "data/sabdab_vhh_atlas/autonomous_human_vh_db.json"

# ── output (new files; directories must already exist) ─────────────────────
OUT_JSON = ROOT / "data/reference/AutonomousHumanVH_Cohort_v1.json"
OUT_CSV  = ROOT / "data/reference/AutonomousHumanVH_Cohort_v1.csv"

# ── constants ──────────────────────────────────────────────────────────────
COHORT_ID = "autonomous_human_vh_v1_0_2026-05-14"
COHORT_DATE = str(date.today())

KABAT_POSITIONS_EXTRA = [18, 50, 68, 89, 94]   # not pre-computed in DB
KABAT_POSITIONS_ALL   = [18, 37, 44, 45, 47, 50, 68, 89, 94]

# Nanobody/VHH contamination: keyword match in entry_name or target
NB_KEYWORDS = [
    "nanobody", "vhh", "xaperone", "llama", "camel", "dromedary",
    "caplacizumab", "envafolimab", "ozoralizumab",
]

# VHH hallmark pattern: E44 + R45 strongly indicates camelid VHH
def _is_camelid_hallmark(hr: dict) -> bool:
    return hr.get("pos44", "?") == "E" and hr.get("pos45", "?") == "R"


def _has_nb_keyword(entry: dict) -> bool:
    name   = (entry.get("entry_name", "") or "").lower()
    target = (entry.get("target", "")      or "").lower()
    return any(kw in name or kw in target for kw in NB_KEYWORDS)


# ── ANARCII helpers ─────────────────────────────────────────────────────────
def kabat_numbering(seq: str) -> Optional[Dict[Tuple[int, str], str]]:
    try:
        engine = Anarcii()
        engine.number([("seq", seq)])
        result = engine.to_scheme("kabat")
        if "seq" not in result or not result["seq"]:
            return None
        return {
            (pos, ins.strip()): aa
            for (pos, ins), aa in result["seq"]["numbering"]
            if aa != "-"
        }
    except Exception as exc:
        print(f"  [WARN] ANARCII failed: {exc}", file=sys.stderr)
        return None


def vregion_hash(kd: Dict[Tuple[int, str], str]) -> str:
    """SHA1 of the V-region sequence (Kabat 1..113, including insertion codes)."""
    residues = "".join(
        aa for (pos, _ins), aa in sorted(kd.items()) if pos <= 113
    )
    return hashlib.sha1(residues.encode()).hexdigest()[:12]


def cdr3_length(kd: Dict[Tuple[int, str], str]) -> int:
    return sum(1 for (pos, _ins) in kd if 95 <= pos <= 102)


def residue_at(kd: Dict[Tuple[int, str], str], pos: int) -> str:
    return kd.get((pos, ""), "?")


# ── main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    print(f"Loading {DB_A_PATH} …")
    entries = json.loads(DB_A_PATH.read_text(encoding="utf-8"))
    print(f"  raw n = {len(entries)}")

    # ── step 1: contamination flagging ──
    for e in entries:
        hr = e.get("hallmark_residues", {})
        e["_flag_nb_keyword"] = _has_nb_keyword(e)
        e["_flag_camelid_hm"] = _is_camelid_hallmark(hr)
        e["_contaminated"]    = e["_flag_nb_keyword"] or e["_flag_camelid_hm"]

    n_contam = sum(1 for e in entries if e["_contaminated"])
    print(f"  contaminated (keyword|camelid hallmark) = {n_contam}")
    clean = [e for e in entries if not e["_contaminated"]]
    print(f"  after contamination filter = {len(clean)}")

    # ── step 2: ANARCII numbering + deduplication ──
    print("Running ANARCII (Kabat) on all clean sequences …")
    processed: list[dict] = []
    seen_hashes: dict[str, str] = {}   # hash → representative pdb_chain

    for e in clean:
        seq   = e.get("sequence", "")
        label = f"{e.get('pdb', '?')}_{e.get('chain', '?')}"
        kd    = kabat_numbering(seq)
        if kd is None:
            print(f"  [SKIP] {label}: ANARCII returned no result")
            continue

        vh = vregion_hash(kd)
        if vh in seen_hashes:
            # duplicate V-region — keep only first occurrence
            continue
        seen_hashes[vh] = label

        # pre-computed hallmarks from DB (already in Kabat per DB annotation)
        hr = e.get("hallmark_residues", {})
        cdr_info = e.get("cdr_lengths", {})

        row = {
            "cohort_id":    COHORT_ID,
            "pdb":          e.get("pdb"),
            "chain":        e.get("chain"),
            "entry_name":   e.get("entry_name"),
            "target":       e.get("target"),
            "heavy_species":e.get("heavy_species"),
            "engineered":   e.get("engineered"),
            "germline_family":      e.get("germline_family"),
            "germline_best_match":  e.get("germline_best_match"),
            "germline_identity":    e.get("germline_identity"),
            "v_seq_hash":   vh,
            # CDR lengths from DB
            "CDR1_len":     cdr_info.get("CDR1_len"),
            "CDR2_len":     cdr_info.get("CDR2_len"),
            "CDR3_len":     cdr_info.get("CDR3_len"),
            # CDR3 from ANARCII (cross-check)
            "cdr3_len_kabat": cdr3_length(kd),
            # Kabat hallmark positions (all re-computed from ANARCII for consistency)
            "k37": residue_at(kd, 37),
            "k44": residue_at(kd, 44),
            "k45": residue_at(kd, 45),
            "k47": residue_at(kd, 47),
            "k18": residue_at(kd, 18),
            "k50": residue_at(kd, 50),
            "k68": residue_at(kd, 68),
            "k89": residue_at(kd, 89),
            "k94": residue_at(kd, 94),
            # Hallmark motif (DB pre-computed, for cross-check)
            "hallmark_motif_db": hr.get("hallmark_motif"),
        }
        processed.append(row)

    print(f"  non-redundant clean sequences = {len(processed)}")

    # ── step 3: CDR3 stratification ──
    df = pd.DataFrame(processed)
    df["cdr3_bucket"] = pd.cut(
        df["cdr3_len_kabat"],
        bins=[0, 7, 14, 999],
        labels=["short_le7", "mid_8to14", "long_ge15"],
    )

    # ── step 4: print summary ──
    print("\n=== CDR3 length distribution (Kabat-based) ===")
    print(df["cdr3_len_kabat"].value_counts().sort_index().to_string())

    print("\n=== CDR3 bucket distribution ===")
    print(df["cdr3_bucket"].value_counts().to_string())

    print("\n=== Residue frequencies at key Kabat positions ===")
    for pos in ["k37", "k44", "k45", "k47", "k18", "k50", "k68", "k89", "k94"]:
        counts = collections.Counter(df[pos])
        total  = sum(counts.values())
        ranked = "  ".join(f"{aa}:{c/total:.0%}" for aa, c in counts.most_common(5))
        print(f"  {pos.upper():>4}: {ranked}")

    print("\n=== Residue frequencies stratified by CDR3 bucket ===")
    for bucket, sub in df.groupby("cdr3_bucket", observed=True):
        n = len(sub)
        if n == 0:
            continue
        print(f"\n  [{bucket}]  n={n}")
        for pos in ["k37", "k44", "k45", "k47", "k50", "k68", "k89"]:
            counts = collections.Counter(sub[pos])
            total  = sum(counts.values())
            ranked = "  ".join(f"{aa}:{c/total:.0%}" for aa, c in counts.most_common(5))
            print(f"    {pos.upper():>4}: {ranked}")

    print("\n=== Hallmark motif cross-check (DB pre-computed vs ANARCII Kabat) ===")
    df["hm_recomputed"] = df["k37"] + df["k44"] + df["k45"] + df["k47"]
    mismatches = df[df["hallmark_motif_db"] != df["hm_recomputed"]]
    if mismatches.empty:
        print("  All hallmark motifs match. ✓")
    else:
        print(f"  {len(mismatches)} mismatches:")
        print(mismatches[["pdb","chain","hallmark_motif_db","hm_recomputed"]].to_string())

    # ── step 5: write outputs ──
    meta = {
        "cohort_id":   COHORT_ID,
        "build_date":  COHORT_DATE,
        "source_file": str(DB_A_PATH.relative_to(ROOT)),
        "n_raw":       len(entries),
        "n_after_contamination_filter": len(clean),
        "n_unique_vregion": len(processed),
        "contamination_filter": {
            "keyword_match": [e["entry_name"] for e in entries if e["_flag_nb_keyword"]],
            "camelid_hallmark": [e["entry_name"] for e in entries if e["_flag_camelid_hm"]],
        },
        "kabat_positions_analyzed": KABAT_POSITIONS_ALL,
        "cdr3_buckets": {"short_le7": "CDR3 ≤7 aa", "mid_8to14": "CDR3 8-14 aa", "long_ge15": "CDR3 ≥15 aa"},
        "status": "PRELIMINARY — pending V1.8.6 owner review",
        "notes": "Hallmark positions (37/44/45/47) re-computed via ANARCII Kabat scheme; not from DB pre-annotation. Other positions (18/50/68/89/94) also via ANARCII Kabat.",
    }

    df_out = df.drop(columns=["cdr3_bucket"])   # cat column not JSON serializable
    records = df_out.to_dict(orient="records")

    out_payload = {"_meta": meta, "entries": records}
    OUT_JSON.write_text(
        json.dumps(out_payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    df_out.to_csv(OUT_CSV, index=False)

    print(f"\nWrote {OUT_JSON}")
    print(f"Wrote {OUT_CSV}")
    print("Done.")


if __name__ == "__main__":
    main()
