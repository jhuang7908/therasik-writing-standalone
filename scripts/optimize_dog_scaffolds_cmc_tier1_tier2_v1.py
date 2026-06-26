#!/usr/bin/env python3
"""
optimize_dog_scaffolds_cmc_tier1_tier2_v1.py
===========================================

Tier1/Tier2 dog scaffold workflow:
  1) Kabat FR1–FR3 split (FR-only evidence layer)
  2) Sequence-only CMC scan (generic motifs)
  3) Greedy FR-only optimization (minimal substitutions) with guardrails

Important:
  - This is **sequence-only**. It does not use structure, solvent exposure, or epitope context.
  - It never enumerates all germlines; it only processes the selected Tier1/Tier2 shortlist.
  - It avoids auto-mutating conserved framework tryptophans (e.g., VH36/VL35) by default.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SUITE))

from core.cmc.generic_cmc_scanner import scan_cmc_liabilities  # noqa: E402
from core.humanization.kabat_utils import get_kabat_numbering, sorted_keys  # noqa: E402


DOG_DIR = SUITE / "data" / "germlines" / "canis_lupus_familiaris_ig_aa"

SHORTLIST_PATH = DOG_DIR / "dog_scaffold_shortlist_tier1_tier2_v1.json"


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


def _index_by_id(entries: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for e in entries or []:
        gid = str(e.get("id") or "").strip()
        if gid:
            out[gid] = e
    return out


def _region_of_kabat_pos(chain: str, pos: int) -> Optional[str]:
    rr = FR_RANGES["VH" if chain == "VH" else "VL"]
    for name, (lo, hi) in rr.items():
        if lo <= pos <= hi:
            return name
    return None


def _is_fr13(chain: str, pos: int) -> bool:
    r = _region_of_kabat_pos(chain, pos)
    return r in ("FR1", "FR3")


def _kabat_for_seq(seq: str) -> Tuple[Dict[Tuple[int, str], str], List[Tuple[int, str]], str]:
    """
    Returns: (kabat_dict, ordered_keys, normalized_seq)
    """
    kd = get_kabat_numbering(seq) or {}
    if not kd:
        return {}, [], ""
    keys = sorted_keys(kd)
    norm = "".join(kd[k] for k in keys)
    return kd, keys, norm


def _site_to_kabat(site: Dict[str, Any], key_by_pos: Dict[int, Tuple[int, str]], chain: str) -> Dict[str, Any]:
    pos_seq = int(site.get("position") or 0)
    kk = key_by_pos.get(pos_seq)
    if not kk:
        return {**site, "kabat_pos": None, "kabat_ins": None, "region": None}
    pos_k, ins = kk
    return {**site, "kabat_pos": pos_k, "kabat_ins": (ins or ""), "region": _region_of_kabat_pos(chain, pos_k)}


def _filter_sites_fr_only(sites: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [s for s in sites if s.get("region") in ("FR1", "FR2", "FR3")]


def _filter_sites_fr13_only(sites: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [s for s in sites if s.get("region") in ("FR1", "FR3")]


def _protected_framework_positions(chain: str) -> Dict[int, str]:
    # Minimal guardrails: framework tryptophan at FR2 start is highly conserved.
    if chain == "VH":
        return {36: "W (conserved FR2 tryptophan)"}
    return {35: "W (conserved FR2 tryptophan)"}


@dataclass
class Mutation:
    chain: str
    locus: str
    gene: str
    kabat_pos: int
    kabat_ins: str
    from_aa: str
    to_aa: str
    reason: str


def _apply_mut(seq: str, i1: int, new_aa: str) -> str:
    """
    Apply mutation at 1-based index i1 to new_aa.
    """
    s = list(seq)
    s[i1 - 1] = new_aa
    return "".join(s)


def _greedy_optimize_fr13(
    chain: str,
    locus: str,
    gene: str,
    seq_norm: str,
    key_by_pos: Dict[int, Tuple[int, str]],
    max_steps: int = 6,
) -> Tuple[str, List[Mutation], Dict[str, Any], Dict[str, Any]]:
    """
    Greedy optimization on FR1/FR3 only.
    Auto-fixes:
      - glycosylation NXS/T (mutate N->Q)
      - deamidation NG/NS/NN (mutate N->Q)
      - isomerization D[PSGT] (mutate D->E)
      - oxidation M (mutate M->L) in FR1/FR3 only
    Does NOT auto-mutate:
      - W oxidation (requires structural review)
      - any protected framework position (e.g. FR2 tryptophan)
    """
    protected = _protected_framework_positions(chain)
    muts: List[Mutation] = []
    seq = seq_norm

    def _scan(seq_s: str) -> Dict[str, Any]:
        raw = scan_cmc_liabilities(seq_s)
        # enrich with kabat mapping
        out = {}
        for k in ("n_glyc_sites", "deamidation_sites", "isomerization_sites", "oxidation_sites"):
            out[k] = [_site_to_kabat(s, key_by_pos, chain=chain) for s in (raw.get(k) or [])]
        out["summary"] = raw.get("summary") or {}
        out["length"] = raw.get("length")
        return out

    before = _scan(seq)

    for _ in range(max_steps):
        current = _scan(seq)
        # consider FR1/FR3 only for auto-fix
        candidates = _filter_sites_fr13_only(
            (current.get("n_glyc_sites") or [])
            + (current.get("deamidation_sites") or [])
            + (current.get("isomerization_sites") or [])
            + (current.get("oxidation_sites") or [])
        )
        if not candidates:
            break

        # pick first fixable candidate (stable ordering)
        fixed = False
        for s in candidates:
            kabat_pos = s.get("kabat_pos")
            if kabat_pos is None:
                continue
            if int(kabat_pos) in protected:
                continue
            pos_seq = int(s.get("position") or 0)
            if pos_seq <= 0 or pos_seq > len(seq):
                continue
            aa = seq[pos_seq - 1]
            cat = str(s.get("category") or "")
            motif = str(s.get("motif") or "")

            if cat in ("glycosylation", "deamidation") and aa == "N":
                seq2 = _apply_mut(seq, pos_seq, "Q")
                muts.append(
                    Mutation(
                        chain=chain,
                        locus=locus,
                        gene=gene,
                        kabat_pos=int(kabat_pos),
                        kabat_ins=str(s.get("kabat_ins") or ""),
                        from_aa="N",
                        to_aa="Q",
                        reason=f"{cat}:{motif}",
                    )
                )
                seq = seq2
                fixed = True
                break

            if cat == "isomerization" and aa == "D":
                seq2 = _apply_mut(seq, pos_seq, "E")
                muts.append(
                    Mutation(
                        chain=chain,
                        locus=locus,
                        gene=gene,
                        kabat_pos=int(kabat_pos),
                        kabat_ins=str(s.get("kabat_ins") or ""),
                        from_aa="D",
                        to_aa="E",
                        reason=f"{cat}:{motif}",
                    )
                )
                seq = seq2
                fixed = True
                break

            if cat == "oxidation" and aa == "M":
                seq2 = _apply_mut(seq, pos_seq, "L")
                muts.append(
                    Mutation(
                        chain=chain,
                        locus=locus,
                        gene=gene,
                        kabat_pos=int(kabat_pos),
                        kabat_ins=str(s.get("kabat_ins") or ""),
                        from_aa="M",
                        to_aa="L",
                        reason="oxidation:M",
                    )
                )
                seq = seq2
                fixed = True
                break

        if not fixed:
            break

    after = _scan(seq)
    return seq, muts, before, after


def main() -> int:
    shortlist = _load_json(SHORTLIST_PATH)

    ighv = _load_json(DOG_DIR / "IGHV_aa.json")
    igkv = _load_json(DOG_DIR / "IGKV_aa.json")
    iglv = _load_json(DOG_DIR / "IGLV_aa.json")

    idx_h = _index_by_id(ighv.get("entries") or [])
    idx_k = _index_by_id(igkv.get("entries") or [])
    idx_l = _index_by_id(iglv.get("entries") or [])

    def _get_seq(locus: str, gid: str) -> Tuple[str, str]:
        m = {"IGHV": idx_h, "IGKV": idx_k, "IGLV": idx_l}.get(locus) or {}
        e = m.get(gid) or {}
        return str(e.get("sequence_aa") or ""), str(e.get("raw_header") or "")

    tier1 = shortlist.get("tier1_clinical_anchors") or {}
    tier2 = shortlist.get("tier2_population_priors") or {}
    tier2_res = (tier2.get("resolution_status") or {}).get("vh_tokens_to_imgt_ids") or {}

    scaffold_items: List[Tuple[str, str, str, str]] = []  # (tier, chain, locus, gene)

    # Tier 1
    for gid in (tier1.get("vh_v_genes_imgt") or []):
        scaffold_items.append(("tier1", "VH", "IGHV", str(gid)))
    for gid in (tier1.get("vk_v_genes_imgt") or []):
        scaffold_items.append(("tier1", "VL", "IGKV", str(gid)))
    for gid in (tier1.get("vl_v_genes_imgt") or []):
        scaffold_items.append(("tier1", "VL", "IGLV", str(gid)))

    # Tier 2 (mapped)
    tier2_tokens = tier2.get("vh_high_frequency_tokens") or []
    for token in tier2_tokens:
        mapped_id = tier2_res.get(token)
        if mapped_id:
            scaffold_items.append(("tier2", "VH", "IGHV", str(mapped_id)))
        else:
            print(f"[WARN] Tier2 token '{token}' has no IMGT mapping in resolution_status")

    rows: List[Dict[str, Any]] = []
    notes: List[str] = []

    for tier, chain, locus, gene in scaffold_items:
        seq, hdr = _get_seq(locus, gene)
        if not seq:
            notes.append(f"[WARN] missing IMGT sequence for {locus}:{gene}")
            continue

        kd, keys, seq_norm = _kabat_for_seq(seq)
        if not kd:
            notes.append(f"[WARN] Kabat numbering failed for {locus}:{gene}")
            continue

        key_by_pos = {i: k for i, k in enumerate(keys, start=1)}

        # FR segments (from Kabat numbering, base keys only)
        rr = FR_RANGES["VH" if chain == "VH" else "VL"]
        fr_parts: Dict[str, str] = {}
        for fr_name, (lo, hi) in rr.items():
            aas: List[str] = []
            for k in keys:
                pos, ins = k
                if ins not in ("", " "):
                    continue
                if lo <= pos <= hi:
                    aas.append(kd[k])
            fr_parts[fr_name] = "".join(aas)
        fr123 = fr_parts.get("FR1", "") + fr_parts.get("FR2", "") + fr_parts.get("FR3", "")

        # CMC scan on normalized seq (positions map to Kabat keys)
        cmc_full = scan_cmc_liabilities(seq_norm)
        cmc_full_mapped = {
            "length": cmc_full.get("length"),
            "summary": cmc_full.get("summary") or {},
            "n_glyc_sites": [_site_to_kabat(s, key_by_pos, chain=chain) for s in (cmc_full.get("n_glyc_sites") or [])],
            "deamidation_sites": [_site_to_kabat(s, key_by_pos, chain=chain) for s in (cmc_full.get("deamidation_sites") or [])],
            "isomerization_sites": [_site_to_kabat(s, key_by_pos, chain=chain) for s in (cmc_full.get("isomerization_sites") or [])],
            "oxidation_sites": [_site_to_kabat(s, key_by_pos, chain=chain) for s in (cmc_full.get("oxidation_sites") or [])],
        }

        cmc_fr_only = {
            "n_glyc_sites": _filter_sites_fr_only(cmc_full_mapped["n_glyc_sites"]),
            "deamidation_sites": _filter_sites_fr_only(cmc_full_mapped["deamidation_sites"]),
            "isomerization_sites": _filter_sites_fr_only(cmc_full_mapped["isomerization_sites"]),
            "oxidation_sites": _filter_sites_fr_only(cmc_full_mapped["oxidation_sites"]),
        }
        cmc_fr13_only = {
            "n_glyc_sites": _filter_sites_fr13_only(cmc_full_mapped["n_glyc_sites"]),
            "deamidation_sites": _filter_sites_fr13_only(cmc_full_mapped["deamidation_sites"]),
            "isomerization_sites": _filter_sites_fr13_only(cmc_full_mapped["isomerization_sites"]),
            "oxidation_sites": _filter_sites_fr13_only(cmc_full_mapped["oxidation_sites"]),
        }

        seq_opt, muts, before, after = _greedy_optimize_fr13(
            chain=chain,
            locus=locus,
            gene=gene,
            seq_norm=seq_norm,
            key_by_pos=key_by_pos,
            max_steps=6,
        )

        rows.append(
            {
                "tier": tier,
                "chain": chain,
                "locus": locus,
                "gene": gene,
                "imgt_functionality": ("F" if "|F|" in hdr else None),
                "raw_header": hdr,
                "sequence_aa_imgt": seq,
                "sequence_aa_kabat_norm": seq_norm,
                "fr_segments": fr_parts,
                "fr1_3_concat": fr123,
                "cmc_full": cmc_full_mapped,
                "cmc_fr_only": {k: len(v) for k, v in cmc_fr_only.items()},
                "cmc_fr13_only": {k: len(v) for k, v in cmc_fr13_only.items()},
                "optimization": {
                    "scope": "FR1/FR3 only",
                    "protected_positions": _protected_framework_positions(chain),
                    "mutations": [m.__dict__ for m in muts],
                    "sequence_aa_opt": seq_opt,
                    "cmc_before": {
                        "summary": before.get("summary") or {},
                        "fr13_counts": {
                            "n_glyc_sites": len(_filter_sites_fr13_only(before.get("n_glyc_sites") or [])),
                            "deamidation_sites": len(_filter_sites_fr13_only(before.get("deamidation_sites") or [])),
                            "isomerization_sites": len(_filter_sites_fr13_only(before.get("isomerization_sites") or [])),
                            "oxidation_sites": len(_filter_sites_fr13_only(before.get("oxidation_sites") or [])),
                        },
                    },
                    "cmc_after": {
                        "summary": after.get("summary") or {},
                        "fr13_counts": {
                            "n_glyc_sites": len(_filter_sites_fr13_only(after.get("n_glyc_sites") or [])),
                            "deamidation_sites": len(_filter_sites_fr13_only(after.get("deamidation_sites") or [])),
                            "isomerization_sites": len(_filter_sites_fr13_only(after.get("isomerization_sites") or [])),
                            "oxidation_sites": len(_filter_sites_fr13_only(after.get("oxidation_sites") or [])),
                        },
                    },
                },
            }
        )

    payload = {
        "artifact_id": "dog_scaffold_cmc_optimization_tier1_tier2_v1",
        "built_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "inputs": {
            "shortlist": str(SHORTLIST_PATH.relative_to(SUITE)),
            "imgt_catalog_dir": str(DOG_DIR.relative_to(SUITE)),
        },
        "tier2_status": {
            "vh_tokens": list(map(str, tier2_tokens)),
            "resolution_map": tier2_res,
            "note": "Tier2 tokens mapped to IMGT IDs via resolution_status; processed as Tier2 scaffolds.",
        },
        "notes": notes,
        "rows": rows,
    }

    out_json = DOG_DIR / "dog_scaffold_cmc_optimization_tier1_tier2_v1.json"
    out_md = DOG_DIR / "dog_scaffold_cmc_optimization_tier1_tier2_v1.md"
    _write_json(out_json, payload)

    md: List[str] = []
    md.append("# Dog scaffold CMC optimization (Tier1/Tier2) — v1")
    md.append("")
    md.append(f"- Built at: `{payload['built_at']}`")
    md.append(f"- Shortlist: `{payload['inputs']['shortlist']}`")
    md.append("")
    md.append("## Tier2 status")
    md.append("")
    md.append(f"- VH tokens: {', '.join(f'`{t}`' for t in payload['tier2_status']['vh_tokens']) or '—'}")
    md.append(f"- Mapping: {json.dumps(payload['tier2_status']['resolution_map'], indent=2)}")
    md.append(f"- Note: {payload['tier2_status']['note']}")
    md.append("")
    if notes:
        md.append("## Notes / warnings")
        md.append("")
        for n in notes:
            md.append(f"- {n}")
        md.append("")

    md.append("## Results (Tier1 & Tier2 scaffolds)")
    md.append("")
    md.append("| tier | locus | gene | chain | FR1 | FR2 | FR3 | CMC(full flags) | CMC(FR13 before→after) | mutations |")
    md.append("|---|---|---|---|---|---|---|---:|---|---:|")

    for r in rows:
        cmc_sum = (r.get("cmc_full") or {}).get("summary") or {}
        total = int(cmc_sum.get("total_flags") or 0)
        b = ((r.get("optimization") or {}).get("cmc_before") or {}).get("fr13_counts") or {}
        a = ((r.get("optimization") or {}).get("cmc_after") or {}).get("fr13_counts") or {}
        before_n = int(sum(int(x or 0) for x in b.values()))
        after_n = int(sum(int(x or 0) for x in a.values()))
        muts_n = len(((r.get("optimization") or {}).get("mutations") or []))
        md.append("| `{tier}` | `{locus}` | `{gene}` | `{chain}` | `{fr1}` | `{fr2}` | `{fr3}` | {t} | {b}→{a} | {m} |".format(
            tier=r.get("tier"),
            locus=r.get("locus"),
            gene=r.get("gene"),
            chain=r.get("chain"),
            fr1=((r.get("fr_segments") or {}).get("FR1") or ""),
            fr2=((r.get("fr_segments") or {}).get("FR2") or ""),
            fr3=((r.get("fr_segments") or {}).get("FR3") or ""),
            t=total,
            b=before_n,
            a=after_n,
            m=muts_n,
        ))
    md.append("")
    md.append("## Mutation details")
    md.append("")
    for r in rows:
        md.append(f"### `{r.get('locus')}:{r.get('gene')}`")
        md.append("")
        muts = (r.get("optimization") or {}).get("mutations") or []
        if not muts:
            md.append("- (no auto-mutations applied)")
            md.append("")
            continue
        md.append("| Kabat | from | to | reason |")
        md.append("|---|---|---|---|")
        for m in muts:
            kab = f"{m.get('kabat_pos')}{m.get('kabat_ins') or ''}"
            md.append(f"| `{kab}` | `{m.get('from_aa')}` | `{m.get('to_aa')}` | `{m.get('reason')}` |")
        md.append("")

    _write_text(out_md, "\n".join(md))

    print(f"[OK] wrote: {out_json}")
    print(f"[OK] wrote: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

