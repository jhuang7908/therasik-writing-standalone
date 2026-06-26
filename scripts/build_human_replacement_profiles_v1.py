#!/usr/bin/env python3
"""
Build human IGHV / IGKV / IGLV Kabat position amino-acid frequency profiles (v1).

All three chains are generated from sources already on disk — no live ANARCI run required.

- IGHV  : Llamanade ANARCI_Hum_H.json  (NGS cohort, ~22k human VH sequences)
- IGKV  : igkv_numbered_cache.json      (IMGT functional germlines, full Kabat position maps)
- IGLV  : data/germlines/human_ig_aa/_cache/IGLV_kabat_cache.json
          (IMGT functional germlines; full-sequence Kabat maps for 115 genes)

Run:
    python scripts/build_human_replacement_profiles_v1.py
No conda env required.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "data" / "reference" / "human_replacement_profiles" / "v1"

LLAMANADE_VH = (
    REPO_ROOT
    / "external" / "llamanade" / "Llamanade_upstream"
    / "resources" / "resources" / "ANARCI_Hum_H.json"
)
IGKV_NUMBERED = (
    REPO_ROOT / "data" / "germlines" / "human_ig_aa" / "igkv_numbered_cache.json"
)
IGLV_CACHE = (
    REPO_ROOT / "data" / "germlines" / "human_ig_aa" / "_cache" / "IGLV_kabat_cache.json"
)
IGHV_CACHE = (
    REPO_ROOT / "data" / "germlines" / "human_ig_aa" / "_cache" / "IGHV_kabat_cache.json"
)

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


# ─── 1. Human VH from Llamanade NGS profile ───────────────────────────────────

def build_ighv_llamanade() -> dict[str, Any]:
    raw = _load(LLAMANADE_VH)
    # raw is already a dict of kabat_pos_str -> {aa: freq}
    return {
        "metadata": {
            "profile_id": "human_ighv_aa_freq_llamanade_ngs_v1",
            "species": "Homo sapiens",
            "locus": "IGHV",
            "numbering_scheme": "Kabat",
            "data_type": "ngs_empirical_cohort",
            "source_file": str(LLAMANADE_VH.relative_to(REPO_ROOT)),
            "cohort_note": (
                "Human VH per-position amino-acid frequencies derived from a large "
                "human VH NGS cohort (described in Llamanade upstream resources as "
                "EMBL-Ig-derived; ~22k sequences). Values are empirical NGS frequencies, "
                "NOT germline counts."
            ),
            "n_positions": len(raw),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "position_to_aa_fraction_v1",
        },
        "positions": raw,
    }


# ─── 2. Human Kappa from igkv_numbered_cache ──────────────────────────────────

def build_igkv() -> dict[str, Any]:
    cache = _load(IGKV_NUMBERED)
    counts: dict[str, Counter] = defaultdict(Counter)
    n_genes = 0
    for gene, pmap in cache.items():
        if not isinstance(pmap, dict):
            continue
        n_genes += 1
        for pos_key, aa in pmap.items():
            if isinstance(aa, str) and aa in AA_ORDER:
                counts[str(pos_key)][aa] += 1
    positions: dict[str, dict[str, float]] = {}
    for key in sorted(counts, key=_kabat_key):
        positions[key] = _norm(counts[key])
    return {
        "metadata": {
            "profile_id": "human_igkv_aa_freq_imgt_germline_v1",
            "species": "Homo sapiens",
            "locus": "IGKV",
            "numbering_scheme": "Kabat",
            "data_type": "imgt_germline_frequency",
            "source_file": str(IGKV_NUMBERED.relative_to(REPO_ROOT)),
            "n_genes": n_genes,
            "n_positions": len(positions),
            "cohort_note": (
                "Per-position amino-acid frequencies over IMGT human κ functional "
                "germline genes from the frozen igkv_numbered_cache. All genes are "
                "equally weighted (unweighted germline frequency). "
                "Does NOT include somatic hypermutation variation."
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "position_to_aa_fraction_v1",
        },
        "positions": positions,
    }


# ─── 3. Human Lambda from IGLV_kabat_cache ────────────────────────────────────
# The cache stores `kabat_position_str -> aa` maps for each gene's vernier residues.
# For the full FR1-FR3 sequence positions we parse the kabat_cdr_lengths to locate
# boundaries, then walk the sequence with the CDR mask.
#
# Simpler, zero-dependency approach: aggregate ALL individual residue positions that
# appear in `vernier_residues` (a sparse but complete set for the Vernier zone),
# AND independently build FR-only position map from sequence_aa by aligning to a
# fixed Kabat numbering implied by the cache (positions 1..113 as in κ/λ Kabat).
# We use only the positions that IGLV_kabat_cache.json explicitly stores as keys
# — this avoids any guessing about gapped positions.

def _iglv_gene_positions(gene_entry: dict[str, Any]) -> dict[str, str]:
    """Return {kabat_pos_str: aa} for one IGLV gene from its cache entry."""
    result: dict[str, str] = {}
    vr = gene_entry.get("vernier_residues")
    if isinstance(vr, dict):
        for k, v in vr.items():
            if isinstance(v, str) and v in AA_ORDER:
                result[str(k)] = v
    return result


def build_iglv() -> dict[str, Any]:
    cache = _load(IGLV_CACHE)
    meta_in = cache.get("_meta", {})
    genes = cache.get("genes", {})

    counts: dict[str, Counter] = defaultdict(Counter)
    n_genes = 0

    for gid, entry in genes.items():
        if not isinstance(entry, dict):
            continue
        positions = _iglv_gene_positions(entry)
        if not positions:
            continue
        n_genes += 1
        for key, aa in positions.items():
            counts[key][aa] += 1

    positions_out: dict[str, dict[str, float]] = {}
    for key in sorted(counts, key=_kabat_key):
        positions_out[key] = _norm(counts[key])

    return {
        "metadata": {
            "profile_id": "human_iglv_aa_freq_imgt_germline_v1",
            "species": "Homo sapiens",
            "locus": "IGLV",
            "numbering_scheme": "Kabat",
            "data_type": "imgt_germline_frequency",
            "source_file": str(IGLV_CACHE.relative_to(REPO_ROOT)),
            "n_genes": n_genes,
            "n_positions": len(positions_out),
            "n_genes_in_cache": meta_in.get("n_cached"),
            "coverage_note": (
                "Covers Vernier zone positions extracted from IGLV_kabat_cache.json. "
                "Full-sequence Kabat maps require ANARCI re-run (see v2 TODO). "
                "Sufficient for Vernier-position frequency lookups."
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "position_to_aa_fraction_v1",
        },
        "positions": positions_out,
    }


# ─── README ───────────────────────────────────────────────────────────────────

def write_readme(profiles: list[dict[str, Any]]) -> None:
    lines = [
        "# Human Replacement Profiles v1",
        "",
        "**Purpose:** Usable, scientifically attributable Kabat-position amino-acid "
        "frequency tables for humanization engineering lookup.",
        "",
        "| File | Locus | Data type | n_positions | Source |",
        "|---|---|---|---|---|",
    ]
    for p in profiles:
        m = p["metadata"]
        fn = f"{m['profile_id']}.json"
        lines.append(
            f"| `{fn}` | {m['locus']} | {m['data_type']} | "
            f"{m['n_positions']} | {m['source_file']} |"
        )
    lines += [
        "",
        "## When to use which table",
        "",
        "- **IGHV (Llamanade NGS):** Use as the primary human-frequency prior for VH / VHH",
        "  humanization position-by-position frequency gate.  This is an empirical NGS cohort —",
        "  not a germline count — and is the scientifically strongest VH reference available",
        "  in-repo without running new sequencing.",
        "",
        "- **IGKV (IMGT germline):** Use for κ light-chain position frequency lookups.",
        "  These are unweighted over all functional human κ germline V genes;",
        "  does not include somatic hypermutation diversity.",
        "",
        "- **IGLV (IMGT germline, Vernier positions):** Use for Vernier-zone λ light-chain",
        "  frequency lookups. Full-sequence Kabat coverage is a v2 TODO.",
        "",
        "## Regenerate",
        "",
        "```bash",
        "python scripts/build_human_replacement_profiles_v1.py",
        "```",
        "",
        "No conda environment required.",
        "",
        "## Version history",
        f"- v1  {datetime.now(timezone.utc).date()}  Initial release.",
    ]
    (OUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    missing = [p for p in (LLAMANADE_VH, IGKV_NUMBERED, IGLV_CACHE) if not p.is_file()]
    if missing:
        for m in missing:
            print(f"ERROR missing: {m}", file=sys.stderr)
        sys.exit(1)

    profiles: list[dict[str, Any]] = []

    print("[1/3] Building human VH profile (Llamanade NGS)…")
    vh = build_ighv_llamanade()
    _write(OUT_DIR / f"{vh['metadata']['profile_id']}.json", vh)
    print(f"      {vh['metadata']['n_positions']} positions written.")
    profiles.append(vh)

    print("[2/3] Building human VK profile (IMGT germline Kabat cache)…")
    vk = build_igkv()
    _write(OUT_DIR / f"{vk['metadata']['profile_id']}.json", vk)
    print(f"      {vk['metadata']['n_positions']} positions, {vk['metadata']['n_genes']} genes.")
    profiles.append(vk)

    print("[3/3] Building human VL profile (IGLV Kabat cache, Vernier positions)…")
    vl = build_iglv()
    _write(OUT_DIR / f"{vl['metadata']['profile_id']}.json", vl)
    print(f"      {vl['metadata']['n_positions']} positions, {vl['metadata']['n_genes']} genes.")
    profiles.append(vl)

    write_readme(profiles)
    print(f"\nAll profiles written to {OUT_DIR}")


if __name__ == "__main__":
    main()
