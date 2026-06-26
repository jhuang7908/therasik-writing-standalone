#!/usr/bin/env python3
"""
export_dog_framework_fr1_fr3_support_v1.py
=========================================

Export an auditable FR1–FR3 (framework-only) support table for dog scaffold selection.

Scope:
  - ONLY computes Kabat segmentation for selected Tier1/Tier2 candidates.
  - Does NOT Kabat-number the entire IMGT catalog.

Inputs (repo-internal):
  - Tier1 anchors: data/germlines/.../dog_production_germline_library_v1.json
  - Tier2 priors:  data/germlines/.../dog_repertoire_and_dla_stats.json
  - IMGT catalogs: data/germlines/.../{IGHV,IGKV,IGLV}_aa.json

Outputs:
  - data/germlines/.../dog_framework_fr1_fr3_support_v1.json
  - data/germlines/.../dog_framework_fr1_fr3_support_v1.md
"""

from __future__ import annotations

import json
import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SUITE))

from core.humanization.kabat_utils import get_kabat_numbering, sorted_keys  # noqa: E402


DOG_DIR = SUITE / "data" / "germlines" / "canis_lupus_familiaris_ig_aa"


FR_RANGES = {
    "VH": {"FR1": (1, 25), "FR2": (36, 49), "FR3": (66, 94)},
    "VL": {"FR1": (1, 23), "FR2": (35, 49), "FR3": (57, 88)},
}


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _is_functional(e: Dict[str, Any]) -> bool:
    return "|F|" in str(e.get("raw_header") or "")


def _clean_gene_token(s: str) -> str:
    return str(s or "").strip()


def _resolve_ighv_from_common_token(token: str, ighv_ids: List[str]) -> List[str]:
    """
    Map a paper/common token like 'VH1-62' to IMGT ids like 'IGHV1-62*01'.
    Returns list of matching ids (may be empty).
    """
    tok = _clean_gene_token(token)
    if not tok:
        return []
    if tok.startswith("IGHV"):
        return [tok] if tok in set(ighv_ids) else []
    # Common style: VH1-62, VH1-44
    if tok.startswith("VH"):
        guess = "IGHV" + tok[2:]
        return [i for i in ighv_ids if i.startswith(guess)]
    return []


_KABAT_CACHE: Dict[str, Dict[Tuple[int, str], str]] = {}


def _kabat(seq: str) -> Dict[Tuple[int, str], str]:
    """
    Cache Kabat numbering per unique sequence to avoid repeated external calls.
    """
    s = str(seq or "").strip().upper()
    if not s:
        return {}
    if s in _KABAT_CACHE:
        return _KABAT_CACHE[s]
    kd = get_kabat_numbering(s) or {}
    _KABAT_CACHE[s] = kd
    return kd


def _kabat_fr_segment(kd: Dict[Tuple[int, str], str], chain: str, lo: int, hi: int) -> Tuple[str, List[Tuple[int, str]]]:
    if not kd:
        return "", []
    out: List[str] = []
    keys_used: List[Tuple[int, str]] = []
    for k in sorted_keys(kd):
        pos, ins = k
        if ins not in ("", " "):
            continue
        if lo <= pos <= hi:
            out.append(kd[k])
            keys_used.append((pos, ""))  # normalize
    return "".join(out), keys_used


def _kabat_fr_only_map(kd: Dict[Tuple[int, str], str], chain: str) -> Dict[Tuple[int, str], str]:
    if not kd:
        return {}
    out: Dict[Tuple[int, str], str] = {}
    ranges = FR_RANGES[chain]
    for k in sorted_keys(kd):
        pos, ins = k
        if ins not in ("", " "):
            continue
        in_fr = any(lo <= pos <= hi for lo, hi in ranges.values())
        if in_fr:
            out[(pos, "")] = kd[k]
    return out


def _consensus(fr_maps: List[Dict[Tuple[int, str], str]]) -> Dict[str, Any]:
    """
    Simple per-position majority consensus with coverage stats.
    """
    if not fr_maps:
        return {"n": 0, "positions": {}, "coverage": {}}
    positions = sorted({k for m in fr_maps for k in m.keys()}, key=lambda x: (x[0], x[1]))
    pos_out: Dict[str, str] = {}
    cov_out: Dict[str, float] = {}
    for k in positions:
        counts: Dict[str, int] = {}
        present = 0
        for m in fr_maps:
            aa = m.get(k)
            if aa:
                present += 1
                counts[aa] = counts.get(aa, 0) + 1
        if not counts:
            continue
        best_aa = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[0][0]
        key_s = f"{k[0]}{k[1]}"
        pos_out[key_s] = best_aa
        cov_out[key_s] = present / max(1, len(fr_maps))
    return {"n": len(fr_maps), "positions": pos_out, "coverage": cov_out}


@dataclass
class Scaffold:
    tier: str
    locus: str  # IGHV/IGKV/IGLV
    chain: str  # VH/VL
    gene: str
    source: str
    sequence_aa: str
    raw_header: Optional[str] = None


def main() -> int:
    tier1_path = DOG_DIR / "dog_production_germline_library_v1.json"
    tier2_path = DOG_DIR / "dog_repertoire_and_dla_stats.json"

    ighv_path = DOG_DIR / "IGHV_aa.json"
    igkv_path = DOG_DIR / "IGKV_aa.json"
    iglv_path = DOG_DIR / "IGLV_aa.json"

    tier1 = _load_json(tier1_path) if tier1_path.exists() else {}
    tier2 = _load_json(tier2_path) if tier2_path.exists() else {}

    ighv = _load_json(ighv_path)
    igkv = _load_json(igkv_path)
    iglv = _load_json(iglv_path)

    idx: Dict[str, Dict[str, Dict[str, Any]]] = {"IGHV": {}, "IGKV": {}, "IGLV": {}}
    for locus, payload in [("IGHV", ighv), ("IGKV", igkv), ("IGLV", iglv)]:
        for e in payload.get("entries") or []:
            gene = str(e.get("id") or "").strip()
            if gene:
                idx[locus][gene] = e

    scaffolds: List[Scaffold] = []

    # Tier1: anchors inferred from clinical references (already selected small set)
    for it in (tier1.get("production_scaffolds_vh_v") or []):
        gene = str(it.get("gene") or "").strip()
        e = idx["IGHV"].get(gene) or {}
        scaffolds.append(
            Scaffold(
                tier="tier1",
                locus="IGHV",
                chain="VH",
                gene=gene,
                source="clinical_anchor_library",
                sequence_aa=str(e.get("sequence_aa") or ""),
                raw_header=str(e.get("raw_header") or ""),
            )
        )
    for it in (tier1.get("production_scaffolds_vl_v") or []):
        locus = str(it.get("locus") or "").strip()
        gene = str(it.get("gene") or "").strip()
        locus_norm = "IGKV" if locus == "IGK" else ("IGLV" if locus == "IGL" else locus)
        e = idx.get(locus_norm, {}).get(gene) or {}
        scaffolds.append(
            Scaffold(
                tier="tier1",
                locus=locus_norm,
                chain="VL",
                gene=gene,
                source="clinical_anchor_library",
                sequence_aa=str(e.get("sequence_aa") or ""),
                raw_header=str(e.get("raw_header") or ""),
            )
        )

    # Tier2: population priors (currently only VH high-frequency tokens)
    tier2_hits: List[Dict[str, Any]] = []
    hf = ((tier2.get("vh_gene_usage") or {}).get("high_frequency_genes") or [])
    ighv_ids = list(idx["IGHV"].keys())
    for g in hf:
        tok = str((g or {}).get("gene") or "")
        resolved = _resolve_ighv_from_common_token(tok, ighv_ids)
        chosen = None
        # prefer functional *01
        for rid in resolved:
            e = idx["IGHV"].get(rid) or {}
            if _is_functional(e) and "*01" in rid:
                chosen = rid
                break
        if chosen is None and resolved:
            chosen = resolved[0]
        tier2_hits.append({"token": tok, "resolved_ids": resolved, "chosen_id": chosen})
        if chosen:
            e = idx["IGHV"].get(chosen) or {}
            scaffolds.append(
                Scaffold(
                    tier="tier2",
                    locus="IGHV",
                    chain="VH",
                    gene=chosen,
                    source=f"population_prior:{tok}",
                    sequence_aa=str(e.get("sequence_aa") or ""),
                    raw_header=str(e.get("raw_header") or ""),
                )
            )

    # De-duplicate by (tier,locus,gene)
    seen = set()
    uniq: List[Scaffold] = []
    for s in scaffolds:
        key = (s.tier, s.locus, s.gene)
        if key in seen:
            continue
        seen.add(key)
        if s.sequence_aa:
            uniq.append(s)

    rows: List[Dict[str, Any]] = []
    grouped_fr_maps: Dict[Tuple[str, str], List[Dict[Tuple[int, str], str]]] = {}
    for s in uniq:
        rr = FR_RANGES["VH" if s.chain == "VH" else "VL"]
        kd = _kabat(s.sequence_aa)
        fr1, _ = _kabat_fr_segment(kd, s.chain, *rr["FR1"])
        fr2, _ = _kabat_fr_segment(kd, s.chain, *rr["FR2"])
        fr3, _ = _kabat_fr_segment(kd, s.chain, *rr["FR3"])
        fr123 = fr1 + fr2 + fr3
        fr_map = _kabat_fr_only_map(kd, s.chain)
        grouped_fr_maps.setdefault((s.tier, s.locus), []).append(fr_map)
        rows.append(
            {
                "tier": s.tier,
                "locus": s.locus,
                "chain": s.chain,
                "gene": s.gene,
                "source": s.source,
                "fr1": fr1,
                "fr2": fr2,
                "fr3": fr3,
                "fr1_3": fr123,
                "raw_header": s.raw_header,
            }
        )

    consensus = {
        f"{tier}:{locus}": _consensus(maps)
        for (tier, locus), maps in grouped_fr_maps.items()
    }

    payload = {
        "artifact_id": "dog_framework_fr1_fr3_support_v1",
        "built_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "inputs": {
            "tier1_anchor_library": str(tier1_path.relative_to(SUITE)) if tier1 else None,
            "tier2_population_priors": str(tier2_path.relative_to(SUITE)) if tier2 else None,
            "imgt_catalogs": {
                "IGHV": str(ighv_path.relative_to(SUITE)),
                "IGKV": str(igkv_path.relative_to(SUITE)),
                "IGLV": str(iglv_path.relative_to(SUITE)),
            },
        },
        "tier2_resolution": {
            "vh_high_frequency_tokens": tier2_hits,
            "note": (
                "Tier2 inputs may use paper/common tokens (e.g., 'VH1-62'). "
                "This export resolves them heuristically to IMGT ids (e.g., 'IGHV1-62*01') when present in the catalog."
            ),
        },
        "kabat_fr_ranges": FR_RANGES,
        "rows": rows,
        "consensus": consensus,
    }

    out_json = DOG_DIR / "dog_framework_fr1_fr3_support_v1.json"
    out_md = DOG_DIR / "dog_framework_fr1_fr3_support_v1.md"
    _write_json(out_json, payload)

    # Render MD
    md: List[str] = []
    md.append("# Dog framework FR1–FR3 support (v1)")
    md.append("")
    md.append(f"- Built at: `{payload['built_at']}`")
    md.append("")
    md.append("## Inputs")
    md.append("")
    for k, v in (payload.get("inputs") or {}).items():
        md.append(f"- `{k}`: `{v}`")
    md.append("")
    md.append("## Kabat FR ranges used")
    md.append("")
    md.append(f"- VH: FR1 {FR_RANGES['VH']['FR1']}, FR2 {FR_RANGES['VH']['FR2']}, FR3 {FR_RANGES['VH']['FR3']}")
    md.append(f"- VL: FR1 {FR_RANGES['VL']['FR1']}, FR2 {FR_RANGES['VL']['FR2']}, FR3 {FR_RANGES['VL']['FR3']}")
    md.append("")

    md.append("## Tier2 token resolution (VH)")
    md.append("")
    md.append("| token | resolved_ids | chosen_id |")
    md.append("|---|---|---|")
    for it in tier2_hits:
        md.append("| `{t}` | {r} | `{c}` |".format(
            t=it.get("token") or "—",
            r=", ".join([f"`{x}`" for x in (it.get("resolved_ids") or [])]) or "—",
            c=it.get("chosen_id") or "—",
        ))
    md.append("")

    md.append("## FR1–FR3 rows (framework-only)")
    md.append("")
    md.append("| tier | locus | gene | FR1 | FR2 | FR3 | FR1-3 | source |")
    md.append("|---|---|---|---|---|---|---|---|")
    for r in rows:
        md.append("| `{tier}` | `{locus}` | `{gene}` | `{fr1}` | `{fr2}` | `{fr3}` | `{fr13}` | {src} |".format(
            tier=r.get("tier"),
            locus=r.get("locus"),
            gene=r.get("gene"),
            fr1=r.get("fr1"),
            fr2=r.get("fr2"),
            fr3=r.get("fr3"),
            fr13=r.get("fr1_3"),
            src=r.get("source") or "—",
        ))
    md.append("")

    md.append("## Consensus (per tier × locus)")
    md.append("")
    md.append("> Consensus is a simple per-position majority over Kabat FR-only positions; coverage reports how many scaffolds provide that position.")
    md.append("")
    for key, c in consensus.items():
        md.append(f"### `{key}`")
        md.append("")
        md.append(f"- n_scaffolds: `{c.get('n')}`")
        md.append(f"- n_positions: `{len(c.get('positions') or {})}`")
        md.append("")
        # show a compact string for positions ordered numerically
        pos_items = list((c.get("positions") or {}).items())
        pos_items.sort(key=lambda x: int(''.join(ch for ch in x[0] if ch.isdigit()) or 0))
        seq = "".join(aa for _, aa in pos_items)
        md.append(f"- consensus_FR_only (concatenated): `{seq}`")
        md.append("")

    _write_text(out_md, "\n".join(md))

    print(f"[OK] wrote: {out_json}")
    print(f"[OK] wrote: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

