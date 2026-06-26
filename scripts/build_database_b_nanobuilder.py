#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database B (humanized / engineered camelid nanobody) —  SAbDab-nano TSV  29 ，
 PDB  VHH ， NanoBodyBuilder2 (ImmuneBuilder) （ AF2）。

：
  data/vhh_database_b_union/database_b_manifest_29.json
  data/vhh_database_b_union/database_b_sequences.json
  data/vhh_database_b_union/immunebuilder_models/<safe_id>/rank0_unrefined.pdb
  data/vhh_database_b_union/run_log.txt
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[1]
TSV_PATH = REPO / "data" / "sabdab_nano" / "sabdab_nano_summary_all.tsv"
OUT_ROOT = REPO / "data" / "vhh_database_b_union"
PDB_CACHE = OUT_ROOT / "_pdb_cache"
MODELS_DIR = OUT_ROOT / "immunebuilder_models"
PREDICT_SCRIPT = REPO / "scripts" / "predict_one_immunebuilder.py"


def _load_sabdab_df():
    import pandas as pd

    return pd.read_csv(TSV_PATH, sep="\t", low_memory=False)


def _camelid_nanobody_mask(df):
    mask_l = df["Lchain"].astype(str).str.upper().isin(["NA", "NAN", ""]) | df["Lchain"].isna()
    hs = df["heavy_species"].astype(str).str.lower()
    mask_camel = hs.str.contains("camel|lama|vicugna|alpaca|dromed", na=False)
    return mask_l & mask_camel


def build_ordered_chain_keys(df, n: int = 29) -> List[Tuple[str, str]]:
    """：compound  humaniz →  Muyldermans  + /。"""
    base = df[_camelid_nanobody_mask(df)].copy()
    comp = base["compound"].astype(str).str.lower()
    set_a = base[comp.str.contains("humaniz", na=False)]

    auth = base["authors"].astype(str).str.lower()
    muy = auth.str.contains("muyldermans|conrath|vincke|loris|decanniere", na=False)
    mc = comp.str.contains(
        "mutant|humaniz|humanis|graft|fgl|chimer|caban|hul|bcii|lys3|an33|"
        "camelid vhh|single-domain|nanobody",
        na=False,
    )
    set_b = base[muy & mc]

    ordered: List[Tuple[str, str]] = []
    seen = set()
    for sub in (set_a, set_b):
        sub = sub.sort_values(["pdb", "Hchain"])
        for _, r in sub.iterrows():
            k = (str(r["pdb"]).lower(), str(r["Hchain"]))
            if k in seen:
                continue
            seen.add(k)
            ordered.append(k)
            if len(ordered) >= n:
                return ordered[:n]
    raise RuntimeError(
        f" {n} ： TSV  {len(ordered)} 。"
        " data/sabdab_nano/sabdab_nano_summary_all.tsv 。"
    )


def _safe_id(pdb: str, chain: str) -> str:
    return f"{pdb.lower()}_{chain}".replace(" ", "")


def extract_chain_sequence_pdb(pdb_path: Path, chain_id: str) -> str:
    from Bio.PDB import PDBParser, PPBuilder

    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("x", str(pdb_path))
    model = structure[0]
    cid = chain_id
    if cid not in model:
        cmap = {str(c.id).upper(): c.id for c in model.get_chains()}
        cid = cmap.get(chain_id.upper(), chain_id)
    chain = model[cid]
    ppb = PPBuilder()
    parts: List[str] = []
    for pp in ppb.build_peptides(chain):
        parts.append(str(pp.get_sequence()))
    return "".join(parts)


def download_pdb(pdb_id: str, cache_dir: Path) -> Path:
    from Bio.PDB import PDBList

    cache_dir.mkdir(parents=True, exist_ok=True)
    pdbl = PDBList(verbose=False)
    out = pdbl.retrieve_pdb_file(pdb_id, pdir=str(cache_dir), file_format="pdb")
    return Path(out)


def run_nanobuilder(seq: str, out_pdb: Path, py_exe: Path) -> None:
    out_pdb.parent.mkdir(parents=True, exist_ok=True)
    payload = {"H": seq, "L": "", "out_path": str(out_pdb), "model_type": "nanobody"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump(payload, tmp)
        tmp_path = tmp.name
    cmd = [str(py_exe), str(PREDICT_SCRIPT), "--json", tmp_path]
    subprocess.run(cmd, check=True)
    Path(tmp_path).unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Database B: 29× NanoBodyBuilder2 ")
    ap.add_argument("--n", type=int, default=29, help="（ 29）")
    ap.add_argument(
        "--python",
        type=Path,
        default=Path(sys.executable),
        help=" ImmuneBuilder  Python（ ImmuneBuilder）",
    )
    ap.add_argument("--skip-predict", action="store_true", help=" manifest/，")
    ap.add_argument("--dry-run", action="store_true", help="")
    args = ap.parse_args()

    if not TSV_PATH.is_file():
        print(f"[ERR]  {TSV_PATH}", file=sys.stderr)
        return 1

    df = _load_sabdab_df()
    keys = build_ordered_chain_keys(df, n=args.n)
    manifest: List[Dict[str, Any]] = []
    rows = []
    for pdb, hchain in keys:
        row = df[(df["pdb"].str.lower() == pdb) & (df["Hchain"] == hchain)].iloc[0]
        compound = str(row.get("compound", ""))
        manifest.append(
            {
                "pdb": pdb,
                "Hchain": hchain,
                "safe_id": _safe_id(pdb, hchain),
                "compound": compound[:500],
                "heavy_species": str(row.get("heavy_species", "")),
            }
        )
        rows.append(row)

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "database_b_manifest_29.json").write_text(
        json.dumps({"n": len(manifest), "entries": manifest}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if args.dry_run:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return 0

    PDB_CACHE.mkdir(parents=True, exist_ok=True)
    sequences: List[Dict[str, Any]] = []
    log_lines: List[str] = []

    for m in manifest:
        pdb, chain = m["pdb"], m["Hchain"]
        sid = m["safe_id"]
        log_lines.append(f"[seq] {sid}")
        try:
            pdb_path = download_pdb(pdb, PDB_CACHE)
            seq = extract_chain_sequence_pdb(pdb_path, chain)
        except Exception as e:
            log_lines.append(f"  FAIL extract: {e}")
            sequences.append({"safe_id": sid, "pdb": pdb, "Hchain": chain, "error": str(e), "sequence": ""})
            continue
        if len(seq) < 80:
            log_lines.append(f"  WARN short seq len={len(seq)}")
        sequences.append(
            {
                "safe_id": sid,
                "pdb": pdb,
                "Hchain": chain,
                "sequence": seq,
                "length": len(seq),
            }
        )

    (OUT_ROOT / "database_b_sequences.json").write_text(
        json.dumps({"n": len(sequences), "entries": sequences}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if args.skip_predict:
        (OUT_ROOT / "run_log.txt").write_text("\n".join(log_lines), encoding="utf-8")
        print(f"Wrote manifest + sequences under {OUT_ROOT} (--skip-predict)")
        return 0

    for ent in sequences:
        if not ent.get("sequence"):
            continue
        sid = ent["safe_id"]
        out_pdb = MODELS_DIR / sid / "rank0_unrefined.pdb"
        log_lines.append(f"[predict] {sid} len={ent['length']}")
        try:
            run_nanobuilder(ent["sequence"], out_pdb, args.python)
            ent["predicted_pdb"] = str(out_pdb.relative_to(REPO))
        except Exception as e:
            log_lines.append(f"  FAIL predict: {e}")
            ent["predict_error"] = str(e)

    (OUT_ROOT / "database_b_sequences.json").write_text(
        json.dumps({"n": len(sequences), "entries": sequences}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (OUT_ROOT / "run_log.txt").write_text("\n".join(log_lines), encoding="utf-8")
    print(f"Done. {OUT_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
