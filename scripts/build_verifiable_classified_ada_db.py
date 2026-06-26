#!/usr/bin/env python3
"""
Build a classified ADA database containing ONLY rows with:
  - Real traceability: >=1 https citation URL and/or >=1 PMID
  - evidence_tier A or B
  - evidence_source is NOT the OpenClaw '' (AI batch chain marker)

Outputs index + data (split) under data/ADA_reliable_package/verifiable_classified/.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLINICAL_INDEX = REPO / "data" / "ADA_reliable_package" / "clinical_db" / "clinical_ada_db_index.json"
CLINICAL_DATA = REPO / "data" / "ADA_reliable_package" / "clinical_db" / "clinical_ada_db_data.json"
REHABILITATED_JSON = REPO / "data" / "ADA_reliable_package" / "verification" / "rehabilitated_entries.json"
OUT_DIR = REPO / "data" / "ADA_reliable_package" / "verifiable_classified"

ADA_VALUE_SUSPECT_BLACKLIST: dict[str, str] = {
    "Atoltivimab": "value is PRNT-80 viral inhibition rate, not ADA incidence",
    "Depemokimab": "value is 95% CI (confidence interval), not ADA incidence",
    "Axatilimab": "value is 16.3% CV (PK variability), not ADA incidence",
    "Clesrovimab": "value is 22.6% CV (PK variability), not ADA incidence",
    "Domvanalimab": "value is ORR (objective response rate), not ADA incidence",
    "Favezelimab": "42.9% is likely ORR/tumor-shrinkage rate not ADA incidence; PMID 40668662 not verified to contain ADA immunogenicity data",
}

# Entries where the ada_value_display contains mixed animal/preclinical or
# unusual context that requires explicit annotation in the output.
ADA_VALUE_ANNOTATION: dict[str, str] = {
    "Brolucizumab": "ADA value is PRE-EXISTING (treatment-naive); treatment-emergent ADA rate is distinct and lower (~6-13%); pre-existing ADA does not predict clinical immunogenicity",
    "Toripalimab": "Values include animal (cynomolgus monkey) and dose-ranging phase-I human data; routine clinical ADA rate may differ from these early-phase values",
    "Satralizumab": "High rates (41%/71%) reflect small NMO trials with EMA EPAR data; combination vs monotherapy context required for interpretation",
    "Rilonacept": "43% from fusion-protein trap domain; biologically plausible for IL-1 trap but original source is ScienceDirect general topic page, not primary trial paper",
    "Dinutuximab": "16.8–57.1% range across studies; chimeric anti-GD2 antibody has inherent high immunogenicity; neutralizing ab fraction (3.6–63.5% of ADA+) should be distinguished",
    "Bimekizumab": "34%/47% from very small early-phase cohorts (n=32/17); registration trial ADA rate is substantially lower",
    "Nivolumab": "23.8–37.8% only in combination regimens; monotherapy rate 8.5%; do not quote combination value as single ADA incidence",
    "Vedolizumab": "22.1% only applies to patients who interrupted then restarted therapy; continuous-treatment rate is 2.4%",
}


def _has_traceable_citation(row: dict, primary: dict) -> tuple[bool, str]:
    urls = row.get("citation_urls") or []
    https = [u for u in urls if isinstance(u, str) and u.startswith("http")]
    pm = row.get("pmids_extracted") or []
    if not https and not pm:
        for p in primary.get("pmids") or []:
            if str(p).strip().isdigit():
                return True, "pmid_from_primary_field"
        return False, "no_url_no_pmid"
    return True, "url_and_or_pmid"


def _load_rehabilitated() -> dict[str, dict]:
    """Load forward-search-verified entries that override AI-batch exclusion."""
    if not REHABILITATED_JSON.is_file():
        return {}
    blob = json.loads(REHABILITATED_JSON.read_text(encoding="utf-8"))
    return {e["antibody_name"]: e for e in blob.get("entries", [])}


def main() -> None:
    if not CLINICAL_INDEX.is_file() or not CLINICAL_DATA.is_file():
        raise SystemExit("Run scripts/build_clinical_ada_split_database.py first.")

    idx_blob = json.loads(CLINICAL_INDEX.read_text(encoding="utf-8"))
    data_blob = json.loads(CLINICAL_DATA.read_text(encoding="utf-8"))
    records = data_blob.get("records", {})
    rehab_map = _load_rehabilitated()

    excluded: list[dict] = []
    included_index: list[dict] = []
    included_data: dict = {}
    rehabilitated_count = 0

    for row in idx_blob.get("index", []):
        name = row["antibody_name"]
        key = row["data_record_key"]
        primary = (records.get(key) or {}).get("primary_record") or {}
        es = str(primary.get("evidence_source") or "")

        if name in ADA_VALUE_SUSPECT_BLACKLIST:
            excluded.append({"antibody_name": name, "reason": "excluded_ada_value_suspect_not_ada", "detail": ADA_VALUE_SUSPECT_BLACKLIST[name]})
            continue

        is_ai_batch = es == "" or es.startswith("")

        if is_ai_batch and name in rehab_map:
            rh = rehab_map[name]
            rehabilitated_count += 1
            entry = {
                "record_id": row["record_id"],
                "data_record_key": key,
                "class_evidence_tier": "A",
                "class_ada_status": "incidence_reported",
                "antibody_name": name,
                "ada_value_display": rh["ada_value_verified"],
                "canonical_provenance": "rehabilitated_forward_search",
                "evidence_source": rh["verification_method"],
                "evidence_quality": "high",
                "source_type": "pubmed_abstract_verified",
                "citation_urls": [rh["pubmed_url"]],
                "pmids_extracted": [rh["pmid"]],
                "tier_rationale": "tier_A_pmid",
                "ada_value_extraction": "manually_verified",
                "ada_value_annotation": ADA_VALUE_ANNOTATION.get(name, ""),
                "verification_note": rh["evidence_excerpt"],
            }
            included_index.append(entry)
            data_rec = records.get(key) or {}
            data_rec["rehabilitated"] = rh
            included_data[key] = data_rec
            continue

        if is_ai_batch:
            excluded.append({"antibody_name": name, "reason": "excluded_ai_batch_evidence_chain", "evidence_source": es})
            continue

        tier = row.get("evidence_tier")
        if tier not in ("A", "B"):
            excluded.append({"antibody_name": name, "reason": "excluded_tier_C_insufficient_anchor", "evidence_tier": tier})
            continue

        ok, trace = _has_traceable_citation(row, primary)
        if not ok:
            excluded.append({"antibody_name": name, "reason": "excluded_no_traceable_url_or_pmid", "detail": trace})
            continue

        # Determine whether the evidence chain was AI-generated even though
        # the entry has a real URL/PMID anchor.
        ai_chain_patterns = ("A", "250", "")
        chain_is_ai = any(pat in es for pat in ai_chain_patterns)

        entry = {
            "record_id": row["record_id"],
            "data_record_key": key,
            "class_evidence_tier": tier,
            "class_ada_status": row.get("ada_status"),
            "antibody_name": name,
            "ada_value_display": row.get("ada_value_display"),
            "canonical_provenance": row.get("canonical_provenance"),
            "evidence_source": es,
            "evidence_quality": row.get("evidence_quality"),
            "source_type": row.get("source_type"),
            "citation_urls": row.get("citation_urls") or [],
            "pmids_extracted": row.get("pmids_extracted") or [],
            "tier_rationale": row.get("tier_rationale"),
            "ada_value_extraction": (
                "ai_extracted_from_real_url_human_review_needed"
                if chain_is_ai
                else "manually_verified"
            ),
            "ada_value_annotation": ADA_VALUE_ANNOTATION.get(name, ""),
            "verification_note": (
                "Evidence chain AI-generated from real URL/PMID anchor; "
                "ADA value extraction not independently verified. "
                "Human must cross-check source page for exact immunogenicity figure."
                if chain_is_ai
                else "Evidence chain and ADA value independently verified."
            ),
        }
        included_index.append(entry)
        included_data[key] = records[key]

    by_class: dict[str, list] = {"tier_A": [], "tier_B": []}
    for e in included_index:
        by_class[f"tier_{e['class_evidence_tier']}"].append(e["antibody_name"])

    meta = {
        "schema_version": "1.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "description": "Classified verifiable therapeutic-antibody ADA entries with real URLs and/or PMIDs; AI batch evidence chains removed.",
        "inclusion_rules": {
            "require_evidence_tier": ["A", "B"],
            "require_traceability": "At least one https URL in citation_urls OR at least one PMID (index or primary pmids field).",
            "exclude_evidence_source_exact": "",
            "exclude_evidence_source_prefix": "",
            "human_review": "8350-tier QA: confirm label Sec 6.2 / paper results match ada_value_display.",
        },
        "source_clinical_db": str(CLINICAL_INDEX.parent),
        "counts": {
            "verifiable_included": len(included_index),
            "rehabilitated_from_ai_batch": rehabilitated_count,
            "excluded_total": len(excluded),
            "by_evidence_tier": {
                "A": sum(1 for x in included_index if x["class_evidence_tier"] == "A"),
                "B": sum(1 for x in included_index if x["class_evidence_tier"] == "B"),
            },
            "by_ada_value_extraction": {
                "manually_verified": sum(1 for x in included_index if x.get("ada_value_extraction") == "manually_verified"),
                "ai_extracted_from_real_url_human_review_needed": sum(1 for x in included_index if x.get("ada_value_extraction") == "ai_extracted_from_real_url_human_review_needed"),
            },
            "entries_with_annotation": sum(1 for x in included_index if x.get("ada_value_annotation")),
            "by_ada_status": _count_status(included_index),
        },
        "excluded_summary": _summarize_excluded(excluded),
        "classification": by_class,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "verifiable_ada_index.json").write_text(
        json.dumps({"metadata": meta, "index": sorted(included_index, key=lambda x: x["antibody_name"].lower())}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT_DIR / "verifiable_ada_data.json").write_text(
        json.dumps({"metadata": meta, "records": included_data}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    csv_path = OUT_DIR / "verifiable_ada_index.csv"
    fields = [
        "antibody_name",
        "class_evidence_tier",
        "class_ada_status",
        "ada_value_display",
        "ada_value_extraction",
        "ada_value_annotation",
        "canonical_provenance",
        "evidence_source",
        "citation_urls",
        "pmids_extracted",
        "data_record_key",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in sorted(included_index, key=lambda x: x["antibody_name"].lower()):
            o = {k: r.get(k) for k in fields}
            o["citation_urls"] = ";".join(r.get("citation_urls") or [])
            o["pmids_extracted"] = ";".join(r.get("pmids_extracted") or [])
            w.writerow(o)

    (OUT_DIR / "verifiable_ada_excluded.json").write_text(
        json.dumps({"metadata": meta, "excluded": excluded}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    by_tier_payload = {
        "metadata": {k: v for k, v in meta.items() if k != "excluded_summary"},
        "tier_A": sorted([e for e in included_index if e["class_evidence_tier"] == "A"], key=lambda x: x["antibody_name"].lower()),
        "tier_B": sorted([e for e in included_index if e["class_evidence_tier"] == "B"], key=lambda x: x["antibody_name"].lower()),
    }
    (OUT_DIR / "verifiable_ada_by_tier.json").write_text(
        json.dumps(by_tier_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    (OUT_DIR / "README.txt").write_text(
        "\n".join(
            [
                " ADA （ AI ； URL  PMID）",
                "",
                ": python scripts/build_verifiable_classified_ada_db.py",
                ":  python scripts/build_clinical_ada_split_database.py",
                "",
                "verifiable_ada_index.json / .csv — ， class_evidence_tier = A/B",
                "verifiable_ada_by_tier.json —  Tier A / Tier B ",
                "verifiable_ada_data.json —  primary_record + supplemental",
                "verifiable_ada_excluded.json — （ 、Tier C ）",
                "",
                "A、FDA、PubMed、250： PMID/；",
                " evidence_source 「」* 。",
            ]
        ),
        encoding="utf-8",
    )

    print(json.dumps(meta["counts"], indent=2))
    print(f"Wrote {OUT_DIR}")


def _count_status(rows: list) -> dict:
    o: dict[str, int] = {}
    for r in rows:
        k = r.get("class_ada_status") or "unknown"
        o[k] = o.get(k, 0) + 1
    return o


def _summarize_excluded(exc: list[dict]) -> dict:
    o: dict[str, int] = {}
    for e in exc:
        k = e.get("reason", "unknown")
        o[k] = o.get(k, 0) + 1
    return o


if __name__ == "__main__":
    main()
