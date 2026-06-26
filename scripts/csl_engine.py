"""
csl_engine.py
=============
TheraSIK CSL (Citation Style Language) rendering engine.

Renders reference lists in any of the 10,000+ journal styles from the official
CSL repository, using citeproc-py. Falls back gracefully if citeproc-py is not
installed or a requested style cannot be resolved.

Resolution order for a style identifier (e.g. "nature", "vancouver",
"frontiers-in-immunology"):
  1. assets/csl_styles/<id>.csl                  (locally cached, offline)
  2. citeproc-py bundled styles (harvard1, etc.)
  3. download from the CSL GitHub repo into assets/csl_styles/<id>.csl
     (independent + dependent styles, master branch)

Public API:
  render_bibliography(csl_items, style)  -> {"entries": [...], "engine": "csl"} | None
  ensure_style(style)                    -> Path | None   (resolve/download .csl)
  available_local_styles()               -> list[str]

CSL-JSON item format (same as Zotero export / export_references format="zotero"):
  {"id": "...", "type": "article-journal", "title": "...",
   "author": [{"family": "Smith", "given": "John A"}],
   "container-title": "...", "issued": {"date-parts": [[2020]]},
   "volume": "12", "issue": "3", "page": "45-50", "DOI": "..."}
"""

from __future__ import annotations

import os
import re
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

SKILL_DIR  = Path(os.environ.get("THERASIK_DIR", Path(__file__).resolve().parents[1]))
CSL_DIR    = SKILL_DIR / "assets" / "csl_styles"
CSL_REPO_RAW = "https://raw.githubusercontent.com/citation-style-language/styles/master"

# Map our friendly legacy names → canonical CSL style ids in the repo
STYLE_ALIASES = {
    # No plain "vancouver.csl" exists in the CSL repo; vancouver-nlm is the
    # canonical NLM/ICMJE numbered ("Vancouver") style.
    "vancouver":  "vancouver-nlm",
    "vancouver-nlm": "vancouver-nlm",
    "icmje":      "vancouver-nlm",
    "apa":        "apa",
    "harvard":    "harvard-cite-them-right",
    "ama":        "american-medical-association",
    "nature":     "nature",
    "mla":        "modern-language-association",
    "ieee":       "ieee",
    "chicago":    "chicago-author-date",
    "cell":       "cell",
    "science":    "science",
    "nejm":       "the-new-england-journal-of-medicine",
    "lancet":     "the-lancet",
    "plos":       "plos",
    "plos-one":   "plos-one",
}

try:
    import citeproc  # noqa: F401
    from citeproc import (CitationStylesStyle, CitationStylesBibliography,
                          Citation, CitationItem, formatter)
    from citeproc.source.json import CiteProcJSON
    _CITEPROC = True
except Exception:
    _CITEPROC = False


def is_available() -> bool:
    """True if citeproc-py is importable."""
    return _CITEPROC


def available_local_styles() -> list[str]:
    """List .csl style ids already cached locally."""
    if not CSL_DIR.exists():
        return []
    return sorted(p.stem for p in CSL_DIR.glob("*.csl"))


def _canonical_id(style: str) -> str:
    s = style.lower().strip()
    return STYLE_ALIASES.get(s, s)


def _download_style(style_id: str) -> Path | None:
    """
    Download a .csl file from the CSL GitHub repo into the local cache.
    Tries the dependent path first (journal-specific styles, 7,996 of them),
    then the independent root path. Each path is retried once.
    """
    CSL_DIR.mkdir(parents=True, exist_ok=True)
    dest = CSL_DIR / f"{style_id}.csl"

    # dependent/ first: most journal styles live there; root holds the
    # ~2,854 independent styles (vancouver, apa, nature, ...).
    for sub in ("dependent/", ""):
        url = f"{CSL_REPO_RAW}/{sub}{style_id}.csl"
        for _attempt in range(2):
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": "therasik-csl/1.0"})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = resp.read()
                    if data and b"<style" in data[:4000]:
                        dest.write_bytes(data)
                        return dest
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    break  # not at this path; try next sub
            except Exception:
                continue   # transient: retry
    return None


_PARENT_RE = re.compile(
    r'<link\s+href="[^"]*?/styles/([^"]+)"\s+rel="independent-parent"',
    re.IGNORECASE,
)


def _parent_style_id(csl_path: Path) -> str | None:
    """
    If a .csl file is a dependent style, return its independent-parent id.
    Dependent styles (journal-specific) only point to a parent and contain no
    formatting rules, so citeproc-py cannot render them directly.
    """
    try:
        head = csl_path.read_text(encoding="utf-8", errors="ignore")[:4000]
    except Exception:
        return None
    m = _PARENT_RE.search(head)
    if m:
        return m.group(1).strip()
    return None


def ensure_style(style: str, allow_download: bool = True) -> Path | str | None:
    """
    Resolve a style identifier to a usable CSL source.

    Returns:
      - Path to a local .csl file, OR
      - a bundled style name string (e.g. "harvard1") citeproc-py recognises, OR
      - None if unresolvable.
    """
    if not _CITEPROC:
        return None

    style_id = _canonical_id(style)

    # 1. Local cache
    local = CSL_DIR / f"{style_id}.csl"
    if local.exists():
        return local

    # 2. Bundled style (citeproc-py ships harvard1; accept exact bundled names)
    if style_id in ("harvard1",):
        return style_id

    # 3. Download from CSL repo
    if allow_download:
        got = _download_style(style_id)
        if got:
            return got

    # 4. Last resort: bundled harvard1 if caller asked for a harvard variant
    if "harvard" in style_id:
        return "harvard1"

    return None


def _author_list(item: dict) -> list[dict]:
    authors = item.get("author") or []
    out = []
    for a in authors:
        if isinstance(a, dict):
            out.append(a)
        else:
            name = str(a)
            if "," in name:
                fam, giv = name.split(",", 1)
                out.append({"family": fam.strip(), "given": giv.strip()})
            else:
                out.append({"literal": name})
    return out


def render_bibliography(csl_items: list[dict], style: str,
                        allow_download: bool = True) -> dict | None:
    """
    Render a reference list using a CSL style.

    Args:
        csl_items:      List of CSL-JSON items (each must have an "id").
        style:          Style identifier (friendly name or canonical CSL id).
        allow_download: Allow fetching the .csl from the CSL repo if not cached.

    Returns:
        {"entries": [str, ...], "engine": "csl", "style_id": "...",
         "style_source": "<path|bundled>"} on success,
        or None if citeproc-py unavailable / style unresolvable / render fails
        (caller should fall back to its own formatter).
    """
    if not _CITEPROC:
        return None

    src = ensure_style(style, allow_download=allow_download)
    if src is None:
        return None

    # Resolve dependent (journal-specific) styles to their independent parent,
    # which holds the actual formatting rules citeproc-py needs.
    resolved_via_parent = None
    if isinstance(src, Path):
        parent_id = _parent_style_id(src)
        if parent_id:
            parent_src = ensure_style(parent_id, allow_download=allow_download)
            if parent_src is not None:
                resolved_via_parent = parent_id
                src = parent_src

    # Normalise items: ensure id + author dicts
    items = []
    for i, it in enumerate(csl_items):
        it = dict(it)
        it.setdefault("id", str(it.get("DOI") or it.get("PMID") or f"ITEM-{i+1}"))
        if it.get("author"):
            it["author"] = _author_list(it)
        items.append(it)

    try:
        bib_source = CiteProcJSON(items)
        style_obj  = CitationStylesStyle(str(src), validate=False)
        bib        = CitationStylesBibliography(style_obj, bib_source,
                                                formatter.plain)
        for it in items:
            bib.register(Citation([CitationItem(it["id"])]))

        entries = []
        for row in bib.bibliography():
            text = "".join(str(x) for x in row)
            text = re.sub(r"\s+", " ", text).strip()
            entries.append(text)

        if not entries:
            return None

        return {
            "entries":          entries,
            "engine":           "csl",
            "style_id":         _canonical_id(style),
            "style_source":     str(src),
            "resolved_parent":  resolved_via_parent,
        }
    except Exception:
        return None
