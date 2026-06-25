"""
submission_prep.py
==================
TheraSIK Submission Package Preparation

Reads a manuscript project, checks compliance against the target journal's
requirements, generates a cover letter template, and assembles a
submission-ready package in 04_submission/.

Usage (CLI):
  python scripts/submission_prep.py prepare <project_dir> [--article-type Article]
  python scripts/submission_prep.py check   <project_dir>
  python scripts/submission_prep.py cover   <project_dir> [--corresponding "Name <email>"]

Programmatic:
  from submission_prep import prepare_submission, check_compliance, generate_cover_letter
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import textwrap
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ── Submission system rules ───────────────────────────────────────────────────
# System-level checklists are fixed regardless of journal-specific word limits.
# Each entry has: aka (name variants), checklist, file_order, figure_format, notes.

SUBMISSION_SYSTEM_RULES: dict[str, dict] = {

    "ScholarOne": {
        "aka": ["ScholarOne Manuscripts", "Manuscript Central", "MC"],
        "url_pattern": "manuscriptcentral.com",
        "checklist": [
            "BLINDING: Remove all author names and affiliations from main manuscript file",
            "TITLE PAGE: Upload as a separate file (not embedded in main document)",
            "FIGURE NAMING: Fig1.tif, Fig2.tif — no spaces, no 'Figure_final_v2' names",
            "FIGURE RESOLUTION: ≥ 300 dpi halftone; ≥ 600 dpi line art (TIFF or EPS)",
            "ORCID: Link your ORCID iD in your ScholarOne account profile before submitting",
            "REVIEWER PREFERENCES: Enter suggested/excluded reviewers in 'Peer Review Preferences' tab",
            "SUPPLEMENTARY: Upload separately, labelled 'Supporting Information' or 'Supplementary Material'",
            "COVER LETTER: Paste into the text box on the submission form (not as a file)",
        ],
        "file_order": ["Main Document (anonymous)", "Title Page", "Figures (each separately)", "Supplementary"],
        "figure_format": ["TIFF (300+ dpi)", "EPS", "PDF"],
        "max_file_size_mb": 50,
        "notes": "Used by Nature Portfolio, Wiley, Oxford (OUP), IEEE, Taylor & Francis, SAGE. "
                 "URL contains 'manuscriptcentral.com'.",
    },

    "Editorial Manager": {
        "aka": ["EM", "Aries Editorial Manager", "Aries Systems"],
        "url_pattern": "editorialmanager.com",
        "checklist": [
            "COVER LETTER: Paste into the EM text box — do NOT upload as a file",
            "FIGURES: Upload each figure as a separate file; name Fig1, Fig2, etc.",
            "FIGURE SIZE: Each figure file must be < 10 MB",
            "LaTeX: Upload .tex + .bib + all figure files as a single ZIP archive",
            "TRACK CHANGES: Accept all changes before final submission (except for revisions)",
            "ORCID: EM can auto-import from orcid.org — link your account in your EM profile",
            "PDF PROOF: EM auto-generates a PDF proof — review it carefully before clicking Submit",
            "HIGHLIGHTS (Elsevier): 3–5 bullet points, ≤ 85 characters each, required for Elsevier journals",
        ],
        "file_order": ["Manuscript", "Cover Letter (text box)", "Figures", "Tables", "Supplementary"],
        "figure_format": ["TIFF", "EPS", "JPEG", "PDF"],
        "max_file_size_mb": 10,  # per figure
        "notes": "Second most widely used system. URL contains 'editorialmanager.com'. "
                 "Springer, Elsevier (most), Lippincott/Wolters Kluwer, AMA journals.",
    },

    "eJournalPress": {
        "aka": ["EJP", "eJP", "ACS Paragon Plus", "ACS Publications"],
        "url_pattern": "ejpress.org",
        "checklist": [
            "ACCOUNT: Create an account at ejpress.org or pubs.acs.org before first submission",
            "FIGURE RESOLUTION: 600 dpi TIFF for halftone/combination; 1200 dpi for pure line art",
            "REFERENCE STYLE: ACS numbered superscript for ACS journals; check individual journal guide",
            "COVER LETTER: Upload as separate PDF (not pasted in text box)",
            "SUPPORTING INFORMATION: Upload as single PDF labelled 'SI.pdf' or individual labelled files",
            "WORD TEMPLATE: Use journal-specific Word template if provided (check journal home page)",
        ],
        "file_order": ["Manuscript (Word or LaTeX)", "Cover Letter", "Figures", "Supporting Information"],
        "figure_format": ["TIFF (600+ dpi)", "EPS"],
        "max_file_size_mb": 20,
        "notes": "Used by ACS (pubs.acs.org), ASM, ASBMB journals.",
    },

    "Frontiers": {
        "aka": ["Frontiers submission system", "Loop", "Frontiers Research"],
        "url_pattern": "frontiersin.org",
        "checklist": [
            "NO BLINDING: Author names and affiliations must appear throughout the manuscript",
            "ORCIDs: Mandatory for ALL authors — collect all ORCIDs before starting submission",
            "ARTICLE TYPE: Select the exact Frontiers article type (Original Research, Review, Mini Review, etc.)",
            "KEYWORDS: 5–8 keywords required (Frontiers enforces this)",
            "ETHICS STATEMENT: Required for all studies involving humans or animals",
            "WORD LIMITS: Strictly enforced by the system — submission blocked if exceeded",
            "FIGURES: Upload as TIFF (≥ 300 dpi) or EPS — system converts for web display",
            "OPEN REVIEW: Reviewers interact openly; authors can respond during review",
            "SPECIALTY SECTION: Choose the correct specialty section — determines editorial board",
        ],
        "file_order": ["Manuscript (Word or LaTeX)", "Figures", "Tables", "Supplementary"],
        "figure_format": ["TIFF (300+ dpi)", "EPS", "PNG"],
        "max_file_size_mb": 30,
        "notes": "Used exclusively by Frontiers Media journals (frontiersin.org). "
                 "Open collaborative review — no anonymous peer review.",
    },

    "Snapp": {
        "aka": ["NPG", "Nature submission system", "Nature Portfolio submission", "mts-nature"],
        "url_pattern": "mts-nature.com",
        "checklist": [
            "ACCOUNT: Use your nature.com account (separate from ScholarOne)",
            "MANUSCRIPT: Single editable Word file — figures embedded AND uploaded separately",
            "REPORTING SUMMARY: Complete the mandatory Nature reporting checklist "
            "(Life Sciences / Statistics / Neuroscience, depending on study type)",
            "EXTENDED DATA: Separate from main figures; still counts toward figure limit",
            "DATA AVAILABILITY: Mandatory 'Data availability' section in manuscript",
            "CODE AVAILABILITY: Mandatory if any custom code/scripts were used",
            "COVER LETTER: Type into the text box — NOT uploaded as a separate file",
            "SUPPLEMENTARY INFO: One PDF preferred; video/data as separate files",
            "COMPETING INTERESTS: All authors must declare (including 'none')",
        ],
        "file_order": ["Main MS (Word)", "Figures (each separately)", "Reporting Summary", "Supplementary"],
        "figure_format": ["PDF", "EPS", "TIFF (600 dpi)"],
        "max_file_size_mb": 30,
        "notes": "Used by Nature and Nature-branded sub-journals. "
                 "URL pattern: mts-*.nature.com. Distinct from ScholarOne used by other Springer Nature journals.",
    },

    "Bench>Press": {
        "aka": ["BenchPress", "HighWire Press", "Rockefeller University Press", "JCI", "BenchPress/HighWire"],
        "url_pattern": "submit.jci.org",
        "checklist": [
            "BLINDING: Remove all identifying information from manuscript and figures",
            "eTOC BLURB: 2-sentence plain-language summary required for Table of Contents entry",
            "FIGURE RESOLUTION: 300 dpi minimum; 600 dpi for combination figures",
            "LaTeX: Supported — upload as ZIP with all dependencies and a compiled PDF",
            "REVIEWER EXCLUSIONS: State in cover letter (no separate form field)",
            "CLINICAL TRIAL REGISTRATION: Number required in abstract and methods if applicable",
        ],
        "file_order": ["Manuscript", "Figures", "Supplemental Materials"],
        "figure_format": ["TIFF", "EPS", "PDF"],
        "max_file_size_mb": 20,
        "notes": "Used by JCI, JEM, JCB (Rockefeller Press), some HighWire Press journals.",
    },

    "EVISE": {
        "aka": ["Elsevier EVISE", "Elsevier Editorial System", "EES"],
        "url_pattern": "evise.com",
        "checklist": [
            "MIGRATION NOTE: EVISE is being migrated to Editorial Manager — check journal's current system",
            "HIGHLIGHTS: 3–5 bullet points, ≤ 85 characters each — required by all Elsevier journals",
            "GRAPHICAL ABSTRACT: 1 image, width 531 px, recommended for most Elsevier journals",
            "CRediT ROLES: Author contribution roles required for all authors",
            "OPEN ACCESS: Choose license (CC-BY / CC-BY-NC-ND) during submission for gold OA",
            "DATA IN BRIEF: Elsevier offers companion Data in Brief article for datasets",
        ],
        "file_order": ["Manuscript", "Highlights", "Graphical Abstract", "Figures", "Supplementary"],
        "figure_format": ["TIFF", "EPS", "JPEG"],
        "max_file_size_mb": 20,
        "notes": "Legacy Elsevier system for Cell Press, Lancet group. Migrating to Editorial Manager.",
    },

    "ScienceSubmit": {
        "aka": ["Science submission system", "AAAS submission"],
        "url_pattern": "submit2.sciencemag.org",
        "checklist": [
            "SINGLE FILE: Submit manuscript as a single PDF for initial review",
            "STRUCTURED ABSTRACT: 125 words maximum; one-paragraph format",
            "IMPACT STATEMENT: One sentence (< 100 characters) for editorial assessment",
            "TECHNICAL COMMENT: If responding to a published article, use specific Technical Comment format",
            "SUPPLEMENTARY MATERIALS: Must be in a single PDF labelled 'Supplementary Materials'",
            "FIGURE LEGENDS: Must be embedded at the end of the main manuscript file",
            "REPLICATION: Statistical analysis and replication details required in all papers",
        ],
        "file_order": ["Single PDF (MS + legends + refs)", "Figures (high-res TIFF)", "Supplementary PDF"],
        "figure_format": ["TIFF (300+ dpi)", "EPS"],
        "max_file_size_mb": 25,
        "notes": "Used exclusively by Science and Science Advances (AAAS).",
    },

    "PeerJ": {
        "aka": ["PeerJ submission", "PeerJ system"],
        "url_pattern": "peerj.com",
        "checklist": [
            "PEERJ ACCOUNT: All authors must have a PeerJ account (free at peerj.com)",
            "PRE-REGISTRATION: Optional but supported via OSF integration",
            "OPEN DATA: Strongly encouraged — upload to figshare, Zenodo, or Dryad",
            "REVIEWER SUGGESTIONS: 5 reviewers suggested (required)",
            "LATEX TEMPLATE: Use PeerJ LaTeX template (github.com/PeerJ/PeerJ-LaTeX-template)",
            "SUPPLEMENTARY: Each file labelled individually; no single ZIP",
        ],
        "file_order": ["Manuscript (Word/LaTeX)", "Figures", "Supplementary Files"],
        "figure_format": ["TIFF", "EPS", "PNG", "JPEG"],
        "max_file_size_mb": 25,
        "notes": "Open access only. Transparent peer review — reviews published alongside paper.",
    },

    "F1000Research": {
        "aka": ["F1000", "Taylor & Francis Open Research", "Open Research platform"],
        "url_pattern": "f1000research.com",
        "checklist": [
            "PUBLISH FIRST: Article is published immediately after basic checks, BEFORE peer review",
            "RAW DATA: Upload all underlying datasets to an approved repository before submission",
            "REGISTERED REPORT: Protocol published before study — pre-registration strongly encouraged",
            "AUTHOR CONTRIBUTIONS: Detailed CRediT statement required",
            "COMPETING INTERESTS: Detailed declaration required for all authors",
            "REVISIONS: All versions remain publicly visible — versioning is transparent",
        ],
        "file_order": ["Manuscript", "Data Files / Repository Links", "Figures"],
        "figure_format": ["TIFF", "PNG", "JPEG", "PDF"],
        "max_file_size_mb": 50,
        "notes": "Publish-then-review model. All versions and reviews publicly visible.",
    },
}

# ── Publisher → submission system heuristic mapping ───────────────────────────
# Ordered list: (pattern_in_publisher, submission_system_name)
# First match wins — put more specific patterns before broader ones.

PUBLISHER_SYSTEM_MAP: list[tuple[str, str]] = [
    # Nature-branded journals (Snapp, not ScholarOne)
    ("nature portfolio", "Snapp"),
    ("springer nature", "Snapp"),          # broad — refined below by journal name checks
    ("nature publishing", "Snapp"),

    # Elsevier properties
    ("cell press", "EVISE"),
    ("lancet", "EVISE"),
    ("elsevier", "Editorial Manager"),

    # Springer (non-Nature) → ScholarOne
    ("springer", "ScholarOne"),
    ("biomed central", "ScholarOne"),
    ("bmc", "ScholarOne"),

    # Wiley
    ("wiley", "ScholarOne"),
    ("blackwell", "ScholarOne"),
    ("john wiley", "ScholarOne"),

    # Oxford
    ("oxford university press", "ScholarOne"),
    ("oup", "ScholarOne"),
    ("oxford academic", "ScholarOne"),

    # Taylor & Francis
    ("taylor & francis", "ScholarOne"),
    ("taylor and francis", "ScholarOne"),
    ("informa", "ScholarOne"),
    ("routledge", "ScholarOne"),

    # SAGE
    ("sage publications", "ScholarOne"),
    ("sage pub", "ScholarOne"),

    # American Chemical Society
    ("american chemical society", "eJournalPress"),
    ("acs publications", "eJournalPress"),

    # Microbiology/Biology societies
    ("american society for microbiology", "eJournalPress"),
    ("asm press", "eJournalPress"),
    ("american society of biochemistry", "eJournalPress"),
    ("american society of biological", "eJournalPress"),
    ("asbmb", "eJournalPress"),

    # Frontiers
    ("frontiers media", "Frontiers"),
    ("frontiers in", "Frontiers"),
    ("frontiers research", "Frontiers"),

    # AAAS / Science
    ("aaas", "ScienceSubmit"),
    ("american association for the advancement", "ScienceSubmit"),

    # HighWire / Rockefeller
    ("rockefeller university", "Bench>Press"),
    ("highwire", "Bench>Press"),
    ("jci", "Bench>Press"),

    # Lippincott / Wolters Kluwer
    ("lippincott", "Editorial Manager"),
    ("wolters kluwer", "Editorial Manager"),

    # American Medical Association
    ("american medical association", "Editorial Manager"),
    ("ama publications", "Editorial Manager"),

    # BMJ Publishing
    ("bmj publishing", "BMJ submission system"),
    ("bmj group", "BMJ submission system"),
    ("british medical journal", "BMJ submission system"),

    # PeerJ
    ("peerj", "PeerJ"),

    # PLOS
    ("plos", "Editorial Manager"),
    ("public library of science", "Editorial Manager"),

    # Higher Education Press
    ("higher education press", "ScholarOne"),

    # MIT Press
    ("mit press", "ScholarOne"),

    # Cambridge University Press
    ("cambridge university press", "ScholarOne"),

    # Royal Society
    ("royal society publishing", "ScholarOne"),
    ("royal society of chemistry", "ScholarOne"),

    # American Physical Society
    ("american physical society", "Editorial Manager"),

    # American Physiological Society
    ("american physiological society", "Editorial Manager"),

    # IOP Publishing
    ("iop publishing", "ScholarOne"),
    ("institute of physics", "ScholarOne"),

    # MDPI
    ("mdpi", "MDPI submission system"),

    # Hindawi
    ("hindawi", "Editorial Manager"),

    # De Gruyter
    ("de gruyter", "Editorial Manager"),

    # Karger
    ("karger", "Editorial Manager"),

    # Thieme
    ("thieme", "Editorial Manager"),

    # IEEE
    ("ieee", "ScholarOne"),
    ("institute of electrical", "ScholarOne"),
]


def infer_submission_system(publisher: str, journal_name: str = "") -> str:
    """
    Infer submission system from publisher name (and optionally journal name).
    Returns system name string or empty string if unknown.
    """
    pub_lower = publisher.lower().strip()
    jnl_lower = journal_name.lower().strip()

    # Snapp vs ScholarOne for Springer Nature: Nature-branded journals use Snapp
    if "springer nature" in pub_lower or "nature portfolio" in pub_lower:
        if any(x in jnl_lower for x in ["nature ", "scientific reports", "communications biology",
                                          "nature medicine", "nature methods", "nature genetics",
                                          "nature communications", "nature climate"]):
            return "Snapp"
        return "ScholarOne"  # Non-Nature Springer journals use ScholarOne

    for pattern, system in PUBLISHER_SYSTEM_MAP:
        if pattern in pub_lower:
            return system

    return ""

# ── Resolve paths ──────────────────────────────────────────────────────────────
SKILL_DIR = Path(os.environ.get("THERASIK_DIR", Path(__file__).resolve().parents[1]))
JOURNAL_DIR = SKILL_DIR / "assets" / "journal_requirements"
LICENSE_API = os.environ.get("THERASIK_LICENSE_API", "https://api.therasik.io")


# ── System rules helper ────────────────────────────────────────────────────────

def _get_system_rules(system_name: str) -> dict | None:
    """
    Return SUBMISSION_SYSTEM_RULES entry for a given system name.
    Matches by exact key or by 'aka' aliases (case-insensitive).
    """
    if not system_name:
        return None
    name_lower = system_name.lower().strip()
    for key, rules in SUBMISSION_SYSTEM_RULES.items():
        if key.lower() == name_lower:
            return rules
        if any(a.lower() == name_lower for a in rules.get("aka", [])):
            return rules
        # partial match on key
        if name_lower in key.lower() or key.lower() in name_lower:
            return rules
    return None


def get_system_guide(system_name: str) -> dict:
    """
    Return full submission guide for a named system.
    Useful as standalone MCP tool or CLI command.
    """
    rules = _get_system_rules(system_name)
    if not rules:
        return {
            "error": f"No built-in rules for '{system_name}'.",
            "available_systems": list(SUBMISSION_SYSTEM_RULES.keys()),
        }
    return {
        "system": system_name,
        **rules,
    }


# ── Journal requirement loader ─────────────────────────────────────────────────

def _load_journal_local(name: str) -> dict | None:
    """Load journal requirements from local JSON cache."""
    index_path = JOURNAL_DIR / "_index.json"
    if not index_path.exists():
        return None

    index = json.loads(index_path.read_text(encoding="utf-8"))
    query = name.lower().strip()

    # Exact key match
    if query in index:
        f = JOURNAL_DIR / f"{query}.json"
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))

    # Fuzzy: query appears in key or display_name
    for k, v in index.items():
        if query in k or query in v.get("display_name", "").lower():
            f = JOURNAL_DIR / f"{k}.json"
            if f.exists():
                return json.loads(f.read_text(encoding="utf-8"))

    return None


def _load_journal_cloud(name: str) -> dict | None:
    """Fetch journal requirements from TheraSIK cloud API."""
    try:
        url = f"{LICENSE_API}/journal/{urllib.parse.quote(name)}"
        req = urllib.request.Request(url, headers={"User-Agent": "therasik-mcp/1.1"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            # If server returned a match-list rather than a single record, take first
            if "matches" in data and "article_types" not in data:
                return None
            return data
    except Exception:
        return None


def load_journal(name: str) -> dict | None:
    """Load journal requirements: local first, cloud fallback."""
    local = _load_journal_local(name)
    if local:
        return local
    return _load_journal_cloud(name)


# ── Word counting ──────────────────────────────────────────────────────────────

def _strip_markdown(text: str) -> str:
    """Remove markdown syntax before word counting."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)  # code blocks
    text = re.sub(r"`[^`]+`", " ", text)                      # inline code
    text = re.sub(r"!\[.*?\]\(.*?\)", " ", text)              # images
    text = re.sub(r"\[.*?\]\(.*?\)", lambda m: m.group(0).split("]")[0][1:], text)  # links
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)  # headings
    text = re.sub(r"[*_~]{1,3}", "", text)                    # bold/italic
    text = re.sub(r"^\s*[-*+>]\s+", "", text, flags=re.MULTILINE)  # bullets/blockquotes
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)   # numbered lists
    text = re.sub(r"\|.*?\|", " ", text)                       # tables
    return text


def count_words(text: str) -> int:
    """Count words in (possibly markdown) text."""
    clean = _strip_markdown(text)
    return len(re.findall(r"\b\w+\b", clean))


def count_abstract_words(text: str) -> int:
    """Extract and count words in the Abstract section."""
    # Match ## Abstract ... (up to the next ## heading)
    m = re.search(
        r"^#{1,3}\s*Abstract\s*\n(.*?)(?=^#{1,3}\s|\Z)",
        text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL
    )
    if m:
        return count_words(m.group(1))
    return 0


def count_references(text: str) -> int:
    """Heuristic reference count from References section."""
    m = re.search(
        r"^#{1,3}\s*References?\s*\n(.*?)(?=^#{1,3}\s|\Z)",
        text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL
    )
    if not m:
        return 0
    ref_block = m.group(1)
    # Count numbered entries like "1." or "[1]" or bare lines with DOI/author patterns
    numbered = re.findall(r"^\s*(?:\d+[\.\)]|\[\d+\])", ref_block, re.MULTILINE)
    if numbered:
        return len(numbered)
    # Fall back: count non-empty lines
    lines = [l.strip() for l in ref_block.split("\n") if l.strip()]
    return len(lines)


def detect_sections(text: str) -> list[str]:
    """Return all section headings found in the manuscript."""
    return [
        m.group(1).strip()
        for m in re.finditer(r"^#{1,3}\s+(.+)$", text, re.MULTILINE)
    ]


def count_figures(text: str, figure_dir: Path | None = None) -> int:
    """
    Count figures: markdown ![...](...) references + files in figures/ dir.
    Returns whichever is larger.
    """
    md_figs = len(re.findall(r"!\[.*?\]\(.*?\)", text))
    dir_figs = 0
    if figure_dir and figure_dir.exists():
        exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".eps", ".pdf", ".svg"}
        dir_figs = sum(1 for f in figure_dir.iterdir() if f.suffix.lower() in exts)
    return max(md_figs, dir_figs)


# ── Compliance check ───────────────────────────────────────────────────────────

COMPLIANCE_PASS = "PASS"
COMPLIANCE_WARN = "WARN"
COMPLIANCE_FAIL = "FAIL"
COMPLIANCE_SKIP = "SKIP"  # requirement not specified


def check_compliance(project_dir: str | Path, article_type: str | None = None) -> dict:
    """
    Check manuscript compliance against target journal requirements.

    Returns:
        {
          "status": "PASS" | "FAIL" | "WARN",
          "journal": str,
          "article_type": str,
          "checks": [{"name": str, "status": str, "detail": str}, ...],
          "submission_url": str,
          "submission_system": str,
        }
    """
    proj = Path(project_dir).resolve()
    config_path = proj / "project_config.json"
    if not config_path.exists():
        return {"status": COMPLIANCE_FAIL, "error": "project_config.json not found"}

    config = json.loads(config_path.read_text(encoding="utf-8"))
    journal_name = config.get("target_journal", "")
    art_type = article_type or config.get("article_type", "Article")

    # Load journal requirements
    journal = load_journal(journal_name)
    if not journal:
        return {
            "status": COMPLIANCE_WARN,
            "journal": journal_name,
            "article_type": art_type,
            "error": f"Journal '{journal_name}' not found in database (5,226 journals available). "
                     "Check spelling or use a different article type.",
            "checks": [],
        }

    # Pick the article_type sub-spec (case-insensitive, fuzzy)
    art_specs: dict = journal.get("article_types", {})
    art_key = None
    for k in art_specs:
        if k.lower() == art_type.lower():
            art_key = k
            break
    if not art_key and art_specs:
        art_key = next(iter(art_specs))  # take first available
    spec = art_specs.get(art_key, {}) if art_key else {}

    # Read manuscript
    ms_path = proj / config.get("outputs", {}).get("manuscript_md", "01_manuscript/manuscript.md")
    if not ms_path.exists():
        ms_path = next(proj.rglob("*.md"), None)
    if not ms_path or not ms_path.exists():
        return {"status": COMPLIANCE_FAIL, "error": "Manuscript file not found", "journal": journal_name}

    text = ms_path.read_text(encoding="utf-8")

    checks: list[dict] = []

    # ── Word count (main text) ─────────────────────────────────────────────────
    word_limit = spec.get("max_words_main_text")
    total_words = count_words(text)
    if word_limit:
        pct = total_words / word_limit * 100
        if total_words <= word_limit:
            status = COMPLIANCE_PASS if pct >= 10 else COMPLIANCE_WARN
            detail = f"{total_words:,} / {word_limit:,} words ({pct:.0f}%)"
        else:
            status = COMPLIANCE_FAIL
            detail = f"{total_words:,} words — EXCEEDS limit of {word_limit:,} by {total_words - word_limit:,}"
        checks.append({"name": "Main text word count", "status": status, "detail": detail})
    else:
        checks.append({
            "name": "Main text word count",
            "status": COMPLIANCE_SKIP,
            "detail": f"{total_words:,} words (no limit specified for this journal/type)"
        })

    # ── Abstract word count ────────────────────────────────────────────────────
    abs_limit = spec.get("max_words_abstract")
    abs_words = count_abstract_words(text)
    if abs_limit:
        if abs_words == 0:
            checks.append({
                "name": "Abstract word count",
                "status": COMPLIANCE_WARN,
                "detail": f"Abstract section not detected. Limit: {abs_limit} words."
            })
        elif abs_words <= abs_limit:
            checks.append({
                "name": "Abstract word count",
                "status": COMPLIANCE_PASS,
                "detail": f"{abs_words} / {abs_limit} words"
            })
        else:
            checks.append({
                "name": "Abstract word count",
                "status": COMPLIANCE_FAIL,
                "detail": f"{abs_words} words — EXCEEDS limit of {abs_limit} by {abs_words - abs_limit}"
            })

    # ── Required sections ──────────────────────────────────────────────────────
    required_sections = spec.get("required_sections", [])
    if required_sections:
        found_sections = [s.lower() for s in detect_sections(text)]
        missing = [s for s in required_sections if s.lower() not in found_sections]
        if missing:
            checks.append({
                "name": "Required sections",
                "status": COMPLIANCE_FAIL,
                "detail": f"Missing: {', '.join(missing)}"
            })
        else:
            checks.append({
                "name": "Required sections",
                "status": COMPLIANCE_PASS,
                "detail": f"All {len(required_sections)} required sections present"
            })

    # ── Reference count ────────────────────────────────────────────────────────
    ref_limit = spec.get("max_references")
    ref_count = count_references(text)
    if ref_limit:
        if ref_count <= ref_limit:
            checks.append({
                "name": "Reference count",
                "status": COMPLIANCE_PASS,
                "detail": f"{ref_count} / {ref_limit} references"
            })
        else:
            checks.append({
                "name": "Reference count",
                "status": COMPLIANCE_FAIL,
                "detail": f"{ref_count} references — EXCEEDS limit of {ref_limit} by {ref_count - ref_limit}"
            })
    else:
        checks.append({
            "name": "Reference count",
            "status": COMPLIANCE_SKIP,
            "detail": f"{ref_count} references (no limit specified)"
        })

    # ── Figure count ───────────────────────────────────────────────────────────
    fig_limit = spec.get("max_figures")
    fig_dir = proj / "figures"
    fig_count = count_figures(text, fig_dir)
    if fig_limit:
        if fig_count <= fig_limit:
            checks.append({
                "name": "Figure count",
                "status": COMPLIANCE_PASS,
                "detail": f"{fig_count} / {fig_limit} figures"
            })
        else:
            checks.append({
                "name": "Figure count",
                "status": COMPLIANCE_FAIL,
                "detail": f"{fig_count} figures — EXCEEDS limit of {fig_limit}"
            })
    else:
        checks.append({
            "name": "Figure count",
            "status": COMPLIANCE_SKIP,
            "detail": f"{fig_count} figures (no limit specified)"
        })

    # ── Reference style ────────────────────────────────────────────────────────
    ref_style = journal.get("reference_style", "")
    if ref_style:
        checks.append({
            "name": "Reference style",
            "status": COMPLIANCE_WARN,  # requires human verification
            "detail": f"Required: {ref_style} — verify manually"
        })

    # ── Figure format ──────────────────────────────────────────────────────────
    fig_formats = journal.get("figure_format", [])
    if fig_formats:
        checks.append({
            "name": "Figure format",
            "status": COMPLIANCE_WARN,
            "detail": f"Accepted: {', '.join(fig_formats)} — verify each figure file"
        })

    # ── Data/code availability ─────────────────────────────────────────────────
    data_avail = journal.get("data_availability", "")
    if "required" in data_avail.lower():
        has_data_stmt = bool(re.search(
            r"data\s+availability|availability\s+of\s+data",
            text, re.IGNORECASE
        ))
        checks.append({
            "name": "Data availability statement",
            "status": COMPLIANCE_PASS if has_data_stmt else COMPLIANCE_FAIL,
            "detail": "Found in manuscript" if has_data_stmt
                      else f"Required by {journal_name} — add Data Availability section"
        })

    # ── QA gates ──────────────────────────────────────────────────────────────
    qa_dir = proj / "03_QA"
    required_qa = [
        "reference_claim_support_QA",
        "figure_contract_QA",
        "ai_style_human_voice_QA",
        "paragraph_structure_QA",
    ]
    qa_pass = []
    qa_fail = []
    for gate in required_qa:
        qa_file = qa_dir / f"{gate}.md"
        if qa_file.exists():
            content = qa_file.read_text(encoding="utf-8")
            if "Status: PASS" in content:
                qa_pass.append(gate)
            else:
                qa_fail.append(gate)
        else:
            qa_fail.append(f"{gate} (missing)")

    if qa_fail:
        checks.append({
            "name": "TheraSIK QA gates",
            "status": COMPLIANCE_FAIL,
            "detail": f"Failed/missing: {', '.join(qa_fail)}"
        })
    else:
        checks.append({
            "name": "TheraSIK QA gates",
            "status": COMPLIANCE_PASS,
            "detail": f"All {len(qa_pass)} gates PASS"
        })

    # ── Submission system-specific rules ──────────────────────────────────────
    sys_name = journal.get("submission_system", "")
    sys_rules = _get_system_rules(sys_name)
    if sys_rules:
        checks.append({
            "name": f"System checklist ({sys_name})",
            "status": COMPLIANCE_WARN,  # always warn: requires human action
            "detail": (
                f"Submission URL: {journal.get('submission_url', '(see journal website)')} | "
                f"File order: {' → '.join(sys_rules.get('file_order', []))} | "
                f"Key rules below."
            ),
            "system_checklist": sys_rules.get("checklist", []),
            "figure_format":    sys_rules.get("figure_format", []),
            "max_file_size_mb": sys_rules.get("max_file_size_mb"),
        })
    elif sys_name:
        checks.append({
            "name": f"Submission system: {sys_name}",
            "status": COMPLIANCE_WARN,
            "detail": f"No built-in ruleset for '{sys_name}'. Check journal website for instructions.",
        })

    # ── Overall status ─────────────────────────────────────────────────────────
    statuses = [c["status"] for c in checks]
    if COMPLIANCE_FAIL in statuses:
        overall = COMPLIANCE_FAIL
    elif COMPLIANCE_WARN in statuses:
        overall = COMPLIANCE_WARN
    else:
        overall = COMPLIANCE_PASS

    return {
        "status":            overall,
        "journal":           journal.get("display_name", journal_name),
        "article_type":      art_key or art_type,
        "submission_system": sys_name,
        "submission_url":    journal.get("submission_url", ""),
        "open_access":       journal.get("open_access_option", False),
        "preprint_policy":   journal.get("preprint_policy", ""),
        "checks":            checks,
        "word_count":        total_words,
        "notes":             spec.get("notes", ""),
        "system_rules":      sys_rules,
    }


# ── Cover letter generator ─────────────────────────────────────────────────────

def generate_cover_letter(
    project_dir: str | Path,
    corresponding_author: str = "",
    article_type: str | None = None,
) -> str:
    """
    Generate a cover letter template for the target journal.

    Returns cover letter text (markdown).
    Writes to 04_submission/cover_letter.md.
    """
    proj = Path(project_dir).resolve()
    config_path = proj / "project_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}

    journal_name = config.get("target_journal", "[Journal Name]")
    art_type = article_type or config.get("article_type", "Article")
    journal = load_journal(journal_name) or {}
    display = journal.get("display_name", journal_name)

    # Extract title from manuscript
    ms_path = proj / config.get("outputs", {}).get("manuscript_md", "01_manuscript/manuscript.md")
    title = "[Manuscript Title]"
    if ms_path.exists():
        text = ms_path.read_text(encoding="utf-8")
        m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if m:
            title = m.group(1).strip()

    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    editor_block = f"The Editorial Office\n{display}"

    if not corresponding_author:
        corresponding_author = "[Corresponding Author Name]\n[Affiliation]\n[Email] | [Phone]"

    letter = textwrap.dedent(f"""\
        # Cover Letter

        {today}

        {editor_block}

        Dear Editor-in-Chief,

        We are pleased to submit our manuscript entitled:

        **"{title}"**

        for consideration as a {art_type} in *{display}*.

        ## Significance

        [2–3 sentences: What is the central question? Why does it matter now?
        What gap does this work fill?]

        ## Key Findings

        [2–3 bullet points of the most important results, in plain language.]

        - [Finding 1]
        - [Finding 2]
        - [Finding 3]

        ## Fit for {display}

        [1–2 sentences: Why is this work appropriate for *{display}*'s scope
        and readership? Reference the journal's stated scope if known.]

        ## Originality and Ethics

        This manuscript has not been previously published and is not under
        consideration elsewhere. All authors have read and approved the final
        version. The study was conducted in accordance with applicable ethical
        standards [add ethics statement / IRB number if applicable].

        ## Data Availability

        [State where data are deposited or that data are available upon request.]

        ## Suggested Reviewers (optional)

        | Name | Affiliation | Email | Expertise |
        |------|-------------|-------|-----------|
        | [Name] | [Affiliation] | [email] | [area] |
        | [Name] | [Affiliation] | [email] | [area] |
        | [Name] | [Affiliation] | [email] | [area] |

        ## Opposed Reviewers (optional)

        [List any reviewers who should be excluded and the reason (e.g., conflict
        of interest).]

        We hope you will find our work suitable for publication in *{display}*
        and look forward to your response.

        Sincerely,

        {corresponding_author}

        ---
        *Generated by TheraSIK Academic Writing Suite*
        *Review all [bracketed placeholders] before submission.*
    """)

    sub_dir = proj / "04_submission"
    sub_dir.mkdir(exist_ok=True)
    (sub_dir / "cover_letter.md").write_text(letter, encoding="utf-8")

    return letter


# ── Submission checklist ───────────────────────────────────────────────────────

def generate_checklist(compliance: dict, project_dir: str | Path) -> str:
    """
    Generate a submission checklist markdown file.
    Writes to 04_submission/submission_checklist.md.
    """
    proj = Path(project_dir).resolve()
    journal = compliance.get("journal", "")
    art_type = compliance.get("article_type", "")
    system = compliance.get("submission_system", "")
    url = compliance.get("submission_url", "")
    overall = compliance.get("status", "UNKNOWN")

    lines = [
        f"# Submission Checklist",
        f"",
        f"**Journal**: {journal}  ",
        f"**Article type**: {art_type}  ",
        f"**Submission system**: {system}  ",
        f"**Submission URL**: {url if url else '(see journal website)'}  ",
        f"**Compliance status**: {overall}  ",
        f"**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"",
        f"---",
        f"",
        f"## Automated Compliance Checks",
        f"",
    ]

    status_icon = {
        COMPLIANCE_PASS: "✅",
        COMPLIANCE_FAIL: "❌",
        COMPLIANCE_WARN: "⚠️",
        COMPLIANCE_SKIP: "–",
    }

    for check in compliance.get("checks", []):
        icon = status_icon.get(check["status"], "?")
        lines.append(f"- {icon} **{check['name']}**: {check['detail']}")

    lines += [
        "",
        "---",
        "",
        "## Manual Checklist",
        "",
        "Complete each item before submitting:",
        "",
        "### Manuscript Files",
        "- [ ] Manuscript is anonymised (if blind review required)",
        "- [ ] Title page with all author affiliations and ORCID IDs",
        "- [ ] Abstract matches required structure and word limit",
        "- [ ] All figure legends included in manuscript",
        "- [ ] Supplementary materials clearly labelled",
        "",
        "### Figures",
        "- [ ] All figures in accepted format (see compliance check above)",
        "- [ ] Resolution ≥ 300 dpi (600 dpi for line art)",
        "- [ ] Colour mode appropriate (RGB for online, CMYK for print if required)",
        "- [ ] Figures numbered in order of appearance",
        "",
        "### References",
        "- [ ] All references formatted in the required style",
        "- [ ] All DOIs verified and clickable",
        "- [ ] Preprint citations flagged if journal requires",
        "",
        "### Declarations",
        "- [ ] Author contributions (CRediT taxonomy)",
        "- [ ] Funding sources and grant numbers",
        "- [ ] Conflicts of interest / competing interests",
        "- [ ] Data availability statement",
        "- [ ] Code availability statement (if applicable)",
        "- [ ] Ethics statement / IRB approval (if applicable)",
        "- [ ] Informed consent statement (if human subjects)",
        "",
        "### Cover Letter",
        "- [ ] Cover letter completed (see cover_letter.md)",
        "- [ ] Suggested reviewers (3–5 recommended)",
        "- [ ] Opposed reviewers listed with justification",
        "",
        "### TheraSIK QA Gates",
        "- [ ] reference_claim_support_QA: PASS",
        "- [ ] figure_contract_QA: PASS",
        "- [ ] ai_style_human_voice_QA: PASS",
        "- [ ] paragraph_structure_QA: PASS",
        "- [ ] workflow_execution_audit_QA: reviewed and signed off",
        "- [ ] author_declarations_QA: all fields completed",
        "",
        "---",
        "",
        "*All ❌ items must be resolved before submission.*  ",
        "*All ⚠️ items require human verification.*  ",
        "*Generated by TheraSIK Academic Writing Suite*",
    ]

    checklist_text = "\n".join(lines)
    sub_dir = proj / "04_submission"
    sub_dir.mkdir(exist_ok=True)
    (sub_dir / "submission_checklist.md").write_text(checklist_text, encoding="utf-8")
    return checklist_text


# ── Package assembler ──────────────────────────────────────────────────────────

def prepare_submission(
    project_dir: str | Path,
    article_type: str | None = None,
    corresponding_author: str = "",
) -> dict:
    """
    Full submission package preparation:
      1. Run compliance check
      2. Generate cover letter
      3. Generate checklist
      4. Copy submission-ready files to 04_submission/

    Returns summary dict with status, checks, and file manifest.
    """
    proj = Path(project_dir).resolve()
    sub_dir = proj / "04_submission"
    sub_dir.mkdir(exist_ok=True)

    # 1. Compliance
    compliance = check_compliance(proj, article_type)

    # 2. Cover letter
    cover = generate_cover_letter(proj, corresponding_author, article_type)

    # 3. Checklist
    checklist = generate_checklist(compliance, proj)

    # 4. Copy outputs
    files_copied: list[str] = []
    config_path = proj / "project_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    outputs = config.get("outputs", {})

    # Manuscript DOCX
    docx_src = proj / outputs.get("docx", "02_outputs/manuscript.docx")
    if docx_src.exists():
        shutil.copy2(docx_src, sub_dir / docx_src.name)
        files_copied.append(str(sub_dir / docx_src.name))

    # Manuscript PDF
    pdf_src = proj / outputs.get("pdf", "02_outputs/manuscript.pdf")
    if pdf_src.exists():
        shutil.copy2(pdf_src, sub_dir / pdf_src.name)
        files_copied.append(str(sub_dir / pdf_src.name))

    # Figures directory
    fig_dir = proj / "figures"
    if fig_dir.exists():
        sub_fig = sub_dir / "figures"
        if sub_fig.exists():
            shutil.rmtree(sub_fig)
        shutil.copytree(fig_dir, sub_fig)
        files_copied.append(str(sub_fig))

    # Supplementary materials
    supp_dir = proj / "supplementary"
    if supp_dir.exists():
        sub_supp = sub_dir / "supplementary"
        if sub_supp.exists():
            shutil.rmtree(sub_supp)
        shutil.copytree(supp_dir, sub_supp)
        files_copied.append(str(sub_supp))

    # QA report (for author records)
    qa_dir = proj / "03_QA"
    if qa_dir.exists():
        sub_qa = sub_dir / "QA_reports"
        if sub_qa.exists():
            shutil.rmtree(sub_qa)
        shutil.copytree(qa_dir, sub_qa)
        files_copied.append(str(sub_qa))

    # Write submission_prep.json manifest
    manifest = {
        "prepared_at":       datetime.now(timezone.utc).isoformat(),
        "journal":           compliance.get("journal", ""),
        "article_type":      compliance.get("article_type", ""),
        "submission_system": compliance.get("submission_system", ""),
        "submission_url":    compliance.get("submission_url", ""),
        "compliance_status": compliance.get("status", ""),
        "word_count":        compliance.get("word_count", 0),
        "checks":            compliance.get("checks", []),
        "files":             files_copied,
    }
    (sub_dir / "submission_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return {
        "status":            compliance.get("status"),
        "journal":           compliance.get("journal", ""),
        "submission_system": compliance.get("submission_system", ""),
        "submission_url":    compliance.get("submission_url", ""),
        "word_count":        compliance.get("word_count", 0),
        "checks":            compliance.get("checks", []),
        "submission_dir":    str(sub_dir),
        "files_copied":      files_copied,
        "cover_letter":      str(sub_dir / "cover_letter.md"),
        "checklist":         str(sub_dir / "submission_checklist.md"),
        "notes":             compliance.get("notes", ""),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def _print_compliance(result: dict):
    status_icon = {
        COMPLIANCE_PASS: "✅ PASS",
        COMPLIANCE_FAIL: "❌ FAIL",
        COMPLIANCE_WARN: "⚠️  WARN",
        COMPLIANCE_SKIP: "–  SKIP",
    }
    print(f"\nJournal:  {result.get('journal', 'unknown')}")
    print(f"Type:     {result.get('article_type', '')}")
    print(f"System:   {result.get('submission_system', '')} — {result.get('submission_url', '')}")
    print(f"Overall:  {result.get('status', 'UNKNOWN')}")
    print()
    for c in result.get("checks", []):
        icon = status_icon.get(c["status"], "?")
        print(f"  {icon:<10} {c['name']}")
        print(f"             {c['detail']}")
    if result.get("notes"):
        print(f"\nNotes: {result['notes']}")
    print()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="TheraSIK Submission Preparation")
    sub = parser.add_subparsers(dest="cmd")

    p_prep = sub.add_parser("prepare", help="Full submission package")
    p_prep.add_argument("project_dir")
    p_prep.add_argument("--article-type", default=None)
    p_prep.add_argument("--corresponding", default="", help="Corresponding author name + email")

    p_check = sub.add_parser("check", help="Compliance check only")
    p_check.add_argument("project_dir")
    p_check.add_argument("--article-type", default=None)

    p_cover = sub.add_parser("cover", help="Cover letter only")
    p_cover.add_argument("project_dir")
    p_cover.add_argument("--corresponding", default="")

    args = parser.parse_args()

    if args.cmd == "prepare":
        result = prepare_submission(
            args.project_dir,
            article_type=args.article_type,
            corresponding_author=args.corresponding,
        )
        _print_compliance(result)
        print(f"Submission package: {result['submission_dir']}")
        print(f"Cover letter:       {result['cover_letter']}")
        print(f"Checklist:          {result['checklist']}")
        if result.get("files_copied"):
            print(f"Files copied:       {len(result['files_copied'])}")

    elif args.cmd == "check":
        result = check_compliance(args.project_dir, article_type=args.article_type)
        _print_compliance(result)

    elif args.cmd == "cover":
        text = generate_cover_letter(args.project_dir, corresponding_author=args.corresponding)
        print(text)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
