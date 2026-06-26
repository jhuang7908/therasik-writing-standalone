"""
Parse RIS and BibTeX (open formats) into normalized reference records.

Used by Module 4 intelligence library import (Zotero / EndNote / Mendeley compatible).
No external dependencies — line-oriented parsers.
"""
from __future__ import annotations

import re
from typing import Any


def _split_ris_records(text: str) -> list[str]:
    chunks: list[str] = []
    buf: list[str] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.strip().upper() == "ER  -" or line.strip().upper() == "ER -":
            buf.append(line)
            if buf:
                chunks.append("\n".join(buf))
            buf = []
        else:
            buf.append(line)
    if buf:
        chunks.append("\n".join(buf))
    return [c for c in chunks if c.strip()]


def _parse_ris_record(block: str) -> dict[str, Any] | None:
    ty = ""
    fields: dict[str, list[str]] = {}
    for line in block.split("\n"):
        if "  - " not in line:
            continue
        tag, val = line.split("  - ", 1)
        tag = tag.strip().upper()
        val = val.strip()
        if tag == "TY":
            ty = val.upper()
        else:
            fields.setdefault(tag, []).append(val)
    title = (fields.get("TI") or fields.get("T1") or [""])[0]
    if not title and ty not in ("PAT", "GEN", "UNPB"):
        return None
    authors = fields.get("AU", []) + fields.get("A1", [])
    journal = (fields.get("JO") or fields.get("JF") or fields.get("T2") or [""])[0]
    year_raw = (fields.get("PY") or fields.get("Y1") or [""])[0]
    year = None
    if year_raw:
        m = re.search(r"\d{4}", year_raw)
        if m:
            year = int(m.group())
    pages = (fields.get("SP") or [""])[0]
    if fields.get("EP"):
        ep = fields["EP"][0]
        pages = f"{pages}-{ep}" if pages else ep
    doi = (fields.get("DO") or [""])[0]
    if doi.startswith("http"):
        doi = doi.split("doi.org/")[-1].split("?")[0]
    abstract = (fields.get("AB") or [""])[0]
    patent_id = (fields.get("AN") or fields.get("M1") or [""])[0]
    assignee = (fields.get("AU") or [""])[0] if ty == "PAT" else ""

    if ty == "PAT":
        return {
            "source": "patent",
            "title": title or f"Patent {patent_id}",
            "authors": assignee,
            "assignee": assignee,
            "year": year,
            "patent_id": re.sub(r"\D", "", patent_id) if patent_id else None,
            "abstract": abstract or None,
            "doi": None,
            "journal": "",
            "url": (fields.get("UR") or [None])[0],
            "verification_status": "user-provided",
        }

    return {
        "source": "manual",
        "title": title,
        "authors": "; ".join(authors) if authors else None,
        "journal": journal,
        "year": year,
        "volume": (fields.get("VL") or [""])[0] or None,
        "issue": (fields.get("IS") or [""])[0] or None,
        "pages": pages or None,
        "doi": doi or None,
        "abstract": abstract or None,
        "pmid": (fields.get("AN") or [""])[0] if (fields.get("AN") or [""])[0].isdigit() else None,
        "url": (fields.get("UR") or [None])[0],
        "openalex_id": doi or (fields.get("UR") or [""])[0],
        "verification_status": "user-provided",
    }


def parse_ris(text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for block in _split_ris_records(text):
        rec = _parse_ris_record(block)
        if rec:
            records.append(rec)
    return records


def _parse_bibtex_entries(text: str) -> list[dict[str, Any]]:
    """Minimal @type{key, ...} parser."""
    records: list[dict[str, Any]] = []
    pattern = re.compile(r"@(\w+)\s*\{\s*([^,]+)\s*,", re.I)
    pos = 0
    while True:
        m = pattern.search(text, pos)
        if not m:
            break
        entry_type = m.group(1).lower()
        start = m.end()
        depth = 1
        i = start
        while i < len(text) and depth > 0:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        body = text[start : i - 1]
        pos = i
        fields: dict[str, str] = {}
        for fm in re.finditer(r"(\w+)\s*=\s*(\{[^{}]*\}|\"[^\"]*\"|[^,\n]+)", body, re.I):
            key = fm.group(1).lower()
            val = fm.group(2).strip().strip("{}").strip('"').strip()
            fields[key] = val
        title = fields.get("title", "")
        if not title:
            continue
        authors = fields.get("author", "")
        year = None
        if fields.get("year"):
            ym = re.search(r"\d{4}", fields["year"])
            if ym:
                year = int(ym.group())
        doi = fields.get("doi", "").replace("https://doi.org/", "")
        if entry_type in ("patent", "misc") and fields.get("howpublished", "").lower().find("patent") >= 0:
            records.append({
                "source": "patent",
                "title": title,
                "assignee": authors,
                "authors": authors,
                "year": year,
                "patent_id": fields.get("number"),
                "abstract": fields.get("abstract"),
                "verification_status": "user-provided",
            })
        else:
            records.append({
                "source": "manual",
                "title": title,
                "authors": authors,
                "journal": fields.get("journal", ""),
                "year": year,
                "volume": fields.get("volume"),
                "pages": fields.get("pages"),
                "doi": doi or None,
                "abstract": fields.get("abstract"),
                "openalex_id": doi,
                "verification_status": "user-provided",
            })
    return records


def parse_bibtex(text: str) -> list[dict[str, Any]]:
    return _parse_bibtex_entries(text)


def parse_references(format: str, content: str) -> list[dict[str, Any]]:
    fmt = (format or "").strip().lower()
    if fmt in ("ris", "endnote", "wos"):
        return parse_ris(content)
    if fmt in ("bib", "bibtex", "latex"):
        return parse_bibtex(content)
    raise ValueError(f"Unsupported import format: {format}")
