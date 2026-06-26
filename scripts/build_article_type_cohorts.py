#!/usr/bin/env python3
"""
Build frozen article-type cohort RELEASE_v1 from:
  - Local papers_raw (reuse, no re-download)
  - SEED_FAMOUS_V1.json landmarks (fetch PMC if missing)

Selection gates (Owner-approved MVP):
  - English US/UK journal source preferred
  - Corresponding author (last author proxy) native-speaker heuristic
  - QC metrics vs type schema bands
  - Famous seeds ranked first

Usage (repo root):
  python scripts/build_article_type_cohorts.py
  python scripts/build_article_type_cohorts.py --fetch-seeds --max-fetch 30
  python scripts/build_article_type_cohorts.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from services.writing_memory.cohort.classify import classify_article_type
from services.writing_memory.cohort.metrics import compute_paper_metrics
from services.writing_memory.cohort.native_author import score_corresponding_author_native
from services.writing_memory.cohort.region import score_uk_us_source
from services.writing_memory.cohort.release import (
    COHORT_TARGETS,
    build_release,
    write_release,
)
from services.writing_memory.ingest.load_papers import fetch_and_parse, pmids_to_pmcids
from services.writing_memory.references.pubmed_client import PubMedRecord, efetch

WM = REPO / "services" / "writing_memory"
PAPERS_RAW = WM / "papers_raw"
SEED_PATH = WM / "data" / "article_type_cohorts" / "SEED_FAMOUS_V1.json"

_FAME_SCORE = {"landmark": 100, "high": 70, "standard": 40}


def _journal_key_for(rec: PubMedRecord) -> str:
    blob = f"{rec.journal_abbrev} {rec.journal}".lower()
    if "plos med" in blob:
        return "plos_med"
    if "elife" in blob or "elifesciences" in blob:
        return "elife"
    if "proc natl acad" in blob or "pnas" in blob:
        return "pnas"
    if "plos" in blob:
        return "plos_med"
    return "pnas"


def _pubmed_stub(rec: PubMedRecord) -> dict[str, Any]:
    return {
        "pmid": rec.pmid,
        "title": rec.title,
        "abstract": rec.abstract,
        "discussion": "",
        "conclusion": "",
        "figure_legends": [],
        "sections_available": {"abstract": bool(rec.abstract)},
        "_pubmed_only": True,
    }


def _load_local_papers() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for p in PAPERS_RAW.rglob("*.json"):
        if p.name.startswith("_"):
            continue
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        pmid = str(doc.get("pmid") or p.stem)
        doc["_path"] = str(p.relative_to(WM))
        out[pmid] = doc
    return out


def _candidate_score(
    *,
    fame: str,
    uk_us: dict,
    native: dict,
    metrics: dict,
    seed_bonus: bool,
) -> float:
    s = _FAME_SCORE.get(fame, 30)
    s += 25 if seed_bonus else 0
    s += 20 * (uk_us.get("score") or 0) if uk_us.get("pass") else -15
    s += 25 if native.get("pass") else -20
    s += 15 if metrics.get("qc_pass") else -25
    s += min(10, (metrics.get("citations_per_1000_words") or 0) / 2)
    return s


def _enrich_from_pubmed(rec: PubMedRecord, doc: dict[str, Any] | None, seed_type: str | None) -> dict[str, Any]:
    paper = dict(doc or {})
    paper.setdefault("pmid", rec.pmid)
    paper.setdefault("title", rec.title)
    paper.setdefault("abstract", rec.abstract or paper.get("abstract"))
    paper.setdefault("doi", rec.doi)
    paper.setdefault("pmcid", rec.pmcid)
    paper.setdefault("year", rec.year)

    cls = classify_article_type(title=rec.title, pub_types=rec.pub_types, seed_type=seed_type)
    uk = score_uk_us_source(rec.journal, rec.journal_abbrev)
    nat = score_corresponding_author_native(rec.authors, rec.affiliations)
    met = compute_paper_metrics(paper, cls["canonical"])

    return {
        "pmid": rec.pmid,
        "pmcid": rec.pmcid,
        "doi": rec.doi,
        "title": rec.title,
        "journal": rec.journal,
        "journal_abbrev": rec.journal_abbrev,
        "year": rec.year,
        "pub_types": rec.pub_types,
        "article_type": cls,
        "uk_us_source": uk,
        "corresponding_author_native": nat,
        "metrics": met,
        "local_path": paper.get("_path"),
        "fame_tier": "seed" if seed_type else "local",
        "verification_status": "verified" if met.get("qc_pass") else "estimated",
    }


def _select_for_type(candidates: list[dict[str, Any]], target: int) -> list[dict[str, Any]]:
    """Prefer qc_pass + native + uk_us; fill shortfall with best score."""
    def ok(c: dict) -> bool:
        return (
            c["metrics"].get("qc_pass")
            and c["uk_us_source"].get("pass")
            and c["corresponding_author_native"].get("pass")
        )

    tier1 = [c for c in candidates if ok(c)]
    tier1.sort(key=lambda c: c.get("_rank_score", 0), reverse=True)
    if len(tier1) >= target:
        return tier1[:target]

    rest = [c for c in candidates if c not in tier1]
    rest.sort(key=lambda c: c.get("_rank_score", 0), reverse=True)
    merged = tier1 + rest
    return merged[:target]


def main() -> int:
    ap = argparse.ArgumentParser(description="Build article-type cohort RELEASE_v1")
    ap.add_argument("--dry-run", action="store_true", help="Report only; do not write release")
    ap.add_argument("--fetch-seeds", action="store_true", help="Download missing seed PMIDs to papers_raw")
    ap.add_argument("--max-fetch", type=int, default=80, help="Max seed PMC downloads per run")
    ap.add_argument("--batch", type=int, default=40, help="PubMed efetch batch size")
    args = ap.parse_args()

    seeds_doc = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    seed_map: dict[str, list[dict]] = seeds_doc.get("seeds") or {}

    local = _load_local_papers()
    print(f"Local papers_raw: {len(local)} files")

    # Index seeds by pmid
    seed_by_pmid: dict[str, tuple[str, dict]] = {}
    for ctype, entries in seed_map.items():
        for ent in entries:
            seed_by_pmid[str(ent["pmid"])] = (ctype, ent)

    all_pmids = list(set(local.keys()) | set(seed_by_pmid.keys()))
    pubmed: dict[str, PubMedRecord] = {}
    for i in range(0, len(all_pmids), args.batch):
        batch = all_pmids[i : i + args.batch]
        for rec in efetch(batch):
            pubmed[rec.pmid] = rec

    fetched = 0
    if args.fetch_seeds:
        need = [pmid for pmid in seed_by_pmid if pmid not in local]
        for batch_start in range(0, len(need), 50):
            batch = need[batch_start : batch_start + 50]
            pmc_map = pmids_to_pmcids(batch)
            for pmid in batch:
                if fetched >= args.max_fetch:
                    break
                rec = pubmed.get(pmid)
                if not rec:
                    continue
                if pmid in local:
                    continue
                pmcid = pmc_map.get(pmid)
                jk = _journal_key_for(rec)
                out_path = PAPERS_RAW / jk / f"{pmid}.json"
                if out_path.exists():
                    local[pmid] = json.loads(out_path.read_text(encoding="utf-8"))
                    continue
                if pmcid:
                    doc = fetch_and_parse(pmid, pmcid, jk)
                    if doc and not doc.get("_error"):
                        out_path.parent.mkdir(parents=True, exist_ok=True)
                        out_path.write_text(
                            json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8",
                        )
                        local[pmid] = doc
                        fetched += 1
                        print(f"  fetched {pmid} -> {out_path.relative_to(REPO)}")
                        continue
                local[pmid] = _pubmed_stub(rec)
                print(f"  pubmed-only stub {pmid} ({rec.journal_abbrev or rec.journal})")
            if fetched >= args.max_fetch:
                break
        print(f"Fetched {fetched} new PMC papers; stubs={sum(1 for p in need if local.get(p, {}).get('_pubmed_only'))}")

    # Build candidates per canonical type
    by_type: dict[str, list[dict[str, Any]]] = {t: [] for t in COHORT_TARGETS}
    seen_per_type: dict[str, set[str]] = {t: set() for t in COHORT_TARGETS}

    def _add_candidate(
        pmid: str,
        doc: dict[str, Any] | None,
        seed_info: tuple[str, dict] | None,
        *,
        force_type: str | None = None,
    ) -> None:
        target_type = force_type or (seed_info[0] if seed_info else None)
        if not target_type or target_type not in by_type:
            return
        if pmid in seen_per_type[target_type]:
            return
        rec = pubmed.get(pmid)
        if not rec:
            return
        seed_type = seed_info[0] if seed_info else None
        fame = seed_info[1].get("fame", "standard") if seed_info else "standard"
        paper = doc or _pubmed_stub(rec)
        row = _enrich_from_pubmed(rec, paper, seed_type)
        if seed_type:
            row["article_type"] = {
                "canonical": seed_type,
                "source": "seed_manifest",
                "confidence": "high",
            }
        elif row["article_type"].get("confidence") == "low":
            return
        row["_rank_score"] = _candidate_score(
            fame=fame,
            uk_us=row["uk_us_source"],
            native=row["corresponding_author_native"],
            metrics=row["metrics"],
            seed_bonus=bool(seed_info),
        )
        row["fame_tier"] = fame
        if seed_info:
            row["seed_label"] = seed_info[1].get("label", "")
        ctype = force_type or row["article_type"]["canonical"]
        if ctype in by_type:
            by_type[ctype].append(row)
            seen_per_type[ctype].add(pmid)

    for ctype, entries in seed_map.items():
        for ent in entries:
            pmid = str(ent["pmid"])
            _add_candidate(pmid, local.get(pmid), (ctype, ent), force_type=ctype)

    for pmid, doc in local.items():
        if pmid in seed_by_pmid:
            continue
        rec = pubmed.get(pmid)
        if not rec:
            continue
        cls = classify_article_type(title=rec.title, pub_types=rec.pub_types)
        if cls.get("confidence") == "low":
            continue
        ctype = cls["canonical"]
        if pmid in seen_per_type.get(ctype, set()):
            continue
        _add_candidate(pmid, doc, None, force_type=ctype)
    selected: dict[str, list[dict[str, Any]]] = {}
    report_lines: list[str] = []

    for ctype, target in COHORT_TARGETS.items():
        pool = by_type.get(ctype, [])
        sel = _select_for_type(pool, target)
        selected[ctype] = [{k: v for k, v in c.items() if not k.startswith("_")} for c in sel]
        n_ok = sum(
            1
            for c in sel
            if c["metrics"].get("qc_pass")
            and c["uk_us_source"].get("pass")
            and c["corresponding_author_native"].get("pass")
        )
        report_lines.append(
            f"{ctype}: selected {len(sel)}/{target} "
            f"(strict_pass={n_ok}, pool={len(pool)})"
        )

    print("\n".join(report_lines))

    release = build_release(
        selected,
        notes=(
            "Owner-approved build: US/UK English sources; native correspondent heuristic; "
            "landmark seeds from SEED_FAMOUS_V1.json. Metrics on partial PMC text."
        ),
    )

    if args.dry_run:
        print(json.dumps({k: len(v) for k, v in selected.items()}, indent=2))
        return 0

    out = write_release(release)
    print(f"Wrote {out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
