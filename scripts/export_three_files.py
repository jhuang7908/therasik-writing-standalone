#!/usr/bin/env python3
"""
Export three final output files:
  File 1 — confirmed_ada.json/.csv   : 80 verified entries (ADA confirmed incl. qualitative)
  File 2 — need_fulltext.json/.csv   : 36 entries that need manual access, with check URLs
  File 3 — cannot_verify_ada.json/.csv: 3 excluded entries + summary why
"""
from __future__ import annotations
import csv, json
from datetime import datetime, timezone
from pathlib import Path

REPO    = Path(__file__).resolve().parents[1]
IDX     = REPO / "data/ADA_reliable_package/verifiable_classified/verifiable_ada_index.json"
EXCL    = REPO / "data/ADA_reliable_package/verifiable_classified/verifiable_ada_excluded.json"
OUT_DIR = REPO / "data/ADA_reliable_package/final_three_files"

# Human-readable URLs for the 13 clinical/EMA unverified entries
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
                     "https://pubmed.ncbi.nlm.nih.gov/?term=infliximab+immunogenicity+incidence+anti-drug+antibody"],
    "Olaratumab":   ["https://pubmed.ncbi.nlm.nih.gov/?term=olaratumab+lartruvo+immunogenicity+ADA"],
    "Satralizumab": ["https://www.ema.europa.eu/en/documents/product-information/enspryng-epar-product-information_en.pdf",
                     "https://pubmed.ncbi.nlm.nih.gov/?term=satralizumab+immunogenicity+NMO"],
}

MANUAL_CHECK_REASON: dict[str, str] = {
    "Bimagrumab":   "investigational; no FDA approval; ADA 4% from clinical trial — check PMC full text",
    "Brentuximab":  "Adcetris FDA label PDF — need human to open PDF and read Section 6.2",
    "Budigalimab":  "investigational ABBV-181; ADA 1.8% from phase-I — check PMC full text",
    "Ecromeximab":  "abandoned drug; 1.8% from PMID 28489678 phase-I — need full text",
    "Elezanumab":   "AbbVie investigational; 2% from PMID 38191982 — need full text",
    "Enuzovimab":   "Chinese COVID-19 antibody HFB30132A; 1.5% from PMID 39793935 — need full text",
    "Etaracizumab": "abandoned MEDI-522; 5% from PMID 17390341 — need full text",
    "Exidavnemab":  "phase-I BAN0805; 7% from PMID 39105497 — need PMC full text PMC12976517",
    "Fulranumab":   "abandoned NGF antibody; 6% from PMID 24590506 — need full text",
    "Gemtuzumab":   "Mylotarg FDA label DailyMed SPL has immunogenicity section — need human to extract 1.1%",
    "Infliximab":   "Remicade FDA label PDF — ranges (10-40%) from multiple indications; need human to open PDF",
    "Olaratumab":   "Lartruvo withdrawn 2019; 3.5% from original FDA label PDF — human must access archive",
    "Satralizumab": "Enspryng EMA approval only; 41%/71% from EMA EPAR PDF — need human to open EMA document",
}


def main() -> None:
    idx_blob  = json.loads(IDX.read_text(encoding="utf-8"))
    excl_blob = json.loads(EXCL.read_text(encoding="utf-8"))
    entries   = idx_blob["index"]

    file1_confirmed: list[dict] = []
    file2_need_ft:   list[dict] = []

    for e in sorted(entries, key=lambda x: x["antibody_name"].lower()):
        vstatus = e.get("verification_status", "")
        name    = e["antibody_name"]

        if vstatus.startswith("verified"):
            file1_confirmed.append(e)
        elif vstatus == "unverified_source_403_inaccessible":
            urls = e.get("citation_urls") or []
            file2_need_ft.append({
                **e,
                "manual_check_reason": "source URL returned HTTP 403 — institutional/subscription access needed",
                "manual_check_urls": urls,
            })
        elif vstatus == "unverified_clinical_trial_or_ema_source":
            file2_need_ft.append({
                **e,
                "manual_check_reason": MANUAL_CHECK_REASON.get(name, "clinical/EMA source"),
                "manual_check_urls": MANUAL_CHECK_URLS.get(name, e.get("citation_urls") or []),
            })
        else:
            # fallback
            file2_need_ft.append({**e,
                "manual_check_reason": vstatus,
                "manual_check_urls": e.get("citation_urls") or [],
            })

    # File 3: excluded entries (wrong PMIDs + no alternative)
    file3_cannot: list[dict] = excl_blob.get("excluded", [])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()

    # ── File 1 ───────────────────────────────────────────────────────────────
    meta1 = {
        "description": "Confirmed ADA entries — ADA value verified against real source text (PubMed/PMC/DailyMed/URL). Includes qualitative 'no ADA detected' entries.",
        "generated_utc": ts,
        "total": len(file1_confirmed),
        "breakdown": _count_status(file1_confirmed, "verification_status"),
    }
    (OUT_DIR / "confirmed_ada.json").write_text(
        json.dumps({"metadata": meta1, "entries": file1_confirmed}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_csv(file1_confirmed, OUT_DIR / "confirmed_ada.csv", [
        "antibody_name", "class_evidence_tier", "ada_value_display",
        "verification_status", "verification_matched_pcts",
        "evidence_source", "citation_urls", "pmids_extracted",
    ])

    # ── File 2 ───────────────────────────────────────────────────────────────
    meta2 = {
        "description": (
            "Entries where ADA value could not be auto-verified but may be obtainable via manual access. "
            "Subcategories: (A) source URL returned 403 — needs institutional/subscription access; "
            "(B) source is EMA EPAR PDF or clinical trial / abandoned drug paper — needs human to open document."
        ),
        "generated_utc": ts,
        "total": len(file2_need_ft),
        "cat_403_inaccessible": sum(1 for e in file2_need_ft if "403" in e.get("manual_check_reason", "")),
        "cat_clinical_trial_or_ema": sum(1 for e in file2_need_ft if "403" not in e.get("manual_check_reason", "")),
    }
    (OUT_DIR / "need_fulltext.json").write_text(
        json.dumps({"metadata": meta2, "entries": file2_need_ft}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_csv(file2_need_ft, OUT_DIR / "need_fulltext.csv", [
        "antibody_name", "class_evidence_tier", "ada_value_display",
        "verification_status", "manual_check_reason", "manual_check_urls",
        "evidence_source", "citation_urls", "pmids_extracted",
    ])

    # ── File 3 ───────────────────────────────────────────────────────────────
    meta3 = {
        "description": (
            "Entries excluded from database: PMID was confirmed to point to a completely different paper, "
            "and no alternative verifiable source was found. These cannot be kept in any verified database."
        ),
        "generated_utc": ts,
        "total": len(file3_cannot),
    }
    (OUT_DIR / "cannot_verify_ada.json").write_text(
        json.dumps({"metadata": meta3, "entries": file3_cannot}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    f3_csv_path = OUT_DIR / "cannot_verify_ada.csv"
    with f3_csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["antibody_name", "reason", "detail"]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in file3_cannot:
            w.writerow({k: r.get(k, "") for k in fields})

    # ── Print summary ─────────────────────────────────────────────────────────
    print("=" * 60)
    print("  ADA DATABASE — FINAL THREE-FILE EXPORT")
    print("=" * 60)
    print()
    print(f"FILE 1: confirmed_ada  ({len(file1_confirmed)} entries)")
    print("  ADA value verified against real source text")
    for k, v in sorted(meta1["breakdown"].items()):
        sym = "✓"
        print(f"    {sym} {k:50s}: {v}")
    print()
    print(f"FILE 2: need_fulltext  ({len(file2_need_ft)} entries)")
    print(f"  (A) HTTP 403 — needs institutional access : {meta2['cat_403_inaccessible']}")
    print(f"  (B) EMA/clinical/abandoned — needs manual : {meta2['cat_clinical_trial_or_ema']}")
    print()
    print("  Full list:")
    for e in sorted(file2_need_ft, key=lambda x: x["antibody_name"]):
        reason = e.get("manual_check_reason", "")[:65]
        ada    = e.get("ada_value_display", "")[:35]
        print(f"    [{e.get('class_evidence_tier','?')}] {e['antibody_name']:25s}  ada={ada:35s}")
        print(f"         reason: {reason}")
        urls = e.get("manual_check_urls") or []
        for u in urls[:2]:
            print(f"         url   : {u[:80]}")
    print()
    print(f"FILE 3: cannot_verify_ada  ({len(file3_cannot)} entries)")
    print("  Excluded: confirmed-wrong PMID, no alternative source found")
    for r in file3_cannot:
        print(f"    ✗ {r.get('antibody_name','?'):20s}: {r.get('detail','')[:70]}")
    print()
    print(f"Wrote to: {OUT_DIR}")


def _count_status(entries: list, field: str) -> dict:
    o: dict[str, int] = {}
    for e in entries:
        k = e.get(field, "unknown")
        o[k] = o.get(k, 0) + 1
    return dict(sorted(o.items()))


def _write_csv(entries: list[dict], path: Path, fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in entries:
            o = {k: r.get(k, "") for k in fields}
            if "citation_urls" in fields:
                o["citation_urls"] = ";".join(r.get("citation_urls") or [])
            if "pmids_extracted" in fields:
                o["pmids_extracted"] = ";".join(str(p) for p in (r.get("pmids_extracted") or []))
            if "manual_check_urls" in fields:
                o["manual_check_urls"] = ";".join(r.get("manual_check_urls") or [])
            if "verification_matched_pcts" in fields:
                o["verification_matched_pcts"] = str(r.get("verification_matched_pcts") or [])
            w.writerow(o)


if __name__ == "__main__":
    main()
