"""
PubMed eutils client — esearch + efetch with rate limiting and retry.

Endpoints used
--------------
  esearch.fcgi  : query → list of PMIDs
  efetch.fcgi   : PMIDs → full XML records (authors, title, journal, year,
                  volume, issue, pages, DOI, abstract, MeSH)

Rate limits
-----------
  Without API key: 3 requests / second
  With API key:    10 requests / second
  Set NCBI_API_KEY in env to enable the higher tier.

Anti-hallucination contract
---------------------------
  Every record returned by this module is sourced from a real NCBI
  HTTP response.  The caller (verify.py) must still cross-check that
  the record actually matches the topic phrase Claude requested.
"""

from __future__ import annotations

import os
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

import requests

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_API_KEY = os.environ.get("NCBI_API_KEY", "").strip()
_TOOL    = os.environ.get("NCBI_TOOL", "insynbio_writing_memory")
_EMAIL   = os.environ.get("NCBI_EMAIL", "support@insynbio.com")
_TIMEOUT = float(os.environ.get("NCBI_TIMEOUT", "30"))

# Rate limit: token bucket
_MIN_INTERVAL = 1.0 / 10.0 if _API_KEY else 1.0 / 3.0
_last_call    = 0.0
_lock         = Lock()


def _throttle() -> None:
    global _last_call
    with _lock:
        now = time.monotonic()
        wait = _MIN_INTERVAL - (now - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()


def _common_params() -> dict[str, str]:
    p = {"tool": _TOOL, "email": _EMAIL}
    if _API_KEY:
        p["api_key"] = _API_KEY
    return p


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class PubMedRecord:
    """Real PubMed record. Every field came from an NCBI HTTP response."""

    pmid:     str
    title:    str = ""
    abstract: str = ""
    authors:  list[tuple[str, str]] = field(default_factory=list)  # (last, initials)
    year:     int | None = None
    journal:  str = ""             # full title
    journal_abbrev: str = ""       # NLM TA (e.g. "Proc Natl Acad Sci U S A")
    volume:   str | None = None
    issue:    str | None = None
    pages:    str | None = None
    doi:      str | None = None
    pmcid:    str | None = None
    pub_types: list[str] = field(default_factory=list)
    mesh:      list[str] = field(default_factory=list)
    affiliations: list[str] = field(default_factory=list)
    retrieved_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "pmid":           self.pmid,
            "title":          self.title,
            "abstract":       self.abstract,
            "authors":        [{"last": a, "initials": i} for a, i in self.authors],
            "year":           self.year,
            "journal":        self.journal,
            "journal_abbrev": self.journal_abbrev,
            "volume":         self.volume,
            "issue":          self.issue,
            "pages":          self.pages,
            "doi":            self.doi,
            "pmcid":          self.pmcid,
            "pub_types":      self.pub_types,
            "mesh":           self.mesh,
            "retrieved_at":   self.retrieved_at,
        }


# ---------------------------------------------------------------------------
# esearch
# ---------------------------------------------------------------------------

def esearch(
    query:       str,
    max_results: int = 5,
    sort:        str = "relevance",
    year_min:    int | None = None,
    year_max:    int | None = None,
    work_type:   str | None = None,
) -> list[str]:
    """
    Query PubMed and return a list of PMIDs.

    `sort` accepts: "relevance" (default), "pub_date", "first_author".
    `year_min/year_max` add a date filter via the eutils mindate/maxdate API.
    """
    if not query.strip():
        return []

    term = query
    if work_type:
        # Map simple types to PubMed PT
        pt_map = {"article": "journal article", "review": "review", "book": "book"}
        pt = pt_map.get(work_type, work_type)
        term += f' AND "{pt}"[PT]'

    params = {
        **_common_params(),
        "db":         "pubmed",
        "term":       term,
        "retmax":     str(max_results),
        "retmode":    "json",
        "sort":       sort,
    }
    if year_min:
        params["mindate"] = str(year_min)
        params["datetype"] = "pdat"
    if year_max:
        params["maxdate"] = str(year_max)
        params["datetype"] = "pdat"

    _throttle()
    r = requests.get(ESEARCH, params=params, timeout=_TIMEOUT)
    r.raise_for_status()
    data = r.json()

    return data.get("esearchresult", {}).get("idlist", []) or []


# ---------------------------------------------------------------------------
# efetch (XML parsing)
# ---------------------------------------------------------------------------

def efetch(pmids: list[str]) -> list[PubMedRecord]:
    """Fetch full PubMed records for a list of PMIDs."""
    if not pmids:
        return []

    params = {
        **_common_params(),
        "db":      "pubmed",
        "id":      ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract",
    }

    _throttle()
    r = requests.get(EFETCH, params=params, timeout=_TIMEOUT)
    r.raise_for_status()

    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return []

    records: list[PubMedRecord] = []
    for art in root.findall(".//PubmedArticle"):
        rec = _parse_pubmed_article(art)
        if rec is not None:
            records.append(rec)
    return records


def _text(node: ET.Element | None) -> str:
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def _parse_pubmed_article(art: ET.Element) -> PubMedRecord | None:
    medline   = art.find(".//MedlineCitation")
    pubmed_d  = art.find(".//PubmedData")
    if medline is None:
        return None

    pmid_el = medline.find("./PMID")
    if pmid_el is None or not pmid_el.text:
        return None
    pmid = pmid_el.text.strip()

    article = medline.find("./Article")
    if article is None:
        return PubMedRecord(pmid=pmid, retrieved_at=_now())

    # Title
    title_el = article.find("./ArticleTitle")
    title = _strip_tags(title_el) if title_el is not None else ""

    # Abstract
    abstract_parts: list[str] = []
    for ab in article.findall("./Abstract/AbstractText"):
        label = ab.get("Label")
        text  = _strip_tags(ab)
        if text:
            abstract_parts.append(f"{label}: {text}" if label else text)
    abstract = " ".join(abstract_parts)

    # Authors + affiliations
    authors: list[tuple[str, str]] = []
    affiliations: list[str] = []
    for au in article.findall("./AuthorList/Author"):
        last = _text(au.find("./LastName"))
        ini  = _text(au.find("./Initials"))
        if last:
            authors.append((last, ini))
        for aff in au.findall("./AffiliationInfo/Affiliation"):
            txt = _strip_tags(aff) if aff is not None else ""
            if txt and txt not in affiliations:
                affiliations.append(txt)

    # Journal info
    journal       = _text(article.find("./Journal/Title"))
    journal_abbrev = _text(article.find("./Journal/ISOAbbreviation"))
    if not journal_abbrev:
        ja = medline.find("./MedlineJournalInfo/MedlineTA")
        journal_abbrev = _text(ja)

    # Year
    year: int | None = None
    for path in (
        "./Journal/JournalIssue/PubDate/Year",
        "./Journal/JournalIssue/PubDate/MedlineDate",
        "./ArticleDate/Year",
    ):
        el = article.find(path)
        if el is not None and el.text:
            m = re.search(r"(19|20)\d{2}", el.text)
            if m:
                year = int(m.group(0))
                break

    volume = _text(article.find("./Journal/JournalIssue/Volume")) or None
    issue  = _text(article.find("./Journal/JournalIssue/Issue"))  or None
    pages  = _text(article.find("./Pagination/MedlinePgn"))       or None

    # DOI + PMC
    doi: str | None = None
    pmcid: str | None = None
    for aid in article.findall("./ELocationID"):
        if (aid.get("EIdType") or "").lower() == "doi" and aid.text:
            doi = aid.text.strip()

    if pubmed_d is not None:
        for aid in pubmed_d.findall(".//ArticleId"):
            idtype = (aid.get("IdType") or "").lower()
            if idtype == "doi" and not doi and aid.text:
                doi = aid.text.strip()
            elif idtype == "pmc" and aid.text:
                pmcid = aid.text.strip()

    # Pub types
    pub_types = []
    for pt in article.findall("./PublicationTypeList/PublicationType"):
        if pt.text:
            pub_types.append(pt.text.strip())

    # MeSH
    mesh = []
    for mh in medline.findall("./MeshHeadingList/MeshHeading/DescriptorName"):
        if mh.text:
            mesh.append(mh.text.strip())

    return PubMedRecord(
        pmid=pmid,
        title=title,
        abstract=abstract,
        authors=authors,
        year=year,
        journal=journal,
        journal_abbrev=journal_abbrev,
        volume=volume,
        issue=issue,
        pages=pages,
        doi=doi,
        pmcid=pmcid,
        pub_types=pub_types,
        mesh=mesh,
        affiliations=affiliations,
        retrieved_at=_now(),
    )


def _strip_tags(node: ET.Element) -> str:
    """ArticleTitle / AbstractText can contain <i>, <sup>, etc. — flatten them."""
    if node is None:
        return ""
    parts: list[str] = []
    if node.text:
        parts.append(node.text)
    for child in node:
        parts.append(_strip_tags(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts).strip()


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Convenience: full search
# ---------------------------------------------------------------------------

def search_and_fetch(
    query:       str,
    max_results: int = 5,
    year_min:    int | None = None,
    year_max:    int | None = None,
    work_type:   str | None = None,
) -> list[PubMedRecord]:
    """Convenience: esearch then efetch in one call. Returns full records."""
    pmids = esearch(query, max_results=max_results, year_min=year_min, year_max=year_max, work_type=work_type)
    if not pmids:
        return []
    return efetch(pmids)


# ---------------------------------------------------------------------------
# Reverse verification helper: PMID → re-fetch
# ---------------------------------------------------------------------------

def fetch_by_pmid(pmid: str) -> PubMedRecord | None:
    """
    Reverse lookup: given a claimed PMID, fetch the canonical record so the
    caller can compare title/authors/year against what Claude claimed.
    """
    if not re.fullmatch(r"\d{4,}", pmid.strip()):
        return None
    recs = efetch([pmid.strip()])
    return recs[0] if recs else None
