#!/usr/bin/env python3
"""
Report approximate DRB1 allele frequencies by superpopulation and phenotype coverage
for curated 27- vs 35-allele MHC-II screening panels.

Panels:
  data/reference/hla_mhcii_panels/panel_drb1_27.txt
  data/reference/hla_mhcii_panels/panel_drb1_35.txt

Frequency table (bundled, rounded priors — **not** a substitute for AFND / trial cohort):
  data/reference/hla_mhcii_panels/drb1_frequency_by_superpopulation.tsv

Coverage model (single locus DRB1, random mating, complete specification):
  Let F = sum of frequencies of alleles in the panel for a population.
  P(individual carries ≥1 copy of any panel allele) = 1 - (1 - F)^2
  where (1 - F) is the summed frequency of **all other** DRB1 specificities (implicit residual).

The TSV includes a row RESIDUAL_OTHER_DRB1 so each population column sums to 1.0.

**Always validate** allele lists and frequencies for regulatory work using:
  - Allele Frequency Net Database (AFND): https://www.allelefrequencies.net
  - IEDB Population Coverage: https://tools.iedb.org/population/

Usage:
  python scripts/report_hla_drb1_panel_coverage.py
  python scripts/report_hla_drb1_panel_coverage.py --write-tsv   # regenerate frequency TSV from embedded priors
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
PANEL_DIR = SUITE / "data/reference/hla_mhcii_panels"
FREQ_TSV = PANEL_DIR / "drb1_frequency_by_superpopulation.tsv"

# Order must match panel_drb1_35.txt (35 alleles)
_ALLELES_35 = [
    "DRB1*01:01",
    "DRB1*03:01",
    "DRB1*04:01",
    "DRB1*04:02",
    "DRB1*04:03",
    "DRB1*04:04",
    "DRB1*04:05",
    "DRB1*04:07",
    "DRB1*07:01",
    "DRB1*08:01",
    "DRB1*08:02",
    "DRB1*08:03",
    "DRB1*09:01",
    "DRB1*10:01",
    "DRB1*11:01",
    "DRB1*11:02",
    "DRB1*11:03",
    "DRB1*11:04",
    "DRB1*12:01",
    "DRB1*13:01",
    "DRB1*13:02",
    "DRB1*13:03",
    "DRB1*14:01",
    "DRB1*15:01",
    "DRB1*15:02",
    "DRB1*15:03",
    "DRB1*16:01",
    "DRB1*01:02",
    "DRB1*03:02",
    "DRB1*04:06",
    "DRB1*04:08",
    "DRB1*07:02",
    "DRB1*09:02",
    "DRB1*13:05",
    "DRB1*14:02",
    "DRB1*15:17",
]

# Literature-informed **priors** (bone marrow / population surveys; rounded).
# Keys: EUR, EAS, AFR, AMR, SAS — will be renormalised + residual added.
_RAW: dict[str, dict[str, float]] = {
    "EUR": {
        "DRB1*15:01": 0.105,
        "DRB1*07:01": 0.095,
        "DRB1*13:01": 0.055,
        "DRB1*04:01": 0.058,
        "DRB1*01:01": 0.072,
        "DRB1*11:01": 0.048,
        "DRB1*03:01": 0.048,
        "DRB1*04:02": 0.028,
        "DRB1*15:02": 0.028,
        "DRB1*07:02": 0.022,
        "DRB1*14:01": 0.022,
        "DRB1*04:03": 0.022,
        "DRB1*01:02": 0.018,
        "DRB1*13:02": 0.018,
        "DRB1*12:01": 0.016,
        "DRB1*10:01": 0.016,
        "DRB1*16:01": 0.016,
        "DRB1*04:04": 0.016,
        "DRB1*15:03": 0.020,
        "DRB1*08:01": 0.024,
        "DRB1*04:07": 0.014,
        "DRB1*11:02": 0.014,
        "DRB1*04:05": 0.012,
        "DRB1*09:01": 0.012,
        "DRB1*11:03": 0.010,
        "DRB1*13:03": 0.009,
        "DRB1*08:02": 0.009,
        "DRB1*03:02": 0.012,
        "DRB1*14:02": 0.008,
        "DRB1*11:04": 0.007,
        "DRB1*04:06": 0.006,
        "DRB1*13:05": 0.006,
        "DRB1*08:03": 0.006,
        "DRB1*04:08": 0.005,
        "DRB1*15:17": 0.005,
        "DRB1*09:02": 0.004,
    },
    "EAS": {
        "DRB1*09:01": 0.125,
        "DRB1*15:01": 0.065,
        "DRB1*08:03": 0.055,
        "DRB1*14:01": 0.048,
        "DRB1*12:01": 0.042,
        "DRB1*04:05": 0.035,
        "DRB1*01:01": 0.038,
        "DRB1*11:01": 0.032,
        "DRB1*13:02": 0.028,
        "DRB1*04:06": 0.030,
        "DRB1*07:01": 0.022,
        "DRB1*04:03": 0.020,
        "DRB1*15:02": 0.018,
        "DRB1*04:01": 0.018,
        "DRB1*16:01": 0.015,
        "DRB1*08:01": 0.014,
        "DRB1*13:01": 0.014,
        "DRB1*11:02": 0.012,
        "DRB1*04:02": 0.012,
        "DRB1*03:01": 0.012,
        "DRB1*15:03": 0.012,
        "DRB1*10:01": 0.010,
        "DRB1*04:04": 0.010,
        "DRB1*01:02": 0.008,
        "DRB1*11:03": 0.008,
        "DRB1*04:07": 0.008,
        "DRB1*09:02": 0.012,
        "DRB1*07:02": 0.008,
        "DRB1*08:02": 0.006,
        "DRB1*13:03": 0.006,
        "DRB1*11:04": 0.005,
        "DRB1*04:08": 0.005,
        "DRB1*03:02": 0.006,
        "DRB1*13:05": 0.005,
        "DRB1*14:02": 0.006,
        "DRB1*15:17": 0.004,
    },
    "AFR": {
        "DRB1*11:01": 0.075,
        "DRB1*11:02": 0.055,
        "DRB1*13:02": 0.048,
        "DRB1*03:02": 0.042,
        "DRB1*15:03": 0.040,
        "DRB1*15:01": 0.038,
        "DRB1*13:01": 0.038,
        "DRB1*07:01": 0.032,
        "DRB1*04:01": 0.028,
        "DRB1*09:01": 0.022,
        "DRB1*10:01": 0.020,
        "DRB1*04:03": 0.018,
        "DRB1*12:01": 0.018,
        "DRB1*14:01": 0.016,
        "DRB1*03:01": 0.016,
        "DRB1*01:01": 0.014,
        "DRB1*04:02": 0.014,
        "DRB1*08:01": 0.012,
        "DRB1*11:03": 0.012,
        "DRB1*15:02": 0.012,
        "DRB1*04:04": 0.010,
        "DRB1*13:03": 0.010,
        "DRB1*16:01": 0.010,
        "DRB1*01:02": 0.008,
        "DRB1*04:05": 0.008,
        "DRB1*11:04": 0.008,
        "DRB1*04:06": 0.008,
        "DRB1*07:02": 0.008,
        "DRB1*04:07": 0.008,
        "DRB1*08:02": 0.006,
        "DRB1*08:03": 0.006,
        "DRB1*04:08": 0.006,
        "DRB1*13:05": 0.006,
        "DRB1*14:02": 0.006,
        "DRB1*09:02": 0.006,
        "DRB1*15:17": 0.006,
    },
    "AMR": {
        "DRB1*04:01": 0.085,
        "DRB1*15:01": 0.065,
        "DRB1*07:01": 0.055,
        "DRB1*11:01": 0.048,
        "DRB1*09:01": 0.042,
        "DRB1*13:01": 0.038,
        "DRB1*01:01": 0.035,
        "DRB1*03:01": 0.032,
        "DRB1*14:01": 0.028,
        "DRB1*04:02": 0.026,
        "DRB1*08:01": 0.022,
        "DRB1*16:01": 0.020,
        "DRB1*12:01": 0.018,
        "DRB1*15:02": 0.018,
        "DRB1*04:03": 0.016,
        "DRB1*13:02": 0.016,
        "DRB1*10:01": 0.014,
        "DRB1*01:02": 0.012,
        "DRB1*15:03": 0.014,
        "DRB1*04:04": 0.012,
        "DRB1*11:02": 0.012,
        "DRB1*07:02": 0.012,
        "DRB1*04:05": 0.010,
        "DRB1*11:03": 0.010,
        "DRB1*08:02": 0.008,
        "DRB1*04:06": 0.010,
        "DRB1*03:02": 0.010,
        "DRB1*13:03": 0.008,
        "DRB1*08:03": 0.008,
        "DRB1*04:07": 0.008,
        "DRB1*11:04": 0.006,
        "DRB1*04:08": 0.006,
        "DRB1*13:05": 0.006,
        "DRB1*14:02": 0.006,
        "DRB1*09:02": 0.008,
        "DRB1*15:17": 0.006,
    },
    "SAS": {
        "DRB1*07:01": 0.085,
        "DRB1*15:01": 0.072,
        "DRB1*11:01": 0.065,
        "DRB1*13:01": 0.058,
        "DRB1*03:01": 0.048,
        "DRB1*04:01": 0.045,
        "DRB1*14:01": 0.038,
        "DRB1*10:01": 0.028,
        "DRB1*08:01": 0.026,
        "DRB1*04:02": 0.024,
        "DRB1*12:01": 0.022,
        "DRB1*15:02": 0.020,
        "DRB1*01:01": 0.018,
        "DRB1*09:01": 0.018,
        "DRB1*13:02": 0.018,
        "DRB1*04:03": 0.016,
        "DRB1*16:01": 0.016,
        "DRB1*15:03": 0.016,
        "DRB1*11:02": 0.014,
        "DRB1*01:02": 0.012,
        "DRB1*04:04": 0.012,
        "DRB1*07:02": 0.012,
        "DRB1*04:05": 0.010,
        "DRB1*11:03": 0.010,
        "DRB1*08:03": 0.010,
        "DRB1*04:06": 0.008,
        "DRB1*03:02": 0.012,
        "DRB1*13:03": 0.008,
        "DRB1*08:02": 0.008,
        "DRB1*04:07": 0.008,
        "DRB1*11:04": 0.006,
        "DRB1*04:08": 0.006,
        "DRB1*13:05": 0.006,
        "DRB1*14:02": 0.006,
        "DRB1*09:02": 0.006,
        "DRB1*15:17": 0.006,
    },
}


def _build_balanced_pop_dicts() -> dict[str, dict[str, float]]:
    """Per superpopulation: frequencies for all 35 panel alleles; scale if sum>1; residual added in TSV."""
    out: dict[str, dict[str, float]] = {}
    for pop, src in _RAW.items():
        dd = {a: float(src.get(a, 0.0)) for a in _ALLELES_35}
        s = sum(dd.values())
        if s > 1.0:
            dd = {k: v / s for k, v in dd.items()}
        out[pop] = dd
    return out


def _rows_for_tsv(pops: dict[str, dict[str, float]], alleles: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for a in alleles:
        row: dict[str, str] = {"allele": a}
        for pop in pops:
            row[pop] = f"{pops[pop].get(a, 0.0):.6f}"
        rows.append(row)
    res: dict[str, str] = {"allele": "RESIDUAL_OTHER_DRB1"}
    for pop in pops:
        fs = sum(pops[pop].get(a, 0.0) for a in alleles)
        res[pop] = f"{max(0.0, 1.0 - fs):.6f}"
    rows.append(res)
    return rows


def _load_panel(path: Path) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        t = line.strip()
        if not t or t.startswith("#"):
            continue
        out.append(t)
    return out


def _phenotype_coverage(freq_by_allele: dict[str, float], panel: set[str]) -> float:
    f = sum(freq_by_allele.get(a, 0.0) for a in panel)
    f = min(1.0, max(0.0, f))
    return 1.0 - (1.0 - f) ** 2


def write_freq_tsv() -> None:
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    balanced = _build_balanced_pop_dicts()
    rows = _rows_for_tsv(balanced, _ALLELES_35)
    cols = ["allele", "EUR", "EAS", "AFR", "AMR", "SAS"]
    with FREQ_TSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in cols})
    print(f"Wrote {FREQ_TSV.relative_to(SUITE)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-tsv", action="store_true", help="Regenerate drb1_frequency_by_superpopulation.tsv")
    args = ap.parse_args()
    if args.write_tsv:
        write_freq_tsv()
        return 0

    if not FREQ_TSV.is_file():
        write_freq_tsv()

    p27 = set(_load_panel(PANEL_DIR / "panel_drb1_27.txt"))
    p35 = set(_load_panel(PANEL_DIR / "panel_drb1_35.txt"))

    by_pop: dict[str, dict[str, float]] = {c: {} for c in ("EUR", "EAS", "AFR", "AMR", "SAS")}
    with FREQ_TSV.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            a = row["allele"]
            for c in by_pop:
                by_pop[c][a] = float(row[c])

    lines = [
        "HLA-DRB1 panel coverage (approximate; validate with AFND + IEDB Population Coverage)",
        "=" * 72,
        "Superpopulations: EUR (European), EAS (East Asian), AFR (Sub-Saharan proxy),",
        "                  AMR (Latin American admixed proxy), SAS (South Asian proxy).",
        "",
        "P(carry ≥1 panel allele) = 1 - (1 - F)^2  with F = summed freq of panel alleles",
        "(RESIDUAL_OTHER_DRB1 captures non-panel chromosomal frequency mass).",
        "",
    ]
    for pop, fd in by_pop.items():
        f27 = sum(fd.get(a, 0) for a in p27)
        f35 = sum(fd.get(a, 0) for a in p35)
        c27 = _phenotype_coverage(fd, p27)
        c35 = _phenotype_coverage(fd, p35)
        lines.append(
            f"{pop}:  F_panel27={f27:.3f}  coverage27={c27:.3f}  |  "
            f"F_panel35={f35:.3f}  coverage35={c35:.3f}  (Δcov vs27: {c35 - c27:+.3f})"
        )
    lines += ["", f"Frequency table: {FREQ_TSV.relative_to(SUITE)}", f"Panels: {PANEL_DIR.relative_to(SUITE)}/panel_drb1_27.txt, panel_drb1_35.txt"]
    text = "\n".join(lines)
    print(text)
    (PANEL_DIR / "panel_coverage_summary.txt").write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
