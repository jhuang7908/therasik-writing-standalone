"""
ADA Immunogenicity ID Reconciliation Builder (read-only).

Cross-walks antibody identifiers across:
  - data/ada_master_136_curated.csv                                  (root-level, 147 rows)
  - data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv  (master copy, 158 rows)
  - data/immunogenicity_knowledge_base/master/immunogenicity_panel_136_master.csv  (136 rows)
  - data/immunogenicity_knowledge_base/InSynBio_Combined_ADA_Database.csv  (146 rows)
  - data/immunogenicity_knowledge_base/master/ada_batch2_master_aligned.csv (10 rows)
  - data/immunogenicity_knowledge_base/master/ada_batch3_master_aligned.csv (10 rows)
  - data/immunogenicity_knowledge_base/master/ada_negative_library_by_phase.csv (312 rows)
  - data/immunogenicity_knowledge_base/master/ada_ph3_disc_candidates.csv (47 rows)
  - data/immunogenicity_knowledge_base/master/ada_curation_gap_list.csv (66 gap entries)

Outputs (all read-only governance artifacts):
  - data/_reconciliation/ADA_ID_RECONCILIATION.csv
  - data/_reconciliation/ADA_ID_RECONCILIATION.json
  - data/_reconciliation/ADA_ID_RECONCILIATION_SUMMARY.json

Run:
    python scripts/reconciliation/build_ada_reconciliation.py
"""

from __future__ import annotations

import csv
import json
import re
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA = REPO_ROOT / "data"
IKB = DATA / "immunogenicity_knowledge_base"
MASTER = IKB / "master"
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


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return [r for r in csv.DictReader(fh) if any(v for v in r.values())]


# ---------------------------------------------------------------------------
# Source loaders
# ---------------------------------------------------------------------------

def _name_key(row: dict, *fields: str) -> str:
    for f in fields:
        v = (row.get(f) or "").strip()
        if v:
            return v
    return ""


def load_source(path: Path, name_fields: list[str]) -> dict[str, dict]:
    rows = _read_csv(path)
    out: dict[str, dict] = {}
    for r in rows:
        n = _name_key(r, *name_fields)
        if not n:
            continue
        slug = _slug(n)
        if slug not in out:
            out[slug] = {"display_name": n, **r}
    return out


# Specific loaders

def load_root_ada() -> dict[str, dict]:
    return load_source(DATA / "ada_master_136_curated.csv", ["antibody_name"])


def load_master_ada() -> dict[str, dict]:
    return load_source(MASTER / "ada_master_136_curated.csv", ["antibody_name"])


def load_panel_136() -> dict[str, dict]:
    """immunogenicity_panel_136_master.csv — 136 rows with ADA values and germline info."""
    rows = _read_csv(MASTER / "immunogenicity_panel_136_master.csv")
    out: dict[str, dict] = {}
    for r in rows:
        n = (r.get("antibody_name") or "").strip()
        if not n:
            continue
        out[_slug(n)] = {
            "display_name": n,
            "ada_first_pct": r.get("ada_first_pct"),
            "ada_value_display": r.get("ada_value_display"),
            "vh_germline": r.get("vh_germline"),
            "vl_germline": r.get("vl_germline"),
            "vh_family": r.get("vh_family"),
            "vl_family": r.get("vl_family"),
            "thera_genetics_class": r.get("thera_genetics_class"),
        }
    return out


def load_combined_db() -> dict[str, dict]:
    """InSynBio_Combined_ADA_Database.csv — 146 rows."""
    rows = _read_csv(IKB / "InSynBio_Combined_ADA_Database.csv")
    out: dict[str, dict] = {}
    for r in rows:
        n = (r.get("antibody_name") or "").strip()
        if not n:
            continue
        out[_slug(n)] = {
            "display_name": n,
            "ada_first_pct_combined_db": r.get("ada_first_pct"),
            "source_db": r.get("source_db"),
        }
    return out


def load_batch2() -> dict[str, dict]:
    return load_source(MASTER / "ada_batch2_master_aligned.csv", ["antibody_name"])


def load_batch3() -> dict[str, dict]:
    return load_source(MASTER / "ada_batch3_master_aligned.csv", ["antibody_name"])


def load_negative_library() -> dict[str, dict]:
    return load_source(MASTER / "ada_negative_library_by_phase.csv", ["antibody_name"])


def load_ph3_candidates() -> dict[str, dict]:
    return load_source(MASTER / "ada_ph3_disc_candidates.csv", ["antibody_name"])


def load_gap_list() -> dict[str, dict]:
    """ada_curation_gap_list.csv — entries with known missing fields."""
    rows = _read_csv(MASTER / "ada_curation_gap_list.csv")
    out: dict[str, dict] = {}
    for r in rows:
        n = (r.get("antibody") or "").strip()
        if not n:
            continue
        out[_slug(n)] = {
            "display_name": n,
            "missing_fields": r.get("missing_fields"),
            "n_missing": r.get("n_missing"),
            "evidence_tier": r.get("evidence_tier"),
        }
    return out


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------

SOURCE_ORDER = [
    "root_ada",
    "master_ada",
    "panel_136",
    "combined_db",
    "batch2",
    "batch3",
    "negative_library",
    "ph3_candidates",
    "gap_list",
]


def build_reconciliation() -> tuple[list[dict], dict]:
    sources: dict[str, dict[str, dict]] = {
        "root_ada":       load_root_ada(),
        "master_ada":     load_master_ada(),
        "panel_136":      load_panel_136(),
        "combined_db":    load_combined_db(),
        "batch2":         load_batch2(),
        "batch3":         load_batch3(),
        "negative_library": load_negative_library(),
        "ph3_candidates": load_ph3_candidates(),
        "gap_list":       load_gap_list(),
    }

    all_slugs: "OrderedDict[str, None]" = OrderedDict()
    for sname in SOURCE_ORDER:
        for slug in sources[sname]:
            all_slugs.setdefault(slug, None)

    rows: list[dict] = []
    for slug in all_slugs:
        display = ""
        for sname in SOURCE_ORDER:
            entry = sources[sname].get(slug)
            if entry and not display:
                display = entry.get("display_name", "")
                if display:
                    break

        panel_entry = sources["panel_136"].get(slug, {})
        combined_entry = sources["combined_db"].get(slug, {})
        gap_entry = sources["gap_list"].get(slug, {})

        # ADA value consistency check between panel_136 and combined_db
        pct_panel = panel_entry.get("ada_first_pct")
        pct_combined = combined_entry.get("ada_first_pct_combined_db")
        ada_consistent: bool | None = None
        if pct_panel is not None and pct_combined is not None:
            try:
                ada_consistent = abs(float(pct_panel) - float(pct_combined)) < 0.01
            except (ValueError, TypeError):
                ada_consistent = None

        in_root = slug in sources["root_ada"]
        in_master = slug in sources["master_ada"]
        in_panel = slug in sources["panel_136"]
        in_combined = slug in sources["combined_db"]
        in_batch2 = slug in sources["batch2"]
        in_batch3 = slug in sources["batch3"]
        in_negative = slug in sources["negative_library"]
        in_ph3 = slug in sources["ph3_candidates"]
        in_gap = slug in sources["gap_list"]

        anomalies: list[str] = []
        if in_root and not in_master:
            anomalies.append("root_only_not_in_master_copy")
        if in_master and not in_root:
            anomalies.append("master_copy_not_in_root")
        if in_panel and not in_combined:
            anomalies.append("panel_136_missing_in_combined_db")
        if in_combined and not in_panel:
            anomalies.append("combined_db_missing_in_panel_136")
        if in_gap:
            missing = gap_entry.get("missing_fields", "")
            anomalies.append(f"curation_gap:{missing}")
        if ada_consistent is False:
            anomalies.append("ada_pct_mismatch_panel_vs_combined")

        rows.append({
            "canonical_id": slug,
            "display_name": display or slug,
            "in_root_ada_147": in_root,
            "in_master_ada_158": in_master,
            "in_panel_136": in_panel,
            "in_combined_db_146": in_combined,
            "in_batch2": in_batch2,
            "in_batch3": in_batch3,
            "in_negative_library": in_negative,
            "in_ph3_candidates": in_ph3,
            "in_gap_list": in_gap,
            "ada_first_pct_panel": panel_entry.get("ada_first_pct"),
            "ada_first_pct_combined": combined_entry.get("ada_first_pct_combined_db"),
            "ada_pct_consistent": ada_consistent,
            "thera_genetics_class": panel_entry.get("thera_genetics_class"),
            "vh_germline": panel_entry.get("vh_germline"),
            "vl_germline": panel_entry.get("vl_germline"),
            "source_db_combined": combined_entry.get("source_db"),
            "curation_gap_fields": gap_entry.get("missing_fields"),
            "evidence_tier": gap_entry.get("evidence_tier"),
            "anomalies": ";".join(anomalies) or None,
        })

    summary = {
        "n_total_unique_ids": len(rows),
        "counts": {
            "root_ada": len(sources["root_ada"]),
            "master_ada": len(sources["master_ada"]),
            "panel_136": len(sources["panel_136"]),
            "combined_db": len(sources["combined_db"]),
            "batch2": len(sources["batch2"]),
            "batch3": len(sources["batch3"]),
            "negative_library": len(sources["negative_library"]),
            "ph3_candidates": len(sources["ph3_candidates"]),
            "gap_list": len(sources["gap_list"]),
        },
        "expected": {
            "root_ada": 147,
            "master_ada": 158,
            "panel_136": 136,
            "combined_db": 146,
        },
        "rows_with_anomalies": sum(1 for r in rows if r["anomalies"]),
        "in_both_positive_and_negative": sum(
            1 for r in rows if r["in_panel_136"] and r["in_negative_library"]
        ),
    }
    return rows, summary


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

CSV_COLUMNS = [
    "canonical_id", "display_name",
    "in_root_ada_147", "in_master_ada_158", "in_panel_136", "in_combined_db_146",
    "in_batch2", "in_batch3", "in_negative_library", "in_ph3_candidates", "in_gap_list",
    "ada_first_pct_panel", "ada_first_pct_combined", "ada_pct_consistent",
    "thera_genetics_class", "vh_germline", "vl_germline",
    "source_db_combined", "curation_gap_fields", "evidence_tier", "anomalies",
]


def write_outputs(rows: list[dict], summary: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = OUT_DIR / "ADA_ID_RECONCILIATION.csv"
    json_path = OUT_DIR / "ADA_ID_RECONCILIATION.json"
    sum_path  = OUT_DIR / "ADA_ID_RECONCILIATION_SUMMARY.json"

    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in CSV_COLUMNS})

    with json_path.open("w", encoding="utf-8") as fh:
        json.dump({
            "_meta": {
                "purpose": "ADA immunogenicity cohort reconciliation across root, master, panel, and batch datasets",
                "generator": "scripts/reconciliation/build_ada_reconciliation.py",
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

    print("[ada-recon] rows:", len(rows))
    for k, v in summary["counts"].items():
        exp = summary["expected"].get(k)
        marker = "" if exp is None or v == exp else f"  (expected {exp})"
        print(f"[ada-recon]   {k}: {v}{marker}")
    print("[ada-recon] anomalies:", summary["rows_with_anomalies"])
    print("[ada-recon] in_both_positive_and_negative:", summary["in_both_positive_and_negative"])
    print("[ada-recon] outputs:", OUT_DIR)


if __name__ == "__main__":
    main()
