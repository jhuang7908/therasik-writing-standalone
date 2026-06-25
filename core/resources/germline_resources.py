"""
AbEngineCore — IMGT / suite germline resource paths and loaders.

Primary data (multi-species antibody engineering)
---------------------------------------------------
  • Nucleotide reference:  data/germlines/IMGT_V-QUEST_reference_directory/<Species>/IG/*.fasta
  • IG translated AA:       data/germlines/aa_translated/IG/<Species>/*_aa.fasta
  • Fc nt (GENE-DB):        data/germlines/fc_nt/<Species>/IGHC|IGKC|IGLC.fasta
  • Fc AA:                  data/germlines/aa_translated/Fc/<Species>/*_aa.fasta

`vh_identity_imgt()` / `vl_identity_imgt()` use **aa_translated** for the requested `species`
(e.g. Homo_sapiens, Mus_musculus, Canis_lupus_familiaris). This is the default source whenever
IMGT material exists under `IMGT_V-QUEST_reference_directory` / `aa_translated`.

OGRDB (supplementary; limited scope)
------------------------------------
Open Germline Receptor Database (AIRR) focuses on **human, non-human primate, and mouse**
germline sets for **IG and TR**; it does **not** replace IMGT for broad multi-species antibody work.

This repo caches **human** IG V alleles only, for ANARCII / confirmed-70 workflows:

  • data/germlines/ogrdb_human_{IGHV,IGKV,IGLV}_v2.json
    (python scripts/fill_anarcii_ogrdb_germlines.py)

For dog, rabbit, alpaca, etc., use **IMGT_V-QUEST_reference_directory** + **aa_translated**, not OGRDB JSON.

Scripts:
  python scripts/imgt_ig_fc_nt_to_aa.py
  python scripts/download_imgt_fc_nt.py

Species folder names match IMGT (e.g. Homo_sapiens, Mus_musculus).
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

_SUITE = Path(__file__).resolve().parents[2]

GERMLINES = _SUITE / "data" / "germlines"
IMGT_VQUEST = GERMLINES / "IMGT_V-QUEST_reference_directory"
AA_IG = GERMLINES / "aa_translated" / "IG"
AA_FC = GERMLINES / "aa_translated" / "Fc"
FC_NT = GERMLINES / "fc_nt"

# Legacy / optional small libraries
LEGACY_VH3_JSON = GERMLINES / "human_VH3_germlines.json"

# Human-only OGRDB (AIRR) V-gene cache — ANARCII / confirmed-70 fallback; not multi-species IMGT.
OGRDB_JSON_IGHV = GERMLINES / "ogrdb_human_IGHV_v2.json"
OGRDB_JSON_IGKV = GERMLINES / "ogrdb_human_IGKV_v2.json"
OGRDB_JSON_IGLV = GERMLINES / "ogrdb_human_IGLV_v2.json"


def aa_ig_fasta(species: str, segment: str) -> Path:
    """segment: IGHV, IGHD, IGHJ, IGKV, IGKJ, IGLV, IGLJ"""
    return AA_IG / species / f"{segment}_aa.fasta"


def aa_fc_fasta(species: str, segment: str) -> Path:
    """segment: IGHC, IGKC, IGLC"""
    return AA_FC / species / f"{segment}_aa.fasta"


def parse_imgt_aa_fasta(path: Path) -> dict[str, str]:
    """
    Parse *_aa.fasta produced by scripts/imgt_ig_fc_nt_to_aa.py.
    Header: >...|ALLELE|species|... or original IMGT nt header + |nt_len=|aa_len=
    Returns {allele_id: aa_sequence_one_letter}.
    """
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    out: dict[str, str] = {}
    header: str | None = None
    seq_chunks: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                _store_fasta_record(out, header, "".join(seq_chunks))
            header = line[1:].strip()
            seq_chunks = []
        else:
            seq_chunks.append(line.replace(" ", ""))
    if header is not None:
        _store_fasta_record(out, header, "".join(seq_chunks))
    return out


def _store_fasta_record(store: dict[str, str], header: str, aa: str) -> None:
    aa = re.sub(r"[^A-Za-z]", "", aa).upper()
    if not aa:
        return
    parts = header.split("|")
    key = parts[1].strip() if len(parts) > 1 else parts[0].strip()
    if not key:
        key = header.split()[0]
    if key not in store or len(aa) > len(store.get(key, "")):
        store[key] = aa


def best_identity_percent(query: str, references: Iterable[tuple[str, str]]) -> tuple[str, float]:
    """Return (best_name, identity_pct) over full-length min window from start."""
    if not query:
        return "unknown", 0.0
    q = query.strip().upper()
    best_n, best_p = "unknown", 0.0
    for name, ref in references:
        r = ref.upper()
        n = min(len(q), len(r))
        if n < 20:
            continue
        pct = sum(a == b for a, b in zip(q[:n], r[:n])) / n * 100.0
        if pct > best_p:
            best_p, best_n = pct, name
    return best_n, round(best_p, 1)


@lru_cache(maxsize=16)
def load_ighv_aa_index(species: str) -> tuple[tuple[str, str], ...]:
    """Cached (name, seq) tuples for species IGHV AA (IMGT aa_translated)."""
    p = aa_ig_fasta(species, "IGHV")
    d = parse_imgt_aa_fasta(p)
    return tuple(sorted(d.items()))


@lru_cache(maxsize=16)
def load_igkv_aa_index(species: str) -> tuple[tuple[str, str], ...]:
    p = aa_ig_fasta(species, "IGKV")
    d = parse_imgt_aa_fasta(p)
    return tuple(sorted(d.items()))


@lru_cache(maxsize=16)
def load_iglv_aa_index(species: str) -> tuple[tuple[str, str], ...]:
    p = aa_ig_fasta(species, "IGLV")
    d = parse_imgt_aa_fasta(p)
    return tuple(sorted(d.items()))


def vh_identity_imgt(vh_seq: str, species: str) -> dict:
    """Closest IGHV by N-terminal identity vs IMGT **aa_translated** (not OGRDB)."""
    refs = load_ighv_aa_index(species)
    if not refs:
        return {}
    name, pct = best_identity_percent(vh_seq, refs)
    rel = aa_ig_fasta(species, "IGHV").relative_to(_SUITE)
    return {
        "closest_vh_germline": name,
        "vh_germline_identity_pct": pct,
        "germline_search_db": str(rel).replace("\\", "/"),
    }


@lru_cache(maxsize=8)
def load_human_ighv_aa_index() -> tuple[tuple[str, str], ...]:
    """Backward compat: human IGHV index."""
    return load_ighv_aa_index("Homo_sapiens")


def human_ighv_identity_fallback(vh_seq: str) -> dict:
    """When legacy human_VH3_germlines.json is absent, use IMGT human IGHV AA."""
    return vh_identity_imgt(vh_seq, "Homo_sapiens")


def vl_identity_imgt(vl_seq: str, species: str) -> dict:
    """
    Closest light-chain V gene: scan IGKV and IGLV in IMGT **aa_translated** (not OGRDB).
    """
    if not vl_seq or not vl_seq.strip():
        return {}
    kv = load_igkv_aa_index(species)
    lv = load_iglv_aa_index(species)
    nk, pk = (best_identity_percent(vl_seq, kv) if kv else ("unknown", 0.0))
    nl, pl = (best_identity_percent(vl_seq, lv) if lv else ("unknown", 0.0))
    if pk >= pl and nk != "unknown":
        winner, wpct, locus = nk, pk, "IGKV"
    elif nl != "unknown":
        winner, wpct, locus = nl, pl, "IGLV"
    else:
        winner, wpct, locus = "unknown", 0.0, "unknown"
    igkv_p = aa_ig_fasta(species, "IGKV")
    iglv_p = aa_ig_fasta(species, "IGLV")
    return {
        "closest_vl_germline": winner,
        "vl_germline_identity_pct": wpct,
        "vl_germline_locus": locus,
        "vl_igkv_candidate": nk,
        "vl_igkv_identity_pct": pk,
        "vl_iglv_candidate": nl,
        "vl_iglv_identity_pct": pl,
        "germline_vl_search_db": (
            f"{igkv_p.relative_to(_SUITE)};{iglv_p.relative_to(_SUITE)}".replace("\\", "/")
        ),
    }


def _merge_fc_aa_globs(species: str, stem_prefix: str) -> tuple[dict[str, str], list[str]]:
    """Merge all aa_translated/Fc/<species>/<stem_prefix>*_aa.fasta (e.g. IGHC + IGHC_NCBI_supplement)."""
    merged: dict[str, str] = {}
    rel_paths: list[str] = []
    ddir = AA_FC / species
    if not ddir.is_dir():
        return merged, rel_paths
    for p in sorted(ddir.glob(f"{stem_prefix}*_aa.fasta")):
        rel_paths.append(str(p.relative_to(_SUITE)).replace("\\", "/"))
        for k, v in parse_imgt_aa_fasta(p).items():
            if k not in merged or len(v) > len(merged.get(k, "")):
                merged[k] = v
    return merged, rel_paths


def summarize_fc_aa_libraries(species: str) -> dict[str, Any]:
    """Counts of AA FASTA per segment; includes IGHC_NCBI_supplement_aa when present (e.g. Felis)."""
    out: dict[str, Any] = {"species": species, "segments": {}}
    for seg, prefix in (("IGHC", "IGHC"), ("IGKC", "IGKC"), ("IGLC", "IGLC")):
        d, paths = _merge_fc_aa_globs(species, prefix)
        out["segments"][seg] = {
            "n_records": len(d),
            "paths": paths if paths else None,
            "path": paths[0] if len(paths) == 1 else None,
        }
    return out


def fc_probe_identity(fc_seq: str, species: str) -> dict:
    """
    Best identity of fc_seq against all AA entries in IGHC + IGKC + IGLC libraries.
    Useful for Fc fusion / isotype sanity checks.
    """
    if not fc_seq or not fc_seq.strip():
        return {}
    all_refs: list[tuple[str, str]] = []
    for seg, prefix in (("IGHC", "IGHC"), ("IGKC", "IGKC"), ("IGLC", "IGLC")):
        d, _ = _merge_fc_aa_globs(species, prefix)
        for k, v in d.items():
            all_refs.append((f"{seg}|{k}", v))
    if not all_refs:
        return {"status": "NO_FC_LIBRARY", "species": species}
    name, pct = best_identity_percent(fc_seq, all_refs)
    return {
        "fc_probe_best_label": name,
        "fc_probe_identity_pct": pct,
        "species": species,
    }
