"""
fix_journal_systems.py
======================
Retroactively maps submission systems for journals where build_journal_db.py
left submission_system blank or "Unknown".

Strategy:
  1. Read all JSON files in assets/journal_requirements/
  2. For each with missing/unknown submission_system:
     a. Apply publisher-name heuristics (PUBLISHER_SYSTEM_MAP from submission_prep.py)
     b. Apply journal-title heuristics (known journal → system mappings)
     c. If still unknown, try CrossRef API for publisher info
  3. Update JSON files in-place
  4. Rebuild _index.json

Usage:
  python scripts/fix_journal_systems.py [--dry-run] [--limit N] [--report]

  --dry-run   : show what would change without writing files
  --limit N   : process at most N journals (for testing)
  --report    : print summary report only (no changes)

GitHub Actions compatible: commit the changes after running.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

SKILL_DIR  = Path(__file__).resolve().parents[1]
JOURNAL_DIR = SKILL_DIR / "assets" / "journal_requirements"

# Import heuristics from submission_prep
sys.path.insert(0, str(SKILL_DIR / "scripts"))
from submission_prep import PUBLISHER_SYSTEM_MAP, infer_submission_system

# ── Journal-title level overrides ─────────────────────────────────────────────
# For cases where publisher name alone is ambiguous.
# Format: (substring_in_title_lower, submission_system)
TITLE_SYSTEM_OVERRIDES: list[tuple[str, str]] = [
    # Nature-branded → Snapp
    ("nature medicine", "Snapp"),
    ("nature methods", "Snapp"),
    ("nature genetics", "Snapp"),
    ("nature biotechnology", "Snapp"),
    ("nature neuroscience", "Snapp"),
    ("nature immunology", "Snapp"),
    ("nature chemical biology", "Snapp"),
    ("nature communications", "Snapp"),
    ("scientific reports", "Snapp"),
    ("communications biology", "Snapp"),
    ("communications medicine", "Snapp"),
    ("nature climate change", "Snapp"),
    ("nature energy", "Snapp"),
    ("nature sustainability", "Snapp"),
    ("nature aging", "Snapp"),
    ("nature metabolism", "Snapp"),
    ("nature cell biology", "Snapp"),
    ("nature structural", "Snapp"),
    ("nature cancer", "Snapp"),
    ("nature cardiovascular", "Snapp"),
    ("npj ", "Snapp"),                # All npj journals
    # Science family → ScienceSubmit
    ("science advances", "ScienceSubmit"),
    ("science signaling", "ScienceSubmit"),
    ("science translational medicine", "ScienceSubmit"),
    ("science immunology", "ScienceSubmit"),
    ("science robotics", "ScienceSubmit"),
    # Cell Press → EVISE
    ("cell stem cell", "EVISE"),
    ("cell host", "EVISE"),
    ("cell metabolism", "EVISE"),
    ("cell chemical biology", "EVISE"),
    ("cell reports", "EVISE"),
    ("current biology", "EVISE"),
    ("developmental cell", "EVISE"),
    ("molecular cell", "EVISE"),
    ("cancer cell", "EVISE"),
    ("immunity", "EVISE"),
    ("neuron", "EVISE"),
    ("structure", "EVISE"),
    # NEJM / JAMA / BMJ flagships
    ("new england journal of medicine", "Editorial Manager"),
    ("jama ", "Editorial Manager"),
    ("british medical journal", "BMJ submission system"),
    # JCI, JEM, JCB → BenchPress
    ("journal of clinical investigation", "Bench>Press"),
    ("journal of experimental medicine", "Bench>Press"),
    ("journal of cell biology", "Bench>Press"),
    ("journal of general physiology", "Bench>Press"),
    ("elife", "eLife submission system"),
    # PLoS family
    ("plos biology", "Editorial Manager"),
    ("plos medicine", "Editorial Manager"),
    ("plos one", "Editorial Manager"),
    ("plos genetics", "Editorial Manager"),
    ("plos pathogens", "Editorial Manager"),
    ("plos computational biology", "Editorial Manager"),
    ("plos neglected tropical", "Editorial Manager"),
    # Frontiers
    ("frontiers in", "Frontiers"),
    # F1000
    ("f1000research", "F1000Research"),
    ("wellcome open research", "F1000Research"),
    ("gates open research", "F1000Research"),
]

UNKNOWN_VALUES = {"", "unknown", "n/a", "none", "not identified", "not found"}


def is_unknown(system: str) -> bool:
    return system.strip().lower() in UNKNOWN_VALUES


def infer_from_title(title: str) -> str:
    """Try title-level override first."""
    title_lower = title.lower()
    for pattern, system in TITLE_SYSTEM_OVERRIDES:
        if pattern in title_lower:
            return system
    return ""


def fetch_crossref_publisher(issn: str) -> str:
    """
    Fetch publisher name from CrossRef by ISSN.
    Returns publisher string or empty on failure.
    """
    if not issn:
        return ""
    try:
        url = f"https://api.crossref.org/journals/{issn.strip()}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "TheraSIK-fix/1.0 (mailto:support@therasik.io)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("message", {}).get("publisher", "")
    except Exception:
        return ""


def process_journal_file(
    path: Path,
    dry_run: bool = False,
    use_crossref: bool = True,
    _crossref_sleep: float = 0.3,
) -> dict:
    """
    Process one journal JSON. Returns result dict:
      {changed, old_system, new_system, method, title}
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    title     = data.get("display_name") or data.get("title") or path.stem
    publisher = data.get("publisher", "")
    issn      = data.get("issn", "")
    old_sys   = data.get("submission_system", "")

    result = {
        "file":       path.name,
        "title":      title,
        "old_system": old_sys,
        "new_system": old_sys,
        "method":     "skipped",
        "changed":    False,
    }

    if not is_unknown(old_sys):
        return result  # already identified — skip

    # 1. Title-level override
    new_sys = infer_from_title(title)
    method  = "title_override"

    # 2. Publisher heuristic
    if not new_sys and publisher:
        new_sys = infer_submission_system(publisher, title)
        method  = "publisher_heuristic"

    # 3. CrossRef fallback for publisher name
    if not new_sys and use_crossref and issn:
        time.sleep(_crossref_sleep)
        cr_publisher = fetch_crossref_publisher(issn)
        if cr_publisher:
            data["publisher"] = cr_publisher  # enrich publisher while we're at it
            new_sys = infer_submission_system(cr_publisher, title)
            method  = "crossref_publisher"

    if not new_sys:
        result["method"] = "still_unknown"
        return result

    result["new_system"] = new_sys
    result["method"]     = method
    result["changed"]    = True

    if not dry_run:
        data["submission_system"] = new_sys
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    return result


def rebuild_index(journal_dir: Path) -> int:
    """Rebuild _index.json from all JSON files. Returns count."""
    index = {}
    for f in sorted(journal_dir.glob("*.json")):
        if f.name == "_index.json":
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            key  = data.get("key") or f.stem
            issn = data.get("issn_print") or data.get("issn_online") or data.get("issn", "")
            if isinstance(issn, list):
                issn = issn[0] if issn else ""
            index[key] = {
                "display_name":      data.get("display_name") or data.get("title") or key,
                "issn":              issn,
                "publisher":         data.get("publisher", ""),
                "submission_system": data.get("submission_system", ""),
                "submission_url":    data.get("submission_url", ""),
                "fetch_status":      data.get("fetch_status", ""),
                "has_source_url":    bool(data.get("source_url") or (data.get("requirements") or {}).get("source_url")),
                "has_guidelines":    bool(data.get("article_types")),
            }
        except Exception:
            continue
    (journal_dir / "_index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return len(index)


def run(
    journal_dir: Path,
    dry_run: bool = False,
    limit: int = 0,
    use_crossref: bool = True,
    verbose: bool = True,
) -> dict:
    """
    Main entry point. Returns summary dict.
    """
    files = [f for f in sorted(journal_dir.glob("*.json")) if f.name != "_index.json"]
    total     = len(files)
    changed   = 0
    still_unk = 0
    by_method: dict[str, int] = {}
    errors: list[str] = []

    processed = 0
    for f in files:
        if limit and processed >= limit:
            break
        try:
            r = process_journal_file(f, dry_run=dry_run, use_crossref=use_crossref)
        except Exception as e:
            errors.append(f"{f.name}: {e}")
            continue

        if r["method"] == "skipped":
            continue

        processed += 1
        by_method[r["method"]] = by_method.get(r["method"], 0) + 1

        if r["changed"]:
            changed += 1
            if verbose:
                print(f"  ✓ {r['title'][:50]:<50} {r['old_system'] or '(empty)'!r} → {r['new_system']!r}  [{r['method']}]")
        elif r["method"] == "still_unknown":
            still_unk += 1

    # Rebuild index
    if not dry_run:
        n = rebuild_index(journal_dir)
        if verbose:
            print(f"\n  _index.json rebuilt ({n} entries)")

    summary = {
        "total_files":     total,
        "processed":       processed,
        "newly_identified": changed,
        "still_unknown":   still_unk,
        "by_method":       by_method,
        "errors":          errors,
        "dry_run":         dry_run,
    }
    return summary


def print_report(summary: dict):
    print()
    print("=" * 60)
    print("  fix_journal_systems.py  —  Results")
    print("=" * 60)
    print(f"  Total journal files       : {summary['total_files']:,}")
    print(f"  Previously unknown        : {summary['processed']:,}")
    print(f"  Newly identified          : {summary['newly_identified']:,}")
    print(f"  Still unknown after run   : {summary['still_unknown']:,}")
    print(f"  Dry run                   : {summary['dry_run']}")
    if summary["by_method"]:
        print()
        print("  Identification methods:")
        for method, count in sorted(summary["by_method"].items(), key=lambda x: -x[1]):
            print(f"    {method:<30} {count:>5}")
    if summary["errors"]:
        print()
        print(f"  Errors ({len(summary['errors'])}):")
        for e in summary["errors"][:10]:
            print(f"    {e}")
    print("=" * 60)
    print()


def main():
    parser = argparse.ArgumentParser(description="Fix unidentified journal submission systems")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show changes without writing files")
    parser.add_argument("--limit", type=int, default=0, metavar="N",
                        help="Process at most N unknown journals (0 = all)")
    parser.add_argument("--no-crossref", action="store_true",
                        help="Skip CrossRef API fallback (faster, less coverage)")
    parser.add_argument("--report", action="store_true",
                        help="Print report without verbose per-journal output")
    parser.add_argument("--journal-dir", default=str(JOURNAL_DIR),
                        help="Path to journal_requirements directory")
    args = parser.parse_args()

    jdir = Path(args.journal_dir)
    if not jdir.exists():
        print(f"ERROR: Journal directory not found: {jdir}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning {jdir} ...")
    if args.dry_run:
        print("  DRY RUN — no files will be modified")
    print()

    summary = run(
        jdir,
        dry_run=args.dry_run,
        limit=args.limit,
        use_crossref=not args.no_crossref,
        verbose=not args.report,
    )
    print_report(summary)

    # Exit code: 0 if any progress made (or dry-run), 1 if none
    if not args.dry_run and summary["newly_identified"] == 0 and summary["processed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
