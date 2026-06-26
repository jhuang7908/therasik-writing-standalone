"""
format_reference -- deterministic reference renderer.

This module is intentionally rule-based, not LLM-driven. Every reference
shown to a user must pass through here so that:

1. The output format is reproducible.
2. Inputs are tied to a real corpus row (a `Paper` dataclass populated from
   the `papers` table or from a PubMed `esummary` payload).
3. The LLM never composes citation text directly.

Usage
-----

    from services.writing_memory.journal_specs.format_reference import (
        Paper, Author, load_style, format_reference,
    )

    paper = Paper(
        authors=[Author("Smith","JA"), Author("Jones","B"), Author("Lee","CK")],
        title="A novel mechanism of antibody clearance",
        journal="Proc Natl Acad Sci U S A",
        year=2024, volume="121", issue="3", pages="e2401234121",
        doi="10.1073/pnas.2401234121",
        pmid="40123456", pmcid="PMC10987654",
    )

    style = load_style("pnas_numbered")          # reads reference_styles/pnas_numbered.json
    rendered = format_reference(paper, style, index=7)
    # -> "7. Smith JA, Jones B, Lee CK. ... Proc Natl Acad Sci U S A. 2024;121(3):e2401234121. doi:10.1073/pnas.2401234121"

The rendered string is deterministic. If the underlying style is still
marked verification_status == 'unverified', the API layer must refuse to
show the rendered string to clients (or display it with a warning).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Input model
# ---------------------------------------------------------------------------

@dataclass
class Author:
    last:     str
    initials: str = ""

    def render_last_initials(self) -> str:
        ini = "".join(c for c in self.initials.replace(".", "").replace(" ", "") if c)
        return f"{self.last} {ini}".strip()


@dataclass
class Paper:
    authors:  list[Author] = field(default_factory=list)
    title:    str = ""
    journal:  str = ""
    year:     int | None = None
    volume:   str | None = None
    issue:    str | None = None
    pages:    str | None = None
    doi:      str | None = None
    pmid:     str | None = None
    pmcid:    str | None = None
    url:      str | None = None
    preprint_server: str | None = None  # e.g. "bioRxiv"


# ---------------------------------------------------------------------------
# Style loading
# ---------------------------------------------------------------------------

_STYLE_DIR = Path(__file__).resolve().parent / "reference_styles"


def load_style(style_id: str) -> dict[str, Any]:
    path = _STYLE_DIR / f"{style_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Unknown reference style id: {style_id}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def style_is_verified(style: dict[str, Any]) -> bool:
    """A style is considered safe for client-facing rendering only when ALL
    three top-level rule blocks are marked verified."""
    keys = ("in_text_citation", "list_order", "list_entry")
    return all(style.get(k, {}).get("verification_status") == "verified" for k in keys)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _render_author_list(authors: list[Author], style: dict[str, Any]) -> str:
    cfg = style["list_entry"]["author_list"]
    fmt = cfg.get("format", "last_initials")
    sep = cfg.get("separator", ", ")
    et_th = cfg.get("et_al_threshold")
    et_keep = cfg.get("et_al_keep_first")

    if not authors:
        return ""

    if fmt != "last_initials":
        # Only last_initials is implemented today; extend as styles are curated.
        raise NotImplementedError(f"Author format '{fmt}' not implemented yet.")

    rendered = [a.render_last_initials() for a in authors]
    if et_th and et_keep and len(rendered) > et_th:
        rendered = rendered[:et_keep] + ["et al."]

    return sep.join(rendered)


def _render_volume_issue_pages(p: Paper, style: dict[str, Any]) -> str:
    tmpl = style["list_entry"].get("volume_issue_pages_format")
    vol = p.volume or ""
    iss = p.issue or ""
    pages = p.pages or ""
    if tmpl == "Vol(Iss):Pages":
        out = vol
        if iss:
            out += f"({iss})"
        if pages:
            out += f":{pages}"
        return out
    # Default fallback: 'Vol(Iss):Pages' if values exist
    out = vol
    if iss:
        out += f"({iss})"
    if pages:
        out += f":{pages}"
    return out


def _render_doi(p: Paper, style: dict[str, Any]) -> str:
    if not p.doi:
        return ""
    fmt = style["list_entry"].get("doi_format") or "doi:10.xxxx/xxxx"
    if fmt.startswith("https://doi.org"):
        return f"https://doi.org/{p.doi}"
    return f"doi:{p.doi}"


def _render_in_text_for_doc(p: Paper, style: dict[str, Any], index: int | None) -> str:
    mode = style["in_text_citation"]["mode"]
    if mode == "numbered_parenthetical" and index is not None:
        return f"({index})"
    if mode == "numbered_bracketed" and index is not None:
        return f"[{index}]"
    if mode == "numbered_superscript" and index is not None:
        return f"^{index}"
    if mode in ("author_year_parenthetical", "author_year_narrative") and p.authors:
        first = p.authors[0].last
        year = p.year or "n.d."
        if len(p.authors) == 1:
            label = f"{first}, {year}"
        elif len(p.authors) == 2:
            label = f"{first} and {p.authors[1].last}, {year}"
        else:
            label = f"{first} et al., {year}"
        return f"({label})" if "parenthetical" in mode else label
    return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def format_in_text(paper: Paper, style: dict[str, Any], index: int | None = None) -> str:
    """Render the in-text citation only (e.g. '(1)' or '(Smith et al., 2024)')."""
    return _render_in_text_for_doc(paper, style, index)


def format_reference(paper: Paper, style: dict[str, Any], index: int | None = None) -> str:
    """Render one full reference-list entry as a single string.

    `index` is used when the style is numbered (by appearance); ignored for
    author-year styles.
    """
    parts: list[str] = []

    # Leading numeric label for numbered styles
    if style["list_order"]["mode"] == "by_appearance" and index is not None:
        parts.append(f"{index}.")

    authors = _render_author_list(paper.authors, style)
    if authors:
        parts.append(authors + ".")

    if paper.title:
        title = paper.title.rstrip(".")
        case = style["list_entry"].get("title_case", "sentence_case")
        if case == "sentence_case":
            # Conservative: keep as-is. True sentence-casing requires NLP-aware
            # rules that we don't apply automatically to avoid mangling
            # gene symbols, drug names, abbreviations, etc.
            pass
        parts.append(title + ".")

    if paper.journal:
        parts.append(paper.journal + ".")

    if paper.year:
        # Vancouver-style year before vol(iss):pages
        vip = _render_volume_issue_pages(paper, style)
        if vip:
            parts.append(f"{paper.year};{vip}.")
        else:
            parts.append(f"{paper.year}.")

    doi = _render_doi(paper, style)
    if doi:
        parts.append(doi)

    return " ".join(parts).strip()


def format_reference_list(papers: list[Paper], style: dict[str, Any]) -> list[str]:
    """Render an entire reference list in this style. Numbering is automatic
    for numbered styles, omitted for author-year styles."""
    out: list[str] = []
    is_numbered = style["list_order"]["mode"] == "by_appearance"

    if not is_numbered:
        ordered = sorted(papers, key=lambda p: ((p.authors[0].last if p.authors else "").lower(), p.year or 0))
        for p in ordered:
            out.append(format_reference(p, style, index=None))
        return out

    for i, p in enumerate(papers, start=1):
        out.append(format_reference(p, style, index=i))
    return out
