"""
Module 4 — literature/patent library import, export, and formatted bibliography.

Reuses open formats (RIS, BibTeX, CSL-JSON) and journal_specs reference styles (OSS profiles).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .reference_exporter import to_bibtex, to_csl_json, to_ris
    from .reference_import import parse_references
    from .intelligence_store import doc_subproject, list_documents, save_document
except ImportError:
    from reference_exporter import to_bibtex, to_csl_json, to_ris  # type: ignore
    from reference_import import parse_references  # type: ignore
    from intelligence_store import doc_subproject, list_documents, save_document  # type: ignore

_STYLE_DIR = Path(__file__).resolve().parent / "journal_specs" / "reference_styles"


def list_reference_styles() -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if _STYLE_DIR.is_dir():
        for p in sorted(_STYLE_DIR.glob("*.json")):
            out.append({"id": p.stem, "label": p.stem.replace("_", " ").title()})
    return out


def _doc_to_ref(doc: dict[str, Any]) -> dict[str, Any]:
    src = doc.get("source") or "manual"
    raw = doc.get("raw")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}
    if not isinstance(raw, dict):
        raw = {}

    if src == "patent":
        return {
            "title": doc.get("title"),
            "authors": doc.get("authors") or raw.get("assignee"),
            "year": doc.get("year"),
            "journal": "Patent",
            "doi": None,
            "abstract": doc.get("abstract"),
            "patent_id": doc.get("patent_id"),
            "url": doc.get("url"),
            "_source": "patent",
        }

    venue = doc.get("venue") or raw.get("venue") or raw.get("journal") or ""
    src = doc.get("source") or raw.get("source") or "openalex"
    pmid = raw.get("pmid") or (doc.get("ext_id") if src == "pubmed" else None)
    return {
        "title": doc.get("title"),
        "authors": doc.get("authors") or raw.get("authors"),
        "journal": venue,
        "year": doc.get("year") or raw.get("year"),
        "volume": raw.get("volume"),
        "issue": raw.get("issue"),
        "pages": raw.get("pages"),
        "doi": doc.get("doi") or raw.get("doi"),
        "abstract": doc.get("abstract") or raw.get("abstract"),
        "pmid": pmid,
        "url": doc.get("url") or raw.get("url"),
        "_source": src,
    }


def _patent_ris_block(r: dict[str, Any]) -> str:
    lines = ["TY  - PAT", f"TI  - {r.get('title') or 'Untitled'}"]
    if r.get("authors"):
        for a in str(r["authors"]).split(";"):
            a = a.strip()
            if a:
                lines.append(f"AU  - {a}")
    if r.get("year"):
        lines.append(f"PY  - {r['year']}/")
    if r.get("patent_id"):
        lines.append(f"AN  - US{r['patent_id']}")
    if r.get("url"):
        lines.append(f"UR  - {r['url']}")
    if r.get("abstract"):
        lines.append(f"AB  - {str(r['abstract'])[:1500]}")
    lines.append("ER  - ")
    return "\n".join(lines)


def _export_refs_to_body(refs: list[dict[str, Any]], fmt: str) -> tuple[str, str, int, int]:
    lit_refs = [r for r in refs if r.get("_source") != "patent"]
    pat_refs = [r for r in refs if r.get("_source") == "patent"]
    f = (fmt or "ris").lower()
    if f == "ris":
        body = to_ris(lit_refs)
        if pat_refs:
            pat_blocks = "\n\n".join(_patent_ris_block(p) for p in pat_refs)
            body = (body + "\n\n" + pat_blocks).strip() if body else pat_blocks
    elif f in ("bib", "bibtex"):
        body = to_bibtex(lit_refs)
        if pat_refs:
            body += "\n\n% --- patents (add manually to BibTeX as @patent if needed) ---\n"
            for p in pat_refs:
                body += f"% US{p.get('patent_id')} {p.get('title')}\n"
    elif f in ("csl", "csl-json", "json"):
        body = to_csl_json(lit_refs)
    else:
        raise ValueError(f"Unsupported export format: {fmt}")
    ext = "bib" if f.startswith("bib") else ("json" if "csl" in f else "ris")
    return body, f, len(lit_refs), len(pat_refs)


def _select_docs(
    project_id: str | None,
    *,
    source_filter: str | None = None,
    document_ids: list[int] | None = None,
    subproject: str | None = None,
) -> list[dict[str, Any]]:
    if document_ids:
        idset = {int(i) for i in document_ids}
        docs = [
            d for d in list_documents(project_id, limit=500)
            if d.get("id") is not None and int(d["id"]) in idset
        ]
    else:
        docs = list_documents(project_id, source=source_filter, limit=500, subproject=subproject)
    if source_filter and document_ids:
        docs = [d for d in docs if (d.get("source") or "") == source_filter]
    if subproject and document_ids:
        if subproject == "__none__":
            docs = [d for d in docs if not doc_subproject(d)]
        else:
            docs = [d for d in docs if doc_subproject(d) == subproject]
    return docs


def export_documents(
    project_id: str | None,
    fmt: str,
    *,
    source_filter: str | None = None,
    document_ids: list[int] | None = None,
    subproject: str | None = None,
) -> dict[str, Any]:
    docs = _select_docs(
        project_id,
        source_filter=source_filter,
        document_ids=document_ids,
        subproject=subproject,
    )

    refs = [_doc_to_ref(d) for d in docs]
    body, f, n_lit, n_pat = _export_refs_to_body(refs, fmt)
    suffix = "batch" if document_ids else "library"

    return {
        "format": f,
        "content": body,
        "count": len(docs),
        "literature_count": n_lit,
        "patent_count": n_pat,
        "batch": bool(document_ids),
        "filename": f"intelligence_{suffix}_{f.replace('-', '_')}.{ 'bib' if f.startswith('bib') else ('json' if 'csl' in f else 'ris')}",
    }


def import_records(
    project_id: str | None,
    format: str,
    content: str,
) -> dict[str, Any]:
    records = parse_references(format, content)
    saved = 0
    updated = 0
    errors: list[str] = []
    for i, rec in enumerate(records):
        try:
            src = rec.pop("source", "manual")
            res = save_document(project_id, src, rec)
            if res.get("inserted"):
                saved += 1
            elif res.get("id"):
                updated += 1
        except Exception as exc:
            errors.append(f"row {i + 1}: {exc}")
    return {
        "ok": len(errors) == 0,
        "parsed": len(records),
        "saved": saved,
        "updated": updated,
        "errors": errors[:10],
    }


def format_bibliography(
    project_id: str | None,
    style_id: str,
    *,
    literature_only: bool = True,
    document_ids: list[int] | None = None,
    subproject: str | None = None,
) -> dict[str, Any]:
    try:
        from .journal_specs.format_reference import Author, Paper, format_reference, load_style
    except ImportError:
        from journal_specs.format_reference import Author, Paper, format_reference, load_style  # type: ignore

    style = load_style(style_id)
    docs = _select_docs(project_id, document_ids=document_ids, subproject=subproject)
    lines: list[str] = []
    n = 0
    for doc in docs:
        if literature_only and (doc.get("source") or "") not in ("openalex", "pubmed", "manual"):
            continue
        ref = _doc_to_ref(doc)
        names = [x.strip() for x in str(ref.get("authors") or "").replace(";", ",").split(",") if x.strip()]
        authors: list[Author] = []
        for name in names:
            toks = name.split()
            if len(toks) >= 2:
                authors.append(Author(last=toks[-1], initials="".join(t[0] for t in toks[:-1])))
            elif toks:
                authors.append(Author(last=toks[0], initials=""))
        paper = Paper(
            authors=authors,
            title=ref.get("title") or "",
            journal=ref.get("journal") or "",
            year=int(ref["year"]) if ref.get("year") else None,
            volume=ref.get("volume"),
            issue=ref.get("issue"),
            pages=ref.get("pages"),
            doi=ref.get("doi"),
            pmid=ref.get("pmid"),
        )
        n += 1
        lines.append(format_reference(paper, style, index=n))

    patent_lines: list[str] = []
    if not literature_only:
        pn = 0
        for doc in docs:
            if doc.get("source") != "patent":
                continue
            pn += 1
            ref = _doc_to_ref(doc)
            patent_lines.append(
                f"{pn}. {ref.get('title') or 'Untitled'}. "
                f"US Patent {ref.get('patent_id') or '—'}. "
                f"{ref.get('year') or ''}."
            )

    body = "\n\n".join(lines + patent_lines)
    suffix = "batch" if document_ids else ("sub" if subproject else "all")
    return {
        "style_id": style_id,
        "references": lines,
        "patent_references": patent_lines,
        "count": n,
        "content": body,
        "filename": f"references_{style_id}_{suffix}.txt",
        "subproject": subproject,
    }
