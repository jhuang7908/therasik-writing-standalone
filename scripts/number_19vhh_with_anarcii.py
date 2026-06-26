"""
Number the 19 clinical VHH sequences using ANARCII (IMGT scheme) and extract CDR boundaries.

Inputs:
  - paper/raw data/TheraSAbDab_19VHH_extracted_rows.csv

Outputs (written to paper/raw data/):
  - TheraSAbDab_19VHH_ANARCII_numbering_full.csv      (all residues with IMGT positions)
  - TheraSAbDab_19VHH_ANARCII_CDR_boundaries.csv      (CDR1/2/3 start/end per antibody)
  - TheraSAbDab_19VHH_ANARCII_summary.txt             (human-readable summary)

CDR definition (IMGT for VHH):
  - CDR1-IMGT: 27-38
  - CDR2-IMGT: 56-65
  - CDR3-IMGT: 105-117

This script uses the project's anarcii_adapter.py to ensure consistency.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.numbering.anarcii_adapter import number_sequence, get_engine_info

IN_EXTRACTED = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_19VHH_extracted_rows.csv"

OUT_DIR = PROJECT_ROOT / "paper" / "raw data"
OUT_NUMBERING_CSV = OUT_DIR / "TheraSAbDab_19VHH_ANARCII_numbering_full.csv"
OUT_CDR_CSV = OUT_DIR / "TheraSAbDab_19VHH_ANARCII_CDR_boundaries.csv"
OUT_SUMMARY = OUT_DIR / "TheraSAbDab_19VHH_ANARCII_summary.txt"


# IMGT CDR boundaries for VHH (single-domain heavy chain)
# CDR1-IMGT: 27-38 (12 positions including insertions)
# CDR2-IMGT: 56-65 (10 positions including insertions)
# CDR3-IMGT: 105-117 (variable length, starts at 105, ends at 117 or before)

IMGT_CDR1_START = 27
IMGT_CDR1_END = 38
IMGT_CDR2_START = 56
IMGT_CDR2_END = 65
IMGT_CDR3_START = 105
IMGT_CDR3_END = 117


def _parse_position_label(label: str) -> tuple[int, str]:
    """Parse IMGT position label into (number, insertion_code)."""
    if not label:
        return (0, "")
    # e.g., "37A" -> (37, "A"), "56" -> (56, "")
    import re
    m = re.match(r"^(\d+)([A-Z]?)$", label.strip())
    if m:
        return (int(m.group(1)), m.group(2) or "")
    return (0, "")


def _in_cdr_range(pos_num: int, start: int, end: int) -> bool:
    """Check if position number falls in CDR range [start, end]."""
    return start <= pos_num <= end


def main() -> None:
    if not IN_EXTRACTED.exists():
        raise FileNotFoundError(f"Missing input: {IN_EXTRACTED}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load 19 VHH sequences
    df = pd.read_csv(IN_EXTRACTED)
    if "_table1_antibody_id" not in df.columns or "HeavySequence" not in df.columns:
        raise ValueError("Input CSV must have columns: _table1_antibody_id, HeavySequence")

    # Get ANARCII engine info
    engine = get_engine_info()
    print(f"Using ANARCII engine: {engine}")

    # Storage for outputs
    all_residues: list[dict] = []
    cdr_boundaries: list[dict] = []
    summary_lines: list[str] = []

    summary_lines.append("=" * 80)
    summary_lines.append("ANARCII IMGT Numbering Summary for 19 Clinical VHHs")
    summary_lines.append("=" * 80)
    summary_lines.append(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    summary_lines.append(f"ANARCII version: {engine.get('version', 'unknown')}")
    summary_lines.append("")

    failed_count = 0
    success_count = 0

    for idx, row in df.iterrows():
        ab_id = str(row["_table1_antibody_id"]).strip()
        seq = str(row.get("HeavySequence", "")).strip()

        if not seq or seq.lower() in {"nan", "none", ""}:
            summary_lines.append(f"[SKIP] {ab_id}: No sequence provided")
            failed_count += 1
            continue

        summary_lines.append("")
        summary_lines.append(f"--- {ab_id} ---")
        summary_lines.append(f"Sequence length: {len(seq)} aa")

        try:
            pos_to_aa, residue_table = number_sequence(seq, scheme="imgt")
        except Exception as e:
            summary_lines.append(f"[ERROR] ANARCII numbering failed: {e}")
            failed_count += 1
            continue

        if not residue_table:
            summary_lines.append("[ERROR] ANARCII returned empty numbering")
            failed_count += 1
            continue

        success_count += 1

        # Extract CDR residues by IMGT position
        cdr1_residues = []
        cdr2_residues = []
        cdr3_residues = []

        for res in residue_table:
            pos_label = res.get("position_label", "")
            aa = res.get("aa", "")
            if not pos_label:
                continue

            pos_num, ins_code = _parse_position_label(pos_label)

            # Annotate region
            region = "FR"
            if _in_cdr_range(pos_num, IMGT_CDR1_START, IMGT_CDR1_END):
                region = "CDR1"
                cdr1_residues.append((pos_label, aa))
            elif _in_cdr_range(pos_num, IMGT_CDR2_START, IMGT_CDR2_END):
                region = "CDR2"
                cdr2_residues.append((pos_label, aa))
            elif _in_cdr_range(pos_num, IMGT_CDR3_START, IMGT_CDR3_END):
                region = "CDR3"
                cdr3_residues.append((pos_label, aa))

            # Append to all_residues
            all_residues.append(
                {
                    "antibody_id": ab_id,
                    "seq_idx": res.get("seq_idx", -1),
                    "imgt_position": pos_label,
                    "aa": aa,
                    "region": region,
                }
            )

        # Record CDR boundaries
        cdr1_seq = "".join([x[1] for x in cdr1_residues])
        cdr2_seq = "".join([x[1] for x in cdr2_residues])
        cdr3_seq = "".join([x[1] for x in cdr3_residues])

        cdr1_start = cdr1_residues[0][0] if cdr1_residues else ""
        cdr1_end = cdr1_residues[-1][0] if cdr1_residues else ""
        cdr2_start = cdr2_residues[0][0] if cdr2_residues else ""
        cdr2_end = cdr2_residues[-1][0] if cdr2_residues else ""
        cdr3_start = cdr3_residues[0][0] if cdr3_residues else ""
        cdr3_end = cdr3_residues[-1][0] if cdr3_residues else ""

        cdr_boundaries.append(
            {
                "antibody_id": ab_id,
                "cdr1_start_imgt": cdr1_start,
                "cdr1_end_imgt": cdr1_end,
                "cdr1_length": len(cdr1_seq),
                "cdr1_sequence": cdr1_seq,
                "cdr2_start_imgt": cdr2_start,
                "cdr2_end_imgt": cdr2_end,
                "cdr2_length": len(cdr2_seq),
                "cdr2_sequence": cdr2_seq,
                "cdr3_start_imgt": cdr3_start,
                "cdr3_end_imgt": cdr3_end,
                "cdr3_length": len(cdr3_seq),
                "cdr3_sequence": cdr3_seq,
            }
        )

        summary_lines.append(f"CDR1 (IMGT {cdr1_start}-{cdr1_end}): {cdr1_seq} (length={len(cdr1_seq)})")
        summary_lines.append(f"CDR2 (IMGT {cdr2_start}-{cdr2_end}): {cdr2_seq} (length={len(cdr2_seq)})")
        summary_lines.append(f"CDR3 (IMGT {cdr3_start}-{cdr3_end}): {cdr3_seq} (length={len(cdr3_seq)})")

    summary_lines.append("")
    summary_lines.append("=" * 80)
    summary_lines.append(f"Summary: {success_count} succeeded, {failed_count} failed (total={len(df)})")
    summary_lines.append("=" * 80)

    # Write outputs
    pd.DataFrame(all_residues).to_csv(OUT_NUMBERING_CSV, index=False)
    pd.DataFrame(cdr_boundaries).to_csv(OUT_CDR_CSV, index=False)
    OUT_SUMMARY.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print(f"Wrote: {OUT_NUMBERING_CSV}")
    print(f"Wrote: {OUT_CDR_CSV}")
    print(f"Wrote: {OUT_SUMMARY}")


if __name__ == "__main__":
    main()
