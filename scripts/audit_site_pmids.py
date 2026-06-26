#!/usr/bin/env python3
"""
Site-wide PubMed (PMID) relevance audit for Therasik / InSynBio web sources.

Scans JSON and HTML under configured roots for:
  - numeric `pmid` / `pmids` fields
  - pubmed.ncbi.nlm.nih.gov URLs in strings
  - plain-text "PMID: 12345" patterns in strings and HTML

For each occurrence, fetches PubMed title+abstract (batched) and scores heuristic
match against local context (name, gene, indication, notes, etc.).

Output:
  reports/site_pmid_audit.csv
  reports/site_pmid_audit.md

Env:
  NCBI_API_KEY   optional, higher eutils rate limit
  NCBI_CONTACT_EMAIL  optional (default kb-audit@therasik.com)

Usage:
  python scripts/audit_site_pmids.py
  python scripts/audit_site_pmids.py --roots therasik-web-source docs
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
REPORTS = REPO / "reports"

# Load shared helpers from vaccine verifier (same efetch / scoring).
_VKB_PATH = Path(__file__).resolve().parent / "verify_vaccine_kb_pmids.py"
_spec = importlib.util.spec_from_file_location("verify_vaccine_kb_pmids", _VKB_PATH)
if _spec is None or _spec.loader is None:
    print("Cannot load verify_vaccine_kb_pmids.py", file=sys.stderr)
    sys.exit(1)
_vkb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_vkb)

efetch_batch = _vkb.efetch_batch
RE_PUBMED_URL = _vkb.RE_PUBMED_URL
RE_PMID_IN_TEXT = _vkb.RE_PMID_IN_TEXT
NCI_META_PMIDS = _vkb.NCI_META_PMIDS
_terms_from_ctx = _vkb._terms_from_ctx
_score_relevance = _vkb._score_relevance


# Extra JSON/HTML context keys merged into notes for term extraction.
_EXTRA_CTX_KEYS = (
    "targets",
    "target",
    "indication",
    "category",
    "subcategory",
    "role",
    "mechanism",
    "brief",
    "design_notes",
    "tier_justification",
    "ref",
    "interp",
    "calc",
    "principle",
    "detection",
    "mitigation",
    "drug",
    "drug_name",
    "alias",
    "aliases",
    "cat",
    "title",
    "description",
    "fc_engineering",
    "disease_class",
)


_CAPTION_STOP = frozenset(
    {
        "that",
        "this",
        "with",
        "from",
        "have",
        "been",
        "were",
        "also",
        "using",
        "et",
        "al",
        "and",
        "the",
        "for",
        "via",
        "into",
    }
)


def _tokens_from_caption(cap: str) -> list[str]:
    """Split HTML anchor text (author, journal) into matchable tokens."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-']{2,}", cap)
    out: list[str] = []
    seen: set[str] = set()
    for w in words:
        low = w.lower().strip("'")
        if low in _CAPTION_STOP or len(low) < 3:
            continue
        if low not in seen:
            seen.add(low)
            out.append(w)
    return out


def _augment_ctx_for_terms(ctx: dict[str, Any]) -> dict[str, Any]:
    """Broaden local terms for ADA / component / guide-style rows."""
    c = dict(ctx)
    blobs: list[str] = []
    for k in _EXTRA_CTX_KEYS:
        v = c.get(k)
        if isinstance(v, str) and v.strip():
            blobs.append(v.strip()[:800])
        elif isinstance(v, list):
            for x in v:
                if isinstance(x, str) and x.strip():
                    blobs.append(x.strip()[:800])
    if blobs:
        prev = c.get("notes", "")
        if isinstance(prev, str) and prev.strip():
            blobs.insert(0, prev.strip()[:400])
        c["notes"] = " ".join(blobs)[:2500]
    return c


def _classify_link_kind(field_path: str, pmid: str, source: str) -> str:
    if pmid in NCI_META_PMIDS and "nci_rank" in field_path:
        return "nci_meta"
    if source.endswith(".html"):
        if RE_PUBMED_URL.search(field_path) or "pubmed" in field_path:
            return "html_url"
        return "html_text"
    if ".pmid" in field_path and "epitope" in field_path:
        return "epitope_ref"
    if "pmids" in field_path:
        return "json_pmids"
    if field_path.endswith(".pmid") or ".pmid" in field_path:
        return "json_pmid"
    return "json_string_pmids"


def _local_name_gene(ctx: dict[str, Any]) -> str:
    name_gene = ""
    if ctx.get("name"):
        name_gene = str(ctx["name"])
    if ctx.get("gene"):
        name_gene = f"{name_gene} / {ctx['gene']}".strip(" /")
    if not name_gene and ctx.get("drug"):
        name_gene = str(ctx["drug"])[:120]
    return name_gene[:300]


def _anchor_text_for_pubmed_match(full_html: str, m: re.Match[str]) -> str:
    """Inner text of the <a> that wraps this PubMed URL (e.g. author + journal)."""
    pmid = m.group(1)
    start, end = m.span()
    seg = full_html[max(0, start - 600) : min(len(full_html), end + 100)]
    pat = re.compile(
        r'<a\s[^>]*href="https?://(?:www\.)?pubmed\.ncbi\.nlm\.nih\.gov/'
        + re.escape(pmid)
        + r'/?"[^>]*>([^<]*)</a>',
        re.I,
    )
    found = pat.search(seg)
    if not found:
        return ""
    t = found.group(1).strip()
    return t.replace(r"\'", "'").replace(r"\"", '"')


def _extract_html_chunk_context(chunk: str) -> dict[str, Any]:
    """Pull last name/mechanism/clone_id-style fields before a PubMed URL in HTML/JS."""
    ctx: dict[str, Any] = {}
    patterns = [
        (r"name\s*:\s*'([^']{1,400})'", "name"),
        (r'name\s*:\s*"([^"]{1,400})"', "name"),
        (r"clone_id\s*:\s*'([^']{1,120})'", "clone_id"),
        (r"mechanism\s*:\s*'([^']{1,500})'", "mechanism"),
        (r"domain\s*:\s*'([^']{1,120})'", "category"),
    ]
    for pat, key in patterns:
        last_val: str | None = None
        for m in re.finditer(pat, chunk, re.I | re.S):
            last_val = m.group(1).strip()
        if last_val:
            ctx[key] = last_val
    return ctx


def _scan_html_file(path: Path, rel: str) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    rows: list[dict[str, Any]] = []
    for m in RE_PUBMED_URL.finditer(text):
        pmid = m.group(1)
        pos = m.start()
        chunk = text[max(0, pos - 4500) : pos]
        ctx = _extract_html_chunk_context(chunk)
        cap = _anchor_text_for_pubmed_match(text, m)
        if cap:
            ctx = dict(ctx)
            ctx["citation_anchor"] = cap
            prev = ctx.get("notes", "")
            if isinstance(prev, str) and prev.strip():
                ctx["notes"] = (cap + " " + prev)[:2000]
            else:
                ctx["notes"] = cap[:800]
        rows.append(
            {
                "pmid": pmid,
                "field_path": f"{rel}@offset{pos}",
                "link_kind": "html_url",
                "ctx": ctx,
                "source_file": rel,
            }
        )
    for m in RE_PMID_IN_TEXT.finditer(text):
        pmid = m.group(1)
        pos = m.start()
        if _url_covers_pmid(text, pos, pmid):
            continue
        chunk = text[max(0, pos - 4500) : pos]
        ctx = _extract_html_chunk_context(chunk)
        rows.append(
            {
                "pmid": pmid,
                "field_path": f"{rel}@pmid_text_offset{pos}",
                "link_kind": "html_pmid_text",
                "ctx": ctx,
                "source_file": rel,
            }
        )
    return rows


def _url_covers_pmid(text: str, pos: int, pmid: str) -> bool:
    """True if this PMID is inside or immediately after a pubmed URL (avoid dup rows)."""
    window_start = max(0, pos - 120)
    window = text[window_start : pos + len(pmid) + 20]
    return f"pubmed.ncbi.nlm.nih.gov/{pmid}" in window.replace(" ", "")


def _scan_string_for_pmids(
    s: str,
    field_path: str,
    rel: str,
    ctx: dict[str, Any],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in RE_PUBMED_URL.finditer(s):
        row_ctx = dict(ctx)
        cap = _anchor_text_for_pubmed_match(s, m)
        if cap:
            row_ctx["citation_anchor"] = cap
            prev = row_ctx.get("notes", "")
            if isinstance(prev, str) and prev.strip():
                row_ctx["notes"] = (cap + " " + prev)[:2000]
            else:
                row_ctx["notes"] = cap[:800]
        out.append(
            {
                "pmid": m.group(1),
                "field_path": field_path,
                "link_kind": "json_url_in_string",
                "ctx": row_ctx,
                "source_file": rel,
            }
        )
    for m in RE_PMID_IN_TEXT.finditer(s):
        pmid = m.group(1)
        if any(x["pmid"] == pmid for x in out):
            continue
        out.append(
            {
                "pmid": pmid,
                "field_path": field_path + ":pmid_text",
                "link_kind": "json_pmid_in_string",
                "ctx": ctx,
                "source_file": rel,
            }
        )
    return out


def walk_json(
    obj: Any,
    path: str,
    rel: str,
    rows: list[dict[str, Any]],
) -> None:
    if isinstance(obj, dict):
        ctx = {k: v for k, v in obj.items() if not str(k).startswith("_")}
        pv = obj.get("pmid")
        if pv is not None and str(pv).strip().isdigit():
            fp_pm = f"{path}.pmid" if path else "pmid"
            rows.append(
                {
                    "pmid": str(pv).strip(),
                    "field_path": fp_pm,
                    "link_kind": _classify_link_kind(fp_pm, str(pv).strip(), "json"),
                    "ctx": ctx,
                    "source_file": rel,
                }
            )
        pms = obj.get("pmids")
        if isinstance(pms, list):
            for i, p in enumerate(pms):
                if p is not None and str(p).strip().isdigit():
                    fp = f"{path}.pmids[{i}]" if path else f"pmids[{i}]"
                    rows.append(
                        {
                            "pmid": str(p).strip(),
                            "field_path": fp,
                            "link_kind": "json_pmids",
                            "ctx": ctx,
                            "source_file": rel,
                        }
                    )
        for k, v in obj.items():
            fp = f"{path}.{k}" if path else str(k)
            if isinstance(v, str) and (
                "pubmed" in v.lower() or RE_PMID_IN_TEXT.search(v)
            ):
                rows.extend(_scan_string_for_pmids(v, fp, rel, ctx))
            elif isinstance(v, (dict, list)):
                walk_json(v, fp, rel, rows)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            walk_json(item, f"{path}[{i}]", rel, rows)


def _terms_for_audit_row(ctx: dict[str, Any]) -> list[str]:
    aug = _augment_ctx_for_terms(ctx)
    terms = list(_terms_from_ctx(aug))
    cap = ctx.get("citation_anchor")
    if isinstance(cap, str) and cap.strip():
        terms.extend(_tokens_from_caption(cap))
    seen: set[str] = set()
    out: list[str] = []
    for t in terms:
        k = t.lower()
        if k not in seen:
            seen.add(k)
            out.append(t)
    return out


def process_json_file(path: Path, root: Path) -> list[dict[str, Any]]:
    rel = f"{root.name}/{path.relative_to(root).as_posix()}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    rows: list[dict[str, Any]] = []
    walk_json(data, "", rel, rows)
    return rows


def iter_scan_roots(roots: list[Path]) -> list[dict[str, Any]]:
    all_rows: list[dict[str, Any]] = []
    for root in roots:
        root = root.resolve()
        if not root.is_dir():
            continue
        for p in root.rglob("*.json"):
            if "node_modules" in p.parts:
                continue
            all_rows.extend(process_json_file(p, root))
        for p in root.rglob("*.html"):
            if "node_modules" in p.parts:
                continue
            rel = f"{root.name}/{p.relative_to(root).as_posix()}"
            all_rows.extend(_scan_html_file(p, rel))
    return all_rows


def dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    out: list[dict[str, Any]] = []
    for r in rows:
        key = (r["source_file"], r["field_path"], r["pmid"])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Site-wide PMID / PubMed relevance audit")
    ap.add_argument(
        "--roots",
        nargs="*",
        default=[
            "therasik-web-source",
            "insynbio-web-source",
            "docs",
        ],
        help="Directory names under repo root to scan",
    )
    args = ap.parse_args()
    root_paths = [(REPO / r).resolve() for r in args.roots]

    raw_rows = iter_scan_roots(root_paths)
    unique_rows = dedupe_rows(raw_rows)
    api_key = os.environ.get("NCBI_API_KEY")
    all_pmids = sorted({r["pmid"] for r in unique_rows})
    pubmed: dict[str, dict[str, str]] = {}
    batch_size = 80
    for i in range(0, len(all_pmids), batch_size):
        chunk = all_pmids[i : i + batch_size]
        pubmed.update(efetch_batch(chunk, api_key))

    REPORTS.mkdir(parents=True, exist_ok=True)
    csv_path = REPORTS / "site_pmid_audit.csv"
    md_path = REPORTS / "site_pmid_audit.md"

    review_lines: list[str] = []

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "pmid",
                "source_file",
                "field_path",
                "link_kind",
                "local_context_summary",
                "pubmed_title",
                "match_status",
                "match_score",
                "matched_terms",
                "verdict",
                "notes",
            ]
        )

        for r in sorted(unique_rows, key=lambda x: (x["source_file"], x["pmid"], x["field_path"])):
            pmid = r["pmid"]
            lk = r["link_kind"]
            ctx = r["ctx"]
            terms = _terms_for_audit_row(ctx)
            rec = pubmed.get(pmid, {})
            title = rec.get("title", "")
            abstract = rec.get("abstract", "")
            authors = rec.get("authors", "")
            abstract_for_score = f"{abstract} {authors}".strip()
            name_gene = _local_name_gene(ctx)

            if pmid in NCI_META_PMIDS and lk == "nci_meta":
                verdict = "ok_shared_ranking_source"
                status, score, hits = "nci_meta_skip_antigen_match", 1.0, []
                notes = (
                    "NCI priority-antigen list style citation; not expected to name every local entity."
                )
            else:
                status, score, hits = _score_relevance(terms, title, abstract_for_score)
                if status == "no_pubmed_text":
                    verdict = "fetch_or_parse_failed"
                    notes = "No title/abstract returned from efetch."
                elif status == "no_local_terms":
                    verdict = "review"
                    notes = "No extractable local terms; check context manually."
                elif status == "weak_or_unrelated":
                    verdict = "review"
                    notes = "Consider replacing PMID or expanding local context."
                elif status == "review":
                    verdict = "review"
                    notes = "Borderline match; manual check recommended."
                else:
                    verdict = "ok"
                    notes = ""

            w.writerow(
                [
                    pmid,
                    r["source_file"],
                    r["field_path"],
                    lk,
                    name_gene[:400],
                    title[:500],
                    status,
                    score,
                    "; ".join(hits[:12]),
                    verdict,
                    notes,
                ]
            )

            if verdict in ("review", "fetch_or_parse_failed"):
                review_lines.append(
                    f"- **PMID {pmid}** `{r['source_file']}` `{r['field_path']}` — {status} (score={score}) — _{title[:100]}…_"
                )

    md_body = [
        "# Site-wide PMID relevance audit",
        "",
        f"Roots scanned: {', '.join(args.roots)}",
        f"Unique PMIDs fetched: {len(all_pmids)}",
        f"Unique occurrences (deduped by file+path+pmid): {len(unique_rows)}",
        "",
        "## Rows needing review",
        "",
    ]
    md_body.extend(review_lines if review_lines else ["- _(none)_", ""])
    md_body.extend(["", f"Full table: `{csv_path.relative_to(REPO).as_posix()}`", ""])
    md_path.write_text("\n".join(md_body), encoding="utf-8")

    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")
    print(f"PMIDs: {len(all_pmids)}, occurrences: {len(unique_rows)}, review rows: {len(review_lines)}")


if __name__ == "__main__":
    main()
