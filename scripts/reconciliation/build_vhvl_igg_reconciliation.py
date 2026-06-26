"""
VH/VL and IgG ID Reconciliation Builder (read-only).

Cross-walks antibody identifiers across:
  - data/natural_380_atlas/master_table.csv           (384 natural IgG)
  - data/natural_380_atlas/natural384_cmc_per_antibody.csv
  - data/engineered_459_atlas/master_table.csv        (458 engineered therapeutic IgG)
  - data/humanization_assay/842_combined_assessment.csv
  - data/humanization_assay/abref458_27m_per_antibody.csv
  - data/reference/AbRef458_stats_v1.json             (frozen benchmark)
  - data/reference/Natural384_IgG_stats_v1.json       (frozen benchmark)

Outputs (all read-only governance artifacts):
  - data/_reconciliation/VHVL_IGG_ID_RECONCILIATION.csv
  - data/_reconciliation/VHVL_IGG_ID_RECONCILIATION.json
  - data/_reconciliation/VHVL_IGG_ID_RECONCILIATION_SUMMARY.json

Run:
    python scripts/reconciliation/build_vhvl_igg_reconciliation.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA = REPO_ROOT / "data"
OUT_DIR = DATA / "_reconciliation"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug(name: str) -> str:
    if not isinstance(name, str):
        return ""
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _hash_seq(seq: str | None) -> str | None:
    if not seq:
        return None
    cleaned = re.sub(r"\s+", "", seq).upper()
    return hashlib.sha1(cleaned.encode()).hexdigest()[:12] if cleaned else None


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return [r for r in csv.DictReader(fh) if any(v for v in r.values())]


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Source loaders
# ---------------------------------------------------------------------------

def load_natural_master() -> dict[str, dict]:
    """data/natural_380_atlas/master_table.csv — natural IgG cohort (384 rows)."""
    rows = _read_csv(DATA / "natural_380_atlas" / "master_table.csv")
    out: dict[str, dict] = {}
    for r in rows:
        aid = (r.get("antibody_id") or "").strip()
        if not aid:
            continue
        out[_slug(aid)] = {
            "display_name": aid,
            "origin": r.get("origin"),
            "vh_seq": r.get("vh_seq") or None,
            "vl_seq": r.get("vl_seq") or None,
            "vh_germline": r.get("vh_germline") or None,
            "vl_germline": r.get("vl_germline") or None,
        }
    return out


def load_natural_cmc() -> dict[str, dict]:
    """data/natural_380_atlas/natural384_cmc_per_antibody.csv."""
    rows = _read_csv(DATA / "natural_380_atlas" / "natural384_cmc_per_antibody.csv")
    out: dict[str, dict] = {}
    for r in rows:
        aid = (r.get("antibody_id") or "").strip()
        if not aid:
            continue
        out[_slug(aid)] = {
            "display_name": aid,
            "ADI_natural384": r.get("ADI_natural384"),
            "pI": r.get("pI"),
            "GRAVY": r.get("GRAVY"),
        }
    return out


def load_engineered_master() -> dict[str, dict]:
    """data/engineered_459_atlas/master_table.csv — engineered therapeutic IgG (458 rows)."""
    rows = _read_csv(DATA / "engineered_459_atlas" / "master_table.csv")
    out: dict[str, dict] = {}
    for r in rows:
        aid = (r.get("antibody_id") or "").strip()
        if not aid:
            continue
        out[_slug(aid)] = {
            "display_name": aid,
            "origin": r.get("origin"),
            "vh_seq": r.get("vh_seq") or None,
            "vl_seq": r.get("vl_seq") or None,
            "vh_germline": r.get("vh_germline") or None,
            "vl_germline": r.get("vl_germline") or None,
        }
    return out


def load_combined_842() -> dict[str, dict]:
    """data/humanization_assay/842_combined_assessment.csv — structural CMC (840 rows)."""
    rows = _read_csv(DATA / "humanization_assay" / "842_combined_assessment.csv")
    out: dict[str, dict] = {}
    for r in rows:
        aid = (r.get("antibody_id") or "").strip()
        if not aid:
            continue
        out[_slug(aid)] = {
            "display_name": aid,
            "origin_842": r.get("origin"),
        }
    return out


def load_abref458_27m() -> dict[str, dict]:
    """data/humanization_assay/abref458_27m_per_antibody.csv — ADI with 27-allele immunogenicity."""
    rows = _read_csv(DATA / "humanization_assay" / "abref458_27m_per_antibody.csv")
    out: dict[str, dict] = {}
    for r in rows:
        aid = (r.get("antibody_id") or "").strip()
        if not aid:
            continue
        out[_slug(aid)] = {
            "display_name": aid,
            "ADI_abref458_27m": r.get("ADI_abref458_27m"),
            "pI": r.get("pI"),
        }
    return out


def load_frozen_abref458() -> dict[str, dict]:
    """data/reference/AbRef458_stats_v1.json — frozen benchmark (per_antibody if available)."""
    d = _read_json(DATA / "reference" / "AbRef458_stats_v1.json")
    if not d:
        return {}
    per_ab = d.get("per_antibody") or {}
    out: dict[str, dict] = {}
    for aid, vals in per_ab.items():
        out[_slug(aid)] = {"display_name": aid, "in_frozen_abref458": True}
    return out


def load_frozen_natural384() -> dict[str, dict]:
    """data/reference/Natural384_IgG_stats_v1.json — frozen benchmark (per_antibody if available)."""
    d = _read_json(DATA / "reference" / "Natural384_IgG_stats_v1.json")
    if not d:
        return {}
    per_ab = d.get("per_antibody") or {}
    out: dict[str, dict] = {}
    for aid, vals in per_ab.items():
        out[_slug(aid)] = {"display_name": aid, "in_frozen_natural384": True}
    return out


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------

SOURCE_ORDER = [
    "natural_master",
    "natural_cmc",
    "engineered_master",
    "combined_842",
    "abref458_27m",
    "frozen_abref458",
    "frozen_natural384",
]


def build_reconciliation() -> tuple[list[dict], dict]:
    sources: dict[str, dict[str, dict]] = {
        "natural_master":   load_natural_master(),
        "natural_cmc":      load_natural_cmc(),
        "engineered_master": load_engineered_master(),
        "combined_842":     load_combined_842(),
        "abref458_27m":     load_abref458_27m(),
        "frozen_abref458":  load_frozen_abref458(),
        "frozen_natural384": load_frozen_natural384(),
    }

    all_slugs: "OrderedDict[str, None]" = OrderedDict()
    for sname in SOURCE_ORDER:
        for slug in sources[sname]:
            all_slugs.setdefault(slug, None)

    rows: list[dict] = []
    for slug in all_slugs:
        display = ""
        vh_seqs: list[str] = []
        vl_seqs: list[str] = []
        origin_tags: list[str] = []

        for sname in SOURCE_ORDER:
            entry = sources[sname].get(slug)
            if not entry:
                continue
            if not display and entry.get("display_name"):
                display = entry["display_name"]
            for fld in ("vh_seq",):
                v = entry.get(fld)
                if v:
                    vh_seqs.append(v)
            for fld in ("vl_seq",):
                v = entry.get(fld)
                if v:
                    vl_seqs.append(v)

        nat_entry = sources["natural_master"].get(slug, {})
        eng_entry = sources["engineered_master"].get(slug, {})
        c842_entry = sources["combined_842"].get(slug, {})

        if slug in sources["natural_master"]:
            origin_tags.append("natural_igg")
        if slug in sources["engineered_master"]:
            origin_tags.append("engineered_therapeutic_igg")
        if c842_entry.get("origin_842") == "engineered_458":
            origin_tags.append("engineered_458_cmc")
        elif c842_entry.get("origin_842") == "natural_384":
            origin_tags.append("natural_384_cmc")

        vh_hashes = sorted({_hash_seq(s) for s in vh_seqs if _hash_seq(s)})
        vl_hashes = sorted({_hash_seq(s) for s in vl_seqs if _hash_seq(s)})
        vh_consistent = len(vh_hashes) <= 1
        vl_consistent = len(vl_hashes) <= 1

        in_nat = slug in sources["natural_master"]
        in_eng = slug in sources["engineered_master"]
        in_nat_cmc = slug in sources["natural_cmc"]
        in_eng_cmc = slug in sources["abref458_27m"]
        in_842 = slug in sources["combined_842"]
        in_frozen_abref = slug in sources["frozen_abref458"]
        in_frozen_nat = slug in sources["frozen_natural384"]

        anomalies: list[str] = []
        if in_nat and in_eng:
            anomalies.append("in_both_natural_and_engineered")
        if in_nat and not in_nat_cmc:
            anomalies.append("natural_missing_in_natural_cmc")
        if in_eng and not in_eng_cmc:
            anomalies.append("engineered_missing_in_abref458_27m")
        if in_nat and not in_842:
            anomalies.append("natural_missing_in_842_combined")
        if in_eng and not in_842:
            anomalies.append("engineered_missing_in_842_combined")
        if not vh_consistent:
            anomalies.append("vh_seq_hash_mismatch")
        if not vl_consistent:
            anomalies.append("vl_seq_hash_mismatch")

        rows.append({
            "canonical_id": slug,
            "display_name": display or slug,
            "origin_tags": ";".join(sorted(set(origin_tags))) or None,
            "in_natural_master_384": in_nat,
            "in_natural_cmc_384": in_nat_cmc,
            "in_engineered_master_458": in_eng,
            "in_abref458_27m_458": in_eng_cmc,
            "in_842_combined": in_842,
            "in_frozen_abref458": in_frozen_abref,
            "in_frozen_natural384": in_frozen_nat,
            "vh_seq_hash": vh_hashes[0] if vh_hashes else None,
            "vl_seq_hash": vl_hashes[0] if vl_hashes else None,
            "vh_seq_consistent": vh_consistent,
            "vl_seq_consistent": vl_consistent,
            "anomalies": ";".join(anomalies) or None,
            "vh_germline": nat_entry.get("vh_germline") or eng_entry.get("vh_germline"),
            "vl_germline": nat_entry.get("vl_germline") or eng_entry.get("vl_germline"),
        })

    n_nat_in_842 = sum(1 for r in rows if r["in_natural_master_384"] and r["in_842_combined"])
    n_eng_in_842 = sum(1 for r in rows if r["in_engineered_master_458"] and r["in_842_combined"])

    summary = {
        "n_total_unique_ids": len(rows),
        "counts": {
            "natural_master": len(sources["natural_master"]),
            "natural_cmc": len(sources["natural_cmc"]),
            "engineered_master": len(sources["engineered_master"]),
            "abref458_27m": len(sources["abref458_27m"]),
            "combined_842": len(sources["combined_842"]),
            "frozen_abref458_per_antibody": len(sources["frozen_abref458"]),
            "frozen_natural384_per_antibody": len(sources["frozen_natural384"]),
        },
        "expected": {
            "natural_master": 384,
            "natural_cmc": 384,
            "engineered_master": 458,
            "abref458_27m": 458,
            "combined_842": 840,
        },
        "natural_in_842_combined": n_nat_in_842,
        "engineered_in_842_combined": n_eng_in_842,
        "rows_with_anomalies": sum(1 for r in rows if r["anomalies"]),
    }
    return rows, summary


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

CSV_COLUMNS = [
    "canonical_id", "display_name", "origin_tags",
    "in_natural_master_384", "in_natural_cmc_384",
    "in_engineered_master_458", "in_abref458_27m_458",
    "in_842_combined", "in_frozen_abref458", "in_frozen_natural384",
    "vh_seq_hash", "vl_seq_hash",
    "vh_seq_consistent", "vl_seq_consistent",
    "anomalies", "vh_germline", "vl_germline",
]


def write_outputs(rows: list[dict], summary: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = OUT_DIR / "VHVL_IGG_ID_RECONCILIATION.csv"
    json_path = OUT_DIR / "VHVL_IGG_ID_RECONCILIATION.json"
    sum_path  = OUT_DIR / "VHVL_IGG_ID_RECONCILIATION_SUMMARY.json"

    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in CSV_COLUMNS})

    with json_path.open("w", encoding="utf-8") as fh:
        json.dump({
            "_meta": {
                "purpose": "VH/VL IgG cohort reconciliation across natural, engineered, and frozen benchmark datasets",
                "generator": "scripts/reconciliation/build_vhvl_igg_reconciliation.py",
                "read_only_governance_artifact": True,
                "n_rows": len(rows),
            },
            "rows": rows,
        }, fh, indent=2, ensure_ascii=False)

    with sum_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)


def main() -> None:
    rows, summary = build_reconciliation()
    write_outputs(rows, summary)

    print("[vhvl-recon] rows:", len(rows))
    for k, v in summary["counts"].items():
        exp = summary["expected"].get(k)
        marker = "" if exp is None or v == exp else f"  (expected {exp})"
        print(f"[vhvl-recon]   {k}: {v}{marker}")
    print("[vhvl-recon] natural in 842_combined:", summary["natural_in_842_combined"])
    print("[vhvl-recon] engineered in 842_combined:", summary["engineered_in_842_combined"])
    print("[vhvl-recon] anomalies:", summary["rows_with_anomalies"])
    print("[vhvl-recon] outputs:", OUT_DIR)


if __name__ == "__main__":
    main()
