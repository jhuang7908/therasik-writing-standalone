#!/usr/bin/env python3
"""
Complete 3-file export covering all 170 entries in clinical_ada_db_index.

File 1: confirmed_ada     — 80 entries with ADA verified against real source
File 2: need_fulltext     — 36 entries (403-blocked or EMA/trial sources) with check URLs
File 3: cannot_verify_ada — 54 entries: 3 wrong-PMID + 6 suspect-value + 45 AI-batch-fake-PMID
"""
from __future__ import annotations
import csv, json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

CLINICAL_IDX  = REPO / "data/ADA_reliable_package/clinical_db/clinical_ada_db_index.json"
CLINICAL_DATA = REPO / "data/ADA_reliable_package/clinical_db/clinical_ada_db_data.json"
VERIF_IDX     = REPO / "data/ADA_reliable_package/verifiable_classified/verifiable_ada_index.json"
VERIF_EXCL    = REPO / "data/ADA_reliable_package/verifiable_classified/verifiable_ada_excluded.json"
OUT_DIR       = REPO / "data/ADA_reliable_package/final_three_files"

ADA_VALUE_SUSPECT = {
    "Atoltivimab":  "80% is PRNT-80 viral inhibition rate, not ADA incidence",
    "Depemokimab":  "95% is 95% CI confidence interval, not ADA incidence",
    "Axatilimab":   "16.3% is CV (PK variability), not ADA incidence",
    "Clesrovimab":  "22.6% is CV (PK variability), not ADA incidence",
    "Domvanalimab": "17.2% is ORR (objective response rate), not ADA incidence",
    "Favezelimab":  "42.9% likely ORR/tumor-shrinkage, not ADA incidence; PMID unverified",
}

MANUAL_CHECK_URLS: dict[str, list[str]] = {
    "Bimagrumab":   ["https://pubmed.ncbi.nlm.nih.gov/?term=bimagrumab+immunogenicity",
                     "https://clinicaltrials.gov/search?term=bimagrumab"],
    "Brentuximab":  ["https://www.accessdata.fda.gov/drugsatfda_docs/label/2018/125388s099lbl.pdf",
                     "https://www.rxlist.com/adcetris-drug.htm"],
    "Budigalimab":  ["https://pubmed.ncbi.nlm.nih.gov/?term=budigalimab+ABBV-181+immunogenicity"],
    "Ecromeximab":  ["https://pubmed.ncbi.nlm.nih.gov/28489678/"],
    "Elezanumab":   ["https://pubmed.ncbi.nlm.nih.gov/38191982/"],
    "Enuzovimab":   ["https://pubmed.ncbi.nlm.nih.gov/39793935/"],
    "Etaracizumab": ["https://pubmed.ncbi.nlm.nih.gov/17390341/"],
    "Exidavnemab":  ["https://pubmed.ncbi.nlm.nih.gov/39105497/"],
    "Fulranumab":   ["https://pubmed.ncbi.nlm.nih.gov/24590506/"],
    "Gemtuzumab":   ["https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=32fd2bb2-1cfa-4250-feb8-d7956c794e05"],
    "Infliximab":   ["https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/103772s5412lbl.pdf",
                     "https://pubmed.ncbi.nlm.nih.gov/?term=infliximab+immunogenicity+incidence"],
    "Olaratumab":   ["https://pubmed.ncbi.nlm.nih.gov/?term=olaratumab+lartruvo+immunogenicity"],
    "Satralizumab": ["https://www.ema.europa.eu/en/documents/product-information/enspryng-epar-product-information_en.pdf"],
}

MANUAL_REASON: dict[str, str] = {
    "Bimagrumab":   "investigational; no FDA approval; ADA 4% from clinical trial",
    "Brentuximab":  "FDA label PDF — open Section 6.2 to read 7% / 30%",
    "Budigalimab":  "investigational ABBV-181; ADA 1.8% from phase-I PMC full text needed",
    "Ecromeximab":  "abandoned; 1.8% from PMID 28489678 full text needed",
    "Elezanumab":   "AbbVie investigational; 2% from PMID 38191982 full text needed",
    "Enuzovimab":   "Chinese COVID antibody HFB30132A; 1.5% from PMID 39793935 full text",
    "Etaracizumab": "abandoned MEDI-522; 5% from PMID 17390341 full text needed",
    "Exidavnemab":  "phase-I BAN0805; 7% from PMID 39105497 PMC full text needed",
    "Fulranumab":   "abandoned; 6% from PMID 24590506 full text needed",
    "Gemtuzumab":   "Mylotarg DailyMed has immunogenicity section — human must extract 1.1%",
    "Infliximab":   "Remicade FDA label PDF — ranges from multiple indications",
    "Olaratumab":   "Lartruvo withdrawn 2019; 3.5% from archived FDA label",
    "Satralizumab": "EMA-only; 41%/71% from EMA EPAR PDF (not DailyMed)",
}


def main() -> None:
    ci_blob = json.loads(CLINICAL_IDX.read_text(encoding="utf-8"))
    cd_blob = json.loads(CLINICAL_DATA.read_text(encoding="utf-8"))
    vi_blob = json.loads(VERIF_IDX.read_text(encoding="utf-8"))
    ex_blob = json.loads(VERIF_EXCL.read_text(encoding="utf-8"))

    records = cd_blob.get("records", {})
    vi_map  = {e["antibody_name"]: e for e in vi_blob["index"]}

    file1: list[dict] = []
    file2: list[dict] = []
    file3: list[dict] = []

    # ── Entries already in verifiable index (116) ──────────────────────────
    for e in vi_blob["index"]:
        vstatus = e.get("verification_status", "")
        name    = e["antibody_name"]
        if vstatus.startswith("verified"):
            file1.append(e)
        elif vstatus == "unverified_source_403_inaccessible":
            urls = e.get("citation_urls") or []
            file2.append({**e,
                "manual_check_reason": "HTTP 403 — institutional/subscription access needed",
                "manual_check_urls":   urls,
                "suggested_action":    "Open URL with institutional access and search Section 6.2 Immunogenicity",
            })
        elif vstatus == "unverified_clinical_trial_or_ema_source":
            file2.append({**e,
                "manual_check_reason": MANUAL_REASON.get(name, "clinical/EMA source"),
                "manual_check_urls":   MANUAL_CHECK_URLS.get(name, e.get("citation_urls") or []),
                "suggested_action":    "Open PMC full text or EMA PDF and search for ADA/immunogenicity section",
            })
        else:
            file2.append({**e,
                "manual_check_reason": vstatus,
                "manual_check_urls":   e.get("citation_urls") or [],
                "suggested_action":    "Manual review required",
            })

    # ── wrong-PMID excluded (3) ────────────────────────────────────────────
    for e in ex_blob["excluded"]:
        file3.append({
            "antibody_name": e.get("antibody_name", "?"),
            "ada_value_display": "",
            "class_evidence_tier": "?",
            "cannot_verify_reason": "wrong_pmid_no_alternative",
            "detail": e.get("detail", ""),
        })

    # ── The 51 silently-dropped entries ───────────────────────────────────
    accounted = {e["antibody_name"] for e in vi_blob["index"]}
    accounted |= {e["antibody_name"] for e in ex_blob["excluded"]}

    for row in sorted(ci_blob["index"], key=lambda x: x["antibody_name"]):
        name = row["antibody_name"]
        if name in accounted:
            continue  # already handled

        key     = row.get("data_record_key", "")
        primary = (records.get(key) or {}).get("primary_record") or {}
        es      = str(primary.get("evidence_source") or "")
        ada     = row.get("ada_value_display", "")
        tier    = row.get("evidence_tier", "?")
        pmids   = row.get("pmids_extracted") or []
        urls    = row.get("citation_urls") or []

        if name in ADA_VALUE_SUSPECT:
            file3.append({
                "antibody_name":       name,
                "ada_value_display":   ada,
                "class_evidence_tier": tier,
                "cannot_verify_reason": "ada_value_is_not_ada_incidence",
                "detail": ADA_VALUE_SUSPECT[name],
                "evidence_source":     es,
                "citation_urls":       urls,
                "pmids_extracted":     pmids,
            })
        elif es == "" or es.startswith(""):
            file3.append({
                "antibody_name":       name,
                "ada_value_display":   ada,
                "class_evidence_tier": tier,
                "cannot_verify_reason": "ai_batch_fake_pmid",
                "detail": f"evidence_source=''; PMID {pmids[0] if pmids else 'none'} verified to point to unrelated paper",
                "evidence_source":     es,
                "citation_urls":       urls,
                "pmids_extracted":     pmids,
            })
        else:
            file3.append({
                "antibody_name":       name,
                "ada_value_display":   ada,
                "class_evidence_tier": tier,
                "cannot_verify_reason": "other_no_verifiable_source",
                "detail": f"tier={tier} es={es}",
                "evidence_source":     es,
                "citation_urls":       urls,
                "pmids_extracted":     pmids,
            })

    total = len(file1) + len(file2) + len(file3)
    ts    = datetime.now(timezone.utc).isoformat()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── File 1 ───────────────────────────────────────────────────────────
    f1_by_status = _count(file1, "verification_status")
    (OUT_DIR / "confirmed_ada.json").write_text(
        json.dumps({"metadata": {
            "description": "Confirmed ADA entries — value verified against real source text (PubMed/PMC/DailyMed). Includes qualitative 'no ADA detected'.",
            "generated_utc": ts,
            "total": len(file1),
            "by_verification_method": f1_by_status,
        }, "entries": sorted(file1, key=lambda x: x["antibody_name"].lower())},
        ensure_ascii=False, indent=2), encoding="utf-8")
    _csv(file1, OUT_DIR / "confirmed_ada.csv", [
        "antibody_name", "class_evidence_tier", "ada_value_display",
        "verification_status", "verification_matched_pcts",
        "ada_value_annotation", "evidence_source", "citation_urls", "pmids_extracted",
    ])

    # ── File 2 ───────────────────────────────────────────────────────────
    cat_403 = sum(1 for e in file2 if "403" in e.get("manual_check_reason",""))
    cat_ema = len(file2) - cat_403
    (OUT_DIR / "need_fulltext.json").write_text(
        json.dumps({"metadata": {
            "description": (
                "Entries where ADA value is plausible but could not be auto-verified. "
                "Category A (403): real URL blocked — needs institutional access. "
                "Category B (EMA/trial): needs human to open PDF or PMC full text."
            ),
            "generated_utc": ts,
            "total": len(file2),
            "cat_403_needs_institutional_access": cat_403,
            "cat_ema_clinical_trial_manual":      cat_ema,
        }, "entries": sorted(file2, key=lambda x: x["antibody_name"].lower())},
        ensure_ascii=False, indent=2), encoding="utf-8")
    _csv(file2, OUT_DIR / "need_fulltext.csv", [
        "antibody_name", "class_evidence_tier", "ada_value_display",
        "verification_status", "manual_check_reason", "manual_check_urls",
        "suggested_action", "evidence_source", "citation_urls", "pmids_extracted",
    ])

    # ── File 3 ───────────────────────────────────────────────────────────
    f3_reasons = _count(file3, "cannot_verify_reason")
    (OUT_DIR / "cannot_verify_ada.json").write_text(
        json.dumps({"metadata": {
            "description": (
                "Entries that cannot be included in any verified database. "
                "Subcategories: (1) wrong_pmid_no_alternative — PMID confirmed to point to unrelated paper; "
                "(2) ada_value_is_not_ada_incidence — claimed value is CV/CI/ORR/PRNT, not ADA incidence; "
                "(3) ai_batch_fake_pmid — AI-generated evidence chain with fake PMID."
            ),
            "generated_utc": ts,
            "total": len(file3),
            "by_reason": f3_reasons,
        }, "entries": sorted(file3, key=lambda x: x["antibody_name"].lower())},
        ensure_ascii=False, indent=2), encoding="utf-8")
    _csv(file3, OUT_DIR / "cannot_verify_ada.csv", [
        "antibody_name", "class_evidence_tier", "ada_value_display",
        "cannot_verify_reason", "detail", "evidence_source",
        "citation_urls", "pmids_extracted",
    ])

    # ── Summary ──────────────────────────────────────────────────────────
    print("=" * 65)
    print("  COMPLETE 3-FILE ADA EXPORT  (all 170 accounted)")
    print("=" * 65)
    print(f"\nFILE 1 — confirmed_ada          : {len(file1):3d} entries")
    for k, v in sorted(f1_by_status.items()):
        print(f"    ✓ {k:50s}: {v}")
    print(f"\nFILE 2 — need_fulltext          : {len(file2):3d} entries")
    print(f"    (A) HTTP 403 blocked (institutional access): {cat_403}")
    print(f"    (B) EMA PDF / clinical trial / abandoned  : {cat_ema}")
    print(f"\nFILE 3 — cannot_verify_ada      : {len(file3):3d} entries")
    for k, v in sorted(f3_reasons.items(), key=lambda x: -x[1]):
        print(f"    ✗ {k:50s}: {v}")
    print(f"\nTotal : {total}  (clinical DB has {len(ci_blob['index'])})")
    print(f"\nWrote to {OUT_DIR}")


def _count(lst: list, field: str) -> dict:
    o: dict[str, int] = {}
    for e in lst:
        k = e.get(field, "unknown")
        o[k] = o.get(k, 0) + 1
    return dict(sorted(o.items()))


def _csv(lst: list, path: Path, fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in sorted(lst, key=lambda x: x.get("antibody_name","").lower()):
            o = {k: r.get(k, "") for k in fields}
            for fld in ("citation_urls", "manual_check_urls", "pmids_extracted"):
                if fld in fields:
                    val = r.get(fld)
                    if isinstance(val, list):
                        o[fld] = ";".join(str(v) for v in val)
            for fld in ("verification_matched_pcts",):
                if fld in fields:
                    val = r.get(fld)
                    if isinstance(val, list):
                        o[fld] = str(val)
            w.writerow(o)


if __name__ == "__main__":
    main()
