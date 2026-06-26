#!/usr/bin/env python3
"""
Join curated ADA records (ada_curated_all_with_ada.json) with QA / OpenClaw exports
copied under data/ADA_reliable_package/qa/. Does not pick a single truth; all
layers are kept for manual adjudication.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CURATED = REPO / "data" / "ADA_reliable_package" / "curated" / "ada_curated_all_with_ada.json"
QA_DIR = REPO / "data" / "ADA_reliable_package" / "qa"
OUT = REPO / "data" / "ADA_reliable_package" / "ada_merged_multisource.json"

QA_CONSISTENCY = QA_DIR / "ada_text_consistency_analysis.json"
QA_REGEN_CMP = QA_DIR / "17_antibodies_regeneration_comparison_20260330_102738.json"
QA_REAL17 = QA_DIR / "17_antibodies_real_ada_evidence.json"


def _load_json(path: Path):
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    if not CURATED.is_file():
        raise SystemExit(f"Run build_ada_reliable_database.py first; missing {CURATED}")

    bundle = _load_json(CURATED)
    antibodies = bundle.get("antibodies", [])

    qc = _load_json(QA_CONSISTENCY) or {}
    qa_by_name = {r["antibody_name"]: r for r in qc.get("detailed_results", []) if r.get("antibody_name")}

    cmp_data = _load_json(QA_REGEN_CMP) or {}
    cmp_by_name = {r["antibody_name"]: r for r in cmp_data.get("comparison_data", []) if r.get("antibody_name")}

    real17 = _load_json(QA_REAL17)
    real_by_name = {}
    if isinstance(real17, list):
        for r in real17:
            if r.get("antibody_name"):
                real_by_name[r["antibody_name"]] = r

    curated_names = {a["antibody_name"] for a in antibodies if a.get("antibody_name")}
    only_in_real17 = sorted(real_by_name.keys() - curated_names)

    merged = []
    for ab in sorted(antibodies, key=lambda x: (x.get("antibody_name") or "").lower()):
        name = ab.get("antibody_name")
        sup = {
            "qa_text_consistency": qa_by_name.get(name),
            "regeneration_comparison_20260330": cmp_by_name.get(name),
            "openclaw_real_evidence_17": real_by_name.get(name),
        }
        sup = {k: v for k, v in sup.items() if v is not None}
        merged.append(
            {
                "antibody_name": name,
                "primary_source": "curated_pipeline_openclaw_reliable_merged",
                "primary_curated": ab,
                "supplemental": sup,
            }
        )

    for name in only_in_real17:
        merged.append(
            {
                "antibody_name": name,
                "primary_source": None,
                "primary_curated": None,
                "supplemental": {
                    "openclaw_real_evidence_17": real_by_name[name],
                },
            }
        )

    payload = {
        "metadata": {
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "description": "Per-antibody union of curated ADA row + optional QA/regeneration/real17 layers.",
            "inputs": {
                "curated": str(CURATED),
                "qa_text_consistency": str(QA_CONSISTENCY) if QA_CONSISTENCY.is_file() else None,
                "regeneration_comparison": str(QA_REGEN_CMP) if QA_REGEN_CMP.is_file() else None,
                "openclaw_real_evidence_17": str(QA_REAL17) if QA_REAL17.is_file() else None,
            },
            "counts": {
                "merged_rows": len(merged),
                "curated_only_rows": len(antibodies),
                "only_in_real_evidence_17": len(only_in_real17),
            },
            "only_in_openclaw_real_evidence_17": only_in_real17,
            "human_review": {
                "final_report_md": str(QA_DIR / "ada_evidence_consistency_final_report.md"),
                "note": "QA layer flags label text mis-attribution (ADA vs CV/CI/viral inhibition). Do not auto-prioritize regenerated Haiku values.",
            },
        },
        "antibodies": merged,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(merged)} rows to {OUT}")


if __name__ == "__main__":
    main()
