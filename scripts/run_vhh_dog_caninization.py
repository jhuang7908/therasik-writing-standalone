"""
VHH → （sdAb）CLI — vhh_dog workflow
================================================
：
    python scripts/run_vhh_dog_caninization.py \\
        --project Caplacizumab_dog \\
        --vhh QVQLVESGG... \\
        [--format sdab|fab] \\
        [--out-dir projects/Caplacizumab_dog/delivery]

（）：
  •   : data/vhh_39_clinical_atlas/ (39  VHH)
  • Germline DB : data/germlines/canis_lupus_familiaris_ig_aa/IGHV_aa.json (54  IGHV)
  •     : config/vhh_dog_caninization_checklist_v1.json (T1/T2/T3 + Hallmark)
  •     : NanoBodyBuilder2 (donor + caninized VHH)
  •     : DLA 6-allele ( MHC-II —  IEDB HLA)
"""

import argparse
import json
import sys
from pathlib import Path

_SUITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SUITE_ROOT))

import scripts.anarci_shim  # MUST be first — before any ImmuneBuilder import


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="VHH → canine sdAb caninization (vhh_dog workflow)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--project",   required=True,  help="Project name / antibody ID")
    p.add_argument("--vhh",       default="",     help="Donor VHH amino acid sequence")
    p.add_argument("--vhh-file",  default="",     help="File containing donor VHH sequence (plain text or .json)")
    p.add_argument(
        "--format", choices=["sdab", "fab"], default="sdab",
        help="Output format: sdab (single-domain, pos44=Q) or fab (add dog VL, pos44=G). "
             "sdab is recommended for most VHH. Default: sdab",
    )
    p.add_argument("--out-dir", default="",       help="Output directory (default: projects/<project>/delivery_vhh_dog)")
    p.add_argument("--json-only", action="store_true", help="Write JSON report only (no MD)")
    return p.parse_args()


def _load_sequence(vhh_str: str, vhh_file: str) -> str:
    if vhh_str:
        return vhh_str.strip()
    if vhh_file:
        fp = Path(vhh_file)
        if not fp.is_file():
            print(f"[ERROR] VHH file not found: {fp}", file=sys.stderr)
            sys.exit(1)
        text = fp.read_text(encoding="utf-8").strip()
        if text.startswith("{"):
            data = json.loads(text)
            for key in ("sequence", "vhh", "VHH", "seq", "aa"):
                if key in data:
                    return data[key].strip()
            print(f"[ERROR] Cannot find sequence key in JSON file {fp}", file=sys.stderr)
            sys.exit(1)
        return text
    return ""


def main() -> None:
    args = _parse_args()

    vhh_seq = _load_sequence(args.vhh, args.vhh_file)
    if not vhh_seq:
        print("[ERROR] Provide --vhh <sequence> or --vhh-file <path>", file=sys.stderr)
        sys.exit(1)

    out_dir = (
        Path(args.out_dir)
        if args.out_dir
        else _SUITE_ROOT / "projects" / args.project / "delivery_vhh_dog"
    )

    print(f"\n{'='*60}")
    print(f"  VHH →  (vhh_dog)  |  {args.project}")
    print(f"  Format : {args.format}")
    print(f"  Out    : {out_dir}")
    print(f"{'='*60}\n")

    from core.humanization.engine import HumanizationEngine

    engine = HumanizationEngine(workflow="vhh_dog")
    result = engine.run(
        mouse_vh=vhh_seq,
        mouse_vl="",              # VHH: no VL
        project_name=args.project,
        out_dir=str(out_dir),
        strategy=args.format,    # fmt passed via strategy slot
    )

    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = result.save_report(out_dir / "vhh_dog_caninization_report.json")
    print(f"\n[Done] JSON report: {json_path}")
    print(f"[Done] Status: {result.overall_status}")

    if not args.json_only:
        md_path = result.save_report_md(out_dir / "vhh_dog_caninization_report.md")
        print(f"[Done] MD report:   {md_path}")

    caninized = result.sequences.get("caninized_vhh", "")
    if caninized:
        seq_path = out_dir / "caninized_vhh.fa"
        seq_path.write_text(f">{args.project}_caninized_vhh\n{caninized}\n", encoding="utf-8")
        print(f"[Done] Sequence:    {seq_path}")
    else:
        print("[WARN] Caninized sequence not generated (dry-run or graft deferred).")

    sys.exit(0 if result.overall_status in ("PASS", "WARN") else 1)


if __name__ == "__main__":
    main()
