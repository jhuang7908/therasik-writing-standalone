#!/usr/bin/env python3
"""
fetch_pmc_legends.py
--------------------
Fetches real figure legends from PMC via NCBI E-utilities (full-text XML API).
Updates benchmark_assets.json with:
  - figure.caption_full  : the complete figure caption as printed in the paper
  - figure.panels        : panel-level descriptions parsed from the caption
  - figure.legend_source : "pmc_xml" | "manual" (traceability)

Run from the services/writing_memory directory:
    python scripts/fetch_pmc_legends.py

Requires: requests (pip install requests)
No authentication needed for PMC OA articles.
"""

import json
import re
import sys
import time
from pathlib import Path
import xml.etree.ElementTree as ET

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

ASSETS_PATH = Path(__file__).parent.parent / "benchmark_assets.json"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
DELAY = 0.5  # seconds between requests (NCBI rate limit: 3/sec without API key)


def fetch_pmc_xml(pmcid: str) -> str | None:
    """Fetch full-text XML for a PMC article."""
    numeric_id = pmcid.replace("PMC", "")
    params = {
        "db": "pmc",
        "id": numeric_id,
        "rettype": "xml",
        "retmode": "xml",
    }
    try:
        resp = requests.get(EFETCH_URL, params=params, timeout=30,
                            headers={"User-Agent": "InSynBio/1.0 (mailto:research@insynbio.com)"})
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"  ERROR fetching {pmcid}: {e}")
        return None


def _strip_markup(elem) -> str:
    """Extract text content from an XML element, ignoring all tags."""
    parts = []
    if elem.text:
        parts.append(elem.text.strip())
    for child in elem:
        parts.append(_strip_markup(child))
        if child.tail:
            parts.append(child.tail.strip())
    return " ".join(p for p in parts if p)


def parse_figures_from_xml(xml_text: str) -> dict[str, dict]:
    """
    Parse <fig> elements from PMC XML.
    Returns dict keyed by fig id or label, value = {caption_full, label}.
    """
    figures = {}
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"  XML parse error: {e}")
        return figures

    # PMC XML namespaces vary; search broadly
    for fig in root.iter("fig"):
        fig_id = fig.get("id", "")
        # Find label (e.g. "Figure 1", "Fig. 2")
        label_el = fig.find("label")
        label = _strip_markup(label_el) if label_el is not None else fig_id

        # Find caption
        caption_el = fig.find("caption")
        if caption_el is None:
            # Try nested
            caption_el = fig.find(".//caption")

        caption_full = ""
        if caption_el is not None:
            # Get full text including all child elements (p, title, bold, etc.)
            caption_full = _strip_markup(caption_el)
            # Also try title element inside caption
            title_el = caption_el.find("title")
            if title_el is not None:
                title_text = _strip_markup(title_el)
                # Ensure title is at front
                if title_text and not caption_full.startswith(title_text):
                    caption_full = title_text + " " + caption_full

        # Clean up whitespace
        caption_full = re.sub(r"\s+", " ", caption_full).strip()

        # Normalize label to "Figure N" style
        norm_label = re.sub(r"(?i)^fig\.?\s*", "Figure ", label).strip()
        if not norm_label.lower().startswith("figure"):
            norm_label = f"Figure {fig_id}"

        figures[norm_label] = {
            "fig_id": fig_id,
            "label": norm_label,
            "caption_full": caption_full,
        }
        # Also index by fig_id for fallback matching
        figures[fig_id] = figures[norm_label]

    return figures


def parse_panels_from_caption(caption: str) -> list[dict]:
    """
    Attempt to split a multi-panel caption into individual panel entries.
    Looks for patterns like "(A) ...", "(B) ...", "A. ...", "a) ..."
    """
    if not caption:
        return []

    # Common panel delimiters
    patterns = [
        r"\(([A-F])\)\s+",        # (A) ...
        r"\b([A-F])\)\s+",        # A) ...
        r"\b([A-F])\.\s+",        # A. ...
        r"Panel\s+([A-F]):\s+",   # Panel A: ...
    ]

    for pat in patterns:
        parts = re.split(pat, caption)
        if len(parts) > 2:
            # Zip labels with text
            panels = []
            # parts = [prefix, label1, text1, label2, text2, ...]
            it = iter(parts[1:])
            for panel_id, text in zip(it, it):
                panels.append({
                    "id": panel_id.upper(),
                    "description": text.strip(),
                    "panel_type": _infer_panel_type(text),
                })
            return panels

    # No multi-panel structure — return single panel
    return [{"id": "A", "description": caption, "panel_type": _infer_panel_type(caption)}]


def _infer_panel_type(text: str) -> str:
    """Very rough panel type inference from caption text."""
    t = text.lower()
    if any(w in t for w in ["bar graph", "bar chart", "bar plot"]): return "bar_chart"
    if any(w in t for w in ["kaplan", "survival curve"]): return "line_plot"
    if any(w in t for w in ["scatter"]): return "scatter"
    if any(w in t for w in ["flow cytometry", "facs", "dot plot"]): return "flow_cytometry_dot_plot"
    if any(w in t for w in ["western blot", "immunoblot"]): return "western_blot"
    if any(w in t for w in ["immunofluorescence", "confocal", "microscopy"]): return "immunofluorescence"
    if any(w in t for w in ["schematic", "diagram", "workflow", "pipeline"]): return "schematic"
    if any(w in t for w in ["table"]): return "table"
    if any(w in t for w in ["forest plot", "meta-analysis"]): return "forest_plot"
    if any(w in t for w in ["heatmap", "heat map"]): return "heatmap"
    if any(w in t for w in ["spr", "biacore", "bli", "sensorgram"]): return "binding_assay"
    if any(w in t for w in ["box plot", "boxplot", "violin"]): return "box_plot"
    return "other"


def match_figure_entry(existing_label: str, pmc_figures: dict) -> dict | None:
    """Try to match an existing figure label to a PMC XML figure entry."""
    # Direct match
    if existing_label in pmc_figures:
        return pmc_figures[existing_label]
    # Try just "Figure N" number extraction
    m = re.search(r"(\d+)", existing_label)
    if m:
        num = m.group(1)
        for key, fig in pmc_figures.items():
            km = re.search(r"(\d+)", key)
            if km and km.group(1) == num:
                return fig
    return None


def process_article_type(atype: str, article_data: dict) -> dict:
    """Fetch PMC XML for one article type, update figure entries."""
    pmcid = article_data.get("pmcid", "")
    pmid = article_data.get("pmid", "")
    print(f"\n{'='*60}")
    print(f"  {atype.upper()} — {pmcid} ({article_data.get('ref','')})")
    print(f"  '{article_data.get('title','')[:70]}'")

    if not pmcid:
        print("  SKIP — no pmcid")
        return article_data

    xml_text = fetch_pmc_xml(pmcid)
    time.sleep(DELAY)

    if not xml_text:
        print("  SKIP — fetch failed")
        return article_data

    if "<fig " not in xml_text and "<fig>" not in xml_text:
        print("  NOTE — no <fig> elements found in XML (article may not be full OA XML)")
        # Check if we at least got article metadata
        if "<article" not in xml_text:
            print("  ERROR — response does not look like PMC XML")
            return article_data

    pmc_figures = parse_figures_from_xml(xml_text)
    print(f"  Found {len(pmc_figures)//2} figures in PMC XML")

    updated_figures = []
    for fig_entry in article_data.get("figures", []):
        label = fig_entry.get("label", "")
        matched = match_figure_entry(label, pmc_figures)
        if matched and matched.get("caption_full"):
            caption_full = matched["caption_full"]
            print(f"  ✓ {label}: {len(caption_full)} chars — '{caption_full[:80]}…'")
            # Parse panels from the real caption
            panels_from_caption = parse_panels_from_caption(caption_full)
            # Merge: prefer parsed panels, fall back to existing
            updated_panels = panels_from_caption if len(panels_from_caption) > 1 else fig_entry.get("panels", panels_from_caption)
            fig_entry = {
                **fig_entry,
                "caption": caption_full[:120] + "…" if len(caption_full) > 120 else caption_full,
                "caption_full": caption_full,
                "panels": updated_panels,
                "legend_source": "pmc_xml",
            }
        else:
            print(f"  ~ {label}: no match in PMC XML, keeping existing description")
            if "legend_source" not in fig_entry:
                fig_entry["legend_source"] = "manual"
        updated_figures.append(fig_entry)

    article_data["figures"] = updated_figures
    return article_data


def main():
    if not ASSETS_PATH.exists():
        print(f"ERROR: {ASSETS_PATH} not found")
        sys.exit(1)

    with open(ASSETS_PATH, encoding="utf-8") as f:
        assets = json.load(f)

    article_types = [k for k in assets if not k.startswith("_")]
    print(f"Processing {len(article_types)} article types: {article_types}")

    updated = dict(assets)
    for atype in article_types:
        updated[atype] = process_article_type(atype, dict(assets[atype]))

    # Write back
    backup = ASSETS_PATH.with_suffix(".bak.json")
    ASSETS_PATH.rename(backup)
    with open(ASSETS_PATH, "w", encoding="utf-8") as f:
        json.dump(updated, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Updated {ASSETS_PATH}")
    print(f"  Backup saved to {backup}")


if __name__ == "__main__":
    main()
