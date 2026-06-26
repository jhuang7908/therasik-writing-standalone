"""
run_pet_template_selector.py
──────────────────────────────────────────────────────────────────────────────
CLI wrapper for the pet template selector.

Selects optimal canine/feline scaffold templates for a donor VH or VL using
the 5-component weighted scoring system.

Usage:
    python scripts/run_pet_template_selector.py \\
        --donor-seq EVQLVES... \\
        --species dog \\
        --locus IGHV \\
        --out-dir my_project/templates
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.petization.template_selector import select_pet_template


def _parse_seq_arg(arg: str) -> str:
    """Accept raw AA string or path to FASTA file (returns first sequence)."""
    if not arg:
        return ""
    p = Path(arg)
    if p.is_file():
        seq_lines: List[str] = []
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith(">") or not line.strip():
                if seq_lines:
                    return "".join(seq_lines).strip()
                continue
            seq_lines.append(line.strip())
        return "".join(seq_lines).strip()
    return arg.strip()


def _render_md_report(result: Dict[str, Any], donor_seq: str) -> str:
    lines: List[str] = [
        "# Pet Template Selection Report",
        "",
        f"**Species:** {result['donor_species'].capitalize()}  ",
        f"**Locus:** {result['donor_locus']}  ",
        f"**Pool size:** {result['pool_size']}  ",
        f"**Passing hard constraints:** {result['n_passing']}  ",
        f"**Rejected:** {result['n_rejected']}  ",
        "",
        f"**Donor sequence length:** {len(donor_seq)} aa",
        "",
        "## Scoring Weights",
        "",
        "| Component | Weight |",
        "|---|---|",
    ]
    for k, v in result["scoring_weights"].items():
        lines.append(f"| {k} | {v:.2f} |")
    lines += ["", "## Top Templates", ""]

    if not result["top_templates"]:
        lines.append("_No templates passed hard constraints._")
    else:
        lines.append(
            "| Rank | Gene | Tier | Total | FR_id | CMC | PGC | CDR_len | Abund | Flags |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for i, t in enumerate(result["top_templates"], 1):
            c = t["scoring"]["components"]
            lines.append(
                f"| {i} | `{t['gene']}` | {t['tier']} | "
                f"**{t['total_score']:.4f}** | {c['fr_identity']:.3f} | "
                f"{c['cmc_quality']:.3f} | {c['template_pgc']:.3f} | "
                f"{c['cdr_length_match']:.3f} | {c['germline_abundance']:.3f} | "
                f"{t.get('total_flags', 'N/A')} |"
            )

    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Pet template selector — 5-component weighted scoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--donor-seq", required=True,
                    help="Donor sequence (raw AA string or FASTA file)")
    ap.add_argument("--species", choices=["dog", "cat"], required=True)
    ap.add_argument("--locus", choices=["IGHV", "IGKV", "IGLV"], required=True)
    ap.add_argument("--out-dir", default=".",
                    help="Output directory for JSON + MD reports")
    ap.add_argument("--top-n", type=int, default=3,
                    help="Number of top templates to return")
    ap.add_argument("--include-rejected", action="store_true",
                    help="Include rejected templates with violations in JSON")
    args = ap.parse_args()

    donor_seq = _parse_seq_arg(args.donor_seq)
    if not donor_seq:
        sys.exit("ERROR: --donor-seq is empty or file not found.")

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    print(f"[Pet Template Selector] Species={args.species} Locus={args.locus} "
          f"Donor_len={len(donor_seq)}")
    result = select_pet_template(
        donor_seq=donor_seq,
        species=args.species,
        locus=args.locus,
        top_n=args.top_n,
        include_failed=args.include_rejected,
    )

    json_path = out / "pet_template_selection.json"
    md_path = out / "PET_TEMPLATE_SELECTION.md"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(_render_md_report(result, donor_seq), encoding="utf-8")

    print(f"  Pool={result['pool_size']} | Passing={result['n_passing']} | "
          f"Rejected={result['n_rejected']}")
    if result["top_templates"]:
        top = result["top_templates"][0]
        print(f"  Top template: {top['gene']} ({top['tier']}) score={top['total_score']:.4f}")
    print(f"  JSON  → {json_path}")
    print(f"  MD    → {md_path}")


if __name__ == "__main__":
    main()
