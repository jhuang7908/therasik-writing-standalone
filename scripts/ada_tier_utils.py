"""Shared Tier A/B/C rules for ADA evidence (PMID / FDA label / ClinicalTrials vs other https)."""

from __future__ import annotations

import re
from typing import Any

URL_RE = re.compile(r"https?://[^\s\)\]\"']+", re.I)
PMID_IN_TEXT = re.compile(r"PMID[:\s]+(\d+)", re.I)
PUBMED_URL_PMID = re.compile(r"pubmed\.ncbi.nlm.nih\.gov/(\d{6,9})(?:/|\?|$)", re.I)
WEAK_VALUE_PATTERN = re.compile(
    r"^\s*(n/?a|not\s+available|unknown|not\s+reported|no\s+data)\s*$",
    re.I,
)
QUALITATIVE_ADA_PATTERN = re.compile(
    r"(no\s+treatment[- ]emergent|not\s+observed|none\s+observed|without\s+detectable|"
    r"below\s+(the\s+)?detection|undetectable\s+ada|very\s+limited\s+immunogenicity)",
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


def pmids_from_record(ab: dict[str, Any], citation_urls: list[str] | None = None) -> list[str]:
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
    v = (ada_value or "").strip()
    if not v:
        return False
    if WEAK_VALUE_PATTERN.match(v):
        return False
    return True


def ada_status_class(ada_value: str) -> str:
    if not has_reported_ada(ada_value):
        return "unreported"
    if QUALITATIVE_ADA_PATTERN.search(ada_value or ""):
        return "qualitative_immunogenicity"
    return "incidence_reported"


def tier_a_anchor(urls: list[str], pmids: list[str]) -> str:
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


def evidence_tier_for_record(ab: dict[str, Any]) -> tuple[str, list[str], str]:
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


def effective_tier_for_index(
    ada_value: str, ab: dict[str, Any]
) -> tuple[str, list[str], str, str]:
    """
    Returns (tier, urls, notes, ada_status).
    No usable ADA text -> tier C, unreported.
    """
    status = ada_status_class(ada_value)
    if status == "unreported":
        chain = ab.get("evidence_chain") or ""
        urls = extract_urls(chain)
        su = (ab.get("source_url") or "").strip()
        if su.startswith("http"):
            urls = [su] + [u for u in urls if u != su]
            urls = list(dict.fromkeys(urls))
        return "C", urls, "catalog_entry_no_ada_value", status
    t, urls, notes = evidence_tier_for_record(ab)
    return t, urls, notes, status


def inn_slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (name or "").strip().lower()).strip("_")
    return s or "unknown"
