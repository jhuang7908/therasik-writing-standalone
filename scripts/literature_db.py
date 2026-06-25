"""
literature_db.py
================
Local literature database for the TheraSIK academic writing suite.

Features:
  - SQLite storage with FTS5 full-text search over title + abstract + full text
  - TF-IDF semantic search using numpy (no external ML deps)
  - Fetch metadata by DOI (CrossRef REST API) or PMID (PubMed E-utilities)
  - Import full text from PDF files (requires pdfplumber)
  - Export selected papers to project references.csv
  - CLI and Python API

Usage (CLI):
  python literature_db.py init [--db path]
  python literature_db.py add-doi 10.1038/s41586-021-03819-2 [--db path]
  python literature_db.py add-pmid 34912118 [--db path]
  python literature_db.py search "antibody complement activation" [--db path] [--limit 10]
  python literature_db.py get 10.1038/nature12345 [--db path]
  python literature_db.py import-pdf paper.pdf --doi 10.1/x [--db path]
  python literature_db.py export-csv paper_id1 paper_id2 --out refs.csv [--db path]
  python literature_db.py list [--db path] [--limit 50]
  python literature_db.py stats [--db path]

Default DB path: {skill_dir}/assets/literature_db/literature.db
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import pickle
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB = SKILL_DIR / "assets" / "literature_db" / "literature.db"
TFIDF_INDEX = SKILL_DIR / "assets" / "literature_db" / "tfidf_index.pkl"

CROSSREF_API = "https://api.crossref.org/works/{doi}"
PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
UA = "therasik-literature-db/1.0 (mailto:research@therasik.io)"


# -- Database setup ----------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    paper_id    TEXT PRIMARY KEY,
    doi         TEXT UNIQUE,
    pmid        TEXT UNIQUE,
    pmcid       TEXT,
    title       TEXT NOT NULL,
    authors     TEXT,
    year        INTEGER,
    journal     TEXT,
    volume      TEXT,
    issue       TEXT,
    pages       TEXT,
    abstract    TEXT,
    keywords    TEXT,
    url         TEXT,
    full_text   TEXT,
    added_at    TEXT,
    source      TEXT
);

CREATE TABLE IF NOT EXISTS project_links (
    project_id  TEXT,
    paper_id    TEXT,
    added_at    TEXT,
    PRIMARY KEY (project_id, paper_id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(
    paper_id UNINDEXED,
    title,
    abstract,
    keywords,
    full_text,
    content=papers,
    content_rowid=rowid
);

CREATE TRIGGER IF NOT EXISTS papers_fts_insert AFTER INSERT ON papers BEGIN
    INSERT INTO papers_fts(rowid, paper_id, title, abstract, keywords, full_text)
    VALUES (new.rowid, new.paper_id, new.title, COALESCE(new.abstract,''),
            COALESCE(new.keywords,''), COALESCE(new.full_text,''));
END;

CREATE TRIGGER IF NOT EXISTS papers_fts_update AFTER UPDATE ON papers BEGIN
    INSERT INTO papers_fts(papers_fts, rowid, paper_id, title, abstract, keywords, full_text)
    VALUES ('delete', old.rowid, old.paper_id, old.title, COALESCE(old.abstract,''),
            COALESCE(old.keywords,''), COALESCE(old.full_text,''));
    INSERT INTO papers_fts(rowid, paper_id, title, abstract, keywords, full_text)
    VALUES (new.rowid, new.paper_id, new.title, COALESCE(new.abstract,''),
            COALESCE(new.keywords,''), COALESCE(new.full_text,''));
END;

CREATE TRIGGER IF NOT EXISTS papers_fts_delete AFTER DELETE ON papers BEGIN
    INSERT INTO papers_fts(papers_fts, rowid, paper_id, title, abstract, keywords, full_text)
    VALUES ('delete', old.rowid, old.paper_id, old.title, COALESCE(old.abstract,''),
            COALESCE(old.keywords,''), COALESCE(old.full_text,''));
END;
"""


def get_db(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


# -- Fetch from external APIs ------------------------------------------------

def _http_get(url: str, params: dict | None = None, timeout: int = 15) -> bytes:
    if params:
        query = "&".join(f"{k}={urllib.request.quote(str(v))}" for k, v in params.items())
        url = f"{url}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_crossref(doi: str) -> dict:
    """Fetch paper metadata from CrossRef by DOI. Returns normalized dict."""
    doi_clean = re.sub(r"^https?://doi\.org/", "", doi.strip())
    url = CROSSREF_API.format(doi=urllib.request.quote(doi_clean, safe="/"))
    try:
        data = json.loads(_http_get(url))
        msg = data.get("message", {})
    except Exception as exc:
        return {"error": str(exc), "doi": doi_clean}

    def first(lst):
        return lst[0] if lst else ""

    authors = []
    for a in msg.get("author", []):
        name = f"{a.get('family', '')}, {a.get('given', '')}".strip(", ")
        if name:
            authors.append(name)

    date_parts = msg.get("published", msg.get("published-print", msg.get("published-online", {})))
    year = None
    dp = date_parts.get("date-parts", [[]])
    if dp and dp[0]:
        year = dp[0][0]

    return {
        "doi": doi_clean,
        "title": first(msg.get("title", [])),
        "authors": authors,
        "year": year,
        "journal": msg.get("container-title", [""])[0] if msg.get("container-title") else "",
        "volume": msg.get("volume", ""),
        "issue": msg.get("issue", ""),
        "pages": msg.get("page", ""),
        "abstract": re.sub(r"<[^>]+>", "", msg.get("abstract", "")),
        "url": msg.get("URL", ""),
        "keywords": "; ".join(msg.get("subject", [])),
    }


def fetch_pubmed(pmid: str) -> dict:
    """Fetch paper metadata from PubMed by PMID. Returns normalized dict."""
    pmid = pmid.strip()
    try:
        xml_bytes = _http_get(PUBMED_EFETCH, {
            "db": "pubmed", "id": pmid, "rettype": "xml", "retmode": "xml"
        })
        root = ET.fromstring(xml_bytes)
    except Exception as exc:
        return {"error": str(exc), "pmid": pmid}

    art = root.find(".//PubmedArticle/MedlineCitation/Article")
    if art is None:
        return {"error": "Article not found", "pmid": pmid}

    title_el = art.find("ArticleTitle")
    title = "".join(title_el.itertext()) if title_el is not None else ""

    abstract_parts = []
    for abs_text in art.findall(".//AbstractText"):
        label = abs_text.get("Label", "")
        text = "".join(abs_text.itertext())
        if label:
            abstract_parts.append(f"{label}: {text}")
        else:
            abstract_parts.append(text)
    abstract = " ".join(abstract_parts)

    authors = []
    for author in art.findall(".//Author"):
        last = author.findtext("LastName", "")
        fore = author.findtext("ForeName", "")
        if last:
            authors.append(f"{last}, {fore}".strip(", "))

    pub_date = art.find(".//PubDate")
    year = None
    if pub_date is not None:
        year_el = pub_date.find("Year")
        if year_el is not None:
            try:
                year = int(year_el.text)
            except (ValueError, TypeError):
                pass

    journal_el = root.find(".//Journal/Title")
    journal = journal_el.text if journal_el is not None else ""

    doi_el = root.find(".//ArticleId[@IdType='doi']")
    doi = doi_el.text if doi_el is not None else ""

    pmcid_el = root.find(".//ArticleId[@IdType='pmc']")
    pmcid = pmcid_el.text if pmcid_el is not None else ""

    kw_list = [kw.text for kw in root.findall(".//Keyword") if kw.text]

    return {
        "pmid": pmid,
        "doi": doi,
        "pmcid": pmcid,
        "title": title,
        "authors": authors,
        "year": year,
        "journal": journal,
        "abstract": abstract,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "keywords": "; ".join(kw_list),
    }


# -- Database operations -----------------------------------------------------

def _gen_id(doi: str | None, pmid: str | None, title: str) -> str:
    import hashlib
    key = doi or pmid or title
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def add_paper(conn: sqlite3.Connection, meta: dict) -> tuple[str, bool]:
    """Insert or update a paper. Returns (paper_id, is_new)."""
    doi = (meta.get("doi") or "").strip() or None
    pmid = (meta.get("pmid") or "").strip() or None
    title = (meta.get("title") or "").strip()
    if not title:
        raise ValueError("Paper must have a title")

    paper_id = _gen_id(doi, pmid, title)
    authors_json = json.dumps(meta.get("authors") or [], ensure_ascii=False)
    now = datetime.now(timezone.utc).isoformat()

    existing = conn.execute("SELECT paper_id FROM papers WHERE paper_id=?", (paper_id,)).fetchone()
    is_new = existing is None

    conn.execute("""
        INSERT INTO papers (paper_id, doi, pmid, pmcid, title, authors, year, journal,
                            volume, issue, pages, abstract, keywords, url, added_at, source)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(paper_id) DO UPDATE SET
            doi=COALESCE(excluded.doi, doi),
            pmid=COALESCE(excluded.pmid, pmid),
            pmcid=COALESCE(excluded.pmcid, pmcid),
            abstract=COALESCE(NULLIF(excluded.abstract,''), abstract),
            keywords=COALESCE(NULLIF(excluded.keywords,''), keywords),
            url=COALESCE(NULLIF(excluded.url,''), url)
    """, (
        paper_id, doi, pmid, meta.get("pmcid") or None, title,
        authors_json, meta.get("year"), meta.get("journal") or None,
        meta.get("volume") or None, meta.get("issue") or None, meta.get("pages") or None,
        meta.get("abstract") or None, meta.get("keywords") or None,
        meta.get("url") or None, now, meta.get("source", "manual")
    ))
    conn.commit()
    return paper_id, is_new


def import_full_text_pdf(conn: sqlite3.Connection, pdf_path: Path,
                         paper_id: str | None = None,
                         doi: str | None = None) -> str:
    """Extract text from PDF and store in database."""
    try:
        import pdfplumber
    except ImportError:
        raise RuntimeError("pdfplumber is required: pip install pdfplumber")

    with pdfplumber.open(str(pdf_path)) as pdf:
        pages = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    full_text = "\n\n".join(pages)

    if doi and not paper_id:
        row = conn.execute("SELECT paper_id FROM papers WHERE doi=?", (doi,)).fetchone()
        if row:
            paper_id = row["paper_id"]

    if not paper_id:
        raise ValueError("Provide paper_id or doi to link the PDF text")

    conn.execute("UPDATE papers SET full_text=? WHERE paper_id=?", (full_text, paper_id))
    conn.commit()
    _rebuild_tfidf(conn)
    return paper_id


def search_fts(conn: sqlite3.Connection, query: str, limit: int = 10) -> list[dict]:
    """Full-text search using SQLite FTS5."""
    rows = conn.execute("""
        SELECT p.paper_id, p.doi, p.pmid, p.title, p.authors, p.year, p.journal,
               p.abstract, p.keywords,
               rank AS score
        FROM papers_fts f
        JOIN papers p ON p.paper_id = f.paper_id
        WHERE papers_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (query, limit)).fetchall()
    return [dict(r) for r in rows]


def search_tfidf(query: str, limit: int = 10,
                 index_path: Path = TFIDF_INDEX) -> list[dict]:
    """TF-IDF semantic search (requires built index)."""
    try:
        import numpy as np
    except ImportError:
        return []
    if not index_path.exists():
        return []
    with open(index_path, "rb") as f:
        idx = pickle.load(f)
    vocab = idx["vocab"]
    matrix = idx["matrix"]   # shape (n_docs, n_terms)
    paper_ids = idx["paper_ids"]

    tokens = _tokenize(query)
    qvec = np.zeros(len(vocab))
    for t in tokens:
        if t in vocab:
            qvec[vocab[t]] = 1.0
    norm = np.linalg.norm(qvec)
    if norm == 0:
        return []
    qvec /= norm

    scores = matrix.dot(qvec)
    top_k = np.argsort(scores)[::-1][:limit]
    return [{"paper_id": paper_ids[i], "tfidf_score": float(scores[i])}
            for i in top_k if scores[i] > 0]


def search(conn: sqlite3.Connection, query: str, limit: int = 10,
           year_from: int | None = None, year_to: int | None = None,
           journal: str | None = None) -> list[dict]:
    """Combined search: FTS5 + TF-IDF, deduplicated and ranked."""
    try:
        fts_results = search_fts(conn, query, limit * 2)
    except Exception:
        fts_results = []

    tfidf_results = search_tfidf(query, limit * 2)

    seen: dict[str, dict] = {}
    for r in fts_results:
        seen[r["paper_id"]] = r

    for r in tfidf_results:
        pid = r["paper_id"]
        if pid in seen:
            seen[pid]["tfidf_score"] = r["tfidf_score"]
        else:
            row = conn.execute("SELECT * FROM papers WHERE paper_id=?", (pid,)).fetchone()
            if row:
                merged = dict(row)
                merged["tfidf_score"] = r["tfidf_score"]
                seen[pid] = merged

    results = list(seen.values())

    if year_from:
        results = [r for r in results if r.get("year") and r["year"] >= year_from]
    if year_to:
        results = [r for r in results if r.get("year") and r["year"] <= year_to]
    if journal:
        jl = journal.lower()
        results = [r for r in results
                   if r.get("journal") and jl in r["journal"].lower()]

    return results[:limit]


def get_paper_by_id(conn: sqlite3.Connection, identifier: str) -> dict | None:
    """Get paper by paper_id, DOI, or PMID."""
    row = (conn.execute("SELECT * FROM papers WHERE paper_id=?", (identifier,)).fetchone()
           or conn.execute("SELECT * FROM papers WHERE doi=?", (identifier,)).fetchone()
           or conn.execute("SELECT * FROM papers WHERE pmid=?", (identifier,)).fetchone())
    if row is None:
        return None
    r = dict(row)
    try:
        r["authors"] = json.loads(r.get("authors") or "[]")
    except (json.JSONDecodeError, TypeError):
        r["authors"] = []
    return r


def export_to_references_csv(conn: sqlite3.Connection,
                              paper_ids: list[str],
                              out_path: Path) -> int:
    """Export papers to references.csv format used by run_reference_claim_qa.py."""
    rows = []
    for pid in paper_ids:
        p = get_paper_by_id(conn, pid)
        if p:
            authors = p.get("authors") or []
            if isinstance(authors, str):
                try:
                    authors = json.loads(authors)
                except Exception:
                    authors = [authors]
            rows.append({
                "id": p.get("doi") or p.get("pmid") or p["paper_id"],
                "title": p.get("title", ""),
                "authors": "; ".join(authors) if isinstance(authors, list) else str(authors),
                "year": p.get("year", ""),
                "doi": p.get("doi", ""),
                "pmid": p.get("pmid", ""),
                "pmcid": p.get("pmcid", ""),
                "url": p.get("url", ""),
                "journal": p.get("journal", ""),
                "status": "PENDING_REVIEW",
            })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["id", "title", "authors", "year", "doi", "pmid", "pmcid", "url", "journal", "status"]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


# -- TF-IDF index ------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = text.split()
    stopwords = {
        "a","an","the","and","or","but","in","on","at","to","for","of","with",
        "by","from","is","are","was","were","be","been","being","have","has",
        "had","do","does","did","will","would","could","should","may","might",
        "this","that","these","those","it","its","as","into","through","during",
        "not","no","nor","so","yet","both","either","neither","each","few",
        "more","most","other","some","such","than","then","too","very","can",
        "we","our","they","their","which","who","whom","how","what","when","where",
    }
    return [t for t in tokens if t not in stopwords and len(t) > 2]


def _rebuild_tfidf(conn: sqlite3.Connection,
                   index_path: Path = TFIDF_INDEX) -> None:
    """Build or rebuild TF-IDF index from all papers in database."""
    try:
        import numpy as np
    except ImportError:
        return

    rows = conn.execute(
        "SELECT paper_id, title, abstract, keywords, full_text FROM papers"
    ).fetchall()

    if not rows:
        return

    docs = []
    paper_ids = []
    for r in rows:
        text = " ".join(filter(None, [r["title"], r["abstract"],
                                      r["keywords"], r["full_text"]]))
        docs.append(_tokenize(text))
        paper_ids.append(r["paper_id"])

    # Build vocabulary
    from collections import Counter
    df: Counter = Counter()
    for doc in docs:
        df.update(set(doc))

    # Keep terms appearing in at least 1 doc and fewer than 90% of docs
    n = len(docs)
    vocab = {term: i for i, (term, count) in enumerate(df.items())
             if 1 <= count <= max(1, int(0.9 * n))}

    # TF-IDF matrix
    matrix = np.zeros((n, len(vocab)), dtype=np.float32)
    for d_idx, doc in enumerate(docs):
        tf: Counter = Counter(doc)
        total = len(doc) or 1
        for term, count in tf.items():
            if term in vocab:
                tf_val = count / total
                idf_val = math.log((n + 1) / (df[term] + 1)) + 1
                matrix[d_idx, vocab[term]] = tf_val * idf_val

    # L2 normalize rows
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1
    matrix /= norms

    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "wb") as f:
        pickle.dump({"vocab": vocab, "matrix": matrix, "paper_ids": paper_ids}, f)


# -- CLI ---------------------------------------------------------------------

def cmd_init(args):
    conn = get_db(Path(args.db))
    _rebuild_tfidf(conn)
    print(f"Database initialized: {args.db}")


def cmd_add_doi(args):
    conn = get_db(Path(args.db))
    print(f"Fetching DOI: {args.doi} ...")
    meta = fetch_crossref(args.doi)
    if "error" in meta:
        print(f"ERROR: {meta['error']}", file=sys.stderr)
        return 1
    meta["source"] = "crossref"
    pid, is_new = add_paper(conn, meta)
    _rebuild_tfidf(conn)
    print(json.dumps({"paper_id": pid, "is_new": is_new, "title": meta.get("title")},
                     ensure_ascii=False))
    return 0


def cmd_add_pmid(args):
    conn = get_db(Path(args.db))
    print(f"Fetching PMID: {args.pmid} ...")
    meta = fetch_pubmed(args.pmid)
    if "error" in meta:
        print(f"ERROR: {meta['error']}", file=sys.stderr)
        return 1
    meta["source"] = "pubmed"
    pid, is_new = add_paper(conn, meta)
    _rebuild_tfidf(conn)
    print(json.dumps({"paper_id": pid, "is_new": is_new, "title": meta.get("title")},
                     ensure_ascii=False))
    return 0


def cmd_search(args):
    conn = get_db(Path(args.db))
    results = search(conn, args.query, limit=args.limit,
                     year_from=args.year_from, year_to=args.year_to,
                     journal=args.journal)
    for r in results:
        authors = r.get("authors") or "[]"
        if isinstance(authors, str):
            try:
                authors = json.loads(authors)
            except Exception:
                authors = []
        first_author = authors[0].split(",")[0] if authors else "?"
        print(f"[{r.get('year','?')}] {r.get('title','?')} -- {first_author} et al.")
        print(f"  DOI: {r.get('doi','')}  PMID: {r.get('pmid','')}")
        print(f"  Journal: {r.get('journal','')}  paper_id: {r.get('paper_id','')}")
        print()
    print(f"Total: {len(results)}")
    return 0


def cmd_get(args):
    conn = get_db(Path(args.db))
    p = get_paper_by_id(conn, args.identifier)
    if not p:
        print("Not found", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(p, ensure_ascii=False, indent=2))
    else:
        print(f"Title:    {p.get('title')}")
        print(f"Authors:  {'; '.join(p.get('authors') or [])}")
        print(f"Year:     {p.get('year')}")
        print(f"Journal:  {p.get('journal')}")
        print(f"DOI:      {p.get('doi')}")
        print(f"PMID:     {p.get('pmid')}")
        print(f"Abstract: {(p.get('abstract') or '')[:300]}...")
    return 0


def cmd_import_pdf(args):
    conn = get_db(Path(args.db))
    pid = import_full_text_pdf(conn, Path(args.pdf), paper_id=args.paper_id, doi=args.doi)
    print(f"Full text imported: paper_id={pid}")
    return 0


def cmd_export_csv(args):
    conn = get_db(Path(args.db))
    n = export_to_references_csv(conn, args.paper_ids, Path(args.out))
    print(f"Exported {n} papers to {args.out}")
    return 0


def cmd_list(args):
    conn = get_db(Path(args.db))
    rows = conn.execute(
        "SELECT paper_id, doi, pmid, title, year, journal FROM papers "
        "ORDER BY year DESC, title LIMIT ?", (args.limit,)
    ).fetchall()
    for r in rows:
        print(f"[{r['year'] or '?'}] {r['title']}")
        print(f"  {r['paper_id']}  DOI={r['doi'] or '-'}  PMID={r['pmid'] or '-'}")
    print(f"\n{len(rows)} papers shown")
    return 0


def cmd_stats(args):
    conn = get_db(Path(args.db))
    total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    with_abstract = conn.execute("SELECT COUNT(*) FROM papers WHERE abstract IS NOT NULL AND abstract != ''").fetchone()[0]
    with_full_text = conn.execute("SELECT COUNT(*) FROM papers WHERE full_text IS NOT NULL AND full_text != ''").fetchone()[0]
    with_doi = conn.execute("SELECT COUNT(*) FROM papers WHERE doi IS NOT NULL").fetchone()[0]
    print(f"Total papers:     {total}")
    print(f"With abstract:    {with_abstract}")
    print(f"With full text:   {with_full_text}")
    print(f"With DOI:         {with_doi}")
    print(f"DB path:          {args.db}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="TheraSIK literature database")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to SQLite database")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("init")

    p_doi = sub.add_parser("add-doi")
    p_doi.add_argument("doi")

    p_pmid = sub.add_parser("add-pmid")
    p_pmid.add_argument("pmid")

    p_search = sub.add_parser("search")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=10)
    p_search.add_argument("--year-from", type=int, default=None)
    p_search.add_argument("--year-to", type=int, default=None)
    p_search.add_argument("--journal", default=None)

    p_get = sub.add_parser("get")
    p_get.add_argument("identifier")
    p_get.add_argument("--json", action="store_true")

    p_pdf = sub.add_parser("import-pdf")
    p_pdf.add_argument("pdf")
    p_pdf.add_argument("--doi", default=None)
    p_pdf.add_argument("--paper-id", default=None)

    p_exp = sub.add_parser("export-csv")
    p_exp.add_argument("paper_ids", nargs="+")
    p_exp.add_argument("--out", required=True)

    p_list = sub.add_parser("list")
    p_list.add_argument("--limit", type=int, default=50)

    sub.add_parser("stats")

    args = parser.parse_args()
    if args.cmd is None:
        parser.print_help()
        return 2

    dispatch = {
        "init": cmd_init, "add-doi": cmd_add_doi, "add-pmid": cmd_add_pmid,
        "search": cmd_search, "get": cmd_get, "import-pdf": cmd_import_pdf,
        "export-csv": cmd_export_csv, "list": cmd_list, "stats": cmd_stats,
    }
    return dispatch[args.cmd](args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
