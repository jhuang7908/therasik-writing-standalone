"""
Extract the 19 clinical VHH raw records from a Thera-SAbDab Excel export.

Goal:
  - Ensure the "raw data" folder contains an auditable, source-linked extraction
    for the exact 19 molecules used in Table 1.

Inputs:
  - paper/raw data/TheraSAbDab_SeqStruc_OnlineDownload (2).xlsx   (downloaded from Thera-SAbDab)
  - paper/tables/Table1_slice3_19_clinical_vhh_master.csv         (project master list; 19 IDs)

Outputs (written to paper/raw data/):
  - TheraSAbDab_19VHH_extracted_rows.csv
  - TheraSAbDab_19VHH_extracted_rows.md
  - TheraSAbDab_19VHH_extraction_report.txt

Notes on matching:
  - Primary: exact, case-insensitive match of any cell to the 19 antibody_id values.
  - Fallback: match base-name (strip trailing digits) ONLY if exact match fails.
    Fallback matches are flagged in output to preserve auditability.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent

IN_XLSX = PROJECT_ROOT / "paper" / "raw data" / "TheraSAbDab_SeqStruc_OnlineDownload (2).xlsx"
IN_TABLE1 = PROJECT_ROOT / "paper" / "tables" / "Table1_slice3_19_clinical_vhh_master.csv"

OUT_DIR = PROJECT_ROOT / "paper" / "raw data"
OUT_ROWS_CSV = OUT_DIR / "TheraSAbDab_19VHH_extracted_rows.csv"
OUT_ROWS_MD = OUT_DIR / "TheraSAbDab_19VHH_extracted_rows.md"
OUT_REPORT = OUT_DIR / "TheraSAbDab_19VHH_extraction_report.txt"
OUT_ALL_HITS_CSV = OUT_DIR / "TheraSAbDab_19VHH_extracted_rows_all_hits.csv"


def _norm_cell(x: object) -> str:
    if x is None:
        return ""
    s = str(x).strip()
    if s.lower() in {"nan", "none"}:
        return ""
    return s


def _norm_key(s: str) -> str:
    return re.sub(r"\s+", " ", _norm_cell(s)).strip().lower()


def _base_name(s: str) -> str:
    s2 = _norm_cell(s)
    return re.sub(r"\d+$", "", s2).strip().lower()


def main() -> None:
    if not IN_XLSX.exists():
        raise FileNotFoundError(f"Missing raw Thera-SAbDab export: {IN_XLSX}")
    if not IN_TABLE1.exists():
        raise FileNotFoundError(f"Missing master Table1 list: {IN_TABLE1}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # The authoritative 19 IDs used in analysis
    t1 = pd.read_csv(IN_TABLE1)
    ids = [str(x).strip() for x in t1["antibody_id"].dropna().tolist()]
    ids_key = {_norm_key(x) for x in ids}
    ids_base = {_base_name(x) for x in ids}

    # Extract matching rows from Excel (scan all sheets)
    xls = pd.ExcelFile(IN_XLSX)
    extracted_rows: list[pd.DataFrame] = []
    hit_detail: list[dict] = []

    for sheet in xls.sheet_names:
        df = pd.read_excel(IN_XLSX, sheet_name=sheet)
        if df.empty:
            continue

        # Build per-column normalized view for fast isin checks
        col_hits_exact = []
        col_hits_base = []
        for col in df.columns:
            ser = df[col].map(_norm_cell).map(_norm_key)
            col_hits_exact.append(ser.isin(ids_key))
            ser_base = df[col].map(_norm_cell).map(_base_name)
            col_hits_base.append(ser_base.isin(ids_base))

        exact_mask = pd.concat(col_hits_exact, axis=1).any(axis=1)
        base_mask = pd.concat(col_hits_base, axis=1).any(axis=1)
        # Fallback base-name matches only where exact didn't hit
        fallback_mask = base_mask & (~exact_mask)
        final_mask = exact_mask | fallback_mask

        sub = df.loc[final_mask].copy()
        if sub.empty:
            continue

        # For auditability: record where the match came from (sheet, row idx, matched value/col, match_type)
        for ridx in sub.index.tolist():
            match_type = "exact" if bool(exact_mask.loc[ridx]) else "base_name"
            matched = None
            for col in df.columns:
                v = _norm_cell(df.at[ridx, col])
                if not v:
                    continue
                if match_type == "exact" and _norm_key(v) in ids_key:
                    matched = (col, v)
                    break
                if match_type == "base_name" and _base_name(v) in ids_base:
                    matched = (col, v)
                    break
            hit_detail.append(
                {
                    "sheet": sheet,
                    "excel_row_index": int(ridx),
                    "match_type": match_type,
                    "matched_column": matched[0] if matched else "",
                    "matched_value": matched[1] if matched else "",
                }
            )

        sub.insert(0, "_sheet", sheet)
        sub.insert(1, "_match_type", ["exact" if bool(exact_mask.loc[i]) else "base_name" for i in sub.index])
        extracted_rows.append(sub)

    if not extracted_rows:
        raise RuntimeError(
            "No matching rows were found in the Excel export for the 19 antibody_id values from Table1."
        )

    out = pd.concat(extracted_rows, axis=0, ignore_index=True)

    # Add a column with the canonical Table1 IDs if we can map them by exact/base-name
    # This helps join back to analysis later without losing provenance.
    def map_to_table1_id(row: pd.Series) -> str:
        # prefer exact matches
        for v in row.tolist():
            nv = _norm_key(v)
            if nv in ids_key:
                # return original-cased ID from Table1
                for src in ids:
                    if _norm_key(src) == nv:
                        return src
        # fallback base-name
        for v in row.tolist():
            nv = _base_name(v)
            if nv in ids_base:
                # if multiple IDs share base-name, return all joined
                matches = [src for src in ids if _base_name(src) == nv]
                return "|".join(matches)
        return ""

    out["_table1_antibody_id"] = out.apply(map_to_table1_id, axis=1)

    # Keep a full "all hits" table for auditability (may include base-name hits that map onto the same Table1 ID)
    out_all = out.copy()
    out_all.to_csv(OUT_ALL_HITS_CSV, index=False)

    # Reduce to exactly 19 rows (one per Table1 ID), preferring exact Therapeutic-name hits when duplicates exist.
    out = out[out["_table1_antibody_id"].astype(str).str.len() > 0].copy()
    if "Therapeutic" in out.columns:
        out["_is_therapeutic_exact"] = out.apply(
            lambda r: _norm_key(r.get("Therapeutic", "")) == _norm_key(r.get("_table1_antibody_id", "")), axis=1
        )
    else:
        out["_is_therapeutic_exact"] = False

    out["_priority"] = 2
    out.loc[out["_match_type"].eq("exact"), "_priority"] = 1
    out.loc[out["_is_therapeutic_exact"].eq(True), "_priority"] = 0

    out = out.sort_values(["_table1_antibody_id", "_priority"]).groupby("_table1_antibody_id", as_index=False).head(1)
    out = out.drop(columns=["_priority", "_is_therapeutic_exact"], errors="ignore")

    # Validate we truly have the canonical 19
    covered = sorted(set(out["_table1_antibody_id"].astype(str).tolist()))
    missing_after_dedup = [x for x in ids if x not in covered]
    if missing_after_dedup or len(out) != len(ids):
        raise RuntimeError(
            "Extraction did not resolve to exactly 19 unique Table1 IDs.\n"
            f"Rows after dedup: {len(out)} (expected {len(ids)})\n"
            f"Missing: {missing_after_dedup}"
        )

    # Persist final 19-row extraction tables in raw data folder
    out.to_csv(OUT_ROWS_CSV, index=False)
    try:
        out.to_markdown(OUT_ROWS_MD, index=False)
    except Exception:
        # markdown is optional (depends on tabulate)
        OUT_ROWS_MD.write_text(
            "Markdown export failed (missing dependency). CSV was written successfully.\n",
            encoding="utf-8",
        )

    # Report: coverage + any ambiguities
    extracted_ids = set([x for x in out["_table1_antibody_id"].astype(str).tolist() if x and x != "nan"])
    # split any multi-mapped
    extracted_ids_split = set()
    ambiguous = []
    for x in extracted_ids:
        if "|" in x:
            ambiguous.append(x)
            extracted_ids_split.update(x.split("|"))
        else:
            extracted_ids_split.add(x)

    missing = [x for x in ids if x not in extracted_ids_split]

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "Thera-SAbDab raw extraction report (19 clinical VHHs)",
        f"UTC timestamp: {ts}",
        "",
        f"Source Excel: {IN_XLSX}",
        f"Source Table1 list: {IN_TABLE1}",
        f"Output rows CSV: {OUT_ROWS_CSV}",
        "",
        f"Excel sheets scanned: {len(xls.sheet_names)}",
        f"Rows extracted (all hits, pre-dedup): {len(out_all)}",
        f"Rows extracted (final, 1 per Table1 ID): {len(out)}",
        f"Unique Table1 IDs covered (split on '|'): {len(extracted_ids_split)} / {len(ids)}",
        "",
        "Missing Table1 IDs (not found in Excel by exact or base-name matching):",
        *(["- " + m for m in missing] if missing else ["- (none)"]),
        "",
        "Ambiguous base-name mappings (multiple Table1 IDs share the same base-name):",
        *(["- " + a for a in ambiguous] if ambiguous else ["- (none)"]),
        "",
        "All-hits audit table (may include base-name duplicates):",
        f"- {OUT_ALL_HITS_CSV}",
        "",
        "Match audit trail (sheet + row index + match_type + matched_column/value):",
    ]
    for h in hit_detail[:5000]:
        lines.append(
            f"- sheet={h['sheet']}; row={h['excel_row_index']}; type={h['match_type']}; "
            f"col={h['matched_column']}; value={h['matched_value']}"
        )
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("Wrote:", OUT_ROWS_CSV)
    print("Wrote:", OUT_ROWS_MD)
    print("Wrote:", OUT_REPORT)
    if missing:
        raise SystemExit(
            "Extraction completed but some Table1 IDs were not found in the Excel export. "
            "See report for details: " + str(OUT_REPORT)
        )


if __name__ == "__main__":
    main()

