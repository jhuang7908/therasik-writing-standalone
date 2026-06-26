#!/usr/bin/env python3
"""Compute HPR Index for numeric ADA records.

HPR = Human Peptide Repertoire Compatibility Index. The implementation reuses
`core.humanization.hpr_index.compute_hpr_index`, which scores variable-region
9-mers against the local human antibody repertoire reference.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.humanization.hpr_index import compute_hpr_index


BAD_VALUES = {"", "nan", "none", "true", "false", "0", "115"}


def is_real_seq(value: object) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    return len(text) > 10 and text.lower() not in BAD_VALUES


def clean_sequence(seq: object, chain: str) -> str:
    if not is_real_seq(seq):
        return ""
    text = re.sub(r"[^A-Za-z]", "", str(seq)).upper()

    # Some ADA rows contain variable + constant regions. HPR is defined on
    # variable regions, so trim common constant-region starts.
    if chain == "H":
        for motif in ("ASTKGPSVF", "TVSSASTK", "RTVAAPSVF"):
            idx = text.find(motif)
            if idx > 90:
                return text[:idx]
    else:
        for motif in ("RTVAAPSVF", "TVAAPSVF", "FGQGTKVEIKRTV"):
            idx = text.find(motif)
            if idx > 85:
                return text[:idx]
    return text


def chain_mode(name: str, vh: str, vl: str) -> str:
    if name.casefold() == "tebentafusp":
        return "fusion_fragment_noncanonical"
    if vh and vl:
        return "VHVL"
    if vh and not vl:
        return "single_domain_or_single_fragment"
    if vl and not vh:
        return "single_light_fragment"
    return "not_computed"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv",
        default="data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv",
    )
    parser.add_argument(
        "--full-xlsx",
        default="data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.xlsx",
    )
    parser.add_argument(
        "--analyzable-xlsx",
        default="data/immunogenicity_knowledge_base/master/ada_analyzable_221_final.xlsx",
    )
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    csv_path = (repo / args.csv).resolve()
    full_xlsx = (repo / args.full_xlsx).resolve()
    analyzable_xlsx = (repo / args.analyzable_xlsx).resolve()

    df = pd.read_csv(csv_path)
    numeric = df[["vh_seq", "vl_seq"]].notna().any(axis=1) & df["ada_first_pct"].notna()
    target_indices = list(df.index[numeric])
    if args.limit:
        target_indices = target_indices[: args.limit]

    hpr_cols = [
        "hpr_metric_name",
        "hpr_chain_mode",
        "hpr_vh_score",
        "hpr_vh_found_9mers",
        "hpr_vh_total_9mers",
        "hpr_vh_status",
        "hpr_vl_score",
        "hpr_vl_found_9mers",
        "hpr_vl_total_9mers",
        "hpr_vl_status",
        "hpr_combined_score",
        "hpr_combined_found_9mers",
        "hpr_combined_total_9mers",
        "hpr_combined_status",
        "hpr_source_reference",
        "hpr_note",
    ]
    for col in hpr_cols:
        if col not in df.columns:
            df[col] = pd.NA

    print(f"Computing HPR for {len(target_indices)} numeric ADA records...")
    for n, idx in enumerate(target_indices, start=1):
        row = df.loc[idx]
        name = str(row.get("antibody_name", ""))
        vh = clean_sequence(row.get("vh_seq"), "H")
        vl = clean_sequence(row.get("vl_seq"), "L")

        mode = chain_mode(name, vh, vl)
        score_vh = vh
        score_vl = vl
        if mode == "single_light_fragment":
            # compute_hpr_index labels first argument as VH; preserve chain mode.
            score_vh, score_vl = vl, ""

        result = compute_hpr_index(score_vh, score_vl)
        vh_result = result.get("vh") or {}
        vl_result = result.get("vl") or {}
        combined = result.get("combined") or {}

        df.loc[idx, "hpr_metric_name"] = "Human Peptide Repertoire Compatibility Index"
        df.loc[idx, "hpr_chain_mode"] = mode
        df.loc[idx, "hpr_vh_score"] = vh_result.get("score")
        df.loc[idx, "hpr_vh_found_9mers"] = vh_result.get("found_9mers")
        df.loc[idx, "hpr_vh_total_9mers"] = vh_result.get("total_9mers")
        df.loc[idx, "hpr_vh_status"] = vh_result.get("status")
        df.loc[idx, "hpr_vl_score"] = vl_result.get("score")
        df.loc[idx, "hpr_vl_found_9mers"] = vl_result.get("found_9mers")
        df.loc[idx, "hpr_vl_total_9mers"] = vl_result.get("total_9mers")
        df.loc[idx, "hpr_vl_status"] = vl_result.get("status")
        df.loc[idx, "hpr_combined_score"] = combined.get("score")
        df.loc[idx, "hpr_combined_found_9mers"] = combined.get("found_9mers")
        df.loc[idx, "hpr_combined_total_9mers"] = combined.get("total_9mers")
        df.loc[idx, "hpr_combined_status"] = combined.get("status")
        df.loc[idx, "hpr_source_reference"] = "core.humanization.hpr_index; promb human-oas local repertoire; variable-region 9-mers"

        note = []
        if row.get("vh_seq") != vh and vh:
            note.append("VH trimmed to variable region before HPR")
        if row.get("vl_seq") != vl and vl:
            note.append("VL trimmed to variable region before HPR")
        if mode == "fusion_fragment_noncanonical":
            note.append("Tebentafusp is TCR-scFv fusion; HPR computed on stored antibody-like fragment only")
        if mode.startswith("single"):
            note.append("Single-domain/single-fragment score; no classical paired VL")
        if result.get("error"):
            note.append(f"error: {result.get('error')}")
        df.loc[idx, "hpr_note"] = "; ".join(note) if note else "computed"

        if n % 25 == 0 or n == len(target_indices):
            print(f"Computed {n}/{len(target_indices)}")

    df.to_csv(csv_path, index=False)
    df.to_excel(full_xlsx, index=False)
    analyzable = df[df[["vh_seq", "vl_seq"]].notna().any(axis=1) & df["ada_first_pct"].notna()].copy()
    analyzable.to_excel(analyzable_xlsx, index=False)

    computed = analyzable["hpr_combined_score"].notna().sum()
    print(f"HPR combined score present: {computed}/{len(analyzable)}")
    print(f"Saved CSV: {csv_path}")
    print(f"Saved Excel: {full_xlsx}")
    print(f"Saved analyzable Excel: {analyzable_xlsx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
