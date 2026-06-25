#!/usr/bin/env python3
"""
Merge all verification phases and rebuild the final database with
comprehensive verification_status for all 116 entries.
"""
from __future__ import annotations
import csv, json
from datetime import datetime, timezone
from pathlib import Path

REPO    = Path(__file__).resolve().parents[1]
IDX     = REPO / "data/ADA_reliable_package/verifiable_classified/verifiable_ada_index.json"
DATA    = REPO / "data/ADA_reliable_package/verifiable_classified/verifiable_ada_data.json"
P1      = REPO / "data/ADA_reliable_package/verification/full_reverification_report.json"
P3_FT   = REPO / "data/ADA_reliable_package/verification/fulltext_reverification.json"
P3_19   = REPO / "data/ADA_reliable_package/verification/final_19_pass_results.json"
OUT_DIR = REPO / "data/ADA_reliable_package/verifiable_classified"

# Entries verified in phase 3 fulltext pass (12)
P3_FT_VERIFIED: dict[str, dict] = {}  # filled from file

# Entries verified in phase 3 brand-name DailyMed/PubMed (6)
P3_19_VERIFIED: dict[str, dict] = {}  # filled from file

# Reason map for the 13 still-unverified entries
UNVERIFIED_REASON: dict[str, str] = {
    "Bimagrumab":   "no FDA approval; ADA 4% from clinical trial, not in DailyMed",
    "Brentuximab":  "DailyMed immunogenicity section found but 7%/30% text not extracted; Adcetris FDA label values known in literature",
    "Budigalimab":  "investigational; no FDA approval; ADA 1.8% from phase-I study",
    "Ecromeximab":  "abandoned drug; no DailyMed; 1.8% from phase-I clinical trial paper",
    "Elezanumab":   "investigational (AbbVie); no FDA approval; 2% from phase-I",
    "Enuzovimab":   "Chinese COVID-19 antibody (HFB30132A); no FDA/DailyMed entry",
    "Etaracizumab": "abandoned (MEDI-522/Vitaxin); no DailyMed; 5% from early trial",
    "Exidavnemab":  "phase-I alpha-synuclein antibody; no FDA approval; 7% from SAD study",
    "Fulranumab":   "abandoned NGF antibody; no DailyMed; 6% from clinical immunogenicity assay paper",
    "Gemtuzumab":   "DailyMed Mylotarg immunogenicity section found but 1.1% not extracted from XML",
    "Infliximab":   "ranges (10-40%/8-17%) are multi-study literature values, not a single FDA label figure; DailyMed section found but ranges not matched",
    "Olaratumab":   "withdrawn from market 2019; DailyMed no longer has SPL",
    "Satralizumab": "EMA-only approval (Enspryng); 41%/71% from EMA EPAR PDF not accessible in DailyMed",
}


def main() -> None:
    idx_blob  = json.loads(IDX.read_text(encoding="utf-8"))
    data_blob = json.loads(DATA.read_text(encoding="utf-8"))
    p1_map    = {r["antibody_name"]: r for r in json.loads(P1.read_text(encoding="utf-8"))["results"]}

    # Load phase 3 results
    for r in json.loads(P3_FT.read_text(encoding="utf-8"))["results"]:
        if r["verified"]:
            P3_FT_VERIFIED[r["antibody_name"]] = r

    p3_19_raw = json.loads(P3_19.read_text(encoding="utf-8"))
    for name, r in p3_19_raw.items():
        if r["verified"]:
            P3_19_VERIFIED[name] = r

    records = data_blob["records"]
    included: list[dict] = []
    not_included: list[dict] = []

    for row in idx_blob["index"]:
        name    = row["antibody_name"]
        p1r     = p1_map.get(name, {})
        p1v     = p1r.get("verdict", "")

        entry = dict(row)

        # Determine final verification status
        if p1v == "all_matched":
            vstatus = "verified_text_match"
            vmatched = p1r.get("check", {}).get("matched", [])
            vsrc = p1r.get("source_tried", "")
        elif p1v == "partial_match":
            vstatus = "verified_partial_primary_value_confirmed"
            vmatched = p1r.get("check", {}).get("matched", [])
            vsrc = p1r.get("source_tried", "")
        elif p1v == "no_numeric_value":
            vstatus = "verified_qualitative_no_pct_to_match"
            vmatched = []
            vsrc = p1r.get("source_tried", "")
        elif name in P3_FT_VERIFIED:
            r3 = P3_FT_VERIFIED[name]
            vstatus = "verified_pmc_fulltext"
            vmatched = r3.get("matched_pcts", [])
            vsrc = r3.get("verified_source", "")
        elif name in P3_19_VERIFIED:
            r3 = P3_19_VERIFIED[name]
            src = r3.get("verified_source", "")
            vstatus = "verified_dailymed_spl" if "DailyMed" in src else "verified_pubmed_fulltext"
            vmatched = r3.get("matched_pcts", [])
            vsrc = src
        elif row.get("verification_status", "").startswith("verified"):
            # Already set as verified in prior build (DailyMed, PMID corrected, etc.)
            vstatus = row["verification_status"]
            vmatched = row.get("verification_matched_pcts", [])
            vsrc = row.get("verification_source_tried", "")
        elif p1v == "fetch_failed":
            vstatus = "unverified_source_403_inaccessible"
            vmatched = []
            vsrc = p1r.get("source_tried", "")
        elif name in UNVERIFIED_REASON:
            vstatus = "unverified_clinical_trial_or_ema_source"
            vmatched = []
            vsrc = UNVERIFIED_REASON[name]
        else:
            vstatus = "unverified_other"
            vmatched = []
            vsrc = ""

        entry["verification_status"]       = vstatus
        entry["verification_matched_pcts"] = vmatched
        entry["verification_source"]       = vsrc
        entry["verification_unmatched"]    = p1r.get("check", {}).get("unmatched", [])
        included.append(entry)

    # Build stats
    by_status: dict[str, int] = {}
    for e in included:
        k = e["verification_status"]
        by_status[k] = by_status.get(k, 0) + 1

    verified_count   = sum(v for k, v in by_status.items() if k.startswith("verified"))
    unverified_count = sum(v for k, v in by_status.items() if k.startswith("unverified"))

    meta = {
        "schema_version": "3.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "description": (
            "Final ADA database after 3-phase automated verification. "
            "Phase-1: PubMed abstract + URL fetch. "
            "Phase-2: DailyMed SPL for FDA PDFs + wrong-PMID rescue. "
            "Phase-3: PMC full-text via PMID→PMCID conversion + brand-name DailyMed."
        ),
        "counts": {
            "total_included": len(included),
            "verified": verified_count,
            "unverified": unverified_count,
            "by_verification_status": dict(sorted(by_status.items())),
            "by_tier": {
                "A": sum(1 for x in included if x.get("class_evidence_tier") == "A"),
                "B": sum(1 for x in included if x.get("class_evidence_tier") == "B"),
            },
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sorted_idx = sorted(included, key=lambda x: x["antibody_name"].lower())

    (OUT_DIR / "verifiable_ada_index.json").write_text(
        json.dumps({"metadata": meta, "index": sorted_idx}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Rebuild data with updated verification fields
    updated_records = {}
    for entry in included:
        key = entry.get("data_record_key")
        if key and key in records:
            rec = dict(records[key])
            rec["verification_status"] = entry["verification_status"]
            rec["verification_matched_pcts"] = entry["verification_matched_pcts"]
            updated_records[key] = rec
    (OUT_DIR / "verifiable_ada_data.json").write_text(
        json.dumps({"metadata": meta, "records": updated_records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # By-tier split
    (OUT_DIR / "verifiable_ada_by_tier.json").write_text(
        json.dumps({
            "metadata": meta,
            "tier_A": [e for e in sorted_idx if e.get("class_evidence_tier") == "A"],
            "tier_B": [e for e in sorted_idx if e.get("class_evidence_tier") == "B"],
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # CSV
    fields = [
        "antibody_name", "class_evidence_tier", "class_ada_status",
        "ada_value_display", "verification_status", "verification_matched_pcts",
        "verification_unmatched", "verification_source",
        "ada_value_extraction", "ada_value_annotation",
        "canonical_provenance", "evidence_source",
        "citation_urls", "pmids_extracted", "data_record_key",
    ]
    csv_path = OUT_DIR / "verifiable_ada_index.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in sorted_idx:
            o = {k: r.get(k, "") for k in fields}
            o["citation_urls"]             = ";".join(r.get("citation_urls") or [])
            o["pmids_extracted"]           = ";".join(str(p) for p in (r.get("pmids_extracted") or []))
            o["verification_matched_pcts"] = str(r.get("verification_matched_pcts") or [])
            o["verification_unmatched"]    = str(r.get("verification_unmatched") or [])
            w.writerow(o)

    print(json.dumps(meta["counts"], indent=2, ensure_ascii=False))
    print(f"\n=== Wrote {OUT_DIR} ===")
    print("\nVerified breakdown:")
    for k, v in sorted(by_status.items()):
        symbol = "✓" if k.startswith("verified") else "✗"
        print(f"  {symbol} {k:55s}: {v:3d}")


if __name__ == "__main__":
    main()
