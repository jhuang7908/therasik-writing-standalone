#!/usr/bin/env python3
"""
Aggregate mouse anti-CD20 demo variants and benchmark vs AbRef-458 (clinical engineered IgG Fv, n=458).

Reads:
  projects/mouse_cd20_humanization/humanized_sequences.json
  projects/mouse_cd20_humanization/graft_surface_compare.json

Writes:
  projects/mouse_cd20_humanization/clinical_abref458_benchmark.json
  projects/mouse_cd20_humanization/CLINICAL_BENCHMARK.md

Does NOT generate new PDBs (structure is sequence-only CMC). Murine Fv PDB path is recorded if present.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))

from core.cmc.cmc_metrics import CMCMetricEngine  # noqa: E402
from core.cmc.adi_score import (  # noqa: E402
    compute_adi,
    compute_adi_percentile,
    compute_adi_with_breakdown,
)

PROJ = SUITE / "projects" / "mouse_cd20_humanization"
ABREF_STATS = SUITE / "data" / "reference" / "AbRef458_stats_v1.json"
ABREF_ADI_DIST = SUITE / "data" / "reference" / "AbRef458_27m_ADI_distribution_v1.json"


def _load_ref_metrics() -> Dict[str, Any]:
    doc = json.loads(ABREF_STATS.read_text(encoding="utf-8"))
    return doc.get("metrics", {})


def _metric_band(name: str, value: float, ref: Dict[str, Any]) -> str:
    """Return qualitative band vs AbRef-458 percentiles."""
    if value is None or not ref:
        return "n/a"
    p5, p25, p50, p75, p95 = (
        ref.get("p5"),
        ref.get("p25"),
        ref.get("p50"),
        ref.get("p75"),
        ref.get("p95"),
    )
    if any(x is None for x in (p5, p95)):
        return "n/a"
    if p5 <= value <= p95:
        if p25 is not None and p75 is not None and p25 <= value <= p75:
            return "IQR (typical clinical)"
        return "within p5–p95"
    return "outside p5–p95"


def main() -> int:
    ref_m = _load_ref_metrics()

    hs_path = PROJ / "humanized_sequences.json"
    gs_path = PROJ / "graft_surface_compare.json"
    if not hs_path.is_file():
        print(f"Missing {hs_path}", file=sys.stderr)
        return 1

    humanized = json.loads(hs_path.read_text(encoding="utf-8"))
    graft_data: Dict[str, Any] = {}
    if gs_path.is_file():
        graft_data = json.loads(gs_path.read_text(encoding="utf-8")).get("variants", {})

    pairs: List[Tuple[str, str, str]] = [
        ("1_murine_parent", humanized["murine"]["vh"], humanized["murine"]["vl"]),
        ("2_DEEP-FR", humanized["deepfr"]["vh"], humanized["deepfr"]["vl"]),
        ("3_9AA-CTX", humanized["9aa_ctx"]["vh"], humanized["9aa_ctx"]["vl"]),
    ]
    for key, label in (
        ("cdr_graft_pure", "4_CDR_graft_pure"),
        ("cdr_graft_vernier_bm", "5_CDR_graft_Vernier_BM"),
        ("surface_reshaping", "6_surface_reshaping"),
    ):
        if key in graft_data:
            pairs.append((label, graft_data[key]["vh"], graft_data[key]["vl"]))

    pdb_murine = PROJ / "mouse_cd20_fv.pdb"
    structure_note = {
        "murine_fv_pdb": str(pdb_murine.resolve()) if pdb_murine.is_file() else None,
        "humanized_structures": "not_generated — run ABodyBuilder2 per variant if PDB required",
    }

    rows: List[Dict[str, Any]] = []
    for label, vh, vl in pairs:
        m = CMCMetricEngine.compute_metrics(vh, vl)
        if m.get("_biopython_missing"):
            print("BioPython missing", file=sys.stderr)
            return 1
        adi = round(compute_adi(m, ref_metrics=ref_m), 2)
        pct_raw = compute_adi_percentile(adi, adi_dist_path=ABREF_ADI_DIST)
        pct = round(float(pct_raw), 1) if pct_raw is not None else None
        br = compute_adi_with_breakdown(m, ref_metrics=ref_m)

        row = {
            "label": label,
            "vh_len": len(vh),
            "vl_len": len(vl),
            "metrics": m,
            "ADI_AbRef458": adi,
            "ADI_percentile_rank_approx": pct,
            "ADI_percentile_rank_approx_raw": pct_raw,
            "bands": {
                "pI": _metric_band("pI", float(m.get("pI", 0)), ref_m.get("pI", {})),
                "GRAVY": _metric_band("GRAVY", float(m.get("GRAVY", 0)), ref_m.get("GRAVY", {})),
                "instability_index": _metric_band(
                    "instability_index",
                    float(m.get("instability_index", 0)),
                    ref_m.get("instability_index", {}),
                ),
                "agg_motifs": _metric_band(
                    "agg_motifs",
                    float(len(m.get("agg_motifs", [])) if isinstance(m.get("agg_motifs"), list) else m.get("agg_motifs", 0)),
                    ref_m.get("agg_motifs", {}),
                ),
            },
            "ADI_breakdown_categories": br.get("category_scores"),
        }
        # agg_motifs is int from engine
        if isinstance(m.get("agg_motifs"), int):
            row["bands"]["agg_motifs"] = _metric_band(
                "agg_motifs", float(m["agg_motifs"]), ref_m.get("agg_motifs", {})
            )
        rows.append(row)

    out_doc: Dict[str, Any] = {
        "_meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "clinical_reference": "AbRef-458 (engineered therapeutic IgG Fv, n=458)",
            "reference_file": str(ABREF_STATS.relative_to(SUITE)),
            "ADI_percentile_from": "data/reference/AbRef458_27m_ADI_distribution_v1.json",
            "structure": structure_note,
        },
        "variants": rows,
    }

    PROJ.mkdir(parents=True, exist_ok=True)
    (PROJ / "clinical_abref458_benchmark.json").write_text(
        json.dumps(out_doc, indent=2, default=str), encoding="utf-8"
    )

    # Markdown summary
    lines: List[str] = [
        "# Mouse anti-CD20 — sequences + clinical (AbRef-458) benchmark",
        "",
        "## Sequence & structure artifacts",
        "",
        "| Artifact | Path |",
        "|----------|------|",
        f"| ANARCI segmentation | `projects/mouse_cd20_humanization/annotation.json` |",
        f"| All humanization variants (FASTA-ready) | `projects/mouse_cd20_humanization/humanized_sequences.json` |",
        f"| CDR graft vs surface reshape | `projects/mouse_cd20_humanization/graft_surface_compare.json` |",
        f"| Murine Fv structure (ABodyBuilder2) | `projects/mouse_cd20_humanization/mouse_cd20_fv.pdb` |",
        "",
        "Humanized/scaffold-only structures were **not** batch-exported as PDB in this project; use ImmuneBuilder ABodyBuilder2 on each VH+VL pair if needed.",
        "",
        "## CMC vs clinical engineered cohort (AbRef-458)",
        "",
        "ADI and per-metric tent scores use **`data/reference/AbRef458_stats_v1.json`** (842 pipeline: engineered 458). ",
        "Approximate ADI percentile uses **`data/reference/AbRef458_27m_ADI_distribution_v1.json`**.",
        "",
        "| Variant | ADI | ADI pct (approx) | pI | GRAVY | Instab. | agg_motifs |",
        "|---------|-----|------------------|-----|-------|---------|------------|",
    ]
    for r in rows:
        m = r["metrics"]
        lines.append(
            f"| {r['label']} | {r['ADI_AbRef458']} | {r['ADI_percentile_rank_approx']} | "
            f"{m.get('pI')} | {m.get('GRAVY')} | {m.get('instability_index')} | {m.get('agg_motifs')} |"
        )
    lines.extend(
        [
            "",
            "Full JSON (including SAP, liabilities, category breakdown): `clinical_abref458_benchmark.json`.",
            "",
        ]
    )
    (PROJ / "CLINICAL_BENCHMARK.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(out_doc["_meta"], indent=2))
    print(f"\nWrote {PROJ / 'clinical_abref458_benchmark.json'}")
    print(f"Wrote {PROJ / 'CLINICAL_BENCHMARK.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
