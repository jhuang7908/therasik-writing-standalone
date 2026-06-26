"""
Reference exporter — converts internal reference records to
RIS, BibTeX, and CSL-JSON formats for Zotero / EndNote import.

All three formats can be served as file downloads or returned as strings.

Public API:
    to_ris(refs)        -> str   (RIS format)
    to_bibtex(refs)     -> str   (BibTeX format)
    to_csl_json(refs)   -> str   (CSL-JSON array)
    to_zotero_ris(refs) -> str   (RIS with Zotero TY tags)
    export_bundle(refs, title) -> dict[format -> str]

Input ref schema (each dict):
    pmid, title, authors (list[str]), journal, year, volume, issue,
    pages, doi, abstract (optional)
"""
from __future__ import annotations

import json
import re
from typing import Any


def _safe(v: Any, fallback: str = "") -> str:
    return str(v).strip() if v else fallback


def _sanitize_bibtex_key(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "", s)


def _ensure_author_list(authors: list[str] | str | None) -> list[str]:
    if not authors:
        return []
    if isinstance(authors, str):
        # Split by common delimiters
        return [a.strip() for a in re.split(r"[,;]\s*", authors) if a.strip()]
    return [str(a).strip() for a in authors if a]


def _ris_author_lines(authors: list[str] | str | None) -> list[str]:
    author_list = _ensure_author_list(authors)
    return [f"AU  - {a}" for a in author_list]


def _bibtex_escape(s: str) -> str:
    """Minimal BibTeX-safe escaping."""
    return s.replace("{", r"\{").replace("}", r"\}").replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("^", r"\^").replace("~", r"\~")


# ─── RIS ──────────────────────────────────────────────────────────────────────

def to_ris(refs: list[dict[str, Any]]) -> str:
    """
    Standard RIS format. Importable by Zotero, Mendeley, EndNote, RefWorks.
    TY JOUR = journal article.
    """
    blocks: list[str] = []
    for r in refs:
        lines = ["TY  - JOUR"]
        lines.append(f"TI  - {_safe(r.get('title'))}")
        lines.extend(_ris_author_lines(r.get("authors")))
        lines.append(f"JO  - {_safe(r.get('journal'))}")
        if r.get("year"):
            lines.append(f"PY  - {_safe(r.get('year'))}/")
        if r.get("volume"):
            lines.append(f"VL  - {_safe(r.get('volume'))}")
        if r.get("issue"):
            lines.append(f"IS  - {_safe(r.get('issue'))}")
        if r.get("pages"):
            # Split pages into SP/EP if range given
            pages = _safe(r.get("pages"))
            if "-" in pages:
                parts = pages.split("-", 1)
                lines.append(f"SP  - {parts[0].strip()}")
                lines.append(f"EP  - {parts[1].strip()}")
            else:
                lines.append(f"SP  - {pages}")
        if r.get("doi"):
            lines.append(f"DO  - {_safe(r.get('doi'))}")
        if r.get("pmid"):
            lines.append(f"AN  - {_safe(r.get('pmid'))}")
            lines.append(f"UR  - https://pubmed.ncbi.nlm.nih.gov/{_safe(r.get('pmid'))}/")
        if r.get("abstract"):
            # RIS AB field — trim to reasonable length
            ab = _safe(r.get("abstract"))[:2000].replace("\n", " ")
            lines.append(f"AB  - {ab}")
        lines.append("ER  - ")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


# ─── BibTeX ───────────────────────────────────────────────────────────────────

def to_bibtex(refs: list[dict[str, Any]]) -> str:
    """
    BibTeX format. Importable by Zotero, Overleaf/LaTeX, JabRef.
    """
    entries: list[str] = []
    used_keys: set[str] = set()
    for i, r in enumerate(refs, start=1):
        # Build citation key: FirstAuthorLastYear
        authors = _ensure_author_list(r.get("authors"))
        first_author = ""
        if authors:
            last_name = authors[0].split(",")[0].split()[-1] if authors[0] else ""
            first_author = _sanitize_bibtex_key(last_name.lower())
        year = _safe(r.get("year"), "0000")
        base_key = f"{first_author}{year}" or f"ref{i}"
        key = base_key
        suffix = "a"
        while key in used_keys:
            key = base_key + suffix
            suffix = chr(ord(suffix) + 1)
        used_keys.add(key)

        fields: list[str] = []
        if r.get("title"):
            fields.append(f"  title = {{{_bibtex_escape(_safe(r.get('title')))}}}") 
        if authors:
            auth_str = " and ".join(_safe(a) for a in authors[:10])
            fields.append(f"  author = {{{_bibtex_escape(auth_str)}}}")
        if r.get("journal"):
            fields.append(f"  journal = {{{_bibtex_escape(_safe(r.get('journal')))}}}") 
        if r.get("year"):
            fields.append(f"  year = {{{year}}}")
        if r.get("volume"):
            fields.append(f"  volume = {{{_safe(r.get('volume'))}}}")
        if r.get("issue"):
            fields.append(f"  number = {{{_safe(r.get('issue'))}}}")
        if r.get("pages"):
            fields.append(f"  pages = {{{_safe(r.get('pages')).replace('--', '--')}}}")
        if r.get("doi"):
            fields.append(f"  doi = {{{_safe(r.get('doi'))}}}")
        if r.get("pmid"):
            fields.append(f"  pmid = {{{_safe(r.get('pmid'))}}}")

        entries.append(f"@article{{{key},\n" + ",\n".join(fields) + "\n}")
    return "\n\n".join(entries)


# ─── CSL-JSON ─────────────────────────────────────────────────────────────────

def to_csl_json(refs: list[dict[str, Any]]) -> str:
    """
    CSL-JSON format. Native Zotero export format; used by citeproc-py.
    Importable by Zotero via "Import from clipboard".
    """
    csl_items: list[dict[str, Any]] = []
    for i, r in enumerate(refs, start=1):
        item: dict[str, Any] = {
            "id": r.get("pmid") or f"ref-{i}",
            "type": "article-journal",
            "title": _safe(r.get("title")),
        }
        authors = r.get("authors") or []
        if authors:
            item["author"] = []
            for a in authors:
                a = a.strip()
                if "," in a:
                    parts = a.split(",", 1)
                    item["author"].append({"family": parts[0].strip(), "given": parts[1].strip()})
                elif " " in a:
                    parts = a.rsplit(" ", 1)
                    item["author"].append({"family": parts[-1], "given": parts[0]})
                else:
                    item["author"].append({"literal": a})
        if r.get("journal"):
            item["container-title"] = _safe(r.get("journal"))
        if r.get("year"):
            item["issued"] = {"date-parts": [[int(_safe(r.get("year"), "0"))]]}
        if r.get("volume"):
            item["volume"] = _safe(r.get("volume"))
        if r.get("issue"):
            item["issue"] = _safe(r.get("issue"))
        if r.get("pages"):
            item["page"] = _safe(r.get("pages"))
        if r.get("doi"):
            item["DOI"] = _safe(r.get("doi"))
        if r.get("pmid"):
            item["PMID"] = _safe(r.get("pmid"))
        if r.get("abstract"):
            item["abstract"] = _safe(r.get("abstract"))[:1200]
        csl_items.append(item)
    return json.dumps(csl_items, indent=2, ensure_ascii=False)


# ─── Bundle ───────────────────────────────────────────────────────────────────

def export_bundle(
    refs: list[dict[str, Any]],
    manuscript_title: str = "manuscript",
) -> dict[str, Any]:
    """
    Return all three export formats as a dict.
    Each value is a string ready for file download.
    """
    return {
        "ris": to_ris(refs),
        "bib": to_bibtex(refs),
        "csl_json": to_csl_json(refs),
        "count": len(refs),
        "manuscript_title": manuscript_title,
        "zotero_instructions": (
            "To import into Zotero: File → Import → choose the .ris or .bib file. "
            "Then install the Zotero Word Plugin (zotero.org/support/word_processor_plugin) "
            "to insert and auto-format citations by journal style — identical to EndNote workflow."
        ),
    }


__all__ = ["to_ris", "to_bibtex", "to_csl_json", "export_bundle"]
