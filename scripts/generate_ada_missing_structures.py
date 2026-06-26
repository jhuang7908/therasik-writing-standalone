#!/usr/bin/env python3
"""Generate ImmuneBuilder structures for ADA master records lacking pdb_path.

This is a maintenance CLI for the ADA knowledge base. It uses existing
`scripts/predict_one_immunebuilder.py`, which routes to ABodyBuilder2 for
VH/VL Fv models and NanoBodyBuilder2 for VHH-style single-domain records.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import pandas as pd


BAD_VALUES = {"", "nan", "none", "true", "false", "0", "115"}
DEFAULT_ENV_PYTHON = Path("D:/Users/NextVivo/miniconda3/envs/anarcii/python.exe")


def is_real_seq(value: object) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    return len(text) > 10 and text.lower() not in BAD_VALUES


def is_present(value: object) -> bool:
    if pd.isna(value):
        return False
    return str(value).strip().lower() not in BAD_VALUES


def clean_sequence(seq: object, chain: str) -> str:
    if not is_real_seq(seq):
        return ""
    text = re.sub(r"[^A-Za-z]", "", str(seq)).upper()

    # Some rows contain variable + constant regions. ABodyBuilder2 expects the Fv.
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


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--csv",
        default="data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv",
        help="Path to ADA master CSV.",
    )
    parser.add_argument(
        "--out-dir",
        default="data/immunogenicity_knowledge_base/structures/ada_immunebuilder_models",
        help="Directory for generated PDB models.",
    )
    parser.add_argument(
        "--env-python",
        default=str(DEFAULT_ENV_PYTHON),
        help="Python executable in the anarcii/ImmuneBuilder environment.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Optional max records to process.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    csv_path = (repo / args.csv).resolve()
    out_dir = (repo / args.out_dir).resolve()
    predictor = repo / "scripts" / "predict_one_immunebuilder.py"
    env_python = Path(args.env_python)

    df = pd.read_csv(csv_path)
    numeric = df[["vh_seq", "vl_seq"]].notna().any(axis=1) & df["ada_first_pct"].notna()
    missing_pdb = numeric & ~df["pdb_path"].apply(is_present)

    candidates = []
    for idx, row in df.loc[missing_pdb].iterrows():
        name = str(row["antibody_name"])
        vh = clean_sequence(row.get("vh_seq"), "H")
        vl = clean_sequence(row.get("vl_seq"), "L")

        # Tebentafusp is a TCR-scFv fusion; the stored fragment is not a full VH/VL Fv.
        if name.casefold() == "tebentafusp":
            continue

        if vh and vl:
            model_type = "abody"
        elif vh and len(vh) >= 100 and vh.startswith(("QV", "EV", "DV")):
            model_type = "nanobody"
        else:
            continue

        candidates.append((idx, name, vh, vl, model_type))

    if args.limit:
        candidates = candidates[: args.limit]

    print(f"Missing pdb_path records: {int(missing_pdb.sum())}")
    print(f"Modelable records: {len(candidates)}")
    for _, name, vh, vl, model_type in candidates:
        print(f" - {name}: {model_type}, H={len(vh)}, L={len(vl)}")

    if args.dry_run:
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)

    updated = 0
    failed: list[str] = []
    for idx, name, vh, vl, model_type in candidates:
        model_dir = out_dir / safe_name(name)
        model_dir.mkdir(parents=True, exist_ok=True)
        out_path = model_dir / "rank0_unrefined.pdb"
        payload_path = model_dir / "payload.json"
        payload = {"out_path": str(out_path), "H": vh, "L": vl, "model_type": model_type}
        payload_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        if out_path.exists() and out_path.stat().st_size > 0:
            print(f"SKIP existing {name}: {out_path}")
        else:
            cmd = [str(env_python), str(predictor), "--json", str(payload_path)]
            print(f"RUN {name}")
            result = subprocess.run(cmd, cwd=str(repo), text=True, capture_output=True)
            if result.returncode != 0:
                print(f"FAIL {name}: {result.stderr or result.stdout}")
                failed.append(name)
                continue

        rel_path = out_path.relative_to(repo).as_posix()
        df.loc[idx, "pdb_path"] = rel_path
        if "structure_source_type" not in df.columns:
            df["structure_source_type"] = pd.NA
        if "structure_source_note" not in df.columns:
            df["structure_source_note"] = pd.NA
        df.loc[idx, "structure_source_type"] = "ImmuneBuilder model"
        df.loc[idx, "structure_source_note"] = f"{model_type}; generated by scripts/generate_ada_missing_structures.py"
        updated += 1

    df.to_csv(csv_path, index=False)
    print(f"Updated pdb_path rows: {updated}")
    if failed:
        print("Failed rows:", ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
