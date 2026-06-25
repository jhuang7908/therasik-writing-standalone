"""
Naive-blood–oriented **relative** human V-gene usage priors (not allele-level genotyping).

Data: `data/germlines/population_usage/human_v_segment_relative_weights.tsv`
See `data/germlines/population_usage/README.md` for scope and limitations.

Heavy chain: fraction is P(gene | naive blood IGHV repertoire), normalised within IGHV.
Light chain: same within IGKV or IGLV; `global` = P(κ)×P(V|κ) or P(λ)×P(V|λ) using
default κ share 0.63 / λ 0.37 (literature ballpark; tunable).
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import pandas as pd

_SUITE = Path(__file__).resolve().parents[2]
_USAGE_TSV = _SUITE / "data/germlines/population_usage/human_v_segment_relative_weights.tsv"

# Ballpark naive repertoire κ:λ (adult blood); replace if you calibrate on a cohort.
KAPPA_SHARE_DEFAULT = 0.63
LAMBDA_SHARE_DEFAULT = 0.37


def v_gene_from_allele(allele: str) -> str:
    a = str(allele or "").strip()
    if not a or a.lower() in ("unknown", "nan", "none"):
        return ""
    return a.split("*")[0] if "*" in a else a


@lru_cache(maxsize=1)
def _segment_fraction_maps() -> dict[str, dict[str, float]]:
    if not _USAGE_TSV.is_file():
        return {}
    df = pd.read_csv(_USAGE_TSV, sep="\t")
    out: dict[str, dict[str, float]] = {}
    for seg, g in df.groupby("segment"):
        w = g.set_index("gene")["weight"].astype(float)
        total = float(w.sum())
        if total <= 0:
            continue
        out[str(seg)] = {str(k): float(v) / total for k, v in w.items()}
    return out


def light_segment_for_gene(gene: str) -> str:
    g = str(gene or "").strip()
    if g.startswith("IGKV"):
        return "IGKV"
    if g.startswith("IGLD"):
        return "IGLV"  # rare designation
    if g.startswith("IGLV"):
        return "IGLV"
    return ""


def population_usage_vh(gene: str) -> tuple[float, float]:
    """
    Returns (fraction_within_IGHV, rarity_neg_log10).
    Missing genes get the minimum weight in the IGHV table (rare proxy).
    """
    g = str(gene or "").strip()
    if not g:
        return float("nan"), float("nan")
    m = _segment_fraction_maps().get("IGHV", {})
    f = m.get(g)
    if f is None and m:
        f = min(m.values())
    elif f is None:
        return float("nan"), float("nan")
    r = -math.log10(f + 1e-15)
    return f, r


def population_usage_vl(
    gene: str,
    *,
    kappa_share: float = KAPPA_SHARE_DEFAULT,
    lambda_share: float = LAMBDA_SHARE_DEFAULT,
) -> tuple[float, float, float, float]:
    """
    Returns (fraction_within_locus, global_fraction_among_all_light_chains,
             rarity_neg_log10_within_locus, rarity_neg_log10_global).

    global_fraction uses κ/λ prior × conditional gene usage within locus.
    """
    g = str(gene or "").strip()
    if not g:
        return (float("nan"),) * 4
    seg = light_segment_for_gene(g)
    if seg not in ("IGKV", "IGLV"):
        return (float("nan"),) * 4
    m = _segment_fraction_maps().get(seg, {})
    f_loc = m.get(g)
    if f_loc is None and m:
        f_loc = min(m.values())
    elif f_loc is None:
        return (float("nan"),) * 4
    share = kappa_share if seg == "IGKV" else lambda_share
    f_glob = share * f_loc
    r_loc = -math.log10(f_loc + 1e-15)
    r_glob = -math.log10(f_glob + 1e-15)
    return f_loc, f_glob, r_loc, r_glob


def population_usage_reference_note() -> str:
    rel = _USAGE_TSV.relative_to(_SUITE).as_posix()
    return f"{rel}; κ={KAPPA_SHARE_DEFAULT}, λ={LAMBDA_SHARE_DEFAULT}; see population_usage/README.md"
