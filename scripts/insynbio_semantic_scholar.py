#!/usr/bin/env python3
"""
InSynBio Semantic Scholar CLI — citation context and paper intelligence.

Uses the Semantic Scholar Academic Graph API (free, no key for basic access).

Subcommands:
  search          Full-text paper search
  paper           Fetch paper metadata + abstract + TLDR
  citations       Fetch incoming citations with intent (background/methodology/result)
  references      Fetch outgoing references of a paper
  cite-context    Get how a paper is cited (supporting / contrasting / mentioning)
  author          Fetch author profile + h-index + recent papers

Why Semantic Scholar vs OpenAlex?
  - Citation INTENT: tells you if citing paper uses this work as background,
    methodology, or direct result (not available in OpenAlex)
  - TLDR: AI-generated 1-sentence summary
  - influential_citation flag: distinguishes highly influential citations
  - Better for "is this paper well-supported in the literature?" queries

Usage:
  python scripts/insynbio_semantic_scholar.py search --query "RFdiffusion antibody design" --limit 10
  python scripts/insynbio_semantic_scholar.py paper --id 10.1038/s41586-023-06415-8
  python scripts/insynbio_semantic_scholar.py citations --id 10.1038/s41586-023-06415-8 --limit 20
  python scripts/insynbio_semantic_scholar.py cite-context --id 10.1038/s41586-023-06415-8
  python scripts/insynbio_semantic_scholar.py author --name "David Baker"
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE_URL = "https://api.semanticscholar.org/graph/v1"
PARTNER_URL = "https://partner.semanticscholar.org/graph/v1"

# Polite pool headers — identify our tool
HEADERS = {
    "User-Agent": "InSynBio-ResearchSuite/1.0 (mailto:research@insynbio.com)",
}


def _get(endpoint: str, params: dict | None = None, retries: int = 2) -> dict | list | None:
    url = f"{BASE_URL}/{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 10 * (attempt + 1)
                print(f"  [S2] Rate limit — waiting {wait}s…", file=sys.stderr)
                time.sleep(wait)
            elif e.code == 404:
                return None
            else:
                print(f"  [S2] HTTP {e.code}: {e.reason}", file=sys.stderr)
                return None
        except Exception as e:
            print(f"  [S2] Error: {e}", file=sys.stderr)
            return None
    return None


def _normalize_id(paper_id: str) -> str:
    """Accept DOI, ArXiv ID, or S2 paper ID."""
    if paper_id.startswith("10."):
        return f"DOI:{paper_id}"
    if "/" in paper_id and not paper_id.startswith("DOI:"):
        return f"DOI:{paper_id}"
    if paper_id.startswith("arxiv:") or paper_id.startswith("ARXIV:"):
        return paper_id.upper()
    # if it looks like arxiv (NNNN.NNNNN)
    if paper_id.replace(".", "").isdigit() and "." in paper_id:
        return f"ARXIV:{paper_id}"
    return paper_id  # assume S2 40-char hash


def _format_paper(p: dict, verbose: bool = False) -> str:
    title = p.get("title", "")
    year = p.get("year", "")
    cit = p.get("citationCount", "?")
    tldr = (p.get("tldr") or {}).get("text", "")
    authors = ", ".join(a.get("name", "") for a in (p.get("authors") or [])[:3])
    if len(p.get("authors") or []) > 3:
        authors += " et al."
    venue = p.get("venue") or p.get("publicationVenue", {}) or ""
    if isinstance(venue, dict):
        venue = venue.get("name", "")
    doi = p.get("externalIds", {}).get("DOI", "")
    s2_id = p.get("paperId", "")

    lines = [f"  [{year}] {title}"]
    lines.append(f"         {authors} · {venue}")
    lines.append(f"         Citations: {cit} · DOI: {doi} · S2: {s2_id[:12]}…")
    if tldr and verbose:
        lines.append(f"         TLDR: {tldr}")
    return "\n".join(lines)


# ── search ────────────────────────────────────────────────────────────────────

def cmd_search(args: argparse.Namespace) -> int:
    params = {
        "query": args.query,
        "limit": args.limit,
        "fields": "title,authors,year,citationCount,venue,externalIds,tldr,openAccessPdf",
        "publicationTypes": args.pub_type or None,
        "year": args.year or None,
        "openAccessPdf": "" if args.oa_only else None,
    }
    if args.oa_only:
        params["openAccessPdf"] = "true"
    else:
        params.pop("openAccessPdf", None)

    data = _get("paper/search", params)
    if not data:
        return 1

    papers = data.get("data", [])
    total = data.get("total", len(papers))
    print(f"\n[S2 Search] query='{args.query}' total={total} showing={len(papers)}\n")

    results = []
    for p in papers:
        print(_format_paper(p, verbose=args.verbose))
        pdf = (p.get("openAccessPdf") or {}).get("url", "")
        if pdf and args.verbose:
            print(f"         OA PDF: {pdf}")
        print()
        results.append(p)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"query": args.query, "total": total, "papers": results},
                                   indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[S2] Saved → {out}")
    return 0


# ── paper ─────────────────────────────────────────────────────────────────────

def cmd_paper(args: argparse.Namespace) -> int:
    pid = _normalize_id(args.id)
    fields = "title,abstract,authors,year,citationCount,referenceCount,venue,externalIds,tldr,isOpenAccess,openAccessPdf,publicationTypes,fieldsOfStudy,influentialCitationCount"
    data = _get(f"paper/{urllib.parse.quote(pid)}", {"fields": fields})
    if not data:
        print(f"[S2] Paper not found: {pid}")
        return 1

    print(f"\n{'='*60}")
    print(f"Title:    {data.get('title')}")
    print(f"Year:     {data.get('year')}")
    authors = ", ".join(a.get("name", "") for a in (data.get("authors") or [])[:5])
    if len(data.get("authors") or []) > 5:
        authors += f" (+{len(data['authors'])-5} more)"
    print(f"Authors:  {authors}")
    venue = data.get("venue") or ""
    if isinstance(venue, dict):
        venue = venue.get("name", "")
    print(f"Venue:    {venue}")
    print(f"DOI:      {data.get('externalIds', {}).get('DOI', 'N/A')}")
    print(f"Citations:{data.get('citationCount', '?')} (influential: {data.get('influentialCitationCount','?')})")
    print(f"Open Access: {data.get('isOpenAccess', False)}")
    tldr = (data.get("tldr") or {}).get("text", "")
    if tldr:
        print(f"\nTLDR:     {tldr}")
    abstract = data.get("abstract", "")
    if abstract and args.verbose:
        print(f"\nAbstract:\n{abstract[:1000]}{'…' if len(abstract)>1000 else ''}")
    fields_of_study = data.get("fieldsOfStudy") or []
    print(f"\nFields:   {', '.join(fields_of_study)}")
    print(f"S2 ID:    {data.get('paperId','')}")
    print("="*60)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[S2] Saved → {out}")
    return 0


# ── citations ─────────────────────────────────────────────────────────────────

INTENT_LABELS = {
    "background": "📖 Background",
    "methodology": "🔬 Methodology",
    "result": "📊 Result",
}


def cmd_citations(args: argparse.Namespace) -> int:
    """Fetch papers that cite the given paper, with citation intent."""
    pid = _normalize_id(args.id)
    fields = "title,authors,year,citationCount,externalIds,intents,isInfluential,contexts"
    data = _get(f"paper/{urllib.parse.quote(pid)}/citations",
                {"fields": fields, "limit": args.limit})
    if not data:
        print(f"[S2] Paper not found or no citations: {pid}")
        return 1

    cits = data.get("data", [])
    print(f"\n[S2 Citations] {pid} — {len(cits)} citations shown (limit={args.limit})")
    print(f"Legend: {' | '.join(INTENT_LABELS.values())}\n")

    by_intent: dict[str, list] = {"background": [], "methodology": [], "result": [], "unknown": []}
    for c in cits:
        paper = c.get("citingPaper", {})
        intents = c.get("intents", [])
        contexts = c.get("contexts", [])
        is_inf = c.get("isInfluential", False)
        intent_key = intents[0] if intents else "unknown"
        by_intent.setdefault(intent_key, []).append({
            "paper": paper,
            "is_influential": is_inf,
            "contexts": contexts[:2],
        })

    for intent_key, items in sorted(by_intent.items(), key=lambda x: -len(x[1])):
        label = INTENT_LABELS.get(intent_key, f"❓ {intent_key}")
        print(f"{label} ({len(items)})")
        for item in items[:10]:
            p = item["paper"]
            inf_mark = " ★" if item["is_influential"] else ""
            title = p.get("title", "")[:70]
            year = p.get("year", "")
            doi = p.get("externalIds", {}).get("DOI", "")
            print(f"  [{year}] {title}{inf_mark}")
            if doi:
                print(f"         DOI: {doi}")
            if item["contexts"] and args.verbose:
                print(f"         Context: \"{item['contexts'][0][:100]}\"")
        if len(items) > 10:
            print(f"  …{len(items)-10} more")
        print()

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"paper_id": pid, "citations": cits}, indent=2,
                                   ensure_ascii=False), encoding="utf-8")
        print(f"[S2] Saved → {out}")
    return 0


# ── cite-context ──────────────────────────────────────────────────────────────

def cmd_cite_context(args: argparse.Namespace) -> int:
    """
    Summarize HOW this paper is cited in the literature.
    Useful for: is this paper mostly used as background, methodology basis, or directly replicated?
    """
    pid = _normalize_id(args.id)
    data = _get(f"paper/{urllib.parse.quote(pid)}/citations",
                {"fields": "title,year,intents,isInfluential,contexts", "limit": 500})
    if not data:
        return 1

    cits = data.get("data", [])
    total = len(cits)
    intent_counts: dict[str, int] = {}
    influential = 0
    for c in cits:
        for intent in (c.get("intents") or ["unknown"]):
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        if c.get("isInfluential"):
            influential += 1

    print(f"\n[S2 Citation Context] S2 ID={pid}")
    print(f"Total citations sampled: {total} | Influential: {influential}")
    print()
    print("How this paper is cited:")
    for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1]):
        bar = "█" * min(40, int(count / max(total, 1) * 40))
        pct = count / max(total, 1) * 100
        label = INTENT_LABELS.get(intent, f"❓ {intent}")
        print(f"  {label:<25} {count:>4} ({pct:4.1f}%)  {bar}")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "paper_id": pid, "total_sampled": total, "influential": influential,
            "intent_counts": intent_counts,
        }, indent=2), encoding="utf-8")
        print(f"\n[S2] Saved → {out}")
    return 0


# ── references ────────────────────────────────────────────────────────────────

def cmd_references(args: argparse.Namespace) -> int:
    pid = _normalize_id(args.id)
    data = _get(f"paper/{urllib.parse.quote(pid)}/references",
                {"fields": "title,authors,year,citationCount,externalIds", "limit": args.limit})
    if not data:
        return 1

    refs = data.get("data", [])
    print(f"\n[S2 References] {pid} — {len(refs)} references")
    for r in refs:
        p = r.get("citedPaper", {})
        print(_format_paper(p))
    print()

    if args.out:
        out = Path(args.out)
        out.write_text(json.dumps({"paper_id": pid, "references": refs}, indent=2,
                                   ensure_ascii=False), encoding="utf-8")
        print(f"[S2] Saved → {out}")
    return 0


# ── author ────────────────────────────────────────────────────────────────────

def cmd_author(args: argparse.Namespace) -> int:
    # Search by name first
    data = _get("author/search", {"query": args.name, "limit": 5,
                                   "fields": "name,hIndex,citationCount,affiliations,paperCount"})
    if not data or not data.get("data"):
        print(f"[S2] Author not found: {args.name}")
        return 1

    for a in data["data"]:
        aff = ", ".join((a.get("affiliations") or [])[:2])
        print(f"\n  {a.get('name')}  (S2 ID: {a.get('authorId','')})")
        print(f"  h-index: {a.get('hIndex','?')} | Citations: {a.get('citationCount','?')} | Papers: {a.get('paperCount','?')}")
        print(f"  Affiliation: {aff}")

    if args.out:
        out = Path(args.out)
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[S2] Saved → {out}")
    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        prog="insynbio_semantic_scholar",
        description="Semantic Scholar API — citation context, paper intelligence, author lookup",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    # search
    p_s = sub.add_parser("search", help="Full-text paper search")
    p_s.add_argument("--query", required=True)
    p_s.add_argument("--limit", type=int, default=10)
    p_s.add_argument("--year", default=None, help="e.g. 2020-2026")
    p_s.add_argument("--pub-type", default=None, help="JournalArticle|Review|Conference")
    p_s.add_argument("--oa-only", action="store_true", help="Only open-access papers")
    p_s.add_argument("--verbose", action="store_true")
    p_s.add_argument("--out", default=None)
    p_s.set_defaults(func=cmd_search)

    # paper
    p_p = sub.add_parser("paper", help="Paper metadata + TLDR")
    p_p.add_argument("--id", required=True, help="DOI, ArXiv ID, or S2 paper ID")
    p_p.add_argument("--verbose", action="store_true", help="Show full abstract")
    p_p.add_argument("--out", default=None)
    p_p.set_defaults(func=cmd_paper)

    # citations
    p_c = sub.add_parser("citations", help="Incoming citations with intent (background/methodology/result)")
    p_c.add_argument("--id", required=True)
    p_c.add_argument("--limit", type=int, default=50)
    p_c.add_argument("--verbose", action="store_true", help="Show citation context sentences")
    p_c.add_argument("--out", default=None)
    p_c.set_defaults(func=cmd_citations)

    # cite-context
    p_cc = sub.add_parser("cite-context", help="Summary of HOW a paper is cited in the literature")
    p_cc.add_argument("--id", required=True)
    p_cc.add_argument("--out", default=None)
    p_cc.set_defaults(func=cmd_cite_context)

    # references
    p_r = sub.add_parser("references", help="Outgoing references of a paper")
    p_r.add_argument("--id", required=True)
    p_r.add_argument("--limit", type=int, default=50)
    p_r.add_argument("--out", default=None)
    p_r.set_defaults(func=cmd_references)

    # author
    p_a = sub.add_parser("author", help="Author profile + h-index")
    p_a.add_argument("--name", required=True)
    p_a.add_argument("--out", default=None)
    p_a.set_defaults(func=cmd_author)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
