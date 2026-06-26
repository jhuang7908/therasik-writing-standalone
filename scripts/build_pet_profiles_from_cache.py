"""
Build dog and cat amino-acid replacement frequency profiles (v2)
from pre-built numbered caches.  Outputs flat {pos: {aa: float}} format,
identical schema to human_replacement_profiles_v1.

Run (no conda required — only reads JSON files):
    python scripts/build_pet_profiles_from_cache.py

Prerequisites:
    data/germlines/canis_lupus_familiaris_ig_aa/_cache/dog_ighv_kabat_numbered_cache.json
    data/germlines/canis_lupus_familiaris_ig_aa/_cache/dog_igkv_kabat_numbered_cache.json
    data/germlines/canis_lupus_familiaris_ig_aa/_cache/dog_iglv_kabat_numbered_cache.json
    data/germlines/felis_catus_ig_aa/_cache/cat_ighv_kabat_numbered_cache.json
    data/germlines/felis_catus_ig_aa/_cache/cat_igkv_kabat_numbered_cache.json
    data/germlines/felis_catus_ig_aa/_cache/cat_iglv_kabat_numbered_cache.json

Output: data/reference/pet_replacement_profiles/v2/
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]

DOG_CACHE_DIR = REPO / "data/germlines/canis_lupus_familiaris_ig_aa/_cache"
CAT_CACHE_DIR = REPO / "data/germlines/felis_catus_ig_aa/_cache"
OUT_DIR = REPO / "data/reference/pet_replacement_profiles/v2"

# Abundance prior for dog (from published BCR-seq repertoire stats)
# gene -> relative_weight (>1 = more abundant, 1 = default)
DOG_REPERTOIRE = REPO / "data/germlines/canis_lupus_familiaris_ig_aa/dog_repertoire_and_dla_stats.json"

AA_ORDER = "ACDEFGHIKLMNPQRSTVWY"


def _load(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def _write(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _kabat_key(k: str) -> tuple[int, str]:
    d = "".join(c for c in k if c.isdigit())
    a = "".join(c for c in k if c.isalpha())
    return (int(d) if d else 0, a)


def _norm(cnt: Counter) -> dict[str, float]:
    tot = sum(cnt.values())
    if not tot:
        return {}
    return {aa: round(cnt[aa] / tot, 6) for aa in AA_ORDER if cnt[aa] > 0}


def _load_dog_weights() -> dict[str, float]:
    """Return {gene_id: abundance_weight} for dog from repertoire stats."""
    if not DOG_REPERTOIRE.exists():
        return {}
    try:
        data = _load(DOG_REPERTOIRE)
        weights: dict[str, float] = {}
        # Look for abundance data under various field names
        for field in ("ighv_abundance", "vh_abundance", "gene_abundance", "repertoire"):
            if field in data:
                for gene, val in data[field].items():
                    if isinstance(val, (int, float)) and val > 0:
                        weights[gene] = float(val)
                break
        return weights
    except Exception:
        return {}


def build_profile_from_cache(
    cache_path: Path,
    species: str,
    species_name: str,
    locus: str,
    gene_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Aggregate a Kabat numbered cache into a flat {pos: {aa: float}} profile."""
    cache = _load(cache_path)
    meta_in = cache.get("_meta", {})
    genes = cache.get("genes", {})

    counts: dict[str, Counter] = defaultdict(Counter)
    n_genes = 0

    for gid, pos_map in genes.items():
        if not isinstance(pos_map, dict) or not pos_map:
            continue
        n_genes += 1
        w = 1.0
        if gene_weights:
            # Try exact match and prefix match (e.g. IGHV3-38 → IGHV3-38*01)
            w = gene_weights.get(gid, 0.0)
            if w == 0.0:
                base = gid.split("*")[0]
                w = gene_weights.get(base, 1.0)
        for pos_key, aa in pos_map.items():
            if isinstance(aa, str) and aa in AA_ORDER:
                counts[str(pos_key)][aa] += w

    positions: dict[str, dict[str, float]] = {}
    for key in sorted(counts, key=_kabat_key):
        nrm = _norm(counts[key])
        if nrm:
            positions[key] = nrm

    weighting = "abundance_weighted" if gene_weights else "unweighted_germline_count"

    return {
        "metadata": {
            "profile_id": f"{species}_{locus.lower()}_aa_freq_kabat_v2",
            "species": species_name,
            "locus": locus,
            "numbering_scheme": "Kabat",
            "data_type": "germline_frequency",
            "source_cache": str(cache_path.relative_to(REPO)),
            "n_genes_input": meta_in.get("n_input"),
            "n_genes_cached": meta_in.get("n_cached"),
            "n_genes_numbered_ok": n_genes,
            "n_positions": len(positions),
            "weighting": weighting,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "position_to_aa_fraction_v1",
        },
        "positions": positions,
    }


def write_readme(profiles: list[dict[str, Any]]) -> None:
    rows = []
    for p in profiles:
        m = p["metadata"]
        fn = f"{m['profile_id']}.json"
        rows.append(
            f"| `{fn}` | {m['species']} | {m['locus']} | "
            f"{m['n_positions']} | {m['weighting']} |"
        )

    lines = [
        "# Pet Replacement Profiles v2",
        "",
        "**Format:** Identical to `human_replacement_profiles/v1` — flat `{pos: {aa: float}}`.",
        "",
        "| File | Species | Locus | n_positions | Weighting |",
        "|---|---|---|---|---|",
        *rows,
        "",
        "## Regenerate",
        "",
        "Step 1 (conda env anarcii, one-time):",
        "```bash",
        "conda run --no-capture-output -n anarcii python scripts/build_dog_numbered_cache.py",
        "conda run --no-capture-output -n anarcii python scripts/build_cat_numbered_cache.py",
        "```",
        "",
        "Step 2 (no conda required):",
        "```bash",
        "python scripts/build_pet_profiles_from_cache.py",
        "```",
        "",
        f"Generated: {datetime.now(timezone.utc).date()}",
    ]
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


SPECS = [
    # (cache_file, species_key, species_name, locus, use_abundance)
    ("dog_ighv_kabat_numbered_cache.json", "dog", "Canis lupus familiaris", "IGHV", True),
    ("dog_igkv_kabat_numbered_cache.json", "dog", "Canis lupus familiaris", "IGKV", True),
    ("dog_iglv_kabat_numbered_cache.json", "dog", "Canis lupus familiaris", "IGLV", True),
    ("cat_ighv_kabat_numbered_cache.json", "cat", "Felis catus", "IGHV", False),
    ("cat_igkv_kabat_numbered_cache.json", "cat", "Felis catus", "IGKV", False),
    ("cat_iglv_kabat_numbered_cache.json", "cat", "Felis catus", "IGLV", False),
]

CACHE_DIRS = {
    "dog": DOG_CACHE_DIR,
    "cat": CAT_CACHE_DIR,
}


def main() -> None:
    dog_weights = _load_dog_weights()
    if dog_weights:
        print(f"Loaded dog abundance weights for {len(dog_weights)} genes.")
    else:
        print("No dog abundance weights found; using unweighted germline counts.")

    profiles: list[dict[str, Any]] = []
    missing: list[str] = []

    for fname, species, species_name, locus, use_abund in SPECS:
        cache_path = CACHE_DIRS[species] / fname
        if not cache_path.exists():
            missing.append(str(cache_path.relative_to(REPO)))
            continue
        print(f"[{species.upper()} {locus}] Building from {fname} ...")
        weights = dog_weights if (use_abund and species == "dog") else None
        profile = build_profile_from_cache(cache_path, species, species_name, locus, weights)
        n = profile["metadata"]["n_positions"]
        print(f"  {n} positions, weighting={profile['metadata']['weighting']}")
        _write(OUT_DIR / f"{profile['metadata']['profile_id']}.json", profile)
        profiles.append(profile)

    write_readme(profiles)

    if missing:
        print(f"\nWARNING: {len(missing)} cache file(s) not found (run cache builders first):")
        for m in missing:
            print(f"  {m}")
        sys.exit(1)

    print(f"\nAll profiles written to {OUT_DIR}")


if __name__ == "__main__":
    main()
