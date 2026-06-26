#!/usr/bin/env python3
"""
Download benchmark figures from PMC Open Access papers.

Usage (run on VPS from writing_memory directory):
    python scripts/download_benchmark_figures.py

Figures are saved to: static/benchmark_figures/{article_type}/figN.jpg
On success each entry in benchmark_assets.json gets local_filename set.
"""

import json
import time
import sys
from pathlib import Path

import requests

ASSETS_FILE = Path(__file__).resolve().parent.parent / "benchmark_assets.json"
OUT_ROOT    = Path(__file__).resolve().parent.parent / "static" / "benchmark_figures"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; BenchmarkFigureDownloader/1.0; "
        "+https://insynbio.com)"
    )
}

# ---------------------------------------------------------------------------
# PMC Open-Access figure URL templates.
# For Frontiers papers the CDN URL works reliably.
# For PMC-hosted papers we use the PMC OA media endpoint.
# ---------------------------------------------------------------------------
def pmc_oa_figure_url(pmcid: str, graphic_id: str) -> list[str]:
    """Return candidate download URLs for a PMC figure (tries several patterns)."""
    # Pattern 1: PMC figure page (image embedded in HTML)
    # Pattern 2: PMC image file path (known suffix patterns)
    numeric = pmcid.replace("PMC", "")
    return [
        f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/bin/{graphic_id}.jpg",
        f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/bin/{graphic_id}.png",
        f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/bin/{graphic_id}.gif",
    ]


def frontiers_figure_url(pmcid: str, pmid: str, fig_n: int) -> list[str]:
    """Construct Frontiers CDN figure URLs."""
    return [
        f"https://www.frontiersin.org/files/Articles/{pmcid}/fimmu-{pmid}-g00{fig_n}.jpg",
        f"https://www.frontiersin.org/files/Articles/{pmcid}/fimmu-{pmid}-g0{fig_n:02d}.jpg",
        # Generic PMC fallback
        f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/bin/fimmu-{pmid}-g00{fig_n}.jpg",
    ]


def download_figure(urls: list[str], dest: Path) -> bool:
    """Try each URL in order; return True if download succeeded."""
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=30, stream=True)
            if r.status_code == 200 and len(r.content) > 1000:
                dest.write_bytes(r.content)
                print(f"  ✓  {dest.name}  ← {url}")
                return True
        except Exception as exc:
            print(f"  ✗  {url}  → {exc}")
        time.sleep(0.5)
    print(f"  ✗  All URLs failed for {dest.name}")
    return False


# ---------------------------------------------------------------------------
# Per-paper figure URL strategies
# ---------------------------------------------------------------------------
PAPER_STRATEGIES = {
    "research": {
        # CUMAb — Nat Biomed Eng / PMC, not Frontiers
        "pmcid": "PMC10842793",
        "pmid":  "37550425",
        "fig_urls": {
            "fig1": [
                "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10842793/bin/41551_2023_1079_Fig1_HTML.jpg",
                "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10842793/bin/fig1.jpg",
            ],
            "fig2": [
                "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10842793/bin/41551_2023_1079_Fig2_HTML.jpg",
                "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10842793/bin/fig2.jpg",
            ],
            "fig3": [
                "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10842793/bin/41551_2023_1079_Fig3_HTML.jpg",
                "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10842793/bin/fig3.jpg",
            ],
        },
    },
    "review": {
        # Gordon Front Immunol 2024 — Frontiers (CC BY)
        "pmcid": "PMC11133524",
        "pmid":  "38812514",
        "fig_urls": {
            "fig1": frontiers_figure_url("PMC11133524", "38812514", 1),
            "fig2": frontiers_figure_url("PMC11133524", "38812514", 2),
            "fig3": frontiers_figure_url("PMC11133524", "38812514", 3),
        },
    },
    "case_report": {
        # Blase Front Immunol 2022 — Frontiers (CC BY)
        "pmcid": "PMC9061985",
        "pmid":  "35514985",
        "fig_urls": {
            "fig1": [
                "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9061985/bin/fimmu-13-863177-g001.jpg",
                "https://www.frontiersin.org/files/Articles/863177/fimmu-13-863177-g001.jpg",
            ],
            "fig2": [
                "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9061985/bin/fimmu-13-863177-g002.jpg",
                "https://www.frontiersin.org/files/Articles/863177/fimmu-13-863177-g002.jpg",
            ],
        },
    },
    "letter": {
        # BioPhi — mAbs / Taylor & Francis / PMC8802135 (CC BY)
        "pmcid": "PMC8802135",
        "pmid":  "35102836",
        "fig_urls": {
            "fig1": [
                "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8802135/bin/kmab-14-01-2026596-g001.jpg",
                "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8802135/bin/fig1.jpg",
            ],
            "fig2": [
                "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8802135/bin/kmab-14-01-2026596-g002.jpg",
                "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8802135/bin/fig2.jpg",
            ],
            "fig3": [
                "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8802135/bin/kmab-14-01-2026596-g003.jpg",
                "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8802135/bin/fig3.jpg",
            ],
        },
    },
    "protocol": {
        # Wang Front Immunol 2024 — Frontiers (CC BY)
        "pmcid": "PMC11238839",
        "pmid":  "39076979",
        "fig_urls": {
            "fig1": frontiers_figure_url("PMC11238839", "39076979", 1),
            "fig2": frontiers_figure_url("PMC11238839", "39076979", 2),
            "fig3": frontiers_figure_url("PMC11238839", "39076979", 3),
        },
    },
    "systematic_review": {
        # Sazonovs BioDrugs 2022 — Springer / PMC9826743 (CC BY)
        "pmcid": "PMC9826743",
        "pmid":  "34797516",
        "fig_urls": {
            "fig1": [
                "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9826743/bin/40259_2021_507_Fig1_HTML.jpg",
                "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9826743/bin/fig1.jpg",
            ],
            "fig2": [
                "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9826743/bin/40259_2021_507_Fig2_HTML.jpg",
                "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9826743/bin/fig2.jpg",
            ],
            "fig3": [
                "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9826743/bin/40259_2021_507_Fig3_HTML.jpg",
                "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9826743/bin/fig3.jpg",
            ],
        },
    },
}


def run():
    assets = json.loads(ASSETS_FILE.read_text(encoding="utf-8"))
    updated = 0

    for atype, strategy in PAPER_STRATEGIES.items():
        print(f"\n── {atype.upper()} ({strategy['pmcid']}) ──")
        atype_dir = OUT_ROOT / atype
        atype_dir.mkdir(parents=True, exist_ok=True)

        for graphic_id, urls in strategy["fig_urls"].items():
            # Derive figure number from graphic_id (fig1 → 1)
            fig_num_str = "".join(c for c in graphic_id if c.isdigit())
            fig_num = int(fig_num_str) if fig_num_str else 1
            dest = atype_dir / f"fig{fig_num}.jpg"

            if dest.exists() and dest.stat().st_size > 5000:
                print(f"  ·  {dest.name} already present, skipping.")
                continue

            ok = download_figure(urls, dest)
            if ok:
                # Update assets JSON local_filename
                figs = assets.get(atype, {}).get("figures", [])
                for fig in figs:
                    if fig.get("pmc_graphic_id") == graphic_id:
                        fig["local_filename"] = f"fig{fig_num}.jpg"
                        updated += 1
            time.sleep(1)

    # Save updated assets
    ASSETS_FILE.write_text(
        json.dumps(assets, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n✓ Done. {updated} local_filename fields updated in benchmark_assets.json")


if __name__ == "__main__":
    run()
