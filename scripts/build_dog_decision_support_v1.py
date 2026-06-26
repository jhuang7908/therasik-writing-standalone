#!/usr/bin/env python3
"""
build_dog_decision_support_v1.py
===============================

Create a single, auditable decision-support artifact for dog caninization that merges:

- Tier 1: clinical anchor scaffolds (in-repo canine therapeutics)
- Tier 2: population priors (BCR repertoire skew + DLA core panel)

When Tier1/Tier2 scaffolds are still insufficient for a given antibody, the recommended
fallback is **surface reshaping ()** + structure-gated rescue (Phase4→5),
instead of expanding to a large Tier3 germline search.

Outputs:
  - data/germlines/canis_lupus_familiaris_ig_aa/dog_decision_support_v1.json
  - data/germlines/canis_lupus_familiaris_ig_aa/dog_decision_support_v1.md
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SUITE))


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _safe_get(d: Dict[str, Any], *keys: str, default):
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return default if cur is None else cur


def main() -> int:
    dog_dir = SUITE / "data" / "germlines" / "canis_lupus_familiaris_ig_aa"

    clinical_lib_path = dog_dir / "dog_production_germline_library_v1.json"
    stats_path = dog_dir / "dog_repertoire_and_dla_stats.json"

    clinical = _load_json(clinical_lib_path) if clinical_lib_path.exists() else {}
    stats = _load_json(stats_path) if stats_path.exists() else {}

    payload: Dict[str, Any] = {
        "artifact_id": "dog_decision_support_v1",
        "species": "Canis_lupus_familiaris",
        "built_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "inputs": {
            "clinical_anchor_library": (
                str(clinical_lib_path.relative_to(SUITE)) if clinical else None
            ),
            "population_priors": str(stats_path.relative_to(SUITE)) if stats else None,
            "population_priors_meta": _safe_get(stats, "meta", default={}),
        },
        "tiers": {
            "tier1_clinical_anchors": {
                "vh_v": _safe_get(clinical, "production_scaffolds_vh_v", default=[]),
                "vl_v": _safe_get(clinical, "production_scaffolds_vl_v", default=[]),
                "notes": [
                    "Derived from in-repo clinical canine antibody references (PDBs).",
                    "These are the highest-confidence, production-proven scaffolds available in this repo.",
                ],
            },
            "tier2_population_priors": {
                "vh_gene_usage": _safe_get(stats, "vh_gene_usage", default={}),
                "dla_core_panel": _safe_get(stats, "dla_core_panel", default={}),
                "notes": [
                    "Population priors are meant to approximate broad tolerance / prevalence across dog populations.",
                    "If you have breed-stratified V/J usage and DLA frequencies, place normalized tables under data/repertoire/canis_lupus_familiaris/.",
                ],
            },
        },
        "decision_policy": [
            "Default scaffold selection order: Tier 1 (clinical anchors) > Tier 2 (population priors).",
            "If Tier1/Tier2 scaffolds are still insufficient, use surface reshaping () on a selected scaffold and then run a structure-gated rescue loop (Phase4→5) on vernier/surface sites.",
            "For immunogenicity checks in dogs, start from the DLA core panel and expand per target breed/population when frequency tables are available.",
        ],
    }

    out_json = dog_dir / "dog_decision_support_v1.json"
    _write_json(out_json, payload)

    md: List[str] = []
    md.append("# Dog decision support (v1)")
    md.append("")
    md.append(f"- Built at: `{payload['built_at']}`")
    md.append(f"- Species: `{payload['species']}`")
    md.append("")

    md.append("## Inputs")
    md.append("")
    for k, v in (payload.get("inputs") or {}).items():
        md.append(f"- `{k}`: `{v}`")
    md.append("")

    md.append("## Decision policy (execution order)")
    md.append("")
    for line in payload.get("decision_policy") or []:
        md.append(f"- {line}")
    md.append("")

    md.append("## Tier 1 — Clinical anchor scaffolds (in-repo)")
    md.append("")
    t1 = _safe_get(payload, "tiers", "tier1_clinical_anchors", default={})
    md.append("### VH V genes")
    md.append("")
    md.append("| gene | best_identity | seen_in |")
    md.append("|---|---:|---|")
    for it in (t1.get("vh_v") or []):
        md.append("| `{g}` | {i:.3f} | {s} |".format(
            g=it.get("gene") or "—",
            i=float(it.get("best_identity") or 0.0),
            s=", ".join(it.get("seen_in") or []),
        ))
    md.append("")
    md.append("### VL V genes")
    md.append("")
    md.append("| locus | gene | best_identity | seen_in |")
    md.append("|---|---|---:|---|")
    for it in (t1.get("vl_v") or []):
        md.append("| {loc} | `{g}` | {i:.3f} | {s} |".format(
            loc=it.get("locus") or "—",
            g=it.get("gene") or "—",
            i=float(it.get("best_identity") or 0.0),
            s=", ".join(it.get("seen_in") or []),
        ))
    md.append("")

    md.append("## Tier 2 — Population priors (BCR repertoire + DLA)")
    md.append("")
    t2 = _safe_get(payload, "tiers", "tier2_population_priors", default={})
    vh_usage = t2.get("vh_gene_usage") or {}
    dla = t2.get("dla_core_panel") or {}

    if vh_usage:
        md.append("### VH usage summary")
        md.append("")
        md.append(f"- Dominant family: `{vh_usage.get('dominant_family')}`")
        md.append(f"- Summary: {vh_usage.get('summary')}")
        md.append("")
        md.append("### High-frequency VH genes (curated)")
        md.append("")
        md.append("| gene | human_homolog | note |")
        md.append("|---|---|---|")
        for g in (vh_usage.get("high_frequency_genes") or []):
            md.append("| `{gene}` | `{hh}` | {note} |".format(
                gene=g.get("gene") or "—",
                hh=g.get("human_homolog") or "—",
                note=g.get("note") or "",
            ))
        md.append("")
    else:
        md.append("- `vh_gene_usage` not available (missing stats file).")
        md.append("")

    if dla:
        md.append("### DLA core panel (curated)")
        md.append("")
        md.append(f"- Description: {dla.get('description')}")
        md.append("")
        md.append("| locus | allele | frequency_note |")
        md.append("|---|---|---|")
        for a in (dla.get("alleles") or []):
            md.append("| `{loc}` | `{al}` | {fn} |".format(
                loc=a.get("locus") or "—",
                al=a.get("allele") or "—",
                fn=a.get("frequency_note") or "",
            ))
        md.append("")
    else:
        md.append("- `dla_core_panel` not available (missing stats file).")
        md.append("")

    md.append("## How to extend with Gemini-found tables")
    md.append("")
    md.append("- Put breed/population tables under `data/repertoire/canis_lupus_familiaris/` (see its README).")
    md.append("- Then update `data/germlines/canis_lupus_familiaris_ig_aa/dog_repertoire_and_dla_stats.json` meta to include dataset citations and pointers.")
    md.append("")

    out_md = dog_dir / "dog_decision_support_v1.md"
    _write_text(out_md, "\n".join(md))

    print(f"[OK] wrote: {out_json}")
    print(f"[OK] wrote: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

