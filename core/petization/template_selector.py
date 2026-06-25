"""Pet Template Selector — 5-weighted scoring + hard constraints.

Selects optimal canine/feline scaffold templates for VH/VL donor sequences.

Scoring formula:
    score = 0.30 × FR_identity              # similarity to donor FR
          + 0.25 × CMC_quality              # Tier-1=1.0, Tier-2=0.7, Tier-3=0.4
          + 0.20 × CGC_or_FGC_template      # template's own species compatibility
          + 0.15 × CDR_length_match         # CDR-H1/H2 length-difference tolerance
          + 0.10 × Germline_abundance       # germline frequency support

Hard constraints (immediate rejection):
    - Species mismatch
    - Locus mismatch
    - CDR-H1 / CDR-H2 length difference > 2
    - Template FR pI outside species reference range
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[2]

# Reference data paths
_SCAFFOLD_JSONS: Dict[str, Path] = {
    "dog": REPO / "data/germlines/canis_lupus_familiaris_ig_aa/dog_scaffold_cmc_optimization_tier1_tier2_v1.json",
    "cat": REPO / "data/germlines/felis_catus_ig_aa/cat_scaffold_cmc_optimization_tier1_tier2_v1.json",
}

# Scoring weights (sum to 1.00)
SCORING_WEIGHTS: Dict[str, float] = {
    "fr_identity": 0.30,
    "cmc_quality": 0.25,
    "template_pgc": 0.20,
    "cdr_length_match": 0.15,
    "germline_abundance": 0.10,
}

# Tier → CMC quality factor
TIER_QUALITY: Dict[str, float] = {"tier1": 1.00, "tier2": 0.70, "tier3": 0.40}

# Species pI reference bounds (FR-only sequences, looser than full V-region)
_SPECIES_PI_BOUNDS: Dict[str, Dict[str, Tuple[float, float]]] = {
    "dog": {"VH": (5.5, 9.8), "VL_kappa": (4.0, 9.0), "VL_lambda": (4.0, 9.0)},
    "cat": {"VH": (5.0, 9.5), "VL_kappa": (4.0, 9.0), "VL_lambda": (4.0, 9.0)},
}

# CDR length-difference tolerance
CDR_LENGTH_TOLERANCE = 2

# Kabat CDR boundaries (used when only the FR concat is available — falls back
# to anarci numbering where possible)
_KABAT_CDR_VH = ((26, 35), (50, 65), (95, 102))
_KABAT_CDR_VL = ((24, 34), (50, 56), (89, 97))


# ══════════════════════════════════════════════════════════════════════════════
# Data loading
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class TemplateRecord:
    species: str
    locus: str
    chain: str
    gene: str
    tier: str
    sequence_aa: str
    fr_segments: Dict[str, str]
    fr_concat: str
    total_flags: Optional[int]
    cmc_summary: Dict[str, Any]


@lru_cache(maxsize=4)
def load_template_pool(species: str, locus: str) -> List[TemplateRecord]:
    """Load all scaffold templates from species + locus JSON."""
    sp = species.lower()
    path = _SCAFFOLD_JSONS.get(sp)
    if not path or not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    out: List[TemplateRecord] = []
    for row in data.get("rows", []):
        if row.get("locus", "") != locus:
            continue
        seq = row.get("sequence_aa_kabat_norm") or row.get("sequence_aa_imgt", "")
        if not seq or len(seq) < 50:
            continue
        cmc_summary = row.get("cmc_full", {}).get("summary", {}) or {}
        out.append(TemplateRecord(
            species=sp,
            locus=row.get("locus", locus),
            chain=row.get("chain", ""),
            gene=row.get("gene", ""),
            tier=row.get("tier", "tier3").lower(),
            sequence_aa=seq,
            fr_segments=row.get("fr_segments", {}) or {},
            fr_concat=row.get("fr1_3_concat", "") or "",
            total_flags=cmc_summary.get("total_flags"),
            cmc_summary=cmc_summary,
        ))
    return out


# ══════════════════════════════════════════════════════════════════════════════
# Helper functions
# ══════════════════════════════════════════════════════════════════════════════

def _kabat_number(seq: str, chain: str) -> Optional[List[Tuple[Tuple[int, str], str]]]:
    """ANARCI Kabat numbering. Returns list of ((pos, ins), aa) or None."""
    try:
        from anarci import anarci  # type: ignore
        results, _, _ = anarci([("q", seq)], scheme="kabat", output=False)
        if not results or results[0] is None:
            return None
        return [
            ((pos, ins.strip()), aa)
            for (pos, ins), aa in results[0][0][0]
            if aa != "-" and aa.isalpha()
        ]
    except Exception:
        return None


def _extract_cdrs(seq: str, chain: str) -> Optional[Dict[str, str]]:
    """Extract CDR1/CDR2/CDR3 sequences using Kabat numbering."""
    numbered = _kabat_number(seq, chain)
    if not numbered:
        return None
    bounds = _KABAT_CDR_VH if chain == "VH" else _KABAT_CDR_VL
    cdrs: Dict[str, List[str]] = {"CDR1": [], "CDR2": [], "CDR3": []}
    for (pos, ins), aa in numbered:
        for idx, (lo, hi) in enumerate(bounds):
            if lo <= pos <= hi:
                cdrs[f"CDR{idx + 1}"].append(aa)
    return {k: "".join(v) for k, v in cdrs.items()}


def _extract_frs(seq: str, chain: str) -> Optional[Dict[str, str]]:
    """Extract FR1/FR2/FR3 sequences using Kabat numbering."""
    numbered = _kabat_number(seq, chain)
    if not numbered:
        return None
    bounds = _KABAT_CDR_VH if chain == "VH" else _KABAT_CDR_VL
    cdr_ranges = [(lo, hi) for lo, hi in bounds]
    frs: Dict[str, List[str]] = {"FR1": [], "FR2": [], "FR3": [], "FR4": []}
    for (pos, ins), aa in numbered:
        if pos < cdr_ranges[0][0]:
            frs["FR1"].append(aa)
        elif cdr_ranges[0][1] < pos < cdr_ranges[1][0]:
            frs["FR2"].append(aa)
        elif cdr_ranges[1][1] < pos < cdr_ranges[2][0]:
            frs["FR3"].append(aa)
        elif pos > cdr_ranges[2][1]:
            frs["FR4"].append(aa)
    return {k: "".join(v) for k, v in frs.items()}


def _seq_identity(a: str, b: str) -> float:
    """Pairwise identity from aligned-by-truncation sequences."""
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    matches = sum(1 for i in range(n) if a[i] == b[i])
    return matches / n


def _compute_pi(seq: str) -> Optional[float]:
    try:
        from Bio.SeqUtils.ProtParam import ProteinAnalysis  # type: ignore
        return round(ProteinAnalysis(seq.replace("X", "A")).isoelectric_point(), 2)
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Scoring components
# ══════════════════════════════════════════════════════════════════════════════

def _score_fr_identity(donor_fr: Dict[str, str], template_fr: Dict[str, str]) -> float:
    """Mean FR identity over FR1+FR2+FR3 (FR4 typically very conserved → skip)."""
    scores = []
    for region in ("FR1", "FR2", "FR3"):
        d = donor_fr.get(region, "")
        t = template_fr.get(region, "")
        if d and t:
            scores.append(_seq_identity(d, t))
    return sum(scores) / len(scores) if scores else 0.0


def _score_cmc_quality(template: TemplateRecord) -> float:
    """Quality factor based on tier; subtract small penalty per CMC flag."""
    base = TIER_QUALITY.get(template.tier, 0.30)
    flags = template.total_flags or 0
    penalty = min(0.20, flags * 0.03)  # cap at 0.20
    return max(0.0, base - penalty)


def _score_template_pgc(template: TemplateRecord) -> float:
    """Compute CGC/FGC of the template's own sequence (already in 9-mer DB)."""
    try:
        from core.cmc.pet_germline_coefficient import compute_pet_germline_coefficient
        result = compute_pet_germline_coefficient(template.species, vh=template.sequence_aa)
        sc = result.get("vh", {}).get("score")
        return float(sc) if sc is not None else 0.0
    except Exception:
        return 0.0


def _score_cdr_length_match(donor_cdrs: Dict[str, str], template_cdrs: Dict[str, str]) -> float:
    """
    Linear penalty for CDR length differences.
    Score = 1.0 if exact match; 0 if any CDR length diff > 2.
    """
    diffs = []
    for region in ("CDR1", "CDR2"):
        d_len = len(donor_cdrs.get(region, ""))
        t_len = len(template_cdrs.get(region, ""))
        diff = abs(d_len - t_len)
        if diff > CDR_LENGTH_TOLERANCE:
            return 0.0
        diffs.append(diff)
    return 1.0 - (sum(diffs) / (2 * CDR_LENGTH_TOLERANCE))


def _score_germline_abundance(template: TemplateRecord) -> float:
    """
    Heuristic: assume gene names containing common high-frequency families
    (VH1, VH3 in dog; VH3 in cat) get higher score. Optimized when freq
    archive is consulted directly via existing v3 combined profiles.
    """
    gene = template.gene.upper()
    # Dog: VH1 and VH3 dominant
    if template.species == "dog":
        if "IGHV1" in gene or "IGHV3" in gene:
            return 1.0
        if "IGKV3" in gene or "IGKV2" in gene:
            return 1.0
    elif template.species == "cat":
        if "IGHV3" in gene or "IGHV1" in gene:
            return 1.0
        if "IGKV1" in gene or "IGKV2" in gene:
            return 1.0
    return 0.5


# ══════════════════════════════════════════════════════════════════════════════
# Hard constraints
# ══════════════════════════════════════════════════════════════════════════════

def _check_hard_constraints(
    donor_cdrs: Optional[Dict[str, str]],
    template: TemplateRecord,
    species: str,
    locus: str,
) -> Tuple[bool, List[str]]:
    """
    Returns (passed, list_of_violations). Empty list = passed.
    """
    violations: List[str] = []

    # Species + locus check (first guard)
    if template.species != species:
        violations.append(f"species_mismatch:{template.species}≠{species}")
    if template.locus != locus:
        violations.append(f"locus_mismatch:{template.locus}≠{locus}")

    # CDR length compatibility
    if donor_cdrs:
        template_cdrs = _extract_cdrs(template.sequence_aa, template.chain)
        if template_cdrs:
            for region in ("CDR1", "CDR2"):
                diff = abs(len(donor_cdrs.get(region, "")) - len(template_cdrs.get(region, "")))
                if diff > CDR_LENGTH_TOLERANCE:
                    violations.append(f"{region}_length_diff:{diff}>{CDR_LENGTH_TOLERANCE}")

    # Template FR pI within species range
    if template.fr_concat:
        pi = _compute_pi(template.fr_concat)
        if pi is not None:
            chain_key = template.chain if template.chain == "VH" else (
                "VL_kappa" if template.locus == "IGKV" else "VL_lambda"
            )
            bounds = _SPECIES_PI_BOUNDS.get(species, {}).get(chain_key)
            if bounds and not (bounds[0] <= pi <= bounds[1]):
                violations.append(f"FR_pI_out_of_range:{pi:.2f}∉{bounds}")

    return (len(violations) == 0, violations)


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

def score_template(donor_seq: str, template: TemplateRecord, species: str) -> Dict[str, Any]:
    """
    Compute the 5-component score for one donor → template pairing.
    Returns dict with components and total_score.
    """
    chain = template.chain or "VH"
    donor_fr = _extract_frs(donor_seq, chain) or {}
    donor_cdrs = _extract_cdrs(donor_seq, chain) or {}
    template_fr = _extract_frs(template.sequence_aa, chain) or template.fr_segments
    template_cdrs = _extract_cdrs(template.sequence_aa, chain) or {}

    s_fr = _score_fr_identity(donor_fr, template_fr)
    s_cmc = _score_cmc_quality(template)
    s_pgc = _score_template_pgc(template)
    s_cdr = _score_cdr_length_match(donor_cdrs, template_cdrs)
    s_abund = _score_germline_abundance(template)

    total = (
        SCORING_WEIGHTS["fr_identity"] * s_fr
        + SCORING_WEIGHTS["cmc_quality"] * s_cmc
        + SCORING_WEIGHTS["template_pgc"] * s_pgc
        + SCORING_WEIGHTS["cdr_length_match"] * s_cdr
        + SCORING_WEIGHTS["germline_abundance"] * s_abund
    )

    return {
        "components": {
            "fr_identity": round(s_fr, 4),
            "cmc_quality": round(s_cmc, 4),
            "template_pgc": round(s_pgc, 4),
            "cdr_length_match": round(s_cdr, 4),
            "germline_abundance": round(s_abund, 4),
        },
        "weights": SCORING_WEIGHTS,
        "total_score": round(total, 4),
    }


def select_pet_template(
    donor_seq: str,
    species: str,
    locus: str,
    top_n: int = 3,
    include_failed: bool = False,
) -> Dict[str, Any]:
    """
    Select top-N templates for a donor sequence under hard constraints.

    Args:
        donor_seq: VH or VL donor sequence
        species: 'dog' or 'cat'
        locus: 'IGHV', 'IGKV', or 'IGLV'
        top_n: maximum number of passing templates to return
        include_failed: if True, also return rejected templates with violations

    Returns:
        Dict with: pool_size, n_passing, top_templates, rejected (if requested)
    """
    sp = species.lower()
    pool = load_template_pool(sp, locus)
    if not pool:
        return {
            "donor_species": sp,
            "donor_locus": locus,
            "pool_size": 0,
            "n_passing": 0,
            "top_templates": [],
            "error": f"No template pool available for {sp}/{locus}",
        }

    # Pre-compute donor CDRs once (used in hard-constraint check across all templates)
    inferred_chain = "VH" if locus == "IGHV" else "VL"
    donor_cdrs = _extract_cdrs(donor_seq, inferred_chain)

    passing: List[Dict[str, Any]] = []
    failing: List[Dict[str, Any]] = []

    for tmpl in pool:
        ok, violations = _check_hard_constraints(donor_cdrs, tmpl, sp, locus)
        record = {
            "gene": tmpl.gene,
            "tier": tmpl.tier,
            "chain": tmpl.chain,
            "locus": tmpl.locus,
            "total_flags": tmpl.total_flags,
            "sequence_aa": tmpl.sequence_aa,
        }
        if not ok:
            record["violations"] = violations
            failing.append(record)
            continue

        scoring = score_template(donor_seq, tmpl, sp)
        record["scoring"] = scoring
        record["total_score"] = scoring["total_score"]
        passing.append(record)

    passing.sort(key=lambda r: r["total_score"], reverse=True)
    top_templates = passing[:top_n]

    result: Dict[str, Any] = {
        "donor_species": sp,
        "donor_locus": locus,
        "pool_size": len(pool),
        "n_passing": len(passing),
        "n_rejected": len(failing),
        "scoring_weights": SCORING_WEIGHTS,
        "top_templates": top_templates,
    }
    if include_failed:
        result["rejected"] = failing
    return result


__all__ = [
    "select_pet_template",
    "score_template",
    "load_template_pool",
    "SCORING_WEIGHTS",
    "TemplateRecord",
]
