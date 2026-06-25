"""
core/vaccine_design/population_coverage.py
──────────────────────────────────────────
HLA population coverage calculator — 100% local, no IEDB API.

Uses published HLA allele frequencies (Gonzalez-Galarza et al., 2020,
Allele Frequency Net Database) to estimate what fraction of a target
population would be covered by a set of HLA alleles.

Supports: global, European, East Asian, African, South Asian populations.

Usage:
    cov = PopulationCoverage()
    result = cov.calculate(["HLA-A*02:01", "HLA-A*24:02", "HLA-B*07:02"])
    print(result)  # {'global': 0.72, 'east_asian': 0.81, ...}
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List

__version__ = "1.0.0"

logger = logging.getLogger(__name__)

# ── HLA-I phenotype frequencies by population ────────────────────────────────
# Source: Allele Frequency Net Database (AFND 2020), phenotype frequency = 2pf - pf²
# where pf = allele frequency × 2 (diploid); values below are phenotype frequencies.

HLA_FREQ: Dict[str, Dict[str, float]] = {
    "HLA-A*01:01": {
        "global": 0.150, "european": 0.290, "east_asian": 0.020,
        "african": 0.060, "south_asian": 0.100,
    },
    "HLA-A*02:01": {
        "global": 0.400, "european": 0.450, "east_asian": 0.200,
        "african": 0.160, "south_asian": 0.250,
    },
    "HLA-A*03:01": {
        "global": 0.140, "european": 0.240, "east_asian": 0.050,
        "african": 0.080, "south_asian": 0.070,
    },
    "HLA-A*11:01": {
        "global": 0.130, "european": 0.100, "east_asian": 0.350,
        "african": 0.030, "south_asian": 0.200,
    },
    "HLA-A*24:02": {
        "global": 0.200, "european": 0.150, "east_asian": 0.380,
        "african": 0.040, "south_asian": 0.150,
    },
    "HLA-A*26:01": {
        "global": 0.060, "european": 0.060, "east_asian": 0.080,
        "african": 0.030, "south_asian": 0.040,
    },
    "HLA-A*68:01": {
        "global": 0.060, "european": 0.080, "east_asian": 0.020,
        "african": 0.100, "south_asian": 0.040,
    },
    "HLA-B*07:02": {
        "global": 0.120, "european": 0.230, "east_asian": 0.060,
        "african": 0.080, "south_asian": 0.080,
    },
    "HLA-B*08:01": {
        "global": 0.100, "european": 0.200, "east_asian": 0.010,
        "african": 0.060, "south_asian": 0.050,
    },
    "HLA-B*15:01": {
        "global": 0.070, "european": 0.100, "east_asian": 0.090,
        "african": 0.020, "south_asian": 0.050,
    },
    "HLA-B*35:01": {
        "global": 0.080, "european": 0.100, "east_asian": 0.060,
        "african": 0.060, "south_asian": 0.080,
    },
    "HLA-B*40:01": {
        "global": 0.070, "european": 0.060, "east_asian": 0.150,
        "african": 0.010, "south_asian": 0.080,
    },
    "HLA-B*44:02": {
        "global": 0.080, "european": 0.140, "east_asian": 0.030,
        "african": 0.040, "south_asian": 0.060,
    },
    "HLA-B*44:03": {
        "global": 0.060, "european": 0.060, "east_asian": 0.070,
        "african": 0.060, "south_asian": 0.040,
    },
    "HLA-B*51:01": {
        "global": 0.070, "european": 0.090, "east_asian": 0.080,
        "african": 0.030, "south_asian": 0.100,
    },
}

POPULATIONS = ["global", "european", "east_asian", "african", "south_asian"]


@dataclass
class CoverageResult:
    alleles: List[str]
    coverage: Dict[str, float]   # population → fraction covered
    per_allele: Dict[str, Dict[str, float]]  # allele → population → freq
    n_alleles: int
    best_population: str
    worst_population: str


class PopulationCoverage:
    """Calculate HLA population coverage — 100% local, no API."""

    def __init__(self, custom_freq: Dict[str, Dict[str, float]] = None):
        self.freq = custom_freq or HLA_FREQ

    def calculate(self, alleles: List[str]) -> CoverageResult:
        """Calculate population coverage for a set of HLA alleles.

        Uses the formula: coverage = 1 - Π(1 - f_i)
        where f_i is phenotype frequency of allele i.
        """
        coverage: Dict[str, float] = {}
        per_allele: Dict[str, Dict[str, float]] = {}

        for allele in alleles:
            per_allele[allele] = self.freq.get(allele, {pop: 0.0 for pop in POPULATIONS})

        for pop in POPULATIONS:
            prob_not_covered = 1.0
            for allele in alleles:
                freq_val = self.freq.get(allele, {}).get(pop, 0.0)
                prob_not_covered *= (1.0 - freq_val)
            coverage[pop] = round(1.0 - prob_not_covered, 4)

        best_pop = max(coverage, key=coverage.get)
        worst_pop = min(coverage, key=coverage.get)

        return CoverageResult(
            alleles=alleles,
            coverage=coverage,
            per_allele=per_allele,
            n_alleles=len(alleles),
            best_population=best_pop,
            worst_population=worst_pop,
        )

    def suggest_alleles(
        self,
        target_coverage: float = 0.90,
        target_population: str = "global",
        max_alleles: int = 8,
    ) -> List[str]:
        """Greedily select alleles to reach target population coverage."""
        selected: List[str] = []
        remaining = list(self.freq.keys())

        for _ in range(max_alleles):
            if not remaining:
                break

            best_allele = None
            best_coverage = 0.0

            for allele in remaining:
                trial = selected + [allele]
                result = self.calculate(trial)
                cov = result.coverage.get(target_population, 0)
                if cov > best_coverage:
                    best_coverage = cov
                    best_allele = allele

            if best_allele is None:
                break

            selected.append(best_allele)
            remaining.remove(best_allele)

            if best_coverage >= target_coverage:
                break

        return selected

    def report(self, alleles: List[str]) -> str:
        """Generate a text summary of population coverage."""
        result = self.calculate(alleles)
        lines = [
            f"HLA Population Coverage Report",
            f"{'='*40}",
            f"Alleles ({result.n_alleles}): {', '.join(result.alleles)}",
            "",
            f"{'Population':<15} {'Coverage':>10}",
            f"{'-'*15} {'-'*10}",
        ]
        for pop in POPULATIONS:
            cov = result.coverage[pop]
            bar = "█" * int(cov * 20) + "░" * (20 - int(cov * 20))
            lines.append(f"{pop:<15} {cov:>9.1%}  {bar}")

        lines.extend([
            "",
            f"Best coverage:  {result.best_population} ({result.coverage[result.best_population]:.1%})",
            f"Worst coverage: {result.worst_population} ({result.coverage[result.worst_population]:.1%})",
        ])
        return "\n".join(lines)
