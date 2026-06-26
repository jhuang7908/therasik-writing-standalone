#!/usr/bin/env python3
"""
Curate ADA records: keep only entries with stated ADA/immunogenicity findings,
grade evidence traceability, flag rows that need literature/label retrieval.

Does NOT invent ADA numbers. Optional PubMed search returns PMIDs only for human review.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    REPO
    / "data"
    / "ADA_reliable_package"
    / "from_openclaw_20260330"
    / "reliable_merged"
    / "reliable_ada_antibodies_database_20260330_231950.json"
)
OUT_DIR = REPO / "data" / "ADA_reliable_package" / "curated"

URL_RE = re.compile(r"https?://[^\s\)\]\"']+", re.I)
PMID_IN_TEXT = re.compile(r"PMID[:\s]+(\d+)", re.I)
# PubMed article pages: .../pubmed.ncbi.nlm.nih.gov/12345678/
PUBMED_URL_PMID = re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{6,9})(?:/|\?|$)", re.I)

WEAK_VALUE_PATTERN = re.compile(
    r"^\s*(n/?a|not\s+available|unknown|not\s+reported|no\s+data)\s*$",
    re.I,
)


def extract_urls(text: str) -> list[str]:
    if not text:
        return []
    return list(dict.fromkeys(URL_RE.findall(text)))


def pmids_from_urls(urls: list[str]) -> list[str]:
    out: list[str] = []
    for u in urls:
        for m in PUBMED_URL_PMID.finditer(u):
            out.append(m.group(1))
    return list(dict.fromkeys(out))


def pmids_from_record(ab: dict, citation_urls: list[str] | None = None) -> list[str]:
    out: list[str] = []
    for p in ab.get("pmids") or []:
        if p is not None and str(p).strip().isdigit():
            out.append(str(p).strip())
    chain = ab.get("evidence_chain") or ""
    out.extend(PMID_IN_TEXT.findall(chain))
    if citation_urls:
        out.extend(pmids_from_urls(citation_urls))
    return list(dict.fromkeys(out))


def has_reported_ada(ada_value: str) -> bool:
    """False only when the field is empty or explicitly 'no data' style."""
    v = (ada_value or "").strip()
    if not v:
        return False
    if WEAK_VALUE_PATTERN.match(v):
        return False
    return True


def tier_a_anchor(urls: list[str], pmids: list[str]) -> str:
    """
    Tier A only if: PMID present, FDA label (accessdata.fda.gov),
    ClinicalTrials.gov, or PMC (pmc.ncbi.nlm.nih.gov).
    Returns a short tag for metadata notes; empty if no Tier-A anchor.
    """
    if pmids:
        return "pmid"
    for u in urls:
        lu = u.lower()
        if "accessdata.fda.gov" in lu:
            return "fda_label"
        if "clinicaltrials.gov" in lu:
            return "clinicaltrials_gov"
        if "pmc.ncbi.nlm.nih.gov" in lu:
            return "pmc"
    return ""


def evidence_tier_for_record(ab: dict) -> tuple[str, list[str], str]:
    """
    A: PMID (field, text, or pubmed URL) OR FDA accessdata label OR clinicaltrials.gov.
    B: at least one http(s) URL but no Tier-A anchor (still treated as traceable ADA).
    C: no URL and no Tier-A anchor.
    """
    chain = ab.get("evidence_chain") or ""
    urls = extract_urls(chain)
    su = (ab.get("source_url") or "").strip()
    if su.startswith("http"):
        urls = [su] + [u for u in urls if u != su]
        urls = list(dict.fromkeys(urls))

    pmids = pmids_from_record(ab, urls)
    anchor = tier_a_anchor(urls, pmids)

    if anchor:
        tier = "A"
        if anchor == "pmid" and not urls:
            notes = "tier_A_pmid_no_http"
        else:
            notes = f"tier_A_{anchor}"
    elif urls:
        tier = "B"
        notes = "tier_B_url_only"
    else:
        tier = "C"
        notes = "tier_C_no_url_no_tier_A_anchor"

    return tier, urls, notes


def needs_retrieval(tier: str, evidence_quality: str) -> bool:
    if tier == "C":
        return True
    if str(evidence_quality or "").lower() == "low" and tier != "A":
        return True
    return False


def retrieval_query(inn: str) -> str:
    return f'"{inn}"[Title/Abstract] AND (immunogenicity OR "anti-drug antibod*" OR ADA)'


def pubmed_esearch(term: str, retmax: int = 8, email: str | None = None) -> list[str]:
    params = {
        "db": "pubmed",
        "term": term,
        "retmax": str(retmax),
        "retmode": "json",
        "sort": "relevance",
    }
    if email:
        params["email"] = email
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.parse.urlencode(
        params
    )
    req = urllib.request.Request(url, headers={"User-Agent": "AntibodyEngineerSuite/ADA-curator"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    return data.get("esearchresult", {}).get("idlist", [])


def normalize_record(ab: dict, tier: str, urls: list[str], tier_notes: str) -> dict:
    pmids = pmids_from_record(ab, urls)
    q = retrieval_query(ab.get("antibody_name", ""))
    return {
        "antibody_name": ab.get("antibody_name"),
        "ada_value": ab.get("ada_value"),
        "has_numeric_ada": ab.get("has_numeric_ada"),
        "evidence_quality": ab.get("evidence_quality"),
        "source_type": ab.get("source_type"),
        "source_url_field": ab.get("source_url"),
        "evidence_source": ab.get("evidence_source"),
        "pmids_extracted": pmids,
        "citation_urls": urls,
        "evidence_tier": tier,
        "evidence_tier_notes": tier_notes,
        "needs_retrieval": needs_retrieval(tier, str(ab.get("evidence_quality", ""))),
        "suggested_pubmed_query": q,
        "evidence_chain": ab.get("evidence_chain"),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Curate ADA JSON into tiered reliable database.")
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument(
        "--pubmed",
        action="store_true",
        help="For rows with needs_retrieval, fetch candidate PMIDs (no abstract; human must verify ADA match).",
    )
    ap.add_argument("--email", default="", help="Email for NCBI E-utilities etiquette.")
    args = ap.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"Input not found: {args.input}")

    with args.input.open(encoding="utf-8") as f:
        bundle = json.load(f)

    kept: list[dict] = []
    skipped: list[dict] = []

    for ab in bundle.get("antibodies", []):
        ada = ab.get("ada_value", "")
        if not has_reported_ada(str(ada)):
            skipped.append({"antibody_name": ab.get("antibody_name"), "ada_value": ada, "reason": "no_ada_field"})
            continue
        tier, urls, tier_notes = evidence_tier_for_record(ab)
        rec = normalize_record(ab, tier, urls, tier_notes)
        kept.append(rec)

    tier_a = [r for r in kept if r["evidence_tier"] == "A"]
    tier_b = [r for r in kept if r["evidence_tier"] == "B"]
    tier_c = [r for r in kept if r["evidence_tier"] == "C"]
    need = [r for r in kept if r["needs_retrieval"]]

    if args.pubmed:
        email = args.email or None
        for i, rec in enumerate(need):
            if not rec["needs_retrieval"]:
                continue
            try:
                rec["pubmed_candidate_pmids"] = pubmed_esearch(
                    rec["suggested_pubmed_query"], retmax=8, email=email
                )
            except Exception as e:
                rec["pubmed_candidate_pmids"] = []
                rec["pubmed_search_error"] = str(e)
            if i < len(need) - 1:
                time.sleep(0.35)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "description": "Curated ADA database: only rows with reported ADA/immunogenicity; tiered traceability.",
        "input": str(args.input),
        "rules": {
            "skip": "Empty ada_value or explicit N/A / not reported.",
            "tier_A": "PMID (field, PMID: text, or pubmed.ncbi.nlm.nih.gov/ID URL) OR FDA accessdata.fda.gov OR clinicaltrials.gov.",
            "tier_B": "Has at least one http(s) URL but no Tier-A anchor (still traceable, real ADA citation).",
            "tier_C": "No URL and no PMID/FDA/ClinicalTrials anchor.",
            "pubmed_flag": "Optional esearch returns PMIDs only; never auto-fill ADA numbers.",
        },
        "counts": {
            "kept_with_ada": len(kept),
            "skipped_no_ada": len(skipped),
            "tier_A": len(tier_a),
            "tier_B": len(tier_b),
            "tier_C": len(tier_c),
            "needs_retrieval": len(need),
        },
    }

    def dump(name: str, antibodies: list) -> Path:
        p = args.out_dir / name
        with p.open("w", encoding="utf-8") as f:
            json.dump({"metadata": meta, "antibodies": antibodies}, f, ensure_ascii=False, indent=2)
        return p

    dump("ada_curated_all_with_ada.json", kept)
    dump("ada_curated_tier_A.json", tier_a)
    dump("ada_curated_tier_B.json", tier_b)
    dump("ada_curated_tier_C_needs_work.json", tier_c)
    dump("ada_curated_needs_retrieval.json", need)
    with (args.out_dir / "ada_skipped_no_ada.json").open("w", encoding="utf-8") as f:
        json.dump({"metadata": meta, "skipped": skipped}, f, ensure_ascii=False, indent=2)

    print(json.dumps(meta["counts"], indent=2))
    print(f"Output directory: {args.out_dir}")


if __name__ == "__main__":
    main()
