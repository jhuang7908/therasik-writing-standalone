"""
build_journal_db.py
===================
Builds a local journal requirements database by:

  1. Downloading the MEDLINE journal list from NLM FTP
     (~5,600 currently-indexed biomedical journals)
  2. For each journal, querying CrossRef API to get publisher + homepage URL
  3. Finding the "Instructions for Authors" page via link analysis
  4. Extracting structured requirements (word limits, figure specs, citation style, etc.)
  5. Saving each journal as a JSON file in assets/journal_requirements/

Designed to run unattended (e.g., GitHub Actions). Resumes automatically
if interrupted -- already-completed journals are skipped.

Usage:
  python scripts/build_journal_db.py [options]

Options:
  --limit N        Process at most N journals (default: all)
  --offset N       Skip first N journals (for parallel runs)
  --issn ISSN      Process a single journal by ISSN
  --outdir PATH    Output directory (default: assets/journal_requirements)
  --delay SECS     Delay between requests in seconds (default: 1.0)
  --verbose        Print details for each journal

GitHub Actions: see .github/workflows/build_journal_db.yml
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTDIR = SKILL_DIR / "assets" / "journal_requirements"
INDEX_FILE = DEFAULT_OUTDIR / "_index.json"

NLM_MEDLINE_URL = "https://ftp.ncbi.nlm.nih.gov/pubmed/J_Medline.txt"
CROSSREF_JOURNALS = "https://api.crossref.org/journals/{issn}"
UA = "therasik-journal-db/1.0 (mailto:research@therasik.io; for academic research)"

# Keywords that indicate an "Instructions for Authors" page
GUIDELINE_KEYWORDS = [
    "instructions-for-authors", "instructions_for_authors",
    "author-guidelines", "author_guidelines", "authorguide",
    "for-authors", "for_authors", "forauthors",
    "guide-for-authors", "guide_for_authors",
    "submission-guidelines", "submission_guidelines",
    "manuscript-preparation", "prepare-manuscript",
    "information-for-authors", "authors/information",
    "authors/instructions", "authors/guidelines",
    "submit", "authors",
]


# --------------------------------------------------------------------------- #
#  HTML utilities                                                              #
# --------------------------------------------------------------------------- #

class LinkExtractor(HTMLParser):
    """Extract all href links from an HTML page."""
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for k, v in attrs:
                if k == "href" and v:
                    self.links.append(v)


def _http_get(url: str, timeout: int = 15) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            charset = "utf-8"
            ct = resp.headers.get_content_charset()
            if ct:
                charset = ct
            return raw.decode(charset, errors="replace")
    except Exception:
        return None


def _find_guideline_url(homepage: str) -> str | None:
    """
    Given a journal homepage URL, find the Instructions for Authors page.
    Strategy:
      1. Fetch homepage HTML
      2. Look for links whose URL contains guideline keywords
      3. Return the best match
    """
    html = _http_get(homepage)
    if not html:
        return None

    parser = LinkExtractor()
    try:
        parser.feed(html)
    except Exception:
        return None

    base = urllib.parse.urlparse(homepage)
    scored: list[tuple[int, str]] = []

    for href in parser.links:
        href_lower = href.lower()
        score = sum(1 for kw in GUIDELINE_KEYWORDS if kw in href_lower)
        if score > 0:
            # Resolve relative URLs
            full = urllib.parse.urljoin(homepage, href)
            scored.append((score, full))

    if not scored:
        return None
    scored.sort(reverse=True)
    return scored[0][1]


# --------------------------------------------------------------------------- #
#  Requirement extraction                                                      #
# --------------------------------------------------------------------------- #

def _first_int(pattern: str, text: str) -> int | None:
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        try:
            return int(m.group(1).replace(",", ""))
        except (ValueError, IndexError):
            pass
    return None


def extract_requirements(url: str, html: str, journal_name: str) -> dict:
    """
    Parse an Instructions for Authors page and extract key submission requirements.
    Uses regex patterns -- no LLM needed.
    """
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)

    req: dict = {
        "source_url": url,
        "word_limits": {},
        "abstract_limit": None,
        "reference_limit": None,
        "figure_format": [],
        "figure_resolution_dpi": None,
        "citation_style": None,
        "required_sections": [],
        "open_access": None,
        "raw_notes": [],
    }

    # -- Word limits --
    # "original articles: 3000 words", "maximum 4000 words", etc.
    for article_type in ["original article", "research article", "letter", "review",
                         "case report", "editorial", "brief communication", "short report"]:
        pat = rf"{re.escape(article_type)}[^.]*?(\d[\d,]*)\s*words?"
        val = _first_int(pat, text)
        if val:
            req["word_limits"][article_type] = val

    # Generic word limit
    if not req["word_limits"]:
        val = _first_int(r"(?:maximum|limit(?:ed to)?|no more than)\s+(\d[\d,]*)\s+words?", text)
        if val:
            req["word_limits"]["general"] = val
        else:
            val = _first_int(r"(\d[\d,]*)[- ]word limit", text)
            if val:
                req["word_limits"]["general"] = val

    # -- Abstract --
    val = _first_int(r"abstract[^.]*?(\d[\d,]*)\s*words?", text)
    if val:
        req["abstract_limit"] = val

    # -- References --
    val = _first_int(r"(?:maximum|limit(?:ed to)?|no more than)\s+(\d+)\s+references?", text)
    if not val:
        val = _first_int(r"references?[^.]*?limited to\s+(\d+)", text)
    if val:
        req["reference_limit"] = val

    # -- Figure format --
    for fmt in ["TIFF", "EPS", "PDF", "SVG", "PNG", "JPEG", "JPG", "AI", "PSD"]:
        if re.search(rf"\b{fmt}\b", text, re.IGNORECASE):
            req["figure_format"].append(fmt.upper())
    req["figure_format"] = list(dict.fromkeys(req["figure_format"]))  # deduplicate

    # -- Figure resolution --
    dpi = _first_int(r"(\d+)\s*(?:dpi|ppi)", text)
    if dpi and 100 <= dpi <= 1200:
        req["figure_resolution_dpi"] = dpi

    # -- Citation style --
    for style in ["Vancouver", "APA", "Harvard", "Chicago", "NLM",
                  "numbered", "author-date", "superscript"]:
        if re.search(rf"\b{re.escape(style)}\b", text, re.IGNORECASE):
            req["citation_style"] = style
            break

    # -- Required sections --
    for section in ["Abstract", "Introduction", "Methods", "Results",
                    "Discussion", "Conclusion", "Acknowledgements",
                    "Conflict of Interest", "Data Availability",
                    "Ethics Statement", "Author Contributions"]:
        if re.search(rf"\b{re.escape(section)}\b", text, re.IGNORECASE):
            req["required_sections"].append(section)

    # -- Open access --
    if re.search(r"\bopen.access\b", text, re.IGNORECASE):
        req["open_access"] = True

    return req


# --------------------------------------------------------------------------- #
#  NLM journal list parser                                                    #
# --------------------------------------------------------------------------- #

def download_nlm_list() -> list[dict]:
    """
    Download and parse J_Medline.txt from NLM FTP.
    Returns list of dicts with keys: nlm_id, title, abbr, issn_print, issn_online
    """
    print(f"Downloading NLM MEDLINE journal list from {NLM_MEDLINE_URL} ...")
    data = _http_get(NLM_MEDLINE_URL)
    if not data:
        print("ERROR: Could not download NLM journal list", file=sys.stderr)
        sys.exit(1)

    journals = []
    current: dict = {}
    for line in data.splitlines():
        line = line.strip()
        if not line:
            if current.get("title") and (current.get("issn_print") or current.get("issn_online")):
                journals.append(current)
            current = {}
            continue
        if ": " in line:
            key, _, val = line.partition(": ")
            key = key.strip().lower()
            val = val.strip()
            mapping = {
                "journaltitle": "title",
                "medabbr": "abbr",
                "nlmid": "nlm_id",
                "issn (print)": "issn_print",
                "issn (online)": "issn_online",
                "isoabbr": "iso_abbr",
            }
            if key in mapping:
                current[mapping[key]] = val

    print(f"Found {len(journals)} MEDLINE-indexed journals")
    return journals


# --------------------------------------------------------------------------- #
#  CrossRef lookup                                                             #
# --------------------------------------------------------------------------- #

def crossref_journal(issn: str) -> dict:
    """Query CrossRef for journal metadata by ISSN."""
    url = CROSSREF_JOURNALS.format(issn=urllib.parse.quote(issn))
    data = _http_get(url)
    if not data:
        return {}
    try:
        msg = json.loads(data).get("message", {})
        return {
            "publisher": msg.get("publisher", ""),
            "homepage": msg.get("URL", ""),
            "subjects": [s.get("name", "") for s in msg.get("subjects", [])],
            "is_referenced_by_count": msg.get("is-referenced-by-count", 0),
        }
    except Exception:
        return {}


# --------------------------------------------------------------------------- #
#  Key generation                                                              #
# --------------------------------------------------------------------------- #

def _make_key(title: str) -> str:
    """Convert journal title to a safe filename key."""
    key = title.lower()
    key = re.sub(r"[^a-z0-9]+", "_", key)
    key = key.strip("_")
    return key[:60]


# --------------------------------------------------------------------------- #
#  Main processing                                                             #
# --------------------------------------------------------------------------- #

def process_journal(journal: dict, outdir: Path, delay: float, verbose: bool) -> bool:
    """
    Process one journal: CrossRef lookup -> find guidelines URL -> extract -> save.
    Returns True if successful, False if skipped or failed.
    """
    title = journal.get("title", "")
    issn = journal.get("issn_online") or journal.get("issn_print", "")
    key = _make_key(title)
    out_file = outdir / f"{key}.json"

    # Skip if already done
    if out_file.exists():
        if verbose:
            print(f"  SKIP (exists): {title}")
        return True

    if verbose:
        print(f"  Processing: {title} [{issn}]")

    result: dict = {
        "key": key,
        "display_name": title,
        "abbr": journal.get("abbr", ""),
        "nlm_id": journal.get("nlm_id", ""),
        "issn_print": journal.get("issn_print", ""),
        "issn_online": journal.get("issn_online", ""),
        "publisher": "",
        "homepage": "",
        "subjects": [],
        "submission_url": None,
        "requirements": {},
        "fetch_status": "pending",
    }

    # CrossRef lookup
    time.sleep(delay * 0.5)
    cr = crossref_journal(issn) if issn else {}
    result["publisher"] = cr.get("publisher", "")
    result["homepage"] = cr.get("homepage", "")
    result["subjects"] = cr.get("subjects", [])

    homepage = result["homepage"]
    if not homepage:
        result["fetch_status"] = "no_homepage"
        _save(out_file, result)
        return False

    # Find guidelines page
    time.sleep(delay * 0.5)
    guideline_url = _find_guideline_url(homepage)
    if not guideline_url:
        result["fetch_status"] = "no_guideline_url"
        _save(out_file, result)
        return False

    result["submission_url"] = guideline_url

    # Fetch and extract requirements
    time.sleep(delay)
    html = _http_get(guideline_url)
    if not html:
        result["fetch_status"] = "fetch_failed"
        _save(out_file, result)
        return False

    req = extract_requirements(guideline_url, html, title)
    result["requirements"] = req
    result["fetch_status"] = "ok"

    _save(out_file, result)
    if verbose:
        print(f"    -> OK: word_limits={req['word_limits']}, dpi={req['figure_resolution_dpi']}")
    return True


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _rebuild_index(outdir: Path) -> None:
    """Rebuild _index.json from all journal JSON files."""
    index: dict = {}
    for f in sorted(outdir.glob("*.json")):
        if f.name == "_index.json":
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            key = data.get("key", f.stem)
            index[key] = {
                "display_name": data.get("display_name", ""),
                "issn_print": data.get("issn_print", ""),
                "issn_online": data.get("issn_online", ""),
                "publisher": data.get("publisher", ""),
                "fetch_status": data.get("fetch_status", ""),
            }
        except Exception:
            pass
    (outdir / "_index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Index rebuilt: {len(index)} journals")


# --------------------------------------------------------------------------- #
#  CLI                                                                        #
# --------------------------------------------------------------------------- #

def main() -> int:
    parser = argparse.ArgumentParser(description="Build journal requirements database from NLM MEDLINE list")
    parser.add_argument("--limit", type=int, default=0, help="Max journals to process (0=all)")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N journals")
    parser.add_argument("--issn", default=None, help="Process a single journal by ISSN")
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR), help="Output directory")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests (seconds)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--rebuild-index", action="store_true", help="Only rebuild _index.json")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if args.rebuild_index:
        _rebuild_index(outdir)
        return 0

    # Download NLM list
    journals = download_nlm_list()

    # Filter by ISSN if specified
    if args.issn:
        journals = [j for j in journals
                    if j.get("issn_print") == args.issn or j.get("issn_online") == args.issn]
        if not journals:
            print(f"ISSN {args.issn} not found in MEDLINE list", file=sys.stderr)
            return 1

    # Apply offset + limit
    journals = journals[args.offset:]
    if args.limit:
        journals = journals[:args.limit]

    total = len(journals)
    print(f"Processing {total} journals (delay={args.delay}s, outdir={outdir})")

    ok = skipped = failed = 0
    for i, journal in enumerate(journals, 1):
        try:
            result = process_journal(journal, outdir, args.delay, args.verbose)
            if result:
                ok += 1
            else:
                failed += 1
        except KeyboardInterrupt:
            print("\nInterrupted. Run again to resume (already-completed journals are skipped).")
            break
        except Exception as exc:
            failed += 1
            if args.verbose:
                print(f"  ERROR: {exc}")

        # Progress report every 50 journals
        if i % 50 == 0 or i == total:
            pct = i / total * 100
            print(f"Progress: {i}/{total} ({pct:.0f}%) | OK={ok} failed={failed}")

    # Rebuild index
    _rebuild_index(outdir)
    print(f"\nDone. OK={ok}, failed={failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
