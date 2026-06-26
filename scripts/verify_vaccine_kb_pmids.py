#!/usr/bin/env python3
"""
Reverse-verify PubMed links in vaccine_kb_data.json against NCBI.

For each PMID found in the JSON (pmid fields + pubmed URLs in strings):
  1. efetch title + abstract from PubMed
  2. Compare to local context (gene, name, antigen, peptide, aliases, notes snippet)
  3. Classify:
     - nci_meta: NCI priority-antigen list paper (shared across many TAA rows)
     - epitope_ref: epitope / MHC row with optional pmid
     - tcr_struct: TCR / structure row with pmid
     - other

Output (default):
  reports/vaccine_kb_pmid_reverse_audit.csv
  reports/vaccine_kb_pmid_reverse_audit.md

Env:
  NCBI_API_KEY  optional, raises eutils rate limit
  VERIFY_KB_JSON  optional path override to vaccine_kb_data.json

Usage:
  python scripts/verify_vaccine_kb_pmids.py
  python scripts/verify_vaccine_kb_pmids.py --json path/to/vaccine_kb_data.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
DEFAULT_JSON = REPO / "therasik-web-source" / "vaccine_kb_data.json"
OUT_DIR = REPO / "reports"

EMAIL = os.environ.get("NCBI_CONTACT_EMAIL", "kb-audit@therasik.com")
DELAY = 0.35
USER_AGENT = "Therasik-KB-PMID-Verifier/1.0"

# PMID used site-wide as source for NCI antigen prioritization ranking (not antigen-specific).
NCI_META_PMIDS = frozenset({"19723653"})

RE_PUBMED_URL = re.compile(
    r"https?://(?:www\.)?pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/?",
    re.I,
)
RE_PMID_IN_TEXT = re.compile(r"PMID[:\s]*(\d+)", re.I)


def efetch_batch(pmids: list[str], api_key: str | None) -> dict[str, dict[str, str]]:
    if not pmids:
        return {}
    params: dict[str, str] = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "xml",
        "retmode": "xml",
        "email": EMAIL,
    }
    if api_key:
        params["api_key"] = api_key
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urllib.parse.urlencode(
        params
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=90) as resp:
        root = ET.fromstring(resp.read())
    out: dict[str, dict[str, str]] = {}
    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        if pmid_el is None or not pmid_el.text:
            continue
        pmid = pmid_el.text.strip()
        title_el = article.find(".//ArticleTitle")
        title = "".join(title_el.itertext()) if title_el is not None else ""
        abs_parts: list[str] = []
        for at in article.findall(".//AbstractText"):
            label = at.get("Label", "")
            text = "".join(at.itertext())
            abs_parts.append(f"{label}: {text}" if label else text)
        author_names: list[str] = []
        for auth in article.findall(".//Author"):
            ln = auth.find("LastName")
            if ln is not None and ln.text and ln.text.strip():
                author_names.append(ln.text.strip())
        out[pmid] = {
            "title": title,
            "abstract": " ".join(abs_parts),
            "authors": " ".join(author_names),
        }
    time.sleep(DELAY)
    return out


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _terms_from_ctx(ctx: dict[str, Any]) -> list[str]:
    raw: list[str] = []
    for k in (
        "name",
        "gene",
        "antigen",
        "peptide",
        "epitope",
        "disease_context",
        "disease",
        "target_antigen",
        "clone_id",
    ):
        v = ctx.get(k)
        if isinstance(v, str) and v.strip():
            raw.append(v.strip())
        elif isinstance(v, list):
            for x in v:
                if isinstance(x, str) and x.strip():
                    raw.append(x.strip())
    aliases = ctx.get("aliases")
    if isinstance(aliases, list):
        for a in aliases:
            if isinstance(a, str) and a.strip():
                raw.append(a.strip())
    notes = ctx.get("notes")
    if isinstance(notes, str) and notes.strip():
        raw.append(notes.strip()[:400])
    # de-dupe while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for r in raw:
        key = r.lower()
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def _flex_antigen(s: str) -> list[str]:
    """Extra tokens for NY-ESO-1, gp100, etc."""
    out: list[str] = []
    low = s.lower()
    if "ny-eso" in low or "nyeso" in low.replace("-", ""):
        out.extend(["ny-eso-1", "ny-eso", "ctag1b", "eso-1"])
    if "gp100" in low or "pmel" in low:
        out.extend(["gp100", "pmel", "premelanosome"])
    if "mart-1" in low or "melan-a" in low:
        out.extend(["mart-1", "melan-a", "mlana", "elagigiltv"])
    if "gliadin" in low or "celiac" in low or "gluten" in low:
        out.extend(["gliadin", "celiac", "gluten", "dq2"])
    if "sm d" in low or "smd" in low.replace(" ", "") or "lupus" in low or "sle" in low:
        out.extend(["smd", "sm d", "lupus", "autoimmune", "snrnp", "u1-70k"])
    if "mage" in low:
        out.extend(["mage-a3", "mage a3", "titin", "cross-reactiv"])
    return out


def _score_relevance(terms: list[str], title: str, abstract: str) -> tuple[str, float, list[str]]:
    blob = _norm(title + " " + abstract)
    if not blob.strip():
        return "no_pubmed_text", 0.0, []
    hits: list[str] = []
    expanded: list[str] = list(terms)
    for t in terms:
        expanded.extend(_flex_antigen(t))
    seen_t: set[str] = set()
    uniq_terms: list[str] = []
    for t in expanded:
        k = t.lower()[:120]
        if k not in seen_t:
            seen_t.add(k)
            uniq_terms.append(t)
    for t in uniq_terms:
        nt = _norm(t)
        if len(nt) < 2:
            continue
        # substring match (gene symbols, peptide sequences, multi-word names)
        if len(nt) >= 8 or " " in nt:
            if nt in blob:
                hits.append(t[:80])
        elif len(nt) >= 3:
            # word boundary-ish: avoid matching "ra" in "therapy"
            if re.search(r"(?<![a-z0-9])" + re.escape(nt) + r"(?![a-z0-9])", blob):
                hits.append(t)
        elif len(nt) == 2 and nt in ("dq", "dr", "hla"):
            if re.search(r"(?<![a-z0-9])" + re.escape(nt) + r"(?![a-z0-9])", blob):
                hits.append(t)
    if not uniq_terms:
        return "no_local_terms", 0.0, []
    score = len(hits) / min(len(uniq_terms), 10)
    if score >= 0.25 or hits:
        status = "likely_relevant" if score >= 0.2 or any(len(h) > 5 for h in hits) else "review"
    else:
        status = "weak_or_unrelated"
    return status, round(score, 3), hits


def _classify_row(field_path: str, pmid: str) -> str:
    if pmid in NCI_META_PMIDS and "nci_rank" in field_path:
        return "nci_meta"
    if ".pmid" in field_path and "epitope" in field_path:
        return "epitope_ref"
    if "tcr" in field_path or "tcr_" in field_path:
        return "tcr_struct"
    return "other"


def walk(
    obj: Any,
    path: str,
    ctx: dict[str, Any],
    rows: list[dict[str, Any]],
) -> None:
    if isinstance(obj, dict):
        new_ctx = {**ctx}
        for k in (
            "name",
            "gene",
            "antigen",
            "aliases",
            "notes",
            "peptide",
            "disease_context",
            "disease",
            "target_antigen",
            "epitope",
            "clone_id",
        ):
            if k in obj:
                new_ctx[k] = obj[k]

        if "pmid" in obj and obj["pmid"]:
            p = str(obj["pmid"]).strip()
            if p.isdigit():
                rows.append(
                    {
                        "pmid": p,
                        "field_path": path + ".pmid",
                        "link_kind": _classify_row(path + ".pmid", p),
                        "ctx": {k: new_ctx[k] for k in new_ctx if new_ctx[k] is not None},
                    }
                )

        for k, v in obj.items():
            walk(v, f"{path}.{k}" if path else k, new_ctx, rows)

        for k in ("nci_rank_source", "nci_rank_citation"):
            if k in obj and isinstance(obj[k], str):
                for m in RE_PUBMED_URL.finditer(obj[k]):
                    p = m.group(1)
                    rows.append(
                        {
                            "pmid": p,
                            "field_path": path + f".{k}",
                            "link_kind": "nci_meta" if p in NCI_META_PMIDS else "citation_url",
                            "ctx": {k2: new_ctx[k2] for k2 in new_ctx if new_ctx[k2] is not None},
                        }
                    )
                for m in RE_PMID_IN_TEXT.finditer(obj[k]):
                    p = m.group(1)
                    if not any(r["pmid"] == p and r["field_path"].endswith(k) for r in rows[-5:]):
                        rows.append(
                            {
                                "pmid": p,
                                "field_path": path + f".{k}",
                                "link_kind": "nci_meta" if p in NCI_META_PMIDS else "citation_text",
                                "ctx": {k2: new_ctx[k2] for k2 in new_ctx if new_ctx[k2] is not None},
                            }
                        )

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            walk(item, f"{path}[{i}]", ctx, rows)


def main() -> None:
    ap = argparse.ArgumentParser(description="Reverse-verify PMIDs in vaccine_kb_data.json")
    ap.add_argument(
        "--json",
        type=Path,
        default=Path(os.environ.get("VERIFY_KB_JSON", str(DEFAULT_JSON))),
        help="Path to vaccine_kb_data.json",
    )
    args = ap.parse_args()
    data = json.loads(args.json.read_text(encoding="utf-8"))

    rows: list[dict[str, Any]] = []
    walk(data, "", {}, rows)

    # de-dupe by (pmid, field_path) keeping first
    seen_key: set[tuple[str, str]] = set()
    unique_rows: list[dict[str, Any]] = []
    for r in rows:
        key = (r["pmid"], r["field_path"])
        if key in seen_key:
            continue
        seen_key.add(key)
        unique_rows.append(r)

    api_key = os.environ.get("NCBI_API_KEY")
    all_pmids = sorted({r["pmid"] for r in unique_rows})
    pubmed: dict[str, dict[str, str]] = {}
    batch_size = 80
    for i in range(0, len(all_pmids), batch_size):
        chunk = all_pmids[i : i + batch_size]
        pubmed.update(efetch_batch(chunk, api_key))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "vaccine_kb_pmid_reverse_audit.csv"
    md_path = OUT_DIR / "vaccine_kb_pmid_reverse_audit.md"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "pmid",
                "field_path",
                "link_kind",
                "local_name_gene",
                "pubmed_title",
                "match_status",
                "match_score",
                "matched_terms",
                "verdict",
                "notes",
            ]
        )

        md_lines = [
            "# Vaccine KB — PMID reverse audit",
            "",
            f"Source JSON: `{args.json}`",
            f"Unique PMID values fetched: {len(all_pmids)}",
            f"Occurrences in KB: {len(unique_rows)}",
            "",
            "## Legend",
            "",
            "- **nci_meta**: shared NCI priority-antigen list citation; not expected to mention every antigen in title/abstract.",
            "- **likely_relevant**: at least one strong local term appears in PubMed title+abstract.",
            "- **weak_or_unrelated**: no local terms matched; **manual review** recommended.",
            "",
            "## Rows needing review (weak_or_unrelated, non-nci_meta)",
            "",
        ]

        review_md: list[str] = []

        for r in unique_rows:
            pmid = r["pmid"]
            lk = r["link_kind"]
            ctx = r["ctx"]
            terms = _terms_from_ctx(ctx)
            rec = pubmed.get(pmid, {})
            title = rec.get("title", "")
            abstract = rec.get("abstract", "")

            name_gene = ""
            if ctx.get("name"):
                name_gene = str(ctx["name"])
            if ctx.get("gene"):
                name_gene = f"{name_gene} / {ctx['gene']}".strip(" /")

            if pmid in NCI_META_PMIDS and lk == "nci_meta":
                verdict = "ok_shared_ranking_source"
                status, score, hits = "nci_meta_skip_antigen_match", 1.0, []
                notes = (
                    "Cheever et al.–style NCI priority list; cited for ranking field, "
                    "not as antigen-specific primary literature."
                )
            else:
                status, score, hits = _score_relevance(terms, title, abstract)
                if status == "no_pubmed_text":
                    verdict = "fetch_or_parse_failed"
                    notes = "No title/abstract returned from efetch."
                elif status == "no_local_terms":
                    verdict = "review"
                    notes = "No extractable local terms; check context manually."
                elif status == "weak_or_unrelated":
                    verdict = "review"
                    notes = "Consider replacing PMID or expanding local context."
                else:
                    verdict = "ok"
                    notes = ""

            w.writerow(
                [
                    pmid,
                    r["field_path"],
                    lk,
                    name_gene,
                    title[:500],
                    status,
                    score,
                    "; ".join(hits[:12]),
                    verdict,
                    notes,
                ]
            )

            if verdict == "review" or verdict == "fetch_or_parse_failed":
                review_md.append(
                    f"- **PMID {pmid}** `{r['field_path']}` — {status} (score={score}) — _{title[:120]}…_"
                )

        md_lines.extend(review_md if review_md else ["- _(none in this run)_", ""])
        md_lines.append("")
        md_lines.append("Full table: `reports/vaccine_kb_pmid_reverse_audit.csv`")
        md_lines.append("")
        md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")
    print(f"PMIDs fetched: {len(all_pmids)}, KB link rows: {len(unique_rows)}")


if __name__ == "__main__":
    main()
