#!/usr/bin/env python3
"""
Merge TheraSAbDab / SAbDab sequence export (xlsx) with InSynBio ADA package.

Reads:  data/thera_sabdab/TheraSAbDab_SeqStruc_OnlineDownload.xlsx (or --input)
Writes: data/thera_sabdab/out/TheraSAbDab_SeqStruc_with_ADA.xlsx (or --output)

ADA JSONs (priority: confirmed > need_fulltext > cannot_verify):
  data/ADA_reliable_package/final_three_files/{confirmed_ada,need_fulltext,cannot_verify_ada}.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

SUITE = Path(__file__).resolve().parents[1]
ADA_DIR = SUITE / "data/ADA_reliable_package/final_three_files"
DEFAULT_IN = SUITE / "data/thera_sabdab/TheraSAbDab_SeqStruc_OnlineDownload.xlsx"
DEFAULT_OUT = SUITE / "data/thera_sabdab/out/TheraSAbDab_SeqStruc_with_ADA.xlsx"

# Prefer exact column headers (TheraSAbDab uses "Therapeutic").
NAME_EXACT_ORDER = (
    "therapeutic",
    "inn",
    "drug name",
    "therapeutic name",
    "antibody name",
    "generic name",
    "mab name",
)
# Substring hints — avoid "alternative … names" matching generic "name"
NAME_SUBSTRING_HINTS = ("inn", "drug name", "therapeutic name", "antibody name", "generic name")
ALT_NAMES_COL_HINTS = ("alternative therapeutic", "alternative name", "synonym")


def _norm_key(s: object) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    t = str(s).strip().lower()
    t = re.sub(r"\s+", "", t)
    t = re.sub(r"[-_/]", "", t)
    return t


def _biosimilar_stripped_key(s: object) -> str:
    base = _norm_key(s)
    m = re.match(r"^([a-z]{6,})([a-z]{4})$", base)
    if m and len(m.group(1)) >= 8:
        return m.group(1)
    return base


def _find_name_column(cols: list[str]) -> str | None:
    low = {c: str(c).strip().lower() for c in cols}
    for ex in NAME_EXACT_ORDER:
        for c, lc in low.items():
            if lc == ex:
                return c
    for hint in NAME_SUBSTRING_HINTS:
        for c, lc in low.items():
            if "alternative" in lc:
                continue
            if hint in lc and len(lc) < 45:
                return c
    for c, lc in low.items():
        if "name" in lc and "alternative" not in lc:
            return c
    return cols[0] if cols else None


def _find_alt_names_column(cols: list[str]) -> str | None:
    low = {c: str(c).strip().lower() for c in cols}
    for c, lc in low.items():
        if any(h in lc for h in ALT_NAMES_COL_HINTS):
            return c
    return None


def _alt_name_tokens(val: object) -> list[str]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []
    s = str(val).strip()
    if not s or s.lower() == "nan" or s.lower() == "na":
        return []
    parts = re.split(r"[;|,/\n]+", s)
    return [p.strip() for p in parts if p.strip()]


def _urls_to_str(urls: object) -> str:
    if not urls:
        return ""
    if isinstance(urls, str):
        return urls
    return "; ".join(str(u) for u in urls if u)


def _load_ada_lookup() -> dict[str, dict]:
    ordered_files = [
        ("cannot_verify", "cannot_verify_ada.json"),
        ("need_fulltext", "need_fulltext.json"),
        ("confirmed", "confirmed_ada.json"),
    ]
    by_key: dict[str, dict] = {}
    for category, fname in ordered_files:
        path = ADA_DIR / fname
        if not path.exists():
            continue
        blob = json.loads(path.read_text(encoding="utf-8"))
        for e in blob.get("entries", []):
            name = e.get("antibody_name") or e.get("name") or ""
            for k in {_norm_key(name), _biosimilar_stripped_key(name)}:
                if not k:
                    continue
                by_key[k] = {
                    "ada_package_category": category,
                    "ada_antibody_name_matched": name,
                    "ada_value_display": e.get("ada_value_display", ""),
                    "ada_evidence_tier": e.get("class_evidence_tier", ""),
                    "ada_verification_status": e.get("verification_status", ""),
                    "ada_citation_urls": _urls_to_str(e.get("citation_urls")),
                    "ada_manual_check_reason": e.get("manual_check_reason", ""),
                    "ada_suggested_action": e.get("suggested_action", ""),
                    "ada_cannot_verify_reason": e.get("cannot_verify_reason", ""),
                    "ada_cannot_verify_detail": e.get("detail", ""),
                    "ada_value_annotation": e.get("ada_value_annotation", ""),
                    "ada_value_extraction": e.get("ada_value_extraction", ""),
                }
    return by_key


def _lookup_one(val: object, ada_by_key: dict[str, dict]) -> dict | None:
    for k in {_norm_key(val), _biosimilar_stripped_key(val)}:
        if k and k in ada_by_key:
            return dict(ada_by_key[k])
    return None


def merge_frame(df: pd.DataFrame, ada_by_key: dict[str, dict]) -> pd.DataFrame:
    cols = list(df.columns)
    name_col = _find_name_column(cols)
    if not name_col:
        raise SystemExit("Could not detect drug/antibody name column.")
    alt_col = _find_alt_names_column(cols)

    def lookup_row(primary: object, alt_cell: object | None) -> dict:
        hit = _lookup_one(primary, ada_by_key)
        if hit:
            return hit
        if alt_cell is not None and alt_col:
            for token in _alt_name_tokens(alt_cell):
                hit = _lookup_one(token, ada_by_key)
                if hit:
                    return hit
        return {
            "ada_package_category": "not_in_ada_package",
            "ada_antibody_name_matched": "",
            "ada_value_display": "",
            "ada_evidence_tier": "",
            "ada_verification_status": "",
            "ada_citation_urls": "",
            "ada_manual_check_reason": "",
            "ada_suggested_action": "",
            "ada_cannot_verify_reason": "",
            "ada_cannot_verify_detail": "",
            "ada_value_annotation": "",
            "ada_value_extraction": "",
        }

    if alt_col:
        ada_df = pd.DataFrame(
            [
                lookup_row(df[name_col].iloc[i], df[alt_col].iloc[i])
                for i in range(len(df))
            ]
        )
    else:
        ada_df = pd.DataFrame([lookup_row(v, None) for v in df[name_col]])
    out = pd.concat([df.reset_index(drop=True), ada_df], axis=1)
    out.insert(len(df.columns), "ada_match_key_used", [_norm_key(v) for v in df[name_col]])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Merge TheraSAbDab xlsx with ADA package.")
    ap.add_argument("--input", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sheet", type=str, default="0", help="Sheet index (int) or sheet name")
    args = ap.parse_args()

    if not args.input.exists():
        raise SystemExit(
            f"Input not found: {args.input}\n"
            "Save TheraSAbDab_SeqStruc_OnlineDownload.xlsx there or pass --input."
        )

    try:
        sheet = int(args.sheet)
    except ValueError:
        sheet = args.sheet

    ada_by_key = _load_ada_lookup()
    df = pd.read_excel(args.input, sheet_name=sheet, engine="openpyxl")
    merged = merge_frame(df, ada_by_key)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    merged.to_excel(args.output, index=False, engine="openpyxl")

    print(f"Wrote: {args.output}")
    print(f"Rows: {len(merged)}")
    print(merged["ada_package_category"].value_counts().to_string())
    nc = _find_name_column(list(df.columns))
    print(f"Name column detected: {nc!r}")


if __name__ == "__main__":
    main()
