"""
PMC full-text hit-rate probe for the Writing Memory MVP.

Goal: for each target journal, determine whether 50 papers with confirmed
PMC JATS full text (containing Abstract + Discussion/Conclusion) are reachable
through PubMed eUtils within the last N years.

This script is read-only against external APIs and writes one JSON report
to ``services/writing_memory/ingest/_out/pmc_hitrate_<timestamp>.json``.

Usage
-----
    python services/writing_memory/ingest/probe_pmc_hitrate.py \
        --years 5 --candidates 100 --target 50

Env vars (optional but recommended)
-----------------------------------
    NCBI_API_KEY     raises eUtils rate limit from 3/s to 10/s
    NCBI_TOOL        polite-pool tool name (default: insynbio_writing_memory)
    NCBI_EMAIL       polite-pool contact email

Anti-hallucination rule
-----------------------
This script does NOT generate any content. It only counts what PubMed/PMC
actually returns and writes the counts to disk.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from lxml import etree


EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
DEFAULT_TOOL = os.environ.get("NCBI_TOOL", "insynbio_writing_memory")
DEFAULT_EMAIL = os.environ.get("NCBI_EMAIL", "")
NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")
RATE_DELAY = 0.11 if NCBI_API_KEY else 0.35  # seconds between calls


# --- Target journals --------------------------------------------------------
# Each entry uses ``term`` exactly as PubMed expects. We deliberately accept
# both modern and legacy journal-name forms because PubMed indexes both.
# PubMed publication-type filters appended to esearch query.
# MVP research corpus: do NOT exclude by ptyp in classic mode — JATS section
# gate is the real filter. Aggressive NOT Review broke PNAS hit-rate (2026-05-25).
ARTICLE_TYPE_FILTERS: dict[str, str] = {
    "research": '"Journal Article"[Publication Type]',
    "review": 'Review[ptyp]',
    "case_report": '"Case Reports"[ptyp]',
    "letter": '(Letter[ptyp] OR Comment[ptyp] OR Editorial[ptyp])',
}

# MVP default: hunt **confirmed free PMC JATS** in an older "classic" window.
# PNAS has a ~6-month PMC deposit embargo on many papers — recent search fails.
CORPUS_STRATEGIES: dict[str, dict[str, Any]] = {
    "classic": {
        "description": "Free PMC full text in a stable older date window (MVP default)",
        "oa_filters": (
            '"free full text"[filter] AND "pubmed pmc open access"[filter]'
        ),
        "sort": "pub_date",
        "default_candidates": 200,
    },
    "recent": {
        "description": "Last N years, newest first (eLife/PLOS OK; PNAS often SHORT)",
        "oa_filters": '"pubmed pmc open access"[filter]',
        "sort": "pub_date",
        "default_candidates": 120,
    },
}

JOURNALS: list[dict[str, str]] = [
    {
        "key": "pnas",
        "display": "Proceedings of the National Academy of Sciences",
        "term": '("Proc Natl Acad Sci U S A"[Journal])',
        "notes": "6-month PMC embargo — classic window 2010:2022",
        "classic_pdat": "2010:2022",
        "recent_years": 8,
    },
    {
        "key": "elife",
        "display": "eLife",
        "term": '("Elife"[Journal] OR "eLife"[Journal])',
        "notes": "Immediate OA, Full PMC participation",
        "classic_pdat": "2012:2023",
        "recent_years": 10,
    },
    {
        "key": "plos_med",
        "display": "PLOS Medicine",
        "term": '("PLoS Med"[Journal] OR "PLOS Med"[Journal])',
        "notes": "Immediate OA, Full PMC participation",
        "classic_pdat": "2010:2023",
        "recent_years": 10,
    },
]


@dataclass
class JournalReport:
    key: str
    display: str
    query: str
    candidate_pmids: int = 0
    with_pmcid: int = 0
    xml_fetched: int = 0
    with_abstract: int = 0
    with_discussion_or_conclusion: int = 0
    with_figure_legends: int = 0
    fully_qualified: int = 0  # has abstract AND (discussion or conclusion)
    qualified_pmids: list[str] = field(default_factory=list)
    sample_failures: list[dict[str, str]] = field(default_factory=list)


def _params(extra: dict[str, Any]) -> dict[str, Any]:
    base: dict[str, Any] = {"tool": DEFAULT_TOOL}
    if DEFAULT_EMAIL:
        base["email"] = DEFAULT_EMAIL
    if NCBI_API_KEY:
        base["api_key"] = NCBI_API_KEY
    base.update(extra)
    return base


def _get(url: str, params: dict[str, Any], timeout: int = 30) -> requests.Response:
    r = requests.get(url, params=_params(params), timeout=timeout)
    r.raise_for_status()
    time.sleep(RATE_DELAY)
    return r


def esearch_journal(
    journal: dict[str, str],
    years: int,
    retmax: int,
    article_type: str = "research",
    strategy: str = "classic",
) -> tuple[list[str], str]:
    """Return PMIDs whose PMC JATS full text is likely free and fetchable.

    ``classic`` (MVP default): older date window + dual OA filters.
    ``recent``: last N years — fine for eLife/PLOS, often fails for PNAS.
    """
    strat = CORPUS_STRATEGIES.get(strategy, CORPUS_STRATEGIES["classic"])
    type_filter = ARTICLE_TYPE_FILTERS.get(article_type, "")

    if strategy == "classic":
        pdat = journal.get("classic_pdat", "2010:2022")
        date_clause = f"{pdat}[PDat]"
    else:
        yr = int(journal.get("recent_years", years))
        date_clause = f'"last {yr} years"[PDat]'

    query = f"{journal['term']} AND {date_clause} AND {strat['oa_filters']}"
    if type_filter:
        query += f" AND {type_filter}"

    r = _get(
        EUTILS + "esearch.fcgi",
        {
            "db": "pubmed",
            "term": query,
            "retmax": retmax,
            "retmode": "json",
            "sort": strat["sort"],
        },
    )
    pmids = r.json().get("esearchresult", {}).get("idlist", [])
    return pmids, query


def _post(url: str, params: dict[str, Any], timeout: int = 30) -> requests.Response:
    """POST helper for eUtils calls that exceed GET URL limits."""
    r = requests.post(url, data=_params(params), timeout=timeout)
    r.raise_for_status()
    time.sleep(RATE_DELAY)
    return r


def _parse_elink_json(data: dict[str, Any]) -> dict[str, str]:
    """Extract PMID -> PMCID from one elink JSON payload."""
    mapping: dict[str, str] = {}
    for ls in data.get("linksets", []):
        ids_in = [str(i) for i in ls.get("ids", [])]
        for entry in ls.get("linksetdbs", []):
            if entry.get("dbto") != "pmc":
                continue
            links = entry.get("links", [])
            # With multiple source ids, NCBI returns one linkset block per id.
            if len(ids_in) == 1 and links:
                mapping[ids_in[0]] = f"PMC{links[0]}"
            elif len(ids_in) == len(links):
                for pmid, pmc in zip(ids_in, links):
                    mapping[pmid] = f"PMC{pmc}"
    return mapping


def elink_pmid_to_pmcid(pmids: list[str], chunk_size: int = 80) -> dict[str, str]:
    """Map PMID -> PMCID via elink (POST, chunked to avoid HTTP 414)."""
    mapping: dict[str, str] = {}
    if not pmids:
        return mapping

    for i in range(0, len(pmids), chunk_size):
        chunk = pmids[i : i + chunk_size]
        try:
            r = _post(
                EUTILS + "elink.fcgi",
                {
                    "dbfrom": "pubmed",
                    "db": "pmc",
                    "id": ",".join(chunk),
                    "retmode": "json",
                },
            )
            mapping.update(_parse_elink_json(r.json()))
        except requests.HTTPError:
            # Fall back to per-id resolution for this chunk only.
            for pmid in chunk:
                try:
                    rr = _post(
                        EUTILS + "elink.fcgi",
                        {"dbfrom": "pubmed", "db": "pmc", "id": pmid, "retmode": "json"},
                    )
                    mapping.update(_parse_elink_json(rr.json()))
                except Exception:
                    continue

    # Final pass for any stragglers
    missing = [p for p in pmids if p not in mapping]
    for pmid in missing:
        try:
            rr = _post(
                EUTILS + "elink.fcgi",
                {"dbfrom": "pubmed", "db": "pmc", "id": pmid, "retmode": "json"},
            )
            mapping.update(_parse_elink_json(rr.json()))
        except Exception:
            continue
    return mapping


def efetch_pmc_xml(pmcid: str) -> bytes | None:
    """Fetch one article's JATS XML from PMC."""
    numeric = pmcid.replace("PMC", "")
    try:
        r = _get(
            EUTILS + "efetch.fcgi",
            {"db": "pmc", "id": numeric, "retmode": "xml"},
            timeout=45,
        )
        return r.content
    except Exception:
        return None


# JATS section detection -----------------------------------------------------

_NS = {"jats": "https://jats.nlm.nih.gov"}


def _local(tag) -> str:
    """Return the local-name of an lxml tag (strip namespace).

    Comment/PI nodes in lxml expose a non-string ``tag``; skip those.
    """
    if not isinstance(tag, str):
        return ""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _section_contains_discussion(sec: etree._Element) -> bool:
    sec_type = (sec.get("sec-type") or "").lower()
    if any(k in sec_type for k in ("discussion", "conclusion", "conclusions")):
        return True
    for child in sec:
        if _local(child.tag) == "title" and child.text:
            t = child.text.strip().lower()
            if t in {"discussion", "conclusion", "conclusions", "discussion and conclusions"}:
                return True
    return False


def _substantive_body_sections(root: etree._Element, min_chars: int = 400) -> int:
    """Count body <sec> blocks with enough text (for reviews / case reports)."""
    count = 0
    for sec in root.iter():
        if _local(sec.tag) != "sec":
            continue
        text = " ".join(sec.itertext()).strip()
        if len(text) >= min_chars:
            count += 1
    return count


def inspect_jats(xml_bytes: bytes, article_type: str = "research") -> dict[str, bool]:
    """Return which sections the article actually contains."""
    flags = {
        "abstract": False,
        "discussion_or_conclusion": False,
        "figure_legends": False,
        "body_sections": False,
    }
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError:
        return flags

    for elem in root.iter():
        tag = _local(elem.tag)
        if tag == "abstract":
            # require at least one <p> child to count as a real abstract
            if any(_local(c.tag) == "p" for c in elem.iter()):
                flags["abstract"] = True
        elif tag == "sec":
            if not flags["discussion_or_conclusion"] and _section_contains_discussion(elem):
                flags["discussion_or_conclusion"] = True
        elif tag == "fig":
            for c in elem.iter():
                if _local(c.tag) == "caption":
                    if any(_local(cc.tag) == "p" for cc in c.iter()):
                        flags["figure_legends"] = True
                        break

    flags["body_sections"] = _substantive_body_sections(root) >= 2
    return flags


def _qualifies(flags: dict[str, bool], article_type: str) -> bool:
    """Article-type-specific minimum section requirements."""
    if article_type == "research":
        return flags["abstract"] and flags["discussion_or_conclusion"]
    if article_type == "review":
        return flags["abstract"] and (
            flags["discussion_or_conclusion"] or flags["body_sections"]
        )
    if article_type == "case_report":
        return flags["abstract"] and (
            flags["discussion_or_conclusion"] or flags["body_sections"]
        )
    if article_type == "letter":
        return flags["abstract"] or flags["body_sections"]
    return flags["abstract"] and flags["discussion_or_conclusion"]


def probe_one_journal(
    j: dict[str, str],
    years: int,
    candidates: int,
    target: int,
    article_type: str = "research",
    strategy: str = "classic",
) -> JournalReport:
    rep = JournalReport(key=j["key"], display=j["display"], query=j["term"])
    print(
        f"\n[{j['key']}] esearch (strategy={strategy}, type={article_type}, "
        f"retmax={candidates}) ..."
    )
    pmids, query_used = esearch_journal(
        j, years=years, retmax=candidates, article_type=article_type, strategy=strategy
    )
    rep.query = query_used
    print(f"[{j['key']}] query: {query_used[:120]}...")
    rep.candidate_pmids = len(pmids)
    print(f"[{j['key']}] esearch returned {rep.candidate_pmids} PMIDs")

    if not pmids:
        return rep

    print(f"[{j['key']}] elink pubmed -> pmc ...")
    pmid_to_pmcid = elink_pmid_to_pmcid(pmids)
    rep.with_pmcid = len(pmid_to_pmcid)
    print(f"[{j['key']}] PMCID resolved for {rep.with_pmcid}/{rep.candidate_pmids}")

    # Walk through PMIDs in PubMed order and stop once we have `target` fully
    # qualified papers; this keeps the probe cheap and representative.
    for pmid in pmids:
        if rep.fully_qualified >= target:
            break
        pmcid = pmid_to_pmcid.get(pmid)
        if not pmcid:
            continue
        xml = efetch_pmc_xml(pmcid)
        if not xml:
            rep.sample_failures.append({"pmid": pmid, "pmcid": pmcid, "reason": "efetch_failed"})
            continue
        rep.xml_fetched += 1
        flags = inspect_jats(xml, article_type=article_type)
        if flags["abstract"]:
            rep.with_abstract += 1
        if flags["discussion_or_conclusion"]:
            rep.with_discussion_or_conclusion += 1
        if flags["figure_legends"]:
            rep.with_figure_legends += 1
        if _qualifies(flags, article_type):
            rep.fully_qualified += 1
            rep.qualified_pmids.append(pmid)
        else:
            if len(rep.sample_failures) < 5:
                rep.sample_failures.append(
                    {"pmid": pmid, "pmcid": pmcid, "reason": "missing_sections", "flags": json.dumps(flags)}
                )

    print(
        f"[{j['key']}] qualified={rep.fully_qualified}/{target} "
        f"(abstract={rep.with_abstract}, disc/concl={rep.with_discussion_or_conclusion}, "
        f"fig_legends={rep.with_figure_legends})"
    )
    return rep


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Probe PMC full-text hit rate for MVP journals.")
    ap.add_argument("--years", type=int, default=5, help="fallback years for strategy=recent")
    ap.add_argument("--candidates", type=int, default=0, help="esearch retmax (0=strategy default)")
    ap.add_argument("--target", type=int, default=50, help="qualified papers needed per journal")
    ap.add_argument("--journals", nargs="*", default=None, help="subset of journal keys (e.g. elife plos_med)")
    ap.add_argument(
        "--strategy",
        default="classic",
        choices=list(CORPUS_STRATEGIES.keys()),
        help="classic=free PMC full text in older window (MVP default); recent=newest papers",
    )
    ap.add_argument(
        "--article-type",
        default="research",
        choices=list(ARTICLE_TYPE_FILTERS.keys()),
        help="PubMed publication type to probe (default: research)",
    )
    ap.add_argument("--out", type=Path, default=None, help="Output JSON path (default: auto timestamp)")
    ap.add_argument(
        "--no-fail-on-short",
        action="store_true",
        help="Exit 0 even if qualified < target (useful for review/letter runs)",
    )
    args = ap.parse_args(argv)

    selected = JOURNALS
    if args.journals:
        keys = set(args.journals)
        selected = [j for j in JOURNALS if j["key"] in keys]
        if not selected:
            print(f"No journals matched {args.journals}", file=sys.stderr)
            return 2

    out_dir = Path(__file__).resolve().parent / "_out"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = args.out or (out_dir / f"pmc_hitrate_{args.article_type}_{ts}.json")

    strat = CORPUS_STRATEGIES[args.strategy]
    candidates = args.candidates or strat["default_candidates"]

    reports: list[JournalReport] = []
    for j in selected:
        try:
            rep = probe_one_journal(
                j,
                args.years,
                candidates,
                args.target,
                article_type=args.article_type,
                strategy=args.strategy,
            )
        except requests.HTTPError as e:
            print(f"[{j['key']}] HTTP error: {e}", file=sys.stderr)
            rep = JournalReport(key=j["key"], display=j["display"], query=j["term"])
        reports.append(rep)

    summary = {
        "generated_at": ts,
        "tool": DEFAULT_TOOL,
        "ncbi_api_key_present": bool(NCBI_API_KEY),
        "article_type": args.article_type,
        "strategy": args.strategy,
        "params": {
            "years": args.years,
            "candidates": candidates,
            "target": args.target,
            "article_type": args.article_type,
            "strategy": args.strategy,
        },
        "journals": [asdict(r) for r in reports],
    }
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nReport written: {out_path}")

    # Brief stdout summary
    print("\n=== summary ===")
    for r in reports:
        verdict = "OK" if r.fully_qualified >= args.target else "SHORT"
        print(
            f"  {r.key:10s} candidate={r.candidate_pmids:3d} pmcid={r.with_pmcid:3d} "
            f"xml={r.xml_fetched:3d} qualified={r.fully_qualified:3d} [{verdict}]"
        )

    any_short = any(r.fully_qualified < args.target for r in reports)
    if any_short and not args.no_fail_on_short:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
