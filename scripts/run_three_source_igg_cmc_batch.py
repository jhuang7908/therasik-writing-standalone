#!/usr/bin/env python3
"""
Offline batch: three Natural-384 discovery-platform antibodies × full IgG CMC pipeline.

Runs the same logic as ``POST /cmc/igg`` (``core.cmc.igg_cmc_pipeline.run_igg_cmc_pipeline``):
AbEvaluator fast modules → regular_ab_developability (source-matched gates, ADI) → optional Fv modeling
→ structural metric patch → FR mutation suggestions → console-style HTML per case.

Usage:
  conda activate anarcii
  # Default output (under repo projects/):
  python scripts/run_three_source_igg_cmc_batch.py

  # Or set output root explicitly:
  python scripts/run_three_source_igg_cmc_batch.py --out-dir projects/my_batch_name

  # Sequence-only (no ImmuneBuilder / SASA — faster smoke):
  python scripts/run_three_source_igg_cmc_batch.py --fast
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Three canonical demo origins (subset stats gates); sequences align with console demos / Markdown smoke script.
CASES: List[Dict[str, Any]] = [
    {
        "id": "natural384_transgenic_animal",
        "label": "Briakinumab (Natural-384 transgenic-animal subset)",
        "antibody_type": "natural384_transgenic_animal",
        "vh": (
            "QVQLVESGGGVVQPGRSLRLSCAASGFTFSSYGMHWVRQAPGKGLEWVAFIRYDGSNKYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCKTHGSHDNWGQGTMVTVSS"
        ),
        "vl": (
            "QSVLTQPPSVSGAPGQRVTISCSGSRSNIGSNTVKWYQQLPGTAPKLLIYYNDQRPSGVPDRFSGSKSGTSASLAITGLQAEDEADYYCQSYDRYTHPALLFGTGTKVTVL"
        ),
    },
    {
        "id": "natural384_phage_display",
        "label": "Adalimumab (Natural-384 phage-display subset)",
        "antibody_type": "natural384_phage_display",
        "vh": (
            "EVQLVESGGGLVQPGRSLRLSCAASGFTFDDYAMHWVRQAPGKGLEWVSAITWNSGHIDYADSVEGRFTISRDNAKNSLYLQMNSLRAEDTAVYYCAKVSYLSTASSLDYWGQGTLVTVSS"
        ),
        "vl": (
            "DIQMTQSPSSLSASVGDRVTITCRASQGIRNYLAWYQQKPGKAPKLLIYAASTLQSGVPSRFSGSGSGTDFTLTISSLQPEDVATYYCQRYNRAPYTFGQGTKVEIK"
        ),
    },
    {
        "id": "natural384_human_b_cell_derived",
        "label": "Actoxumab (Natural-384 human B-cell-derived subset)",
        "antibody_type": "natural384_human_b_cell_derived",
        "vh": (
            "QVQLVESGGGVVQPGRSLRLSCAASGFSFSNYGMHWVRQAPGKGLEWVALIWYDGSNEDYTDSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARWGMVRGVIDVFDIWGQGTVVTVSS"
        ),
        "vl": (
            "DIQMTQSPSSVSASVGDRVTITCRASQGISSWLAWYQHKPGKAPKLLIYAASSLQSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQANSFPWTFGQGTKVEIK"
        ),
    },
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Batch IgG CMC for three Natural-384 platform subsets.")
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help=(
            "Output root (default: projects/three_source_n384_igg_cmc/<UTC timestamp>/). "
            "Each case writes <out-dir>/<case_id>/result.json, CMC_Report.html, index.html, optional PDB."
        ),
    )
    ap.add_argument(
        "--fast",
        action="store_true",
        help="Skip Fv structure modeling (no PDB / SASA / structural TAP patch).",
    )
    args = ap.parse_args()
    if args.out_dir is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
        out_root = (ROOT / "projects" / "three_source_n384_igg_cmc" / stamp).resolve()
    else:
        out_root = args.out_dir.resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    from core.cmc.igg_cmc_report_html import _generate_igg_cmc_html
    from core.cmc.igg_cmc_pipeline import run_igg_cmc_pipeline

    rows: List[str] = []
    for case in CASES:
        cid = case["id"]
        job_dir = out_root / cid
        job_dir.mkdir(parents=True, exist_ok=True)
        payload = run_igg_cmc_pipeline(
            vh_sequence=case["vh"],
            vl_sequence=case["vl"],
            antibody_type=case["antibody_type"],
            project_name=str(case.get("label") or cid)[:100],
            out_dir=job_dir,
            job_id_for_urls=None,
            progress=None,
            run_structure=not args.fast,
        )
        (job_dir / "result.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        html_path = _generate_igg_cmc_html(payload, job_dir)
        hn = html_path.name if html_path else "—"
        rows.append(
            f'<li><a href="{html.escape(cid + "/" + hn)}">{html.escape(cid)}</a> '
            f"— {html.escape(str(case.get('label') or ''))}</li>"
        )

    index_html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Three-source IgG CMC batch</title></head>
<body style="font-family:system-ui,sans-serif;padding:24px">
<h1>Three-source IgG CMC batch</h1>
<p>Each folder contains <code>result.json</code>, console-style HTML, and (unless <code>--fast</code>) <code>Fv_ABodyBuilder2.pdb</code>.</p>
<ul>
{chr(10).join(rows)}
</ul>
</body></html>
"""
    (out_root / "index.html").write_text(index_html, encoding="utf-8")
    print(f"Wrote batch under {out_root} (index.html + {len(CASES)} cases).")
    print(f"Open: {(out_root / 'index.html').as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
