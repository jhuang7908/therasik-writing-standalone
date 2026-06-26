#!/usr/bin/env python3
"""
Build the list of all therapeutic antibodies that are multispecific AND have linker
(scFv, BiTE, Tandem, Mixed mAb+scFv, etc.) from Thera-SAbDab export.

Reads: data/thera_sabdab/thera_export.xlsx
Writes: data/design_rules/multispecific_linker_from_export.json
        data/design_rules/multispecific_linker_from_export.csv (optional)

Usage:
  python scripts/build_multispecific_linker_list.py
  python scripts/build_multispecific_linker_list.py --csv
"""
import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXCEL_PATH = PROJECT_ROOT / "data" / "thera_sabdab" / "thera_export.xlsx"
OUT_DIR = PROJECT_ROOT / "data" / "design_rules"

# : ///
MULTI_KEYWORDS = ("Bispecific", "Trispecific", "Tetraspecific", "Pentaspecific")

#  linker :  scFv、BiTE、Tandem、Mixed mAb and scFv 
LINKER_INDICATORS = (
    "scFv",
    "BiTE",
    "Tandem",
    "Mixed mAb and scFv",
    "scFv-scFv",
    "G1-scFv",
    "VH-",
    "Crossover",  # scFv with Crossover
)


def _valid_str(val):
    try:
        import pandas as pd
        if pd.isna(val):
            return ""
    except Exception:
        pass
    return str(val).strip() if val is not None else ""


def is_multispecific(format_val) -> bool:
    s = _valid_str(format_val)
    return any(k in s for k in MULTI_KEYWORDS)


def has_linker_format(format_val) -> bool:
    s = _valid_str(format_val)
    return any(ind in s for ind in LINKER_INDICATORS)


def main():
    parser = argparse.ArgumentParser(description="Build multispecific+linker list from thera_export.xlsx")
    parser.add_argument("--csv", action="store_true", help="Also write multispecific_linker_from_export.csv")
    parser.add_argument("--xlsx", type=str, default=None, help="Path to thera export Excel (default: data/thera_sabdab/thera_export.xlsx)")
    args = parser.parse_args()

    xlsx_path = Path(args.xlsx) if args.xlsx else EXCEL_PATH
    if not xlsx_path.is_file():
        raise FileNotFoundError(f"Export not found: {xlsx_path}")

    try:
        import pandas as pd
    except ImportError:
        raise SystemExit("Requires pandas and openpyxl: pip install pandas openpyxl")

    df = pd.read_excel(xlsx_path, engine="openpyxl")
    if "Format" not in df.columns or "Therapeutic" not in df.columns:
        raise ValueError("Excel must have columns 'Format' and 'Therapeutic'")

    mask = df.apply(
        lambda row: is_multispecific(row.get("Format")) and has_linker_format(row.get("Format")),
        axis=1,
    )
    subset = df.loc[mask, ["Therapeutic", "Format"]].drop_duplicates(subset=["Therapeutic"], keep="first")
    subset = subset.sort_values("Therapeutic").reset_index(drop=True)

    records = []
    for _, row in subset.iterrows():
        aid = str(row["Therapeutic"]).strip()
        fmt = row["Format"]
        if pd.isna(fmt):
            fmt_str = ""
        else:
            fmt_str = str(fmt).strip()
        records.append({"antibody_id": aid, "format_raw": fmt_str})

    antibody_ids = [r["antibody_id"] for r in records]

    out = {
        "meta": {
            "source": "thera_export.xlsx",
            "description": "All multispecific antibodies with linker (scFv, BiTE, Tandem, Mixed mAb+scFv, etc.)",
            "count": len(antibody_ids),
        },
        "antibody_ids": antibody_ids,
        "records": records,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_json = OUT_DIR / "multispecific_linker_from_export.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {out_json.name}: {len(antibody_ids)} antibodies")

    if args.csv:
        out_csv = OUT_DIR / "multispecific_linker_from_export.csv"
        subset.to_csv(out_csv, index=False, encoding="utf-8")
        print(f"Wrote {out_csv.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
