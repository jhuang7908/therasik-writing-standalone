"""
run_article_profiles.py — Step 2: send each paper JSON through Claude Sonnet
to extract a structured writing-style profile, validate it against the schema,
and save the result to ``article_profiles/<journal_key>/<pmid>.json``.

This script is the first LLM step. It is designed for:
  - Batch processing with configurable concurrency (default 3 parallel calls)
  - Skip-already-done (``--resume``)
  - Dry-run preview (``--dry-run``)
  - Phrase-evidence anti-hallucination re-check (substring test, logged to report)

Usage
-----
    # Smoke: 1 paper per journal
    python services/writing_memory/ingest/run_article_profiles.py --smoke

    # Full corpus (150 papers, ~15-20 min @ Sonnet rate limits)
    python services/writing_memory/ingest/run_article_profiles.py

    # Resume interrupted run
    python services/writing_memory/ingest/run_article_profiles.py --resume

    # Single journal only
    python services/writing_memory/ingest/run_article_profiles.py --journals pnas

Environment variables
---------------------
    ANTHROPIC_API_KEY     required
    ANTHROPIC_MODEL       default: claude-sonnet-4-5 (override to claude-haiku-4-5 for dev)
    WRITING_MEMORY_PAPERS_DIR   override papers_raw location

Output
------
    services/writing_memory/article_profiles/
        pnas/<pmid>.json
        elife/<pmid>.json
        plos_med/<pmid>.json
    services/writing_memory/article_profiles/_profile_report.json
        per-run summary: ok, fail, schema_violations, phrase_mismatches
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic
import jsonschema

_HERE = Path(__file__).resolve().parent
_SERVICE_ROOT = _HERE.parent

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
PAPERS_DIR = Path(
    os.environ.get("WRITING_MEMORY_PAPERS_DIR", str(_SERVICE_ROOT / "papers_raw"))
)
PROFILES_DIR = _SERVICE_ROOT / "article_profiles"

_SYSTEM_PROMPT_PATH = _SERVICE_ROOT / "prompts" / "article_profile.system.md"
_SCHEMA_PATH = _SERVICE_ROOT / "schemas" / "article_profile.schema.json"

MAX_WORKERS = 3       # parallel Anthropic calls
MAX_TOKENS  = 4096    # profile JSON with evidence phrases can reach ~3 k tokens
TEMPERATURE = 0.1     # near-deterministic for extraction tasks

# Sections fed to Claude in priority order
SECTION_PRIORITY = ["discussion", "conclusion", "abstract"]
# Max chars sent to Claude per section (discussion can be 20k+ in eLife)
MAX_SECTION_CHARS = 8000
MAX_LEGENDS = 4        # max figure legends to include (keep token budget)
MAX_LEGEND_CHARS = 300 # chars per legend


# ---------------------------------------------------------------------------
# Load shared assets once at import time
# ---------------------------------------------------------------------------

def _load_system_prompt() -> str:
    return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")

def _load_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Build user message from paper JSON
# ---------------------------------------------------------------------------

def _build_user_message(paper: dict[str, Any], schema: dict[str, Any]) -> str:
    parts: list[str] = []

    parts.append("## Paper metadata")
    parts.append(f"- PMID: {paper.get('pmid', 'unknown')}")
    parts.append(f"- PMCID: {paper.get('pmcid', 'unknown')}")
    parts.append(f"- Journal: {paper.get('journal', 'unknown')}")
    parts.append(f"- Year: {paper.get('year', 'unknown')}")
    parts.append(f"- Title: {paper.get('title', 'unknown')}")
    parts.append("")

    # Collect text sections (truncated to token budget)
    sections_used: list[str] = []

    for sec_name in SECTION_PRIORITY:
        text = (paper.get(sec_name) or "").strip()
        if text:
            truncated = text[:MAX_SECTION_CHARS]
            if len(text) > MAX_SECTION_CHARS:
                truncated += " ... [truncated]"
            parts.append(f"## {sec_name.capitalize()}")
            parts.append(truncated)
            parts.append("")
            sections_used.append(sec_name)

    legends = paper.get("figure_legends") or []
    if legends:
        selected = legends[:MAX_LEGENDS]
        parts.append("## Figure legends (sample)")
        for i, leg in enumerate(selected, 1):
            short = leg[:MAX_LEGEND_CHARS]
            if len(leg) > MAX_LEGEND_CHARS:
                short += " ..."
            parts.append(f"Figure {i}: {short}")
        parts.append("")
        sections_used.append("figure_legends")

    if not sections_used:
        parts.append("## [No usable text sections found]")
        parts.append("")

    # Attach schema so Claude knows the required output shape
    parts.append("## Required JSON Schema (ArticleProfile v0.1.0)")
    parts.append("```json")
    parts.append(json.dumps(schema, indent=2))
    parts.append("```")
    parts.append("")
    parts.append(
        f"Sections available in this article: {', '.join(sections_used) if sections_used else 'none'}."
        " Fill `source.sections_used` with this list.\n"
        f"Fill `source.pmid` = \"{paper.get('pmid')}\","
        f" `source.pmcid` = \"{paper.get('pmcid')}\","
        f" `source.journal` = \"{paper.get('journal')}\","
        f" `source.year` = {paper.get('year')},"
        f" `source.doi` = {json.dumps(paper.get('doi'))}.\n"
        "Output ONLY the JSON object. No markdown fences. No commentary."
    )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Anti-hallucination phrase check
# ---------------------------------------------------------------------------

def _check_phrase_evidence(
    profile: dict[str, Any],
    paper: dict[str, Any],
) -> list[dict[str, str]]:
    """
    Verify that every phrase in phrase_evidence and claim_strength_profile.examples
    is a literal case-insensitive substring of the paper text.

    Returns a list of violations (empty list = all clear).
    """
    # Build full text corpus from paper (whitespace-normalised for fuzzy match)
    corpus_parts: list[str] = []
    for key in ("title", "abstract", "discussion", "conclusion"):
        if paper.get(key):
            corpus_parts.append(paper[key])
    for leg in (paper.get("figure_legends") or []):
        corpus_parts.append(leg)

    def _norm(s: str) -> str:
        return re.sub(r"\s+", " ", s).lower().strip()

    full_text = _norm(" ".join(corpus_parts))

    violations: list[dict[str, str]] = []

    for item in (profile.get("phrase_evidence") or []):
        phrase = _norm(item.get("phrase") or "")
        if phrase and phrase not in full_text:
            violations.append({
                "field": "phrase_evidence",
                "phrase": item.get("phrase", ""),
                "issue": "not found in paper text",
            })

    for ex in (profile.get("claim_strength_profile", {}).get("examples") or []):
        qp = _norm(ex.get("quoted_phrase") or "")
        if qp and qp not in full_text:
            violations.append({
                "field": "claim_strength_profile.examples.quoted_phrase",
                "phrase": ex.get("quoted_phrase", ""),
                "issue": "not found in paper text",
            })

    return violations


# ---------------------------------------------------------------------------
# Single paper → profile
# ---------------------------------------------------------------------------

def extract_one(
    pmid: str,
    journal_key: str,
    client: anthropic.Anthropic,
    system_prompt: str,
    schema: dict[str, Any],
    papers_dir: Path,
    profiles_dir: Path,
) -> dict[str, Any]:
    """
    Load paper JSON, call Sonnet, validate, save profile.
    Returns a result dict for the report.
    """
    paper_path = papers_dir / journal_key / f"{pmid}.json"
    out_path = profiles_dir / journal_key / f"{pmid}.json"

    result: dict[str, Any] = {
        "pmid": pmid,
        "journal_key": journal_key,
        "status": "fail",
        "schema_valid": False,
        "phrase_violations": [],
        "error": None,
    }

    # Load paper
    try:
        paper = json.loads(paper_path.read_text(encoding="utf-8"))
    except Exception as exc:
        result["error"] = f"paper load error: {exc}"
        return result

    # Build prompt
    user_msg = _build_user_message(paper, schema)

    # Call Claude (retry up to 3 times on empty/truncated response)
    raw_text = None
    last_stop_reason = None
    for attempt in range(3):
        try:
            response = client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                system=system_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )
            last_stop_reason = getattr(response, "stop_reason", None)
            if response.content:
                raw_text = response.content[0].text.strip()
                if raw_text:
                    break
            # Empty or whitespace-only content — increase budget and retry
            MAX_TOKENS_RETRY = MAX_TOKENS * 2 if attempt == 1 else MAX_TOKENS
            time.sleep(5.0 * (attempt + 1))
        except Exception as exc:
            if attempt < 2:
                time.sleep(8.0)
                continue
            result["error"] = f"Claude API error: {exc}"
            return result

    if not raw_text:
        result["error"] = (
            f"Claude returned empty response after 3 attempts"
            f" (last stop_reason={last_stop_reason})"
        )
        return result

    # Parse JSON (strip accidental markdown fences if any)
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)
    try:
        profile = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        result["error"] = f"JSON parse error: {exc}; raw={raw_text[:200]}"
        return result

    # Schema validation
    try:
        jsonschema.validate(instance=profile, schema=schema)
        result["schema_valid"] = True
    except jsonschema.ValidationError as exc:
        result["error"] = f"schema violation: {exc.message}"
        # Still save the partial profile for debugging, but mark as invalid
        profile["_schema_error"] = exc.message

    # Anti-hallucination phrase check
    violations = _check_phrase_evidence(profile, paper)
    result["phrase_violations"] = violations
    if violations:
        profile["_phrase_violations"] = violations

    # Attach load metadata
    profile["_meta"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": DEFAULT_MODEL,
        "papers_path": str(paper_path),
        "phrase_check_violations": len(violations),
        "schema_valid": result["schema_valid"],
    }

    # Save
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

    result["status"] = "ok" if result["schema_valid"] and len(violations) == 0 else "warn"
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _discover_papers(
    papers_dir: Path,
    journals: list[str] | None,
    smoke: bool,
    resume: bool,
    profiles_dir: Path,
) -> list[tuple[str, str]]:
    """Return list of (pmid, journal_key) pairs to process."""
    jobs: list[tuple[str, str]] = []

    all_keys = [d.name for d in papers_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]
    if journals:
        all_keys = [k for k in all_keys if k in journals]

    for jkey in sorted(all_keys):
        jdir = papers_dir / jkey
        pmids = sorted(p.stem for p in jdir.glob("*.json"))
        if smoke:
            pmids = pmids[:1]
        for pmid in pmids:
            if resume and (profiles_dir / jkey / f"{pmid}.json").exists():
                continue
            jobs.append((pmid, jkey))

    return jobs


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Extract per-paper writing profiles using Claude Sonnet."
    )
    ap.add_argument("--papers-dir", type=Path, default=PAPERS_DIR)
    ap.add_argument("--out-dir", type=Path, default=PROFILES_DIR)
    ap.add_argument("--journals", nargs="*", default=None)
    ap.add_argument("--smoke", action="store_true",
                    help="Process 1 paper per journal only")
    ap.add_argument("--resume", action="store_true",
                    help="Skip profiles that already exist")
    ap.add_argument("--workers", type=int, default=MAX_WORKERS,
                    help="Parallel Claude calls (default 3)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would be processed without calling Claude")
    args = ap.parse_args(argv)

    # Validate API key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key and not args.dry_run:
        print("ERROR: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        return 1

    system_prompt = _load_system_prompt()
    schema = _load_schema()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    jobs = _discover_papers(
        args.papers_dir, args.journals,
        smoke=args.smoke, resume=args.resume,
        profiles_dir=args.out_dir,
    )

    if not jobs:
        print("No papers to process (all done or no papers found).")
        return 0

    print(f"Will process {len(jobs)} paper(s) with model={DEFAULT_MODEL}  workers={args.workers}")
    if args.dry_run:
        for pmid, jkey in jobs:
            print(f"  {jkey}/{pmid}")
        return 0

    client = anthropic.Anthropic(api_key=api_key)

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": DEFAULT_MODEL,
        "total": len(jobs),
        "ok": 0, "warn": 0, "fail": 0,
        "schema_violations": 0,
        "phrase_mismatches": 0,
        "details": [],
    }

    def _run(args_tuple: tuple[str, str]) -> dict[str, Any]:
        pmid, jkey = args_tuple
        return extract_one(pmid, jkey, client, system_prompt, schema, args.papers_dir, args.out_dir)

    completed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_run, job): job for job in jobs}
        for fut in as_completed(futures):
            res = fut.result()
            completed += 1
            status = res["status"]
            pv = len(res.get("phrase_violations") or [])
            sv = 0 if res.get("schema_valid", False) else 1

            status_label = {
                "ok": "OK  ",
                "warn": "WARN",
                "fail": "FAIL",
            }.get(status, status)

            print(
                f"  [{completed}/{len(jobs)}] {res['journal_key']}/{res['pmid']}"
                f"  {status_label}"
                f"  schema={'ok' if res.get('schema_valid') else 'FAIL'}"
                f"  phrase_violations={pv}"
                + (f"  err={res['error']}" if res.get("error") else "")
            )

            report[status] = report.get(status, 0) + 1  # type: ignore[assignment]
            report["schema_violations"] += sv
            report["phrase_mismatches"] += pv
            report["details"].append(res)

    # Write report
    report_path = args.out_dir / "_profile_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nProfile report: {report_path}")
    print(
        f"Results: ok={report['ok']}  warn={report['warn']}  fail={report['fail']}"
        f"  schema_violations={report['schema_violations']}"
        f"  phrase_mismatches={report['phrase_mismatches']}"
    )

    return 0 if report["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
