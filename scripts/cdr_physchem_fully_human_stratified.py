"""
Stratified CDR physico-chemical statistics for the fully-human IgG Fab cohort.

Default cohort (\"358\" / complete atlas standard Fab):
  natural_380_atlas rows with genetics_normalized=genetically_human,
  format_type=monospecific_IgG_Fab, modality=standard — typically n=357
  (includes drugs whose meta phase_bucket is unknown but atlas lists standard Fab).

Strict regulatory-style slice (legacy):
  --cohort meta_minimal  — antibody_meta_models.json: same genetics/format,
  engineering_level=minimal, phase_bucket!=unknown — n=353.

Platform buckets use knowledge-based labels for the 357 cohort.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd


LOCI = {
    "vh_cdr1": "vh_cdr1",
    "vh_cdr2": "vh_cdr2",
    "vh_cdr3": "vh_cdr3",
    "vl_cdr1": "vl_cdr1",
    "vl_cdr2": "vl_cdr2",
    "vl_cdr3": "vl_cdr3",
}


def _load_cdr_pc_module(repo_root: Path):
    path = repo_root / "scripts" / "cdr_physchem_distribution.py"
    spec = importlib.util.spec_from_file_location("cdr_physchem_distribution", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def classify_dev_tech(raw: object) -> str:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return "unknown_unlabeled"
    s = str(raw).strip().lower()
    if not s:
        return "unknown_unlabeled"
    
    # Check if it's already a bucket key
    if s in ("phage_display", "transgenic_animal", "human_b_cell_derived"):
        return s
        
    if "phage" in s or "hucal" in s or "display" in s:
        return "phage_display"
    if any(
        k in s
        for k in (
            "mouse",
            "xenomouse",
            "velocimmune",
            "humab",
            "ultimab",
            "transgenic",
            "omnirat",
        )
    ):
        return "transgenic_animal"
    if "b-cell" in s or "b cell" in s or "single b" in s or "isolated" in s:
        return "human_b_cell_derived"
    return "other_labeled"


def meta_minimal_phase_known_names(repo_root: Path) -> List[str]:
    data = json.loads((repo_root / "data/thera_sabdab/out/antibody_meta_models.json").read_text(encoding="utf-8"))
    sel = [
        x
        for x in data
        if x.get("genetics", {}).get("normalized") == "genetically_human"
        and x.get("format", {}).get("format_class") == "monospecific_IgG_Fab"
        and x.get("clinical", {}).get("phase_bucket") != "unknown"
        and not x.get("format", {}).get("is_bispecific")
        and x.get("engineering", {}).get("engineering_level") == "minimal"
    ]
    return sorted({x["name"] for x in sel})


def natural_standard_gen_human_fab_names(natural_csv: Path) -> List[str]:
    """All fully-human standard-modality monospecific IgG Fab rows in natural atlas."""
    nat = pd.read_csv(natural_csv)
    m = nat[
        (nat["genetics_normalized"] == "genetically_human")
        & (nat["format_type"] == "monospecific_IgG_Fab")
        & (nat["modality"].astype(str) == "standard")
    ]
    return sorted(m["antibody_id"].astype(str).unique().tolist())


def dev_tech_map_fully_human(repo_root: Path) -> Dict[str, str]:
    # Load the comprehensive labels generated for the 357 cohort
    label_path = repo_root / "data/reference/fully_human_357_platform_labels.json"
    if label_path.exists():
        return json.loads(label_path.read_text(encoding="utf-8"))
    
    # Fallback to immuno70 if labels not found
    sp = pd.read_csv(repo_root / "data/thera_sabdab/out/immuno70_sprint_matrix.csv")
    fh = sp[sp["origin"] == "fully_human"][["antibody_name", "dev_tech"]]
    out: Dict[str, str] = {}
    for _, row in fh.iterrows():
        name = str(row["antibody_name"]).strip()
        dt = row["dev_tech"]
        if name and name not in out:
            out[name] = dt if pd.notna(dt) else ""
        elif name and pd.notna(dt) and not str(out.get(name, "")).strip():
            out[name] = dt
    return out


def dataframe_to_pairs(df: pd.DataFrame, id_col: str) -> Dict[str, List[Tuple[str, str]]]:
    pairs: Dict[str, List[Tuple[str, str]]] = {k: [] for k in LOCI}
    for _, row in df.iterrows():
        aid = str(row[id_col]).strip()
        if not aid:
            continue
        for locus, col in LOCI.items():
            seq = str(row[col]).strip().upper()
            if seq and seq != "NAN" and re.fullmatch(r"[A-Z]+", seq):
                pairs[locus].append((aid, seq))
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--cohort",
        choices=("natural_standard", "meta_minimal"),
        default="natural_standard",
        help="natural_standard: complete standard Fab in atlas (default). "
        "meta_minimal: phase-known minimal-engineering meta slice (n=353).",
    )
    parser.add_argument(
        "--natural-csv",
        type=Path,
        default=None,
        help="Default: data/natural_380_atlas/master_table.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/reference/CDR_physchem_FullyHuman358_by_platform_v1.json"),
    )
    args = parser.parse_args()
    root = args.repo_root.resolve()
    natural_csv = args.natural_csv or (root / "data/natural_380_atlas/master_table.csv")
    if not natural_csv.exists():
        raise SystemExit(f"Missing {natural_csv}")

    cdr_pc = _load_cdr_pc_module(root)
    compute_locus_block = cdr_pc.compute_locus_block

    if args.cohort == "meta_minimal":
        names = meta_minimal_phase_known_names(root)
        cohort_definition = (
            "antibody_meta_models.json: genetics_normalized=genetically_human, "
            "format_class=monospecific_IgG_Fab, phase_bucket!=unknown, "
            "not bispecific, engineering_level=minimal; intersect natural_380_atlas"
        )
        user_label = "FullyHuman353_meta_minimal_slice"
    else:
        names = natural_standard_gen_human_fab_names(natural_csv)
        cohort_definition = (
            "natural_380_atlas/master_table.csv: genetics_normalized=genetically_human, "
            "format_type=monospecific_IgG_Fab, modality=standard (complete standard Fab rows)"
        )
        user_label = "FullyHuman358_operational_natural_standard"

    nat = pd.read_csv(natural_csv)
    sub = nat[nat["antibody_id"].isin(names)].copy()
    if len(sub) != len(names):
        missing = set(names) - set(sub["antibody_id"].astype(str))
        raise SystemExit(f"Expected {len(names)} rows in natural atlas; got {len(sub)}; missing {len(missing)}")

    dt_map = dev_tech_map_fully_human(root)

    meta_minimal_set = set(meta_minimal_phase_known_names(root))
    extra_vs_meta_minimal = sorted(set(names) - meta_minimal_set) if args.cohort == "natural_standard" else []
    dropped_vs_natural_standard = sorted(meta_minimal_set - set(names)) if args.cohort == "meta_minimal" else []

    buckets: Dict[str, List[str]] = {
        "transgenic_animal": [],
        "phage_display": [],
        "human_b_cell_derived": [],
        "other_labeled": [],
        "unknown_unlabeled": [],
    }
    label_detail: List[Dict[str, str]] = []

    for nm in names:
        raw = dt_map.get(nm, "")
        if raw is None or (isinstance(raw, float) and pd.isna(raw)) or str(raw).strip() == "":
            bucket = "unknown_unlabeled"
            raw_s = ""
        else:
            raw_s = str(raw).strip()
            bucket = classify_dev_tech(raw_s)
        buckets[bucket].append(nm)
        if raw_s:
            label_detail.append({"antibody_id": nm, "dev_tech": raw_s, "platform_bucket": bucket})

    n_labeled_dt = sum(1 for nm in names if str(dt_map.get(nm, "")).strip())
    out: Dict = {
        "_meta": {
            "version": "v1",
            "generated": str(date.today()),
            "cohort_key": args.cohort,
            "cohort_user_label": user_label,
            "cohort_definition": cohort_definition,
            "n_antibodies": len(names),
            "note_358_vs_353_vs_357": (
                "Business label '358' is mapped to the complete atlas standard-modality "
                "fully-human IgG Fab set (typically n=357 in natural_380_atlas). "
                "The stricter antibody_meta_models slice with phase_bucket!=unknown "
                "and minimal engineering yields n=353; difference is mainly unknown-phase "
                "standard drugs still present in the atlas."
            ),
            "cdr_definition": "IMGT segments (natural_380_atlas master_table)",
            "platform_label_source": (
                "Knowledge-based mapping + heuristic for 357 cohort (fully_human_357_platform_labels.json)"
            ),
            "platform_label_coverage": {
                "n_with_non_null_dev_tech": n_labeled_dt,
                "n_unknown_unlabeled": len(buckets["unknown_unlabeled"]),
            },
            "bucket_counts": {k: len(v) for k, v in buckets.items()},
            "reconcile_meta_minimal_slice": {
                "n_meta_minimal_phase_known": len(meta_minimal_set),
                "extra_antibody_ids_in_this_cohort_vs_meta_minimal": extra_vs_meta_minimal,
                "meta_minimal_antibody_ids_not_in_this_cohort": dropped_vs_natural_standard,
            },
        },
        "labeled_antibodies": sorted(label_detail, key=lambda x: x["antibody_id"]),
        "pooled_all": {
            "n_antibodies": len(names),
            "loci": {
                locus: compute_locus_block(pairs)
                for locus, pairs in dataframe_to_pairs(sub, "antibody_id").items()
            },
        },
        "by_platform_bucket": {},
    }

    for bucket, ids in buckets.items():
        if not ids:
            out["by_platform_bucket"][bucket] = {
                "_meta": {"n_antibodies": 0},
                "loci": {locus: compute_locus_block([]) for locus in LOCI},
            }
            continue
        df_b = sub[sub["antibody_id"].isin(ids)]
        pairs_b = dataframe_to_pairs(df_b, "antibody_id")
        out["by_platform_bucket"][bucket] = {
            "_meta": {"n_antibodies": len(ids)},
            "loci": {locus: compute_locus_block(pairs_b[locus]) for locus in LOCI},
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("[OK] wrote", args.output)
    print(" bucket_counts:", out["_meta"]["bucket_counts"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
