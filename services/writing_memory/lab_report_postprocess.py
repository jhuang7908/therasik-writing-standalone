"""
Post-process lab HTML reports: real figures, PMID-verified references.
"""

from __future__ import annotations

import html as html_lib
import re
from typing import Any


def strip_phantom_figure_markup(article_html: str) -> str:
    """Remove figure/caption placeholders that cite filenames without embedded images."""
    if not article_html:
        return article_html

    def _figure_repl(m: re.Match[str]) -> str:
        chunk = m.group(0)
        if re.search(r"<img\s", chunk, re.IGNORECASE):
            return chunk
        return ""

    out = re.sub(r"<figure[\s\S]*?</figure>", _figure_repl, article_html, flags=re.IGNORECASE)
    out = re.sub(
        r"<figcaption[^>]*>[\s\S]*?</figcaption>",
        "",
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r"<p>\s*Figure\s+\d+[^<]*\([^)]*\.(?:png|jpe?g|svg|csv|xlsx?)[^)]*\)[^<]*</p>",
        "",
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r"<p>\s*Figure\s+\d+[^<]*\b(?:curve|yield|data)\.(?:png|csv|xlsx?)\b[^<]*</p>",
        "",
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r"<p>\s*Figure\s+\d+[^<]{0,200}\.(?:png|jpe?g|svg|csv|xlsx?)[^<]*</p>",
        "",
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r"Figure\s+\d+\s*[\.\:][^<\n]{0,180}\([^)]*\.(?:png|jpe?g|svg|csv|xlsx?)[^)]*\)\s*\.?",
        "",
        out,
        flags=re.IGNORECASE,
    )
    return out


def _format_authors(authors: list[tuple[str, str]]) -> str:
    if not authors:
        return "Unknown"
    last, ini = authors[0]
    lead = f"{last} {ini}".strip() if ini else last
    if len(authors) == 1:
        return lead
    return f"{lead} et al."


def _format_citation(rec: Any, *, verdict: str, similarity: float, relevance: float | None = None) -> str:
    authors = _format_authors(getattr(rec, "authors", []) or [])
    title = (getattr(rec, "title", None) or "Untitled").strip()
    journal = (getattr(rec, "journal_abbrev", None) or getattr(rec, "journal", None) or "").strip()
    year = getattr(rec, "year", None)
    pmid = getattr(rec, "pmid", "") or ""
    yr = f" ({year})" if year else ""
    jpart = f" <em>{html_lib.escape(journal)}</em>" if journal else ""
    tag = verdict if verdict in ("verified", "partial", "unverified", "conflict") else "unverified"
    sim = f" · match={similarity:.2f}" if similarity else ""
    # Relevance label from keyword overlap (set by _lab_pubmed_for_report)
    rel_label = ""
    if relevance is not None:
        if relevance >= 0.4:
            rel_label = ' <span style="color:#1a7a1a;font-size:9pt" title="Keyword overlap with experiment topic">[relevance: high]</span>'
        elif relevance >= 0.2:
            rel_label = ' <span style="color:#8a6000;font-size:9pt" title="Keyword overlap with experiment topic">[relevance: medium]</span>'
        else:
            rel_label = ' <span style="color:#a00;font-size:9pt" title="Low keyword overlap — verify manually">[relevance: low — verify]</span>'
    return (
        f'<span class="ref-tag ref-{tag}">[{tag}]</span> '
        f"{html_lib.escape(authors)}. "
        f"{html_lib.escape(title)}.{jpart}{yr}. "
        f'<a href="https://pubmed.ncbi.nlm.nih.gov/{html_lib.escape(pmid)}/" '
        f'target="_blank" rel="noopener">PMID {html_lib.escape(pmid)}</a>{sim}{rel_label}'
    )


def build_verified_references_html(
    topic: str,
    pubmed_records: list[Any],
    *,
    extra_pmids: list[str] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """
    Build a References section from PubMed records only (reverse lookup + verify).
    Returns (html_fragment, audit_rows).
    """
    from .references.pubmed_client import PubMedRecord, fetch_by_pmid
    from .references.verify import batch_score, verify_record

    seen: set[str] = set()
    candidates: list[Any] = []
    for rec in pubmed_records or []:
        pmid = str(getattr(rec, "pmid", "") or "").strip()
        if pmid and pmid not in seen:
            seen.add(pmid)
            candidates.append(rec)

    for pmid in extra_pmids or []:
        pmid = str(pmid).strip()
        if not pmid or pmid in seen:
            continue
        seen.add(pmid)
        try:
            fetched = fetch_by_pmid(pmid)
            if fetched:
                candidates.append(fetched)
        except Exception:
            continue

    audit: list[dict[str, Any]] = []
    items: list[str] = []
    topic = (topic or "").strip() or "laboratory experiment"

    scores: list[float] = []
    try:
        scores = batch_score(topic, [c for c in candidates if isinstance(c, PubMedRecord)])
    except Exception:
        scores = [0.0] * len(candidates)

    for i, rec in enumerate(candidates):
        if not isinstance(rec, PubMedRecord):
            continue
        sim = scores[i] if i < len(scores) else None
        v = verify_record(topic, rec, similarity_score=sim, cross_check_doi=True)
        verdict = v.verdict
        if verdict not in ("verified", "partial"):
            continue
        # Relevance score attached by _lab_pubmed_for_report (keyword-overlap, 0–1)
        relevance: float | None = getattr(rec, "_lab_relevance", None)
        items.append(
            f'<li style="margin-bottom:0.65em">{_format_citation(rec, verdict=verdict, similarity=v.similarity, relevance=relevance)}</li>'
        )
        audit.append({
            "pmid": rec.pmid,
            "verdict": verdict,
            "similarity": v.similarity,
            "relevance_score": relevance,
            "relevance_label": (
                "high" if relevance is not None and relevance >= 0.4
                else "medium" if relevance is not None and relevance >= 0.2
                else "low"
            ),
            "title": rec.title,
        })

    note = (
        '<p style="font-size:10pt;color:#555;margin-top:0.8em">'
        "References are limited to PubMed records retrieved and verified against this experiment "
        "(embedding similarity + DOI cross-check + keyword-overlap relevance). "
        "Tags: <strong>[verified]</strong> high semantic match; <strong>[partial]</strong> use with caution. "
        "Relevance labels show keyword overlap between abstract and experiment topic. "
        "Low-relevance citations should be manually confirmed before submission.</p>"
    )
    if not items:
        body = (
            "<p><em>No literature citations met the verification threshold for this report. "
            "Add SOP keywords or background text and regenerate, or paste PMIDs after manual review.</em></p>"
            + note
        )
    else:
        body = '<ol style="padding-left:1.4em">' + "".join(items) + "</ol>" + note

    section = (
        '<section class="lab-references-verified"><h2>References</h2>' + body + "</section>"
    )
    return section, audit


def replace_references_section(full_html: str, references_section_html: str) -> str:
    """Replace or append the References h2 block in a full HTML document."""
    ref_inner = references_section_html
    m = re.search(r"<section[^>]*class=\"lab-references-verified\"[\s\S]*?</section>", ref_inner)
    if m:
        ref_inner = m.group(0)
    elif "<h2" in ref_inner:
        ref_inner = f"<section>{ref_inner}</section>" if not ref_inner.strip().startswith("<section") else ref_inner

    if re.search(r"<h2[^>]*>\s*References\s*</h2>", full_html, re.IGNORECASE):
        return re.sub(
            r"<h2[^>]*>\s*References\s*</h2>[\s\S]*?(?=<h2[^>]*>|</article>|</body>)",
            ref_inner.replace("<section class=\"lab-references-verified\">", "").replace("</section>", "")
            if "lab-references-verified" in ref_inner
            else f"<h2>References</h2>{ref_inner}",
            full_html,
            count=1,
            flags=re.IGNORECASE,
        )
    if "</article>" in full_html:
        return full_html.replace("</article>", ref_inner + "</article>", 1)
    if "</body>" in full_html:
        return full_html.replace("</body>", ref_inner + "</body>", 1)
    return full_html + ref_inner


def apply_article_postprocess(
    full_html: str,
    *,
    topic: str,
    pubmed_records: list[Any],
    extra_pmids: list[str] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Strip phantom figures in <article> and rebuild verified References."""
    if not full_html:
        return full_html, []

    art_m = re.search(r"(<article[\s\S]*?</article>)", full_html, re.IGNORECASE)
    if not art_m:
        ref_sec, audit = build_verified_references_html(topic, pubmed_records, extra_pmids=extra_pmids)
        return replace_references_section(full_html, ref_sec), audit

    article = art_m.group(1)
    article = strip_phantom_figure_markup(article)
    ref_sec, audit = build_verified_references_html(topic, pubmed_records, extra_pmids=extra_pmids)
    article = re.sub(
        r"<h2[^>]*>\s*References\s*</h2>[\s\S]*?(?=<h2[^>]*>|</article>)",
        "",
        article,
        count=1,
        flags=re.IGNORECASE,
    )
    article = article.replace("</article>", ref_sec + "</article>", 1)
    return full_html.replace(art_m.group(1), article, 1), audit


def strip_figures_section_html(full_html: str) -> str:
    """Remove appended Figures / Statistical charts section before re-injecting charts."""
    if not full_html:
        return full_html
    return re.sub(
        r"<section[^>]*>[\s\S]*?Figures\s*/\s*Statistical charts[\s\S]*?</section>",
        "",
        full_html,
        count=1,
        flags=re.IGNORECASE,
    )


def extract_pmids_from_html(html: str) -> list[str]:
    found = re.findall(r"\bPMID[:\s]*(\d{6,9})\b", html or "", re.IGNORECASE)
    found += re.findall(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{6,9})", html or "", re.IGNORECASE)
    out: list[str] = []
    seen: set[str] = set()
    for p in found:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out
