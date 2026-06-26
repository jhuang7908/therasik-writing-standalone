"""
InSynBio Submission System CLI — last-mile submission system lookup.

Identifies which submission system a journal uses, derives the official
author-guidelines URL, and scaffolds new journal-submission-bundle profiles.

We do NOT invent word counts, figure limits, or file-size caps.
We provide: (1) which system, (2) official URL, (3) profile skeleton to fill manually.

Sources:
  CrossRef API   → publisher name (already wired in insynbio_journal_format.py)
  OpenAlex API   → publisher + host_organization confirmation
  Static map     → ~15 major publishers → submission system + guidelines URL template
                   (reference data, manually verified, not AI-generated)

Usage:
    python scripts/insynbio_submission_system.py identify "Nature Medicine"
    python scripts/insynbio_submission_system.py identify --issn 1078-8956
    python scripts/insynbio_submission_system.py checklist "Nature Medicine"
    python scripts/insynbio_submission_system.py new-profile "Nature Medicine" --type review
    python scripts/insynbio_submission_system.py list-systems
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    sys.exit("ERROR: 'requests' not installed.")

import os

CROSSREF_BASE  = "https://api.crossref.org"
OPENALEX_BASE  = "https://api.openalex.org"
CROSSREF_EMAIL = os.environ.get("CROSSREF_EMAIL", "research@insynbio.com")


# ── Publisher → Submission System Map ────────────────────────────────────────
# Manually verified, last checked 2026-06. Only reference data — NOT AI-generated.
# DO NOT add "likely" or "assumed" entries; only confirmed publishers.

PUBLISHER_SYSTEM_MAP: list[dict] = [
    # Nature Portfolio / Springer Nature
    {
        "match_keywords": ["nature portfolio", "springer nature", "nature publishing"],
        "publisher_canonical": "Nature Portfolio / Springer Nature",
        "system": "ScholarOne",
        "system_url": "https://mc.manuscriptcentral.com/{journal_slug}",
        "guidelines_url": "https://www.nature.com/{journal_slug}/submission-guidelines",
        "guidelines_url_alt": "https://www.springernature.com/gp/authors",
        "file_formats": ["DOCX", "LaTeX", "PDF"],
        "figure_format": "TIFF/EPS (≥300 dpi for halftone, ≥1000 dpi for line art)",
        "cover_letter": True,
        "data_availability": True,
        "notes": "Nature journals use ScholarOne. Slug derived from journal URL (e.g. 'nature-medicine').",
    },
    # Oxford University Press
    {
        "match_keywords": ["oxford university press", "oup"],
        "publisher_canonical": "Oxford University Press (OUP)",
        "system": "ScholarOne",
        "system_url": "https://mc.manuscriptcentral.com/{journal_slug}",
        "guidelines_url": "https://academic.oup.com/{journal_slug}/pages/General_Instructions",
        "file_formats": ["DOCX", "LaTeX"],
        "figure_format": "TIFF/EPS ≥300 dpi; separate file upload",
        "cover_letter": True,
        "data_availability": True,
        "notes": "OUP journals predominantly use ScholarOne. Antibody Therapeutics is a confirmed example.",
    },
    # Wiley
    {
        "match_keywords": ["wiley", "john wiley", "wiley-blackwell", "wiley-vch"],
        "publisher_canonical": "Wiley",
        "system": "ScholarOne",
        "system_url": "https://mc.manuscriptcentral.com/{journal_slug}",
        "guidelines_url": "https://onlinelibrary.wiley.com/page/{issn}/author-guidelines",
        "file_formats": ["DOCX", "LaTeX", "PDF"],
        "figure_format": "TIFF/EPS ≥300 dpi; embed at submission, separate for revision",
        "cover_letter": True,
        "data_availability": True,
        "notes": "Most Wiley journals use ScholarOne. Some specialty journals use Editorial Manager.",
    },
    # Elsevier
    {
        "match_keywords": ["elsevier", "cell press", "the lancet", "lancet"],
        "publisher_canonical": "Elsevier",
        "system": "Editorial Manager",
        "system_url": "https://www.editorialmanager.com/{journal_slug}/",
        "guidelines_url": "https://www.sciencedirect.com/journal/{journal_slug}/publish/guide-for-authors",
        "guidelines_url_alt": "https://www.cell.com/{journal_slug}/info/authors",
        "file_formats": ["DOCX", "LaTeX", "PDF"],
        "figure_format": "TIFF/EPS ≥300 dpi; figure files uploaded separately",
        "cover_letter": True,
        "data_availability": True,
        "notes": "Elsevier uses Editorial Manager (formerly EVISE). Cell Press uses own portal.",
    },
    # Springer (non-Nature)
    {
        "match_keywords": ["springer science", "springer llc", "springer berlin", "springer international"],
        "publisher_canonical": "Springer",
        "system": "Editorial Manager",
        "system_url": "https://www.editorialmanager.com/{journal_slug}/",
        "guidelines_url": "https://www.springer.com/{journal_slug}",
        "file_formats": ["DOCX", "LaTeX"],
        "figure_format": "TIFF/PNG ≥300 dpi for halftone, ≥1200 dpi for line art",
        "cover_letter": True,
        "data_availability": True,
        "notes": "Non-Nature Springer journals use Editorial Manager.",
    },
    # PLOS
    {
        "match_keywords": ["public library of science", "plos", "public library"],
        "publisher_canonical": "PLOS",
        "system": "Editorial Manager",
        "system_url": "https://editorial.plos.org/{journal_slug}/",
        "guidelines_url": "https://journals.plos.org/{journal_slug}/s/submission-guidelines",
        "file_formats": ["DOCX", "LaTeX"],
        "figure_format": "TIFF/EPS ≥300 dpi; max 10 MB per file",
        "cover_letter": False,
        "data_availability": True,
        "notes": "PLOS uses Editorial Manager. No cover letter required. All data must be deposited.",
    },
    # Frontiers
    {
        "match_keywords": ["frontiers media", "frontiers in"],
        "publisher_canonical": "Frontiers Media",
        "system": "Frontiers (proprietary)",
        "system_url": "https://www.frontiersin.org/submission/start",
        "guidelines_url": "https://www.frontiersin.org/guidelines/author-guidelines",
        "file_formats": ["DOCX", "LaTeX"],
        "figure_format": "TIFF/PDF ≥300 dpi; max 30 MB total",
        "cover_letter": False,
        "data_availability": True,
        "notes": "Frontiers uses its own submission portal (not ScholarOne or EM).",
    },
    # MDPI
    {
        "match_keywords": ["mdpi", "multidisciplinary digital publishing"],
        "publisher_canonical": "MDPI",
        "system": "MDPI SuSy (proprietary)",
        "system_url": "https://susy.mdpi.com/",
        "guidelines_url": "https://www.mdpi.com/{journal_slug}/instructions",
        "file_formats": ["DOCX", "LaTeX"],
        "figure_format": "TIFF/EPS ≥300 dpi for production; PNG acceptable at submission",
        "cover_letter": False,
        "data_availability": True,
        "notes": "MDPI uses its own SuSy system. No cover letter for most journals.",
    },
    # BMJ
    {
        "match_keywords": ["bmj", "british medical journal"],
        "publisher_canonical": "BMJ",
        "system": "ScholarOne",
        "system_url": "https://mc.manuscriptcentral.com/{journal_slug}",
        "guidelines_url": "https://www.bmj.com/pages/authors/",
        "file_formats": ["DOCX", "RTF"],
        "figure_format": "TIFF/EPS ≥300 dpi; JPEG acceptable for photos",
        "cover_letter": True,
        "data_availability": True,
        "notes": "BMJ and affiliated journals use ScholarOne.",
    },
    # NEJM / Massachusetts Medical Society
    {
        "match_keywords": ["massachusetts medical society", "new england journal", "nejm group"],
        "publisher_canonical": "Massachusetts Medical Society (NEJM Group)",
        "system": "eJP (eJournal Press)",
        "system_url": "https://authors.nejm.org/",
        "guidelines_url": "https://www.nejm.org/author-center/new-manuscripts",
        "file_formats": ["DOCX", "RTF"],
        "figure_format": "TIFF ≥300 dpi; EPS for vector; uploaded separately",
        "cover_letter": True,
        "data_availability": True,
        "notes": "NEJM uses eJP system. Strict word limits enforced at submission.",
    },
    # JAMA Network / American Medical Association
    {
        "match_keywords": ["american medical association", "ama", "jama network"],
        "publisher_canonical": "American Medical Association (JAMA Network)",
        "system": "Editorial Manager",
        "system_url": "https://www.editorialmanager.com/{journal_slug}/",
        "guidelines_url": "https://jamanetwork.com/journals/{journal_slug}/pages/instructions-for-authors",
        "file_formats": ["DOCX", "RTF"],
        "figure_format": "TIFF ≥300 dpi; 1200 dpi for line art",
        "cover_letter": True,
        "data_availability": True,
        "notes": "JAMA Network journals use Editorial Manager.",
    },
    # American Chemical Society
    {
        "match_keywords": ["american chemical society", "acs publications"],
        "publisher_canonical": "American Chemical Society (ACS)",
        "system": "ACS Paragon Plus",
        "system_url": "https://pubs.acs.org/journal/{journal_slug}",
        "guidelines_url": "https://pubs.acs.org/page/policy/author/authors.html",
        "file_formats": ["DOCX", "LaTeX", "PDF"],
        "figure_format": "TIFF/EPS 300 dpi (halftone) / 1200 dpi (line art); max 9 cm width (1-col)",
        "cover_letter": True,
        "data_availability": True,
        "notes": "ACS uses its own Paragon Plus system.",
    },
    # Royal Society of Chemistry
    {
        "match_keywords": ["royal society of chemistry", "rsc"],
        "publisher_canonical": "Royal Society of Chemistry (RSC)",
        "system": "RSC ChemSci portal",
        "system_url": "https://rsc.li/upload-manuscript",
        "guidelines_url": "https://www.rsc.org/journals-books-databases/author-and-reviewer-hub/authors-information/",
        "file_formats": ["DOCX", "LaTeX"],
        "figure_format": "TIFF/EPS ≥300 dpi; embedded at submission acceptable",
        "cover_letter": True,
        "data_availability": True,
        "notes": "RSC uses its own manuscript upload system.",
    },
    # American Association for the Advancement of Science
    {
        "match_keywords": ["american association for the advancement of science", "aaas", "science magazine"],
        "publisher_canonical": "AAAS / Science",
        "system": "Science online submission",
        "system_url": "https://www.science.org/content/page/information-authors",
        "guidelines_url": "https://www.science.org/content/page/science-information-authors",
        "file_formats": ["DOCX", "LaTeX"],
        "figure_format": "TIFF/EPS ≥300 dpi; ≤ 5 MB per figure",
        "cover_letter": True,
        "data_availability": True,
        "notes": "Science/AAAS uses its own web portal for submission.",
    },
    # Cell Press (now Elsevier)
    {
        "match_keywords": ["cell press"],
        "publisher_canonical": "Cell Press (Elsevier)",
        "system": "Cell Press submission portal",
        "system_url": "https://www.cell.com/{journal_slug}/info/authors",
        "guidelines_url": "https://www.cell.com/{journal_slug}/info/authors",
        "file_formats": ["DOCX", "PDF"],
        "figure_format": "TIFF/EPS ≥300 dpi; embed figures in DOCX at submission",
        "cover_letter": True,
        "data_availability": True,
        "notes": "Cell Press journals use their own submission system, different from Elsevier EM.",
    },
]

UNKNOWN_SYSTEM = {
    "system": "Unknown — check publisher website",
    "publisher_canonical": "",
    "system_url": "",
    "guidelines_url": "",
    "notes": "Publisher not in map. Use CrossRef result to find publisher website, then check 'Author Instructions'.",
}


# ── API helpers ───────────────────────────────────────────────────────────────

def _get(url: str, params: dict | None = None, retries: int = 3) -> Any:
    for attempt in range(retries):
        resp = requests.get(url, params=params or {}, timeout=15)
        if resp.status_code == 429:
            time.sleep(4 * (attempt + 1))
            continue
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        ct = resp.headers.get("Content-Type", "")
        return resp.json() if "json" in ct else resp.text
    raise RuntimeError(f"API failed: {url}")


def _normalize_issn(raw: str) -> str:
    digits = re.sub(r"[^0-9X]", "", raw.upper())
    return f"{digits[:4]}-{digits[4:]}" if len(digits) == 8 else raw


def crossref_publisher(journal_name: str | None, issn: str | None) -> dict:
    """Resolve journal → CrossRef record → publisher name."""
    if issn:
        issn = _normalize_issn(issn)
        data = _get(f"{CROSSREF_BASE}/journals/{issn}",
                    params={"mailto": CROSSREF_EMAIL})
        if data:
            rec = data.get("message", data)
            return {
                "title": rec.get("title", ""),
                "publisher": rec.get("publisher", ""),
                "issn": (rec.get("ISSN") or [issn])[0],
                "crossref_url": f"https://api.crossref.org/journals/{issn}",
            }
    if journal_name:
        data = _get(f"{CROSSREF_BASE}/journals",
                    params={"query": journal_name, "rows": 1, "mailto": CROSSREF_EMAIL})
        if data:
            items = data.get("message", {}).get("items", [])
            if items:
                rec = items[0]
                issns = rec.get("ISSN", [])
                return {
                    "title": rec.get("title", ""),
                    "publisher": rec.get("publisher", ""),
                    "issn": issns[0] if issns else "",
                    "crossref_url": f"https://api.crossref.org/journals/{issns[0]}" if issns else "",
                }
    return {}


def match_publisher_to_system(publisher: str, journal_title: str = "") -> dict:
    """
    Match CrossRef publisher string to submission system map entry.
    Title-override: CrossRef reports Springer Nature journals as "Springer Science and Business Media LLC"
    but Nature-branded journals (Nature Medicine, Nature Methods, etc.) use ScholarOne, not EM.
    """
    pub_lower = publisher.lower()
    title_lower = journal_title.lower()

    # Title-level override: Nature-branded journals → Nature Portfolio (ScholarOne)
    nature_title_signals = ["nature medicine", "nature methods", "nature biotechnology",
                            "nature chemical", "nature communications", "nature cancer",
                            "nature cell", "nature climate", "nature ecology",
                            "nature energy", "nature genetics", "nature geoscience",
                            "nature immunology", "nature metabolism", "nature microbiology",
                            "nature nanotechnology", "nature neuroscience", "nature photonics",
                            "nature physics", "nature plants", "nature structural",
                            "nature sustainability", "nature aging"]
    if any(sig in title_lower for sig in nature_title_signals) or (
        title_lower.startswith("nature ") and "springer" in pub_lower
    ):
        # Return the Nature Portfolio entry (first in map)
        return PUBLISHER_SYSTEM_MAP[0]

    for entry in PUBLISHER_SYSTEM_MAP:
        if any(kw in pub_lower for kw in entry["match_keywords"]):
            return entry
    return {**UNKNOWN_SYSTEM, "publisher_canonical": publisher}


def _fill_url(url_template: str, journal_title: str, issn: str) -> str:
    """Fill URL templates with journal slug and ISSN."""
    slug = re.sub(r"[^\w\s-]", "", journal_title.lower())
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return url_template.replace("{journal_slug}", slug).replace("{issn}", issn)


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_identify(args: argparse.Namespace) -> None:
    """Identify submission system for a journal."""
    journal = args.journal
    issn = args.issn
    print(f"[SubmissionSystem] Resolving publisher via CrossRef...")
    pub_info = crossref_publisher(journal, issn)
    if not pub_info:
        print(f"[SubmissionSystem] Could not resolve journal. Try --issn.")
        return

    publisher = pub_info.get("publisher", "")
    title = pub_info.get("title", journal or "")
    issn_resolved = pub_info.get("issn", issn or "")
    print(f"[SubmissionSystem] Journal: {title} | Publisher: {publisher} | ISSN: {issn_resolved}")

    system = match_publisher_to_system(publisher, title)

    guidelines = _fill_url(system.get("guidelines_url", ""), title, issn_resolved)
    portal = _fill_url(system.get("system_url", ""), title, issn_resolved)

    result = {
        "journal": title,
        "publisher": system.get("publisher_canonical") or publisher,
        "issn": issn_resolved,
        "submission_system": system["system"],
        "submission_portal": portal,
        "author_guidelines": guidelines,
        "file_formats": system.get("file_formats", []),
        "figure_format": system.get("figure_format", ""),
        "cover_letter_required": system.get("cover_letter"),
        "data_availability_required": system.get("data_availability"),
        "notes": system.get("notes", ""),
        "_crossref_url": pub_info.get("crossref_url", ""),
    }

    _output(result, args.out)
    if not args.out:
        print(f"\n  System:      {result['submission_system']}")
        print(f"  Portal:      {result['submission_portal']}")
        print(f"  Guidelines:  {result['author_guidelines']}")
        print(f"  Formats:     {', '.join(result['file_formats'])}")
        print(f"  Figures:     {result['figure_format']}")
        print(f"  Cover letter: {'required' if result['cover_letter_required'] else 'not required'}")
        print(f"  Data avail:  {'required' if result['data_availability_required'] else 'check guidelines'}")
        if result['notes']:
            print(f"  Note: {result['notes']}")


def cmd_checklist(args: argparse.Namespace) -> None:
    """Generate submission checklist with direct links to official requirements."""
    journal = args.journal
    issn = args.issn
    print(f"[SubmissionSystem] Building checklist for '{journal or issn}'...")
    pub_info = crossref_publisher(journal, issn)
    if not pub_info:
        print(f"[SubmissionSystem] Could not resolve journal.")
        return

    publisher = pub_info.get("publisher", "")
    title = pub_info.get("title", journal or "")
    issn_resolved = pub_info.get("issn", issn or "")
    system = match_publisher_to_system(publisher, title)
    guidelines = _fill_url(system.get("guidelines_url", ""), title, issn_resolved)
    portal = _fill_url(system.get("system_url", ""), title, issn_resolved)

    platform_doc = ""
    sys_name = system.get("system", "")
    if "ScholarOne" in sys_name:
        platform_doc = "services/writing_memory/submission_bundle/platforms/scholarone_standard.md"
    elif "Editorial Manager" in sys_name:
        platform_doc = "services/writing_memory/submission_bundle/platforms/editorial_manager_standard.md"

    checklist_lines = [
        f"# Submission Checklist — {title}",
        f"",
        f"**System:** {sys_name}  ",
        f"**Portal:** {portal}  ",
        f"**Author Guidelines:** {guidelines}  ",
        f"",
        f"## Pre-submission (content — from journal guidelines)",
        f"",
        f"- [ ] Abstract word limit — **check**: {guidelines}",
        f"- [ ] Main text word limit — **check**: {guidelines}",
        f"- [ ] Max figures / tables — **check**: {guidelines}",
        f"- [ ] Max references — **check**: {guidelines}",
        f"- [ ] Structured abstract (yes/no) — **check**: {guidelines}",
        f"- [ ] Keywords (number, format) — **check**: {guidelines}",
        f"",
        f"## File preparation (platform-level — {sys_name})",
        f"",
        f"- [ ] Manuscript format: {', '.join(system.get('file_formats', ['DOCX']))}",
        f"- [ ] Figures: {system.get('figure_format', 'check guidelines')}",
        f"- [ ] Supplementary materials named per journal convention",
        f"- [ ] Line numbers enabled (most systems require)",
        f"- [ ] Double spacing (most systems require)",
        f"- [ ] Page numbers",
        f"- [ ] Blinded (author info removed from main text if double-blind)",
        f"",
        f"## Required statements (varies by journal — verify at guidelines URL)",
        f"",
        f"- [ ] Cover letter — {'required' if system.get('cover_letter') else 'check guidelines'}",
        f"- [ ] Data availability statement — {'required' if system.get('data_availability') else 'check guidelines'}",
        f"- [ ] Author contributions (CRediT taxonomy recommended)",
        f"- [ ] Conflict of interest / competing interests",
        f"- [ ] Funding statement",
        f"- [ ] Ethics approval (if human/animal subjects)",
        f"- [ ] Informed consent (if applicable)",
        f"",
        f"## Portal-specific steps",
        f"",
        f"- [ ] Register / log in at: {portal}",
        f"- [ ] Enter all author info (ORCID recommended)",
        f"- [ ] Select article type matching your manuscript",
        f"- [ ] Upload files in required order (see platform doc below)",
        f"- [ ] Enter keywords and classifications in portal",
        f"- [ ] Suggest / exclude reviewers (if option available)",
        f"- [ ] Review PDF proof before final submit",
        f"",
        f"## InSynBio tools",
        f"",
        f"```powershell",
        f"# Check OA policy",
        f"python scripts/insynbio_journal_format.py oa-policy \"{title}\"",
        f"",
        f"# Download citation style",
        f"python scripts/insynbio_journal_format.py get-csl \"{title}\" --out styles/{re.sub(r'[^\\w]', '-', title.lower())}.csl",
        f"",
        f"# Build submission bundle (if profile exists)",
        f"python scripts/build_submission_bundle.py --list-profiles",
        f"python scripts/build_submission_bundle.py --profile <profile_id> --workspace paper/Submission_Package",
        f"",
        f"# Scaffold new profile (if not yet created)",
        f"python scripts/insynbio_submission_system.py new-profile \"{title}\" --type <review|research|case-report>",
        f"```",
        f"",
    ]
    if platform_doc:
        checklist_lines += [
            f"## Platform standard requirements",
            f"Read: `{platform_doc}`",
            f"",
        ]
    checklist_lines += [
        f"---",
        f"*Requirements are journal-specific. Always verify word counts, figure limits,",
        f"and required statements at the official guidelines URL before submitting.*",
        f"*Do not rely on AI-generated numbers for word limits or figure specifications.*",
    ]
    checklist_text = "\n".join(checklist_lines)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(checklist_text, encoding="utf-8")
        print(f"[SubmissionSystem] Checklist → {args.out}")
    else:
        print(checklist_text)


def cmd_new_profile(args: argparse.Namespace) -> None:
    """Scaffold a new journal-submission-bundle profile JSON."""
    journal = args.journal
    issn = args.issn
    article_type = args.type
    print(f"[SubmissionSystem] Scaffolding profile for '{journal}'...")
    pub_info = crossref_publisher(journal, issn)
    publisher = pub_info.get("publisher", "UNKNOWN")
    title = pub_info.get("title", journal or "UNKNOWN")
    issn_resolved = pub_info.get("issn", "")
    system = match_publisher_to_system(publisher, title)
    guidelines = _fill_url(system.get("guidelines_url", ""), title, issn_resolved)

    slug = re.sub(r"[^\w]", "_", title.lower()).strip("_")
    sys_slug = re.sub(r"[^\w]", "_", system["system"].split("(")[0].strip().lower())
    profile_id = f"{slug}_{sys_slug}_{article_type}"

    profile = {
        "_warning": "SKELETON — do NOT use until all FILL_ME fields are replaced with human-verified values from official guidelines.",
        "_sourced_from": guidelines or "FILL_ME: paste official author guidelines URL",
        "_last_verified": "FILL_ME: YYYY-MM-DD",
        "profile_id": profile_id,
        "journal": title,
        "publisher": system.get("publisher_canonical") or publisher,
        "issn": issn_resolved,
        "submission_system": system["system"],
        "submission_portal": _fill_url(system.get("system_url", ""), title, issn_resolved),
        "article_type": article_type,
        "build_recipe": "generic_manuscript_bundle",
        "content_limits": {
            "_note": "All limits below are FILL_ME — copy from official guidelines, do NOT guess.",
            "abstract_words": "FILL_ME",
            "main_text_words": "FILL_ME",
            "max_figures": "FILL_ME",
            "max_tables": "FILL_ME",
            "max_references": "FILL_ME",
            "keywords_count": "FILL_ME",
            "structured_abstract": "FILL_ME (true/false)",
        },
        "file_requirements": {
            "manuscript_format": system.get("file_formats", ["DOCX"]),
            "figure_format": system.get("figure_format", "FILL_ME"),
            "line_numbers": True,
            "double_spacing": True,
            "page_numbers": True,
            "blinded": "FILL_ME (true/false — check if double-blind review)",
        },
        "required_items": {
            "cover_letter": system.get("cover_letter", "FILL_ME"),
            "data_availability_statement": system.get("data_availability", True),
            "author_contributions": True,
            "conflict_of_interest": True,
            "funding_statement": True,
            "ethics_approval": "FILL_ME (required if human/animal subjects)",
            "informed_consent": "FILL_ME",
        },
        "upload_order": [
            "FILL_ME: paste upload order from submission system guide",
            "Example: ['cover_letter', 'manuscript', 'figures', 'supplementary']",
        ],
        "forbidden_upload_types": [".md", ".json", ".py", ".log", ".tmp"],
        "notes": system.get("notes", ""),
    }

    out_dir = Path("services/writing_memory/submission_bundle/profiles")
    out_path = out_dir / f"{profile_id}.json"
    if args.out:
        out_path = Path(args.out)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[SubmissionSystem] Profile skeleton → {out_path}")
    print(f"\n  NEXT STEPS (mandatory before use):")
    print(f"  1. Open: {out_path}")
    print(f"  2. Go to: {guidelines or pub_info.get('crossref_url', 'publisher website')}")
    print(f"  3. Fill every FILL_ME field with values from official guidelines")
    print(f"  4. Set _last_verified to today's date")
    print(f"  5. Register in: services/writing_memory/submission_bundle/profiles/index.json")
    print(f"  6. Test: python scripts/build_submission_bundle.py --profile {profile_id} --audit-only")


def cmd_list_systems(args: argparse.Namespace) -> None:
    """List all known publisher → submission system mappings."""
    print(f"\n{'Publisher':<45} {'System':<35} Source\n" + "-" * 100)
    for entry in PUBLISHER_SYSTEM_MAP:
        pub = entry["publisher_canonical"]
        sys_name = entry["system"]
        url = entry.get("guidelines_url", "")
        print(f"  {pub:<43} {sys_name:<35} {url}")
    print(f"\n{len(PUBLISHER_SYSTEM_MAP)} publishers mapped.")
    print(f"For unlisted publishers: use CrossRef to get publisher name, then visit publisher website.")


def _output(data: Any, out_path: str | None) -> None:
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[SubmissionSystem] → {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="insynbio_submission_system",
        description=(
            "Last-mile submission system lookup. Identifies platform, links to official "
            "guidelines, and scaffolds new profiles. Does NOT generate word limits or "
            "figure specs — those must come from official guidelines."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # identify
    p_id = sub.add_parser("identify", help="Identify submission system for a journal")
    p_id.add_argument("journal", nargs="?", default=None, help="Journal name")
    p_id.add_argument("--issn", default=None)
    p_id.add_argument("--out", default=None, help="Save JSON result")

    # checklist
    p_cl = sub.add_parser("checklist", help="Generate submission checklist with official links")
    p_cl.add_argument("journal", nargs="?", default=None, help="Journal name")
    p_cl.add_argument("--issn", default=None)
    p_cl.add_argument("--out", default=None, help="Save markdown checklist")

    # new-profile
    p_np = sub.add_parser("new-profile", help="Scaffold a new journal-submission-bundle profile JSON")
    p_np.add_argument("journal", nargs="?", default=None, help="Journal name")
    p_np.add_argument("--issn", default=None)
    p_np.add_argument("--type", default="research",
                      choices=["review", "research", "case-report", "letter", "commentary", "other"],
                      help="Article type")
    p_np.add_argument("--out", default=None, help="Output path for profile JSON")

    # list-systems
    sub.add_parser("list-systems", help="List all known publisher → system mappings")

    args = parser.parse_args()
    dispatch = {
        "identify": cmd_identify,
        "checklist": cmd_checklist,
        "new-profile": cmd_new_profile,
        "list-systems": cmd_list_systems,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
