"""
AFDB pLDDT per-residue confidence figure — InSynBio Figure Recipe.

Adopted from GDM science-skills `alphafold_database_fetch_and_analyze` (Apache-2.0).
See vendor/adopted/science-skills/afdb/SKILL_mirror.md.

Usage (CLI):
    python core/figure/afdb_plddt.py --uniprot Q9Y6R7 --out figures/plddt.pdf
    python core/figure/afdb_plddt.py --uniprot P0DTC2 --highlight "CDR3:99:113" --out figures/plddt.pdf

Usage (API):
    from core.figure.afdb_plddt import fetch_afdb_plddt, plot_plddt
    plddt, meta = fetch_afdb_plddt("Q9Y6R7")
    fig = plot_plddt(plddt, highlight_regions=[("CDR3", 99, 113)])
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    sys.exit("ERROR: 'requests' not installed. Run: pip install requests")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
except ImportError:
    sys.exit("ERROR: 'matplotlib' not installed. Run: pip install matplotlib")

# pLDDT color scale matching AFDB standard
PLDDT_COLORS = [
    (90, 100, "#0053D6"),   # very high — dark blue
    (70, 90,  "#65CBF3"),   # confident — light blue
    (50, 70,  "#FFDB13"),   # low — yellow
    (0,  50,  "#FF7D45"),   # very low / disordered — orange
]

AFDB_API = "https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}"


def fetch_afdb_plddt(uniprot_id: str, *, retries: int = 3) -> tuple[list[float], dict]:
    """
    Fetch pLDDT scores for a UniProt accession from the AlphaFold Database.

    Returns:
        plddt (list[float]): per-residue pLDDT scores (0–100)
        meta (dict): raw API metadata entry
    """
    url = AFDB_API.format(uniprot_id=uniprot_id.strip().upper())
    for attempt in range(retries):
        resp = requests.get(url, timeout=20)
        if resp.status_code == 429:
            wait = 5 * (attempt + 1)
            print(f"[AFDB] Rate limited — waiting {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        if resp.status_code == 404:
            raise ValueError(f"UniProt ID '{uniprot_id}' not found in AlphaFold Database.")
        resp.raise_for_status()
        data = resp.json()
        break
    else:
        raise RuntimeError(f"AFDB API failed after {retries} retries for '{uniprot_id}'")

    # API returns a list; take the first (main) entry
    entry = data[0] if isinstance(data, list) else data
    plddt = entry.get("confidenceScore", entry.get("bFactorMeanPerResidue", []))
    if not plddt:
        raise ValueError(f"No pLDDT data in AFDB response for '{uniprot_id}'")
    return list(plddt), entry


def _plddt_color(score: float) -> str:
    for lo, hi, color in PLDDT_COLORS:
        if lo <= score <= hi:
            return color
    return PLDDT_COLORS[-1][2]


def plot_plddt(
    plddt: list[float],
    *,
    title: str = "",
    highlight_regions: list[tuple[str, int, int]] | None = None,
    double_column: bool = False,
    dpi: int = 300,
) -> "plt.Figure":
    """
    Draw a per-residue pLDDT ribbon plot with optional region highlights.

    Args:
        plddt: per-residue confidence scores
        title: plot title (e.g. "UniProt Q9Y6R7 — AFDB pLDDT")
        highlight_regions: list of (label, start_0idx, end_0idx_inclusive)
        double_column: if True use 17.4 cm width, else 8.5 cm (single column)
        dpi: figure DPI for raster export
    """
    from core.figure.matplotlib_nature import apply_nature_rcparams
    apply_nature_rcparams(font_size=7)

    width_cm = 17.4 if double_column else 8.5
    fig, ax = plt.subplots(figsize=(width_cm / 2.54, 4.5 / 2.54))

    x = list(range(1, len(plddt) + 1))
    colors = [_plddt_color(v) for v in plddt]

    # Draw bar chart with per-residue coloring
    ax.bar(x, plddt, color=colors, width=1.0, linewidth=0)

    # Highlight regions (CDR / FR overlays)
    if highlight_regions:
        for label, start, end in highlight_regions:
            ax.axvspan(start + 1, end + 2, alpha=0.18, color="#888888",
                       linewidth=0, label=label)
            mid = (start + end) / 2 + 1.5
            ax.text(mid, 103, label, ha="center", va="bottom",
                    fontsize=6, color="#444444", rotation=30)

    # Reference lines
    for threshold, ls in [(90, "--"), (70, ":"), (50, ":")]:
        ax.axhline(threshold, color="#888888", linewidth=0.6, linestyle=ls, zorder=0)

    ax.set_xlim(0, len(plddt) + 1)
    ax.set_ylim(0, 115)
    ax.set_xlabel("Residue position", fontsize=7)
    ax.set_ylabel("pLDDT", fontsize=7)
    if title:
        ax.set_title(title, fontsize=8, pad=4)

    # AFDB legend patches
    patches = [mpatches.Patch(color=c, label=f"{lo}–{hi}") for lo, hi, c in PLDDT_COLORS]
    ax.legend(handles=patches, title="pLDDT", title_fontsize=6, fontsize=6,
              loc="lower right", bbox_to_anchor=(1.0, 0.0))

    plt.tight_layout(pad=0.3)
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="afdb_plddt",
        description="Fetch AFDB pLDDT and generate per-residue confidence figure",
    )
    parser.add_argument("--uniprot", required=True, help="UniProt accession (e.g. Q9Y6R7)")
    parser.add_argument("--out", required=True, help="Output path (PDF or PNG)")
    parser.add_argument(
        "--highlight", nargs="*", default=[],
        help="Region highlights: 'LABEL:START:END' (0-indexed, e.g. 'CDR3:99:113')"
    )
    parser.add_argument("--double-column", action="store_true")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--save-json", default=None, help="Also write raw AFDB metadata JSON")

    args = parser.parse_args()

    print(f"[AFDB] Fetching pLDDT for {args.uniprot} …")
    plddt, meta = fetch_afdb_plddt(args.uniprot)
    print(f"[AFDB] {len(plddt)} residues. Mean pLDDT: {sum(plddt)/len(plddt):.1f}")

    if args.save_json:
        Path(args.save_json).write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"[AFDB] metadata → {args.save_json}")

    highlights: list[tuple[str, int, int]] = []
    for h in args.highlight:
        parts = h.split(":")
        if len(parts) == 3:
            highlights.append((parts[0], int(parts[1]), int(parts[2])))
        else:
            print(f"[AFDB] WARN: skipping malformed highlight '{h}' (expected LABEL:START:END)")

    title = f"AlphaFold pLDDT — {args.uniprot}"
    fig = plot_plddt(plddt, title=title, highlight_regions=highlights or None,
                     double_column=args.double_column, dpi=args.dpi)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=args.dpi, bbox_inches="tight")
    print(f"[AFDB] figure → {out}")
    plt.close(fig)


if __name__ == "__main__":
    main()
