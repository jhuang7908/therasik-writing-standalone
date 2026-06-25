"""Pet Germline Coefficient (CGC / FGC) — pet 9-mer compatibility metric.

Mirror of `core/humanization/hpr_index.py` (HPR), but the reference 9-mer
library is the species-specific Pet 9-mer DB built from clinical antibodies,
Tier-1 CMC scaffolds, and germline sequences.

CGC = Canine Germline Coefficient (dog)
FGC = Feline Germline Coefficient (cat)

Formula (identical math to HPR):
    score = N_found_9mers / N_total_9mers
    where each 9-mer is sliced from the variable region and looked up
    against the species reference DB (binary IN/OUT).

Tier interpretation:
    >= 0.85  → highly_compatible
    >= 0.70  → acceptable
    <  0.70  → warn / unfamiliar
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Set

REPO = Path(__file__).resolve().parents[2]

_DB_PATHS: Dict[str, Path] = {
    "dog": REPO / "data/reference/pet_9mer_db/dog_9mer_v1.txt",
    "cat": REPO / "data/reference/pet_9mer_db/cat_9mer_v1.txt",
}

# Tier thresholds (parallel to HPR human-OAS conventions)
TIER_HIGH = 0.85
TIER_OK = 0.70


@dataclass
class ChainPGC:
    """Per-chain Pet Germline Coefficient result."""
    score: Optional[float]
    found_9mers: Optional[int]
    total_9mers: Optional[int]
    tier: str = "not_computed"
    status: str = "not_computed"
    error: Optional[str] = None


@lru_cache(maxsize=4)
def _load_db(species: str) -> Optional[Set[str]]:
    """Load species-specific 9-mer reference DB into a set."""
    path = _DB_PATHS.get(species)
    if not path or not path.is_file():
        return None
    try:
        return set(
            line.strip().upper()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and len(line.strip()) == 9
        )
    except Exception:
        return None


def _classify_tier(score: Optional[float]) -> str:
    if score is None:
        return "not_computed"
    if score >= TIER_HIGH:
        return "highly_compatible"
    if score >= TIER_OK:
        return "acceptable"
    return "warn_unfamiliar"


def _chop_9mers(seq: str) -> list:
    s = (seq or "").strip().upper()
    if len(s) < 9:
        return []
    return [s[i:i + 9] for i in range(len(s) - 9 + 1)]


def _score_chain(seq: str, db: Set[str]) -> ChainPGC:
    seq = (seq or "").strip().upper()
    if len(seq) < 9:
        return ChainPGC(None, None, None, "not_computed", "not_computed",
                        "sequence shorter than 9 aa")
    peptides = _chop_9mers(seq)
    total = len(peptides)
    if total <= 0:
        return ChainPGC(None, 0, 0, "not_computed", "not_computed", "no 9-mers generated")
    found = sum(1 for p in peptides if p in db)
    score = round(found / total, 4)
    return ChainPGC(score, found, total, _classify_tier(score), "computed", None)


def _empty_chain(reason: str) -> ChainPGC:
    return ChainPGC(None, None, None, "not_computed", "not_computed", reason)


def compute_pet_germline_coefficient(
    species: str,
    vh: str = "",
    vl: str = "",
) -> Dict[str, Any]:
    """
    Compute species-aware pet germline coefficient.

    Args:
        species: 'dog' (CGC) or 'cat' (FGC)
        vh: heavy-chain variable region
        vl: light-chain variable region (optional)

    Returns:
        Dict with metric_name, vh / vl / combined results, tier, error.
    """
    sp = (species or "").strip().lower()
    if sp not in _DB_PATHS:
        return {
            "metric_name": "PGC",
            "species": species,
            "error": f"Unsupported species '{species}'. Use 'dog' or 'cat'.",
            "vh": asdict(_empty_chain("unsupported species")),
            "vl": asdict(_empty_chain("unsupported species")),
            "combined": asdict(_empty_chain("unsupported species")),
        }

    db = _load_db(sp)
    if db is None:
        return {
            "metric_name": "PGC",
            "species": sp,
            "error": f"9-mer DB not found at {_DB_PATHS[sp]}",
            "vh": asdict(_empty_chain("db missing")),
            "vl": asdict(_empty_chain("db missing")),
            "combined": asdict(_empty_chain("db missing")),
        }

    metric_full = "Canine Germline Coefficient" if sp == "dog" else "Feline Germline Coefficient"
    metric_short = "CGC" if sp == "dog" else "FGC"

    vh_result = _score_chain(vh, db) if vh else _empty_chain("vh empty")
    vl_result = _score_chain(vl, db) if vl else _empty_chain("vl empty")

    combined_found = (vh_result.found_9mers or 0) + (vl_result.found_9mers or 0)
    combined_total = (vh_result.total_9mers or 0) + (vl_result.total_9mers or 0)
    if combined_total > 0:
        combined_score = round(combined_found / combined_total, 4)
        combined_chain = ChainPGC(
            combined_score, combined_found, combined_total,
            _classify_tier(combined_score), "computed", None,
        )
    else:
        combined_chain = _empty_chain("no chains scored")

    return {
        "metric_name": metric_short,
        "full_name": metric_full,
        "species": sp,
        "method_summary": (
            f"Variable-region 9-mer compatibility against {sp} reference DB "
            f"(clinical ×3 + Tier-1 scaffold ×2 + germline ×1)."
        ),
        "db_path": str(_DB_PATHS[sp]),
        "db_size_9mers": len(db),
        "tier_thresholds": {"highly_compatible": TIER_HIGH, "acceptable": TIER_OK},
        "vh": asdict(vh_result),
        "vl": asdict(vl_result),
        "combined": asdict(combined_chain),
    }


def compute_cgc(vh: str, vl: str = "") -> Dict[str, Any]:
    """Convenience wrapper for canine germline coefficient."""
    return compute_pet_germline_coefficient("dog", vh, vl)


def compute_fgc(vh: str, vl: str = "") -> Dict[str, Any]:
    """Convenience wrapper for feline germline coefficient."""
    return compute_pet_germline_coefficient("cat", vh, vl)


__all__ = [
    "compute_pet_germline_coefficient",
    "compute_cgc",
    "compute_fgc",
    "TIER_HIGH",
    "TIER_OK",
]
