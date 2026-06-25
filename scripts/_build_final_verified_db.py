#!/usr/bin/env python3
"""
Final consolidation: merge Phase-1 and Phase-2 verification results,
assign verification_status to every entry, exclude confirmed-bad entries,
fix Golimumab PMID, and rebuild the verifiable classified database.
"""
from __future__ import annotations
import csv, json, re
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
IDX_PATH = REPO / "data/ADA_reliable_package/verifiable_classified/verifiable_ada_index.json"
DATA_PATH = REPO / "data/ADA_reliable_package/verifiable_classified/verifiable_ada_data.json"
P1_REPORT = REPO / "data/ADA_reliable_package/verification/full_reverification_report.json"
P2_REPORT = REPO / "data/ADA_reliable_package/verification/phase2_pdf_wrongpmid_results.json"
OUT_DIR = REPO / "data/ADA_reliable_package/verifiable_classified"

# ──────────────────────────────────────────────────────────────────────────────
# Entries confirmed with wrong PMIDs AND no alternative verification found
# → excluded from final database
EXCLUDE_WRONG_PMID: dict[str, str] = {
    "Abciximab": "PMID 15987447 is a COX-2 paper; DailyMed not found; no ADA source verified",
    "Belantamab": "PMID 31711027 is a carbon materials paper; DailyMed not found for belantamab",
    "Cadonilimab": "PMID 34807181 is a metal-mirror paper; Chinese NMPA drug with no FDA/DailyMed entry",
}

# Entries where PMID was wrong but DailyMed confirmed the value
# → keep with corrected provenance note
PMID_WRONG_BUT_DAILYMED_CONFIRMED: dict[str, str] = {
    "Lecanemab": "original PMID 38932388 is mRNA-vaccine paper; ADA value confirmed via DailyMed SPL",
    "Naxitamab": "original PMID 39177945 is about omalizumab treatment of ADA; ADA value confirmed via DailyMed SPL",
    "Nirsevimab": "original PMID 39572535 is broad neutralizing antibody paper; ADA value confirmed via DailyMed SPL",
}

# Golimumab: wrong PMID but correct PMID found via PubMed search
PMID_FIX: dict[str, dict] = {
    "Golimumab": {
        "old_pmid": "23089571",
        "new_pmid": "30412238",
        "new_source": "Immunogenicity of golimumab and its clinical relevance (PMID 30412238)",
        "note": "Original PMID 23089571 was a PCOS paper; replaced with PMID 30412238 (golimumab immunogenicity study)",
    }
}

# Phase-2 DailyMed confirmed entries (PDF entries verified via DailyMed SPL text)
DAILYMED_VERIFIED: set[str] = {
    "Benralizumab", "Bevacizumab", "Burosumab", "Galcanezumab",
    "Ranibizumab", "Risankizumab", "Sarilumab",
}

# Phase-1 result: partial matches - primary ADA value confirmed
PARTIAL_MATCH_CONFIRMED: set[str] = {
    "Alemtuzumab", "Anakinra", "Basiliximab", "Brodalumab",
    "Guselkumab", "Tildrakizumab", "Tocilizumab", "Ustekinumab",
}

# ──────────────────────────────────────────────────────────────────────────────

def assign_verification_status(name: str, p1_verdict: str, p2_result: dict | None) -> str:
    """Assign a verification_status string based on all available evidence."""
    if name in EXCLUDE_WRONG_PMID:
        return "excluded_wrong_pmid_no_alternative"
    if name in PMID_WRONG_BUT_DAILYMED_CONFIRMED:
        return "verified_dailymed_spl_pmid_corrected"
    if name in PMID_FIX:
        return "verified_pmid_corrected_match"
    if name in DAILYMED_VERIFIED:
        return "verified_fda_label_dailymed_spl"
    if name in PARTIAL_MATCH_CONFIRMED:
        return "verified_partial_primary_value_confirmed"
    if p1_verdict == "all_matched":
        return "verified_text_match"
    if p1_verdict == "no_numeric_value":
        return "verified_qualitative_no_pct_to_match"
    # Check phase 2
    if p2_result and p2_result.get("overall") == "verified":
        return "verified_fda_label_dailymed_spl"
    if p1_verdict == "fetch_failed":
        return "unverified_source_403_inaccessible"
    if p1_verdict == "not_found":
        # Check if source snippet mentions the drug name (Group C)
        return "unverified_pct_not_in_abstract_fulltext_needed"
    return "unverified_unknown"


def main() -> None:
    idx_blob = json.loads(IDX_PATH.read_text(encoding="utf-8"))
    data_blob = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    p1_blob = json.loads(P1_REPORT.read_text(encoding="utf-8"))
    p2_blob = json.loads(P2_REPORT.read_text(encoding="utf-8"))

    p1_map = {r["antibody_name"]: r for r in p1_blob["results"]}
    p2_map = p2_blob  # {name: result}

    included_index: list[dict] = []
    included_data: dict = {}
    excluded_list: list[dict] = []

    records = data_blob.get("records", {})

    for row in idx_blob["index"]:
        name = row["antibody_name"]

        if name in EXCLUDE_WRONG_PMID:
            excluded_list.append({
                "antibody_name": name,
                "reason": "excluded_wrong_pmid_no_alternative",
                "detail": EXCLUDE_WRONG_PMID[name],
            })
            continue

        p1 = p1_map.get(name, {})
        p2 = p2_map.get(name)
        v_status = assign_verification_status(name, p1.get("verdict", ""), p2)

        entry = dict(row)  # copy all existing fields

        # Apply PMID fix for Golimumab
        if name in PMID_FIX:
            fix = PMID_FIX[name]
            entry["pmids_extracted"] = [fix["new_pmid"]]
            entry["pmid_fix_note"] = fix["note"]
            entry["canonical_provenance"] = "pmid_corrected_via_pubmed_search"

        # Apply note for entries whose PMID was wrong but DailyMed confirmed
        if name in PMID_WRONG_BUT_DAILYMED_CONFIRMED:
            entry["pmid_warning"] = PMID_WRONG_BUT_DAILYMED_CONFIRMED[name]
            entry["canonical_provenance"] = "dailymed_spl_verified"

        # Add DailyMed setid if available
        if p2 and p2.get("dailymed_setid"):
            entry["dailymed_setid"] = p2["dailymed_setid"]

        entry["verification_status"] = v_status
        entry["verification_p1_verdict"] = p1.get("verdict", "")
        entry["verification_matched_pcts"] = p1.get("check", {}).get("matched", [])
        entry["verification_unmatched_pcts"] = p1.get("check", {}).get("unmatched", [])
        entry["verification_source_tried"] = p1.get("source_tried", "")

        included_index.append(entry)
        key = row["data_record_key"]
        if key in records:
            rec = dict(records[key])
            rec["verification_status"] = v_status
            included_data[key] = rec

    # Build counts
    by_status: dict[str, int] = {}
    for e in included_index:
        k = e["verification_status"]
        by_status[k] = by_status.get(k, 0) + 1

    verified_count = sum(v for k, v in by_status.items() if k.startswith("verified"))
    unverified_count = sum(v for k, v in by_status.items() if k.startswith("unverified"))

    meta = {
        "schema_version": "2.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "description": (
            "Final re-verified ADA database. Every entry has been subjected to "
            "automated source verification (PubMed abstract, PMC full-text, "
            "DailyMed SPL XML). verification_status field shows result for each entry."
        ),
        "verification_methodology": {
            "phase1": "Fetched PMID abstract via NCBI efetch OR URL page text; checked if claimed ADA % appears in text",
            "phase2_pdf": "DailyMed SPL XML API used to extract immunogenicity section from FDA labels that were binary PDFs",
            "phase2_wrongpmid": "PubMed esearch + DailyMed used to find correct sources for entries with wrong PMIDs",
        },
        "counts": {
            "total_included": len(included_index),
            "total_excluded": len(excluded_list),
            "verified": verified_count,
            "unverified": unverified_count,
            "by_verification_status": dict(sorted(by_status.items())),
            "by_tier": {
                "A": sum(1 for x in included_index if x.get("class_evidence_tier") == "A"),
                "B": sum(1 for x in included_index if x.get("class_evidence_tier") == "B"),
            },
        },
        "exclusions_this_run": {
            "wrong_pmid_no_alternative": [e["antibody_name"] for e in excluded_list
                                          if "wrong_pmid" in e["reason"]],
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    (OUT_DIR / "verifiable_ada_index.json").write_text(
        json.dumps({"metadata": meta, "index": sorted(included_index, key=lambda x: x["antibody_name"].lower())},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT_DIR / "verifiable_ada_data.json").write_text(
        json.dumps({"metadata": meta, "records": included_data}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT_DIR / "verifiable_ada_excluded.json").write_text(
        json.dumps({"metadata": meta, "excluded": excluded_list}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Rebuild by-tier
    by_tier_payload = {
        "metadata": meta,
        "tier_A": sorted([e for e in included_index if e.get("class_evidence_tier") == "A"],
                         key=lambda x: x["antibody_name"].lower()),
        "tier_B": sorted([e for e in included_index if e.get("class_evidence_tier") == "B"],
                         key=lambda x: x["antibody_name"].lower()),
    }
    (OUT_DIR / "verifiable_ada_by_tier.json").write_text(
        json.dumps(by_tier_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # CSV with verification columns
    fields = [
        "antibody_name", "class_evidence_tier", "class_ada_status",
        "ada_value_display", "verification_status", "verification_p1_verdict",
        "verification_matched_pcts", "verification_unmatched_pcts",
        "ada_value_extraction", "ada_value_annotation",
        "canonical_provenance", "evidence_source",
        "citation_urls", "pmids_extracted", "data_record_key",
    ]
    csv_path = OUT_DIR / "verifiable_ada_index.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in sorted(included_index, key=lambda x: x["antibody_name"].lower()):
            o = {k: r.get(k, "") for k in fields}
            o["citation_urls"] = ";".join(r.get("citation_urls") or [])
            o["pmids_extracted"] = ";".join(str(p) for p in (r.get("pmids_extracted") or []))
            o["verification_matched_pcts"] = str(r.get("verification_matched_pcts") or [])
            o["verification_unmatched_pcts"] = str(r.get("verification_unmatched_pcts") or [])
            w.writerow(o)

    print(json.dumps(meta["counts"], indent=2, ensure_ascii=False))
    print(f"\nWrote {OUT_DIR}")
    print(f"\nExcluded this run:")
    for e in excluded_list:
        print(f"  {e['antibody_name']}: {e['detail']}")


if __name__ == "__main__":
    main()
