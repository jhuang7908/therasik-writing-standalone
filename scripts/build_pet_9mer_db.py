"""
build_pet_9mer_db.py
──────────────────────────────────────────────────────────────────────────────
 9-mer （dog / cat）

 CGC / FGC（） 9-mer 。
 HPR : score = N_found_9mers / N_total_9mers

（）
---------------------------
L1  (×3 )  — pet_antibody_atlas/master_table.csv
L2 Tier-1 scaffold (×2 ) — dog/cat_scaffold_cmc_optimization JSON
L3  (×1 )  — IMGT  FASTA  cache 


----
data/reference/pet_9mer_db/dog_9mer_v1.txt     9-mer ()
data/reference/pet_9mer_db/cat_9mer_v1.txt
data/reference/pet_9mer_db/dog_9mer_v1.json    + 
data/reference/pet_9mer_db/cat_9mer_v1.json

: 9-mer ；""，
      DB  9-mer  (set)，CGC  IN/OUT；
      meta JSON  source_counts 。

Usage:
    python scripts/build_pet_9mer_db.py
    python scripts/build_pet_9mer_db.py --species dog
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Tuple

REPO = Path(__file__).resolve().parents[1]
ATLAS_CSV = REPO / "data/pet_antibody_atlas/master_table.csv"
DOG_SCAFFOLD_JSON = REPO / "data/germlines/canis_lupus_familiaris_ig_aa/dog_scaffold_cmc_optimization_tier1_tier2_v1.json"
CAT_SCAFFOLD_JSON = REPO / "data/germlines/felis_catus_ig_aa/cat_scaffold_cmc_optimization_tier1_tier2_v1.json"

# v2 germline frequency JSONs are aggregates; we need the underlying germline
# sequences themselves. Use the cache files.
DOG_GERMLINE_CACHE = {
    "IGHV": REPO / "data/germlines/canis_lupus_familiaris_ig_aa/_cache/dog_ighv_kabat_numbered_cache.json",
    "IGKV": REPO / "data/germlines/canis_lupus_familiaris_ig_aa/_cache/dog_igkv_kabat_numbered_cache.json",
    "IGLV": REPO / "data/germlines/canis_lupus_familiaris_ig_aa/_cache/dog_iglv_kabat_numbered_cache.json",
}
CAT_GERMLINE_CACHE = {
    "IGHV": REPO / "data/germlines/felis_catus_ig_aa/_cache/cat_ighv_kabat_numbered_cache.json",
    "IGKV": REPO / "data/germlines/felis_catus_ig_aa/_cache/cat_igkv_kabat_numbered_cache.json",
    "IGLV": REPO / "data/germlines/felis_catus_ig_aa/_cache/cat_iglv_kabat_numbered_cache.json",
}

OUT_DIR = REPO / "data/reference/pet_9mer_db"


def chop_9mers(seq: str) -> List[str]:
    """Slide a 9-aa window across a sequence; return all 9-mers (uppercase)."""
    if not seq or len(seq) < 9:
        return []
    s = seq.strip().upper()
    return [s[i:i + 9] for i in range(len(s) - 9 + 1)]


def load_atlas_seqs(species: str) -> List[Tuple[str, str]]:
    """Return list of (antibody_id, seq) for VH and VL across the species."""
    out = []
    with ATLAS_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pet = row.get("pet_type", "").strip().lower()
            if species == "dog" and pet != "canine":
                continue
            if species == "cat" and pet != "feline":
                continue
            ab_id = row.get("antibody_id", "")
            for col in ("vh_seq", "vl_seq"):
                seq = row.get(col, "").strip()
                if seq and len(seq) > 60:
                    out.append((f"{ab_id}|{col}", seq))
    return out


def load_scaffold_seqs(species: str) -> List[str]:
    """Load Tier-1 scaffold sequences across all loci for the species."""
    path = DOG_SCAFFOLD_JSON if species == "dog" else CAT_SCAFFOLD_JSON
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for row in data.get("rows", []):
        if row.get("tier") != "tier1":
            continue
        seq = row.get("sequence_aa_kabat_norm") or row.get("sequence_aa_imgt", "")
        if seq and len(seq) > 50:
            out.append(seq)
    return out


def _sort_pos_key(k: str) -> Tuple[int, str]:
    """Sort key for Kabat position strings like '52', '52A', '82B'."""
    digits = "".join(c for c in k if c.isdigit())
    letters = "".join(c for c in k if c.isalpha())
    try:
        n = int(digits) if digits else 0
    except Exception:
        n = 0
    return (n, letters)


def load_germline_seqs(species: str) -> List[str]:
    """
    Reconstruct linear AA sequences from Kabat-numbered cache files.
    Cache format: {"genes": {gene_id: {pos_str: aa_char, ...}, ...}}
    """
    cache_map = DOG_GERMLINE_CACHE if species == "dog" else CAT_GERMLINE_CACHE
    out = []
    for locus, cache_path in cache_map.items():
        if not cache_path.is_file():
            print(f"  [WARN] cache missing: {cache_path}", file=sys.stderr)
            continue
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  [WARN] failed to parse {cache_path}: {e}", file=sys.stderr)
            continue
        genes = data.get("genes", {})
        for gene_id, pos_map in genes.items():
            if not isinstance(pos_map, dict):
                continue
            try:
                ordered = sorted(pos_map.items(), key=lambda kv: _sort_pos_key(kv[0]))
                seq = "".join(
                    aa for _, aa in ordered
                    if aa and aa != "-" and isinstance(aa, str) and aa.isalpha()
                )
                if len(seq) > 60:
                    out.append(seq)
            except Exception:
                continue
    return out


def build_db(species: str) -> Dict:
    print(f"\n[{species.upper()}] Loading data sources ...")

    atlas = load_atlas_seqs(species)
    scaffolds = load_scaffold_seqs(species)
    germlines = load_germline_seqs(species)

    print(f"  L1 clinical sequences: {len(atlas)}")
    print(f"  L2 Tier-1 scaffold sequences: {len(scaffolds)}")
    print(f"  L3 germline sequences: {len(germlines)}")

    nine_mer_counts: Dict[str, int] = defaultdict(int)
    source_counts = {"L1_clinical": 0, "L2_scaffold": 0, "L3_germline": 0}

    # L1 (×3 weight via 3 insertions per 9-mer)
    for ab_id, seq in atlas:
        mers = chop_9mers(seq)
        source_counts["L1_clinical"] += len(mers)
        for m in mers:
            nine_mer_counts[m] += 3

    # L2 (×2)
    for seq in scaffolds:
        mers = chop_9mers(seq)
        source_counts["L2_scaffold"] += len(mers)
        for m in mers:
            nine_mer_counts[m] += 2

    # L3 (×1)
    for seq in germlines:
        mers = chop_9mers(seq)
        source_counts["L3_germline"] += len(mers)
        for m in mers:
            nine_mer_counts[m] += 1

    unique_9mers = set(nine_mer_counts.keys())
    print(f"  Unique 9-mers in DB: {len(unique_9mers)}")

    return {
        "metadata": {
            "db_id": f"{species}_9mer_v1",
            "species": "Canis lupus familiaris" if species == "dog" else "Felis catus",
            "purpose": "Reference library for CGC/FGC (Canine/Feline Germline Coefficient) — mirrors HPR design",
            "construction": {
                "L1_weight": 3,
                "L2_weight": 2,
                "L3_weight": 1,
                "saturation_note": "9-mer presence is binary in lookup; weights stored for provenance",
            },
            "source_counts": source_counts,
            "unique_9mers": len(unique_9mers),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "pet_9mer_db_v1",
        },
        "nine_mer_counts": dict(nine_mer_counts),  # full counts for audit
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Build pet 9-mer reference DB (dog / cat)")
    ap.add_argument("--species", choices=["dog", "cat", "both"], default="both")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target = ["dog", "cat"] if args.species == "both" else [args.species]

    for sp in target:
        db = build_db(sp)
        json_path = OUT_DIR / f"{sp}_9mer_v1.json"
        txt_path = OUT_DIR / f"{sp}_9mer_v1.txt"
        json_path.write_text(json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")
        with txt_path.open("w", encoding="utf-8") as fh:
            for mer in sorted(db["nine_mer_counts"].keys()):
                fh.write(mer + "\n")
        print(f"  JSON  → {json_path}")
        print(f"  TXT   → {txt_path}")


if __name__ == "__main__":
    main()
