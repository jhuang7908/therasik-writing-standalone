"""
load_papers.py — Step 1 of Week 2: pull full PMC JATS XML for every PMID
in corpus_manifest.json, parse each article with jats_extract.py, and write
one JSON file per paper to ``papers_raw/<journal_key>/``.

This script is **purely code-driven** — no LLM calls. It only reads from NCBI
and writes structured JSON to disk. The output files become the input for
``run_article_profiles.py`` (Claude / Sonnet).

Usage
-----
    # Smoke-test: 4 papers per journal (12 total)
    python services/writing_memory/ingest/load_papers.py --smoke

    # Full corpus (150 papers, ~25-35 min depending on NCBI speed)
    python services/writing_memory/ingest/load_papers.py

    # Specific journals only
    python services/writing_memory/ingest/load_papers.py --journals pnas elife

    # Resume (skip already-downloaded papers)
    python services/writing_memory/ingest/load_papers.py --resume

Environment variables
---------------------
    NCBI_API_KEY    raises eUtils rate-limit from 3/s to 10/s
    NCBI_TOOL       polite-pool tool name
    NCBI_EMAIL      polite-pool contact email

Output
------
    services/writing_memory/papers_raw/
        pnas/
            <pmid>.json
        elife/
            <pmid>.json
        plos_med/
            <pmid>.json
    services/writing_memory/papers_raw/_load_report.json
        summary of what succeeded, failed, and why

Each <pmid>.json contains:
    {
      "pmid": "...",
      "journal_key": "pnas",
      "title": "...",
      "abstract": "...",
      "discussion": "...",
      "conclusion": "...",
      "figure_legends": [...],
      "doi": "...",
      "pmcid": "...",
      "year": 2024,
      "sections_available": {...},
      "text_provenance": "pmc_jats",
      "char_counts": {"abstract": N, "discussion": N, ...}
    }
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from lxml import etree

# Local imports
_HERE = Path(__file__).resolve().parent
_SERVICE_ROOT = _HERE.parent
sys.path.insert(0, str(_SERVICE_ROOT.parent.parent))  # repo root

from services.writing_memory.ingest.jats_extract import extract, strip_inline_refs


# ---------------------------------------------------------------------------
# eUtils helpers (shared with probe script)
# ---------------------------------------------------------------------------

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")
DEFAULT_TOOL = os.environ.get("NCBI_TOOL", "insynbio_writing_memory")
DEFAULT_EMAIL = os.environ.get("NCBI_EMAIL", "")
RATE_DELAY = 0.11 if NCBI_API_KEY else 0.35


def _params(extra: dict[str, Any]) -> dict[str, Any]:
    base: dict[str, Any] = {"tool": DEFAULT_TOOL}
    if DEFAULT_EMAIL:
        base["email"] = DEFAULT_EMAIL
    if NCBI_API_KEY:
        base["api_key"] = NCBI_API_KEY
    base.update(extra)
    return base


def _post(url: str, data: dict[str, Any], timeout: int = 30) -> requests.Response:
    r = requests.post(url, data=_params(data), timeout=timeout)
    r.raise_for_status()
    time.sleep(RATE_DELAY)
    return r


def _get(url: str, params: dict[str, Any], timeout: int = 45) -> requests.Response:
    r = requests.get(url, params=_params(params), timeout=timeout)
    r.raise_for_status()
    time.sleep(RATE_DELAY)
    return r


# ---------------------------------------------------------------------------
# PMID → PMCID (batched POST, chunks of 80)
# ---------------------------------------------------------------------------

def _pmcid_from_elink_response(data: dict[str, Any]) -> str | None:
    """Extract the first PMC link for a single-PMID elink JSON response."""
    for ls in data.get("linksets", []):
        for entry in ls.get("linksetdbs", []):
            if entry.get("dbto") != "pmc":
                continue
            links = entry.get("links", [])
            if links:
                return f"PMC{links[0]}"
    return None


def pmids_to_pmcids(pmids: list[str]) -> dict[str, str]:
    """
    Resolve PMID → PMCID one-at-a-time via elink.

    Batch elink does not guarantee a 1:1 pair in its JSON output when only a
    subset of the input PMIDs have PMC records. Individual calls are the only
    reliable approach.

    With NCBI_API_KEY set (10 req/s) and RATE_DELAY=0.11 s, 150 PMIDs ≈ 17 s.
    """
    mapping: dict[str, str] = {}
    for pmid in pmids:
        try:
            r = _post(EUTILS + "elink.fcgi", {
                "dbfrom": "pubmed", "db": "pmc",
                "id": pmid, "retmode": "json",
            })
            pmcid = _pmcid_from_elink_response(r.json())
            if pmcid:
                mapping[pmid] = pmcid
        except Exception:
            continue
    return mapping


# ---------------------------------------------------------------------------
# Fetch + enrich one article
# ---------------------------------------------------------------------------

def fetch_and_parse(pmid: str, pmcid: str, journal_key: str) -> dict[str, Any] | None:
    """
    Download PMC JATS XML for *pmcid*, parse it, and return a structured
    dict suitable for saving as JSON. Returns None on unrecoverable error.
    """
    numeric = pmcid.replace("PMC", "")
    try:
        r = _get(EUTILS + "efetch.fcgi", {
            "db": "pmc", "id": numeric, "retmode": "xml",
        }, timeout=60)
        xml_bytes = r.content
    except Exception as exc:
        return {"_error": f"efetch failed: {exc}", "pmid": pmid, "pmcid": pmcid}

    art = extract(xml_bytes)

    # Override pmid from probe data if JATS doesn't carry it
    if not art.pmid:
        art.pmid = pmid
    if not art.pmcid:
        art.pmcid = pmcid

    doc = asdict(art)
    doc["journal_key"] = journal_key

    # Strip inline citation markers from text fields before saving
    for field in ("abstract", "discussion", "conclusion"):
        if doc.get(field):
            doc[field] = strip_inline_refs(doc[field])
    doc["figure_legends"] = [
        strip_inline_refs(l) for l in (doc.get("figure_legends") or [])
    ]

    # Character counts — useful for estimating Claude token usage downstream
    doc["char_counts"] = {
        "abstract":        len(doc.get("abstract") or ""),
        "discussion":      len(doc.get("discussion") or ""),
        "conclusion":      len(doc.get("conclusion") or ""),
        "figure_legends":  sum(len(l) for l in doc.get("figure_legends") or []),
    }

    return doc


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Download + parse 150 PMC full-text articles into papers_raw/."
    )
    ap.add_argument("--manifest", type=Path,
                    default=_HERE / "_out" / "corpus_manifest.json",
                    help="Path to corpus_manifest.json")
    ap.add_argument("--out-dir", type=Path,
                    default=_SERVICE_ROOT / "papers_raw",
                    help="Root directory for output JSON files")
    ap.add_argument("--journals", nargs="*", default=None,
                    help="Restrict to journal keys (e.g. pnas elife)")
    ap.add_argument("--smoke", action="store_true",
                    help="Smoke-test mode: only download 4 papers per journal")
    ap.add_argument("--resume", action="store_true",
                    help="Skip PMIDs whose output JSON already exists")
    args = ap.parse_args(argv)

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    journals = manifest["journals"]

    if args.journals:
        journals = {k: v for k, v in journals.items() if k in args.journals}

    def _pmids_for_journal(jinfo: dict[str, Any]) -> list[tuple[str, str]]:
        """Return [(pmid, article_type), ...] deduplicated by pmid (first type wins)."""
        pairs: list[tuple[str, str]] = []
        seen: set[str] = set()
        by_type = jinfo.get("by_article_type")
        if by_type:
            for atype, block in by_type.items():
                for pmid in block.get("qualified_pmids", []):
                    if pmid not in seen:
                        seen.add(pmid)
                        pairs.append((pmid, atype))
        else:
            for pmid in jinfo.get("qualified_pmids", []):
                if pmid not in seen:
                    seen.add(pmid)
                    pairs.append((pmid, "research"))
        return pairs

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "smoke": args.smoke,
        "journals": {},
    }

    total_ok = total_fail = 0

    for journal_key, jinfo in journals.items():
        jdir = out_dir / journal_key
        jdir.mkdir(parents=True, exist_ok=True)

        pmid_pairs = _pmids_for_journal(jinfo)
        if args.smoke:
            pmid_pairs = pmid_pairs[:4]

        pmids = [p for p, _ in pmid_pairs]
        pmid_article_type = {p: t for p, t in pmid_pairs}

        # ---- resolve PMCIDs -----------------------------------------------
        print(f"\n[{journal_key}] resolving {len(pmids)} PMIDs → PMCIDs ...")
        pmid_to_pmcid = pmids_to_pmcids(pmids)
        print(f"[{journal_key}] resolved {len(pmid_to_pmcid)}/{len(pmids)}")

        ok = fail = 0
        fail_details: list[dict[str, str]] = []

        for idx, pmid in enumerate(pmids, 1):
            out_path = jdir / f"{pmid}.json"

            if args.resume and out_path.exists():
                print(f"  [{idx}/{len(pmids)}] {pmid} — skip (exists)")
                ok += 1
                continue

            pmcid = pmid_to_pmcid.get(pmid)
            if not pmcid:
                print(f"  [{idx}/{len(pmids)}] {pmid} — SKIP (no PMCID)")
                fail += 1
                fail_details.append({"pmid": pmid, "reason": "no_pmcid"})
                continue

            print(f"  [{idx}/{len(pmids)}] {pmid} ({pmcid}) ...", end=" ", flush=True)
            doc = fetch_and_parse(pmid, pmcid, journal_key)
            if doc is not None and "_error" not in doc:
                doc["article_type"] = pmid_article_type.get(pmid, "research")

            if doc is None or "_error" in doc:
                reason = (doc or {}).get("_error", "unknown")
                print(f"FAIL — {reason}")
                fail += 1
                fail_details.append({"pmid": pmid, "pmcid": pmcid, "reason": reason})
                continue

            # Quality check — relaxed for non-research types
            atype = doc.get("article_type", "research")
            has_abs = bool(doc.get("abstract"))
            has_disc = bool(doc.get("discussion") or doc.get("conclusion"))
            if atype == "research" and not (has_abs and has_disc):
                print(f"WARN (abs={has_abs} disc/concl={has_disc})")
            elif not has_abs:
                print(f"WARN (no abstract, type={atype})")
            else:
                abs_chars = doc["char_counts"]["abstract"]
                disc_chars = doc["char_counts"]["discussion"] or doc["char_counts"]["conclusion"]
                print(f"OK  type={atype}  abs={abs_chars}c  disc/concl={disc_chars}c")

            out_path.write_text(
                json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            ok += 1

        total_ok += ok
        total_fail += fail
        report["journals"][journal_key] = {
            "total": len(pmids),
            "ok": ok,
            "fail": fail,
            "failures": fail_details,
        }
        print(f"[{journal_key}] done: ok={ok}  fail={fail}")

    # ---- write load report -----------------------------------------------
    report["total_ok"] = total_ok
    report["total_fail"] = total_fail
    report_path = out_dir / "_load_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nLoad report: {report_path}")
    print(f"Total: ok={total_ok}  fail={total_fail}")

    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
