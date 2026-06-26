"""
Job 2 — Scrape submission platform documentation (7 systems, full refresh each run).

Output: assets/journal_requirements/_platform_docs.json

Platforms covered:
  1. ScholarOne        (mc.manuscriptcentral.com)
  2. Editorial Manager (editorialmanager.com)
  3. NPG / Snapp       (mts-nature.nature.com / nature.com)
  4. Frontiers         (frontiersin.org)
  5. ACS Paragon Plus  (acsparagonplus.acs.org)
  6. AAAS Submit       (submit.science.org)
  7. MDPI Submission   (susy.mdpi.com / mdpi.com)

Usage:
    python scripts/journal_db/scrape_platform_docs.py
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    PLAYWRIGHT_OK = True
except ImportError:
    PLAYWRIGHT_OK = False

OUT_PATH = Path("assets/journal_requirements/_platform_docs.json")
NAV_TIMEOUT = 25_000  # ms


# ── Platform definitions ────────────────────────────────────────────────────────
# Each entry: system name → list of (label, URL) pairs to scrape

PLATFORMS = {
    "ScholarOne": {
        "url": "https://clarivate.com/products/scientific-and-academic-research/research-publishing-solutions/scholarone/",
        "help_pages": [
            ("Author Guidelines", "https://clarivate.com/products/scientific-and-academic-research/research-publishing-solutions/scholarone/"),
            ("File Types", "https://support.clarivate.com/ScholarOne/s/article/ScholarOne-Manuscripts-Accepted-File-Types"),
        ],
        "static_info": {
            "max_file_size_mb": 400,
            "accepted_formats": ["DOCX", "DOC", "PDF", "LaTeX", "RTF", "ODT"],
            "figure_formats": ["TIFF", "EPS", "PDF", "JPEG", "PNG", "BMP", "GIF"],
            "figure_resolution_dpi": 300,
            "cover_letter": True,
            "blinded_review_support": True,
            "supplementary_files": True,
            "notes": "Widely used by Wiley, OUP, Taylor&Francis, Cambridge, SAGE, AHA, ADA, ASH, ASCO, APS"
        }
    },

    "Editorial Manager": {
        "url": "https://www.editorialmanager.com/",
        "help_pages": [
            ("EM Help Center", "https://support.aries-systems.com/hc/en-us"),
        ],
        "static_info": {
            "max_file_size_mb": 500,
            "accepted_formats": ["DOCX", "DOC", "PDF", "LaTeX", "RTF", "TEX"],
            "figure_formats": ["TIFF", "EPS", "PDF", "JPEG", "PNG"],
            "figure_resolution_dpi": 300,
            "cover_letter": True,
            "blinded_review_support": True,
            "supplementary_files": True,
            "notes": "Used by Springer Nature, Elsevier, BMC, PLOS, Karger, Lippincott/WK, Cell Press, Thieme, EMBO"
        }
    },

    "NPG / Snapp": {
        "url": "https://www.nature.com/authors/",
        "help_pages": [
            ("Nature Author Guidelines", "https://www.nature.com/authors/"),
            ("Nature Manuscript Format", "https://www.nature.com/nature/for-authors/formatting-guide"),
            ("Nature Portfolio Policies", "https://www.nature.com/nature-portfolio/editorial-policies"),
        ],
        "static_info": {
            "max_file_size_mb": 30,
            "accepted_formats": ["DOCX", "DOC", "PDF", "LaTeX"],
            "figure_formats": ["PDF", "EPS", "TIFF", "JPEG"],
            "figure_resolution_dpi": 300,
            "cover_letter": True,
            "blinded_review_support": False,
            "supplementary_files": True,
            "notes": "Covers all 45+ Nature-branded journals. Snapp is the internal name for Nature's submission portal."
        }
    },

    "Frontiers": {
        "url": "https://www.frontiersin.org/guidelines/author-guidelines",
        "help_pages": [
            ("Frontiers Author Guidelines", "https://www.frontiersin.org/guidelines/author-guidelines"),
            ("Frontiers Article Types", "https://www.frontiersin.org/about/article-types"),
            ("Frontiers Figure Preparation", "https://www.frontiersin.org/guidelines/author-guidelines#figures-tables-and-data-presentation"),
        ],
        "static_info": {
            "max_file_size_mb": 25,
            "accepted_formats": ["DOCX", "DOC", "LaTeX"],
            "figure_formats": ["TIFF", "JPEG", "PNG", "EPS", "SVG"],
            "figure_resolution_dpi": 300,
            "cover_letter": False,
            "blinded_review_support": False,
            "supplementary_files": True,
            "article_types_global": [
                "Original Research", "Review", "Mini Review", "Systematic Review",
                "Meta-Analysis", "Methods", "Hypothesis and Theory",
                "Brief Research Report", "Perspective", "Opinion", "Editorial",
                "General Commentary", "Technology and Code", "Data Report",
                "Clinical Trial", "Case Report", "Correction", "Erratum"
            ],
            "notes": "Open-access publisher. All articles peer-reviewed interactively. No cover letter required."
        }
    },

    "ACS Paragon Plus": {
        "url": "https://publish.acs.org/publish/author_guidelines",
        "help_pages": [
            ("ACS Author Guidelines", "https://publish.acs.org/publish/author_guidelines"),
            ("ACS Figure Guidelines", "https://publish.acs.org/publish/author_guidelines?coden=jacsat#graphics"),
        ],
        "static_info": {
            "max_file_size_mb": 100,
            "accepted_formats": ["DOCX", "DOC", "PDF", "LaTeX", "ACS Word Template"],
            "figure_formats": ["TIFF", "EPS", "CDX", "PICT", "PDF"],
            "figure_resolution_dpi": 600,
            "cover_letter": True,
            "blinded_review_support": True,
            "supplementary_files": True,
            "notes": "American Chemical Society platform. High-resolution figures required (600 dpi). LaTeX strongly preferred."
        }
    },

    "AAAS Submit": {
        "url": "https://www.science.org/content/page/authors",
        "help_pages": [
            ("Science Author Guidelines", "https://www.science.org/content/page/authors"),
            ("Science Submission Portal", "https://submit.science.org/"),
        ],
        "static_info": {
            "max_file_size_mb": 50,
            "accepted_formats": ["DOCX", "PDF", "LaTeX"],
            "figure_formats": ["TIFF", "EPS", "PDF"],
            "figure_resolution_dpi": 300,
            "cover_letter": True,
            "blinded_review_support": False,
            "supplementary_files": True,
            "article_types_global": [
                "Research Article", "Review", "Perspective", "Letter",
                "Technical Comment", "Policy Forum", "Books et al.",
                "Report (Science Translational Medicine)",
                "Research Article (Science Advances)",
                "Review (Science Advances)"
            ],
            "notes": "AAAS journals: Science, Sci Translational Medicine, Sci Advances, Sci Signaling, Sci Immunology, Sci Robotics"
        }
    },

    "MDPI Submission": {
        "url": "https://www.mdpi.com/authors",
        "help_pages": [
            ("MDPI Author Guidelines", "https://www.mdpi.com/authors"),
            ("MDPI Instructions for Authors", "https://www.mdpi.com/journal/molecules/instructions"),
        ],
        "static_info": {
            "max_file_size_mb": 120,
            "accepted_formats": ["DOCX", "LaTeX", "MDPI LaTeX Template"],
            "figure_formats": ["TIFF", "JPEG", "PNG", "PDF", "EPS"],
            "figure_resolution_dpi": 300,
            "cover_letter": False,
            "blinded_review_support": False,
            "supplementary_files": True,
            "article_types_global": [
                "Article", "Review", "Communication", "Letter",
                "Technical Note", "Essay", "Opinion", "Book Review",
                "Case Report", "Hypothesis", "Project Report", "Reply"
            ],
            "notes": "Open-access publisher. Fast turnaround. No cover letter required. LaTeX template available."
        }
    },
}


def scrape_page(page, label: str, url: str) -> str:
    """Scrape a help page and return extracted text (truncated)."""
    try:
        page.goto(url, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        text = page.inner_text("main, article, .content, body") or ""
        # Trim to 3000 chars to avoid bloat
        return text[:3000].strip()
    except (PWTimeout, Exception) as e:
        return f"[scrape error: {e}]"


def main():
    if not PLAYWRIGHT_OK:
        print("ERROR: playwright not installed.")
        sys.exit(1)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "platforms": {}
    }

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (compatible; InSynBio-JournalDB/2.0)",
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()

        for name, info in PLATFORMS.items():
            print(f"\n── {name} ──────────────────────────────────────────────")
            platform_data = {
                "portal_url": info["url"],
                "static_info": info["static_info"],
                "scraped_pages": {}
            }

            for label, url in info.get("help_pages", []):
                print(f"  Scraping: {label} → {url[:70]}", flush=True)
                text = scrape_page(page, label, url)
                platform_data["scraped_pages"][label] = {
                    "url": url,
                    "text_preview": text[:1500],
                }
                time.sleep(1.0)

            result["platforms"][name] = platform_data
            print(f"  ✓ Done")

        page.close()
        ctx.close()
        browser.close()

    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ Platform docs saved → {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
