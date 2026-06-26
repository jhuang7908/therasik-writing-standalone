"""
Regenerate VHH humanization HTML report via the same path as the Web Console API
(_humanize_vhh_impl → humanization_report.html).

Usage (from repo root):
  conda activate anarcii
  python scripts/regen_vhh_web_report.py

Optional:
  python scripts/regen_vhh_web_report.py --job-id my_job --out-copy "projects/foo/report.html"
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_SEQ = (
    "QVQLQESGGGLVQAGGSLRLSCAASGTISSLDSMGWYRQAPGKERELVAAIAGGAITYYADSVKGRFTISRDNAKNTVYLQMNSLKPEDTAVYYCAAFTRARQGHYYWGQGTQVTVSS"
)


def main() -> int:
    p = argparse.ArgumentParser(description="Regenerate VHH console HTML report locally.")
    p.add_argument("--seq", default="", help="VHH amino acid sequence (default: sisi E6-4)")
    p.add_argument("--project-name", default="sisi E6-4")
    p.add_argument("--sequence-name", default="sisi E6-4")
    p.add_argument("--job-id", default="sisi_E6-4_regen")
    p.add_argument(
        "--out-copy",
        default=str(ROOT / "projects" / "sisi E6-4" / "delivery_vhh_humanization" / "humanization_report.html"),
        help="Copy generated HTML to this path (parent dirs created). Use empty to skip.",
    )
    args = p.parse_args()

    seq = (args.seq or DEFAULT_SEQ).strip().upper()

    from api.routers.humanization import VHHRequest, _humanize_vhh_impl, jobs

    job_id = args.job_id.strip()
    jobs[job_id] = {"status": "running", "progress": 0, "progress_note": "CLI regen…"}

    req = VHHRequest(
        vhh_sequence=seq,
        project_name=args.project_name,
        sequence_name=args.sequence_name,
        source_species="alpaca",
        strategy="auto",
    )

    res = _humanize_vhh_impl(job_id, req)
    out_dir = ROOT / ".job_storage" / job_id
    html_path = out_dir / "humanization_report.html"

    print("status:", res.status)
    print("report_url:", res.report_url)
    print("html_path:", html_path)

    if html_path.is_file() and args.out_copy.strip():
        dest = Path(args.out_copy)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(html_path, dest)
        print("copied_to:", dest.resolve())

    return 0 if res.status == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
