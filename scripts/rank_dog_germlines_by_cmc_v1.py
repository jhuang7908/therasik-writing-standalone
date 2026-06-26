#!/usr/bin/env python3
"""
rank_dog_germlines_by_cmc_v1.py
================================

Build an experience-based "production-friendly" dog germline shortlist (v1)
using sequence-only CMC liability proxies (no wet-lab expression data).

Inputs:
  - data/germlines/canis_lupus_familiaris_ig_aa/{IGHV,IGKV,IGLV}_aa.json

Method (proxy, not wet-lab truth):
  - Keep IMGT functional entries only (header contains "|F|")
  - Run core.cmc.generic_cmc_scanner.scan_cmc_liabilities(sequence_aa)
  - Rank by: total_flags (asc) then oxidation_sites count (asc) then length (asc)

Outputs:
  - data/germlines/canis_lupus_familiaris_ig_aa/dog_germline_production_candidates_v1.json
  - data/germlines/canis_lupus_familiaris_ig_aa/dog_germline_production_candidates_v1.md
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SUITE))


from core.cmc.generic_cmc_scanner import scan_cmc_liabilities  # noqa: E402


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _functional(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for e in entries:
        if "|F|" in str(e.get("raw_header") or ""):
            out.append(e)
    return out


@dataclass
class Ranked:
    locus: str
    gene: str
    length: int
    total_flags: int
    risk_level: str
    n_glyc: int
    n_deamid: int
    n_isom: int
    n_oxid: int
    raw_header: str
    sequence_aa: str


def _rank(locus: str, entries: List[Dict[str, Any]], top_n: int = 20) -> List[Ranked]:
    ranked: List[Ranked] = []
    for e in _functional(entries):
        gene = str(e.get("id") or "").strip()
        seq = str(e.get("sequence_aa") or "").strip().upper()
        if not gene or not seq:
            continue
        try:
            cmc = scan_cmc_liabilities(seq)
        except Exception:
            continue
        ranked.append(
            Ranked(
                locus=locus,
                gene=gene,
                length=int(cmc.get("length") or len(seq)),
                total_flags=int((cmc.get("summary") or {}).get("total_flags") or 0),
                risk_level=str((cmc.get("summary") or {}).get("risk_level") or "—"),
                n_glyc=len(cmc.get("n_glyc_sites") or []),
                n_deamid=len(cmc.get("deamidation_sites") or []),
                n_isom=len(cmc.get("isomerization_sites") or []),
                n_oxid=len(cmc.get("oxidation_sites") or []),
                raw_header=str(e.get("raw_header") or ""),
                sequence_aa=seq,
            )
        )

    ranked.sort(key=lambda r: (r.total_flags, r.n_oxid, r.length, r.gene))
    return ranked[: max(0, int(top_n))]


def main() -> int:
    dog_dir = SUITE / "data" / "germlines" / "canis_lupus_familiaris_ig_aa"
    ig_hv = _load_json(dog_dir / "IGHV_aa.json")["entries"]
    ig_kv = _load_json(dog_dir / "IGKV_aa.json")["entries"]
    ig_lv = _load_json(dog_dir / "IGLV_aa.json")["entries"]

    top_h = _rank("IGHV", ig_hv, top_n=20)
    top_k = _rank("IGKV", ig_kv, top_n=20)
    top_l = _rank("IGLV", ig_lv, top_n=20)

    payload = {
        "candidate_set_id": "dog_germline_production_candidates_v1",
        "species": "Canis_lupus_familiaris",
        "built_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "method_note": (
            "Proxy ranking using sequence-only CMC liabilities "
            "(glycosylation/deamidation/isomerization/oxidation motifs). "
            "Not a wet-lab expression yield database."
        ),
        "top": {
            "IGHV": [r.__dict__ for r in top_h],
            "IGKV": [r.__dict__ for r in top_k],
            "IGLV": [r.__dict__ for r in top_l],
        },
    }

    out_json = dog_dir / "dog_germline_production_candidates_v1.json"
    _write_json(out_json, payload)

    md: List[str] = []
    md.append("# Dog germline production candidates (v1)")
    md.append("")
    md.append(f"- Built at: `{payload['built_at']}`")
    md.append(f"- Species: `{payload['species']}`")
    md.append("")
    md.append("## What this file is (and is not)")
    md.append("")
    md.append("- ****：“/”（CMC liabilities ）")
    md.append("- ****：/；")
    md.append("")

    def _table(title: str, items: List[Ranked]) -> None:
        md.append(f"## {title}")
        md.append("")
        md.append("| gene | length | total_flags | risk | n_glyc | n_deamid | n_isom | n_oxid |")
        md.append("|---|---:|---:|---|---:|---:|---:|---:|")
        for r in items:
            md.append("| `{g}` | {l} | {t} | {rk} | {ng} | {nd} | {ni} | {no} |".format(
                g=r.gene,
                l=r.length,
                t=r.total_flags,
                rk=r.risk_level,
                ng=r.n_glyc,
                nd=r.n_deamid,
                ni=r.n_isom,
                no=r.n_oxid,
            ))
        md.append("")

    _table("IGHV (top 20)", top_h)
    _table("IGKV (top 20)", top_k)
    _table("IGLV (top 20)", top_l)

    md.append("## Notes")
    md.append("")
    md.append("-  `core/cmc/generic_cmc_scanner.py`， CMC 。")
    md.append("-  caninization/： scaffold，。")
    md.append("")

    out_md = dog_dir / "dog_germline_production_candidates_v1.md"
    _write_text(out_md, "\n".join(md))

    print(f"[OK] wrote: {out_json}")
    print(f"[OK] wrote: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

