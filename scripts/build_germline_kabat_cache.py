#!/usr/bin/env python3
"""
build_germline_kabat_cache.py
=============================

One-time precompute cache so per-project runs NEVER re-number hundreds of germlines.

Input (IMGT AA databases):
  - data/germlines/human_ig_aa/IGHV_aa.json
  - data/germlines/human_ig_aa/IGKV_aa.json
  - data/germlines/human_ig_aa/IGLV_aa.json (V1.1+)

Output (cache, repo-local, read-only at runtime):
  - data/germlines/human_ig_aa/_cache/IGHV_kabat_cache.json
  - data/germlines/human_ig_aa/_cache/IGKV_kabat_cache.json
  - data/germlines/human_ig_aa/_cache/IGLV_kabat_cache.json (V1.1+)

Cache contents per gene:
  - sequence_aa
  - kabat_cdr_lengths (CDR1/2/3)
  - fr_concat (FR1+FR2+FR3, Kabat)
  - vernier_residues (Kabat base positions only; VH14 / VL8 / VL8+λ50)

Usage:
  python scripts/build_germline_kabat_cache.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE))

VALID_AA = set("ACDEFGHIKLMNPQRSTVWY")
AA_RE = re.compile(r"^[ACDEFGHIKLMNPQRSTVWY]+$")


def _load_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _write_json(p: Path, obj: Dict[str, Any]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _clean(seq: str) -> str:
    return re.sub(r"\s+", "", (seq or "").upper().strip())


def _span(kd: Dict[Tuple[int, str], str], lo: int, hi: int) -> str:
    from core.humanization.kabat_utils import sorted_keys  # noqa: PLC0415
    return "".join(kd[k] for k in sorted_keys(kd) if lo <= k[0] <= hi)


def _cdr_lengths(kd: Dict[Tuple[int, str], str], chain: str) -> Dict[str, int]:
    from core.humanization.kabat_utils import CDR_RANGES_VH, CDR_RANGES_VL  # noqa: PLC0415
    ranges = CDR_RANGES_VH if chain == "VH" else CDR_RANGES_VL
    names = ["CDR1", "CDR2", "CDR3"]
    return {n: len(_span(kd, lo, hi)) for n, (lo, hi) in zip(names, ranges)}


def _fr_concat(kd: Dict[Tuple[int, str], str], chain: str) -> str:
    if chain == "VH":
        ranges = [(1, 25), (36, 49), (66, 94)]
    else:
        ranges = [(1, 23), (35, 49), (57, 88)]
    return "".join(_span(kd, lo, hi) for lo, hi in ranges)


def _vernier_residues(kd: Dict[Tuple[int, str], str], chain: str, is_lambda: bool = False) -> Dict[str, str]:
    vh_pos = [2, 27, 28, 29, 30, 48, 49, 67, 69, 71, 73, 78, 93, 94]
    vl_pos = [2, 4, 36, 46, 49, 69, 71, 98]
    # Lambda light chain adds position 50 (Vernier T2 position in IGLV2/IGLV3)
    if is_lambda:
        vl_pos = vl_pos + [50]
    pos = vh_pos if chain == "VH" else vl_pos
    out: Dict[str, str] = {}
    for p in pos:
        aa = kd.get((p, ""))
        if aa:
            out[str(p)] = aa
    return out


def _build(db_path: Path, chain: str, is_lambda: bool = False) -> Dict[str, Any]:
    from core.humanization.kabat_utils import kabat_from_anarcii  # noqa: PLC0415
    from anarcii import Anarcii  # noqa: PLC0415

    db = _load_json(db_path)
    entries = db.get("entries") or []

    pairs: List[Tuple[str, str]] = []
    genes: List[str] = []
    seqs: List[str] = []
    for i, e in enumerate(entries):
        gene = str(e.get("id") or e.get("name") or e.get("gene") or "")
        seq = _clean(str(e.get("sequence_aa") or e.get("sequence") or ""))
        if not gene or not seq or not AA_RE.match(seq):
            continue
        uid = f"gl_{i}"
        pairs.append((uid, seq))
        genes.append(gene)
        seqs.append(seq)

    engine = Anarcii()
    res = engine.number(pairs)
    try:
        res = engine.to_scheme("kabat")
    except Exception:
        pass

    cache: Dict[str, Any] = {}
    for uid, gene, seq in zip([u for u, _ in pairs], genes, seqs):
        entry = (res or {}).get(uid, {}) if isinstance(res, dict) else {}
        numbering = entry.get("numbering") if isinstance(entry, dict) else None
        if not numbering:
            continue
        kd = kabat_from_anarcii(numbering)
        if not kd:
            continue
        cache[gene] = {
            "sequence_aa": seq,
            "kabat_cdr_lengths": _cdr_lengths(kd, chain),
            "fr_concat": _fr_concat(kd, chain),
            "vernier_residues": _vernier_residues(kd, chain, is_lambda=is_lambda),
        }

    return {
        "_meta": {
            "source_db": str(db_path.as_posix()),
            "chain": chain,
            "n_entries_in_db": len(entries),
            "n_cached": len(cache),
        },
        "genes": cache,
    }


def main() -> int:
    out_dir = SUITE / "data" / "germlines" / "human_ig_aa" / "_cache"
    out_vh = out_dir / "IGHV_kabat_cache.json"
    out_vk = out_dir / "IGKV_kabat_cache.json"
    out_vl = out_dir / "IGLV_kabat_cache.json"

    print("[cache] building IGHV...")
    vh = _build(SUITE / "data" / "germlines" / "human_ig_aa" / "IGHV_aa.json", chain="VH")
    _write_json(out_vh, vh)
    print(f"[cache] wrote {out_vh}  (n={vh['_meta']['n_cached']})")

    print("[cache] building IGKV...")
    vk = _build(SUITE / "data" / "germlines" / "human_ig_aa" / "IGKV_aa.json", chain="VL")
    _write_json(out_vk, vk)
    print(f"[cache] wrote {out_vk}  (n={vk['_meta']['n_cached']})")

    print("[cache] building IGLV (lambda light chain)...")
    vl = _build(SUITE / "data" / "germlines" / "human_ig_aa" / "IGLV_aa.json", chain="VL", is_lambda=True)
    _write_json(out_vl, vl)
    print(f"[cache] wrote {out_vl}  (n={vl['_meta']['n_cached']})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

