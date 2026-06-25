"""
core/vh2vhh/structure_qa.py
============================
Phase 5 Structure QA utilities for VH→VHH conversion pipeline.

Implements:
  compute_ca_rg(pdb_path)      — Cα Radius of Gyration
  derive_plddt_proxy(errs)     — NanoBodyBuilder2 ensemble RMS → pLDDT proxy

Thresholds from VH_TO_VHH_CONVERSION_STANDARD_V1.8.2 §9.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─── V1.8.2 §9 thresholds ────────────────────────────────────────────────────
_RG_WARN_ANGSTROM: float = 14.5   # Rg > this → WARN
_RG_FAIL_ANGSTROM: float = 16.0   # Rg > this → FAIL (extended/unfolded)
_RG_LOW_WARN: float = 11.5        # Rg < this → WARN (over-compact / truncated)

_PLDDT_PASS_THRESHOLD: float = 70.0   # proxy ≥ 70 → PASS
_PLDDT_WARN_THRESHOLD: float = 55.0   # proxy ≥ 55 → WARN; < 55 → FAIL

# pLDDT proxy formula (calibrated on SP34 NanoBodyBuilder2 run, 2026-05-08):
#   proxy = 100 − 25 × mean_rmsd_Å   (clamp to [0, 100])
_PLDDT_COEFF: float = 25.0


def compute_ca_rg(pdb_path: str) -> Dict[str, Any]:
    """
    Compute Cα Radius of Gyration from a PDB file.

    Returns dict with keys:
      rg_angstrom   float | None
      n_ca          int
      tier          "PASS" | "WARN" | "FAIL"
      note          str
      error         str | None
    """
    try:
        coords: List[tuple] = []
        path = Path(pdb_path)
        if not path.exists():
            return {"rg_angstrom": None, "n_ca": 0, "tier": "FAIL",
                    "note": "PDB file not found", "error": f"Missing: {pdb_path}"}

        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if line.startswith("ATOM") and line[12:16].strip() == "CA":
                    try:
                        x = float(line[30:38])
                        y = float(line[38:46])
                        z = float(line[46:54])
                        coords.append((x, y, z))
                    except ValueError:
                        continue

        n = len(coords)
        if n < 5:
            return {"rg_angstrom": None, "n_ca": n, "tier": "FAIL",
                    "note": f"Too few Cα atoms ({n}) to compute Rg", "error": None}

        cx = sum(c[0] for c in coords) / n
        cy = sum(c[1] for c in coords) / n
        cz = sum(c[2] for c in coords) / n

        rg = math.sqrt(
            sum((c[0]-cx)**2 + (c[1]-cy)**2 + (c[2]-cz)**2 for c in coords) / n
        )

        if rg > _RG_FAIL_ANGSTROM:
            tier = "FAIL"
            note = f"Rg {rg:.3f} Å > {_RG_FAIL_ANGSTROM} Å — likely unfolded or extended conformation"
        elif rg > _RG_WARN_ANGSTROM:
            tier = "WARN"
            note = f"Rg {rg:.3f} Å > {_RG_WARN_ANGSTROM} Å — above compact VHH reference range"
        elif rg < _RG_LOW_WARN:
            tier = "WARN"
            note = f"Rg {rg:.3f} Å < {_RG_LOW_WARN} Å — unexpectedly compact; check truncation"
        else:
            tier = "PASS"
            note = f"Rg {rg:.3f} Å — within compact VHH reference range ({_RG_LOW_WARN}–{_RG_WARN_ANGSTROM} Å)"

        return {
            "rg_angstrom": round(rg, 3),
            "n_ca": n,
            "tier": tier,
            "note": note,
            "error": None,
        }

    except Exception as exc:
        return {"rg_angstrom": None, "n_ca": 0, "tier": "FAIL",
                "note": "Rg computation failed", "error": str(exc)}


def derive_plddt_proxy(
    error_estimates: Optional[List[float]],
) -> Dict[str, Any]:
    """
    Convert NanoBodyBuilder2 per-residue ensemble RMSD (Å) to a pLDDT proxy.

    Formula (V1.8.2 §9.2, calibrated 2026-05-08 on SP34):
        proxy_i = clamp(100 − 25 × rmsd_i, 0, 100)
        mean_proxy = mean(proxy_i)
        min_proxy  = min(proxy_i)

    Returns dict with keys:
      plddt_proxy_mean   float | None
      plddt_proxy_min    float | None
      n_residues         int
      tier               "PASS" | "WARN" | "FAIL"
      note               str
      error              str | None
    """
    try:
        if not error_estimates or len(error_estimates) == 0:
            return {"plddt_proxy_mean": None, "plddt_proxy_min": None,
                    "n_residues": 0, "tier": "FAIL",
                    "note": "No error estimates from NanoBodyBuilder2", "error": None}

        proxies = [
            max(0.0, min(100.0, 100.0 - _PLDDT_COEFF * e))
            for e in error_estimates
        ]
        mean_p = sum(proxies) / len(proxies)
        min_p = min(proxies)

        if mean_p >= _PLDDT_PASS_THRESHOLD:
            tier = "PASS"
            note = f"pLDDT proxy mean {mean_p:.1f} ≥ {_PLDDT_PASS_THRESHOLD} — high confidence fold"
        elif mean_p >= _PLDDT_WARN_THRESHOLD:
            tier = "WARN"
            note = (
                f"pLDDT proxy mean {mean_p:.1f} ∈ [{_PLDDT_WARN_THRESHOLD}, {_PLDDT_PASS_THRESHOLD}) "
                "— moderate confidence; recommend experimental structure confirmation"
            )
        else:
            tier = "FAIL"
            note = (
                f"pLDDT proxy mean {mean_p:.1f} < {_PLDDT_WARN_THRESHOLD} "
                "— low confidence; NanoBodyBuilder2 ensemble divergence high; "
                "consider AlphaFold2 or wet-lab structural characterisation"
            )

        return {
            "plddt_proxy_mean": round(mean_p, 1),
            "plddt_proxy_min": round(min_p, 1),
            "n_residues": len(proxies),
            "tier": tier,
            "note": note,
            "error": None,
        }

    except Exception as exc:
        return {"plddt_proxy_mean": None, "plddt_proxy_min": None,
                "n_residues": 0, "tier": "FAIL",
                "note": "pLDDT proxy computation failed", "error": str(exc)}


def phase5_overall_tier(rg_result: Dict[str, Any], plddt_result: Dict[str, Any]) -> str:
    """
    Combine Rg tier and pLDDT proxy tier into a single Phase 5 verdict.
    FAIL if either component is FAIL; WARN if either is WARN; else PASS.
    """
    tiers = {rg_result.get("tier", "FAIL"), plddt_result.get("tier", "FAIL")}
    if "FAIL" in tiers:
        return "FAIL"
    if "WARN" in tiers:
        return "WARN"
    return "PASS"
