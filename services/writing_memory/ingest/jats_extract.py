"""
JATS XML section extractor for the Writing Memory MVP.

Inputs : raw PMC JATS XML bytes (from efetch db=pmc retmode=xml)
Outputs: dict with title, abstract, discussion, conclusion, figure_legends,
         and a sections_available map.

Design notes
------------
- We deliberately keep this extractor specific to **PNAS, eLife, and PLOS
  Medicine**. A universal JATS parser is out of scope for the MVP.
- We do not attempt to repair missing sections. If a section is absent, the
  field is None and `sections_available[section] == False`.
- We do not strip <xref> markers; downstream embedding code should call
  `strip_inline_refs()` if needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from lxml import etree


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _local(tag) -> str:
    if not isinstance(tag, str):
        return ""
    return tag.split("}", 1)[1] if "}" in tag else tag


def _itertext(elem: etree._Element) -> str:
    parts: list[str] = []
    for piece in elem.itertext():
        if piece:
            parts.append(piece)
    return " ".join("".join(parts).split())


def _first(elem: etree._Element, local_name: str) -> etree._Element | None:
    for child in elem.iter():
        if _local(child.tag) == local_name:
            return child
    return None


def _all(elem: etree._Element, local_name: str) -> list[etree._Element]:
    return [c for c in elem.iter() if _local(c.tag) == local_name]


def _section_title(sec: etree._Element) -> str:
    t = _first(sec, "title")
    if t is None:
        return ""
    return _itertext(t).strip().lower()


def _section_type(sec: etree._Element) -> str:
    return (sec.get("sec-type") or "").strip().lower()


def _section_is(sec: etree._Element, keywords: Iterable[str]) -> bool:
    typ = _section_type(sec)
    title = _section_title(sec)
    for k in keywords:
        k = k.lower()
        if k in typ or k == title or k in title:
            return True
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass
class JatsArticle:
    pmid: str | None = None
    pmcid: str | None = None
    doi: str | None = None
    journal: str | None = None
    year: int | None = None
    title: str | None = None
    abstract: str | None = None
    discussion: str | None = None
    conclusion: str | None = None
    figure_legends: list[str] = field(default_factory=list)
    sections_available: dict[str, bool] = field(default_factory=dict)
    text_provenance: str = "pmc_jats"


def extract(xml_bytes: bytes) -> JatsArticle:
    art = JatsArticle()
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError:
        art.sections_available = {
            "abstract": False, "discussion": False,
            "conclusion": False, "figure_legends": False,
        }
        return art

    # ---- IDs ---------------------------------------------------------------
    for aid in _all(root, "article-id"):
        idtype = (aid.get("pub-id-type") or "").lower()
        val = (aid.text or "").strip()
        if not val:
            continue
        if idtype == "pmid":
            art.pmid = val
        elif idtype == "pmc":
            art.pmcid = val if val.startswith("PMC") else f"PMC{val}"
        elif idtype == "doi":
            art.doi = val

    # ---- Journal / year ----------------------------------------------------
    jtitle = _first(root, "journal-title")
    if jtitle is not None:
        art.journal = _itertext(jtitle)

    for pubdate in _all(root, "pub-date"):
        y = _first(pubdate, "year")
        if y is not None and y.text and y.text.strip().isdigit():
            art.year = int(y.text.strip())
            break

    # ---- Title -------------------------------------------------------------
    title_group = _first(root, "title-group")
    if title_group is not None:
        atit = _first(title_group, "article-title")
        if atit is not None:
            art.title = _itertext(atit)

    # ---- Abstract ----------------------------------------------------------
    # Prefer the first <abstract> without abstract-type (i.e., the main one).
    abstracts = _all(root, "abstract")
    main_abs = None
    for a in abstracts:
        if not (a.get("abstract-type") or "").strip():
            main_abs = a
            break
    if main_abs is None and abstracts:
        main_abs = abstracts[0]
    if main_abs is not None:
        text = _itertext(main_abs)
        art.abstract = text if text else None

    # ---- Body sections -----------------------------------------------------
    body = _first(root, "body")
    if body is not None:
        disc_parts: list[str] = []
        concl_parts: list[str] = []

        for sec in _all(body, "sec"):
            if _section_is(sec, ("discussion",)):
                # Avoid descending into a nested conclusion sub-section twice
                disc_parts.append(_itertext(sec))
            elif _section_is(sec, ("conclusion", "conclusions")):
                concl_parts.append(_itertext(sec))

        if disc_parts:
            art.discussion = "\n\n".join(disc_parts)
        if concl_parts:
            art.conclusion = "\n\n".join(concl_parts)

    # ---- Figure legends ----------------------------------------------------
    for fig in _all(root, "fig"):
        cap = _first(fig, "caption")
        if cap is None:
            continue
        cap_text = _itertext(cap)
        if cap_text:
            art.figure_legends.append(cap_text)

    art.sections_available = {
        "abstract": bool(art.abstract),
        "discussion": bool(art.discussion),
        "conclusion": bool(art.conclusion),
        "figure_legends": bool(art.figure_legends),
    }
    return art


# ---------------------------------------------------------------------------
# Optional utilities
# ---------------------------------------------------------------------------

def strip_inline_refs(text: str) -> str:
    """Remove obvious inline citation markers like (1, 2) / [3,4] from text.

    Useful before embedding so similarity is driven by phrasing, not citation
    densities. Intentionally conservative: only removes patterns very likely
    to be citation tokens.
    """
    import re
    s = re.sub(r"\(\s*\d+(?:\s*[,\-\u2013]\s*\d+)*\s*\)", " ", text)
    s = re.sub(r"\[\s*\d+(?:\s*[,\-\u2013]\s*\d+)*\s*\]", " ", s)
    return re.sub(r"\s+", " ", s).strip()
