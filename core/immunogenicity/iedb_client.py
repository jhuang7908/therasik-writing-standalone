"""
iedb_client.py — InSynBio AbEngineCore v1.0
============================================
IEDB Tools API client.  Canonical location for all IEDB I/O.

Endpoints used
--------------
  MHC-II binding:  https://tools-cluster-interface.iedb.org/tools_api/mhcii/
  MHC-I  binding:  https://tools-cluster-interface.iedb.org/tools_api/mhci/

Notes
-----
- Requires the `requests` library (already in requirements.txt).
- Network timeout is 120 s per request (configurable).
- On HTTP error or network failure, raises IEDBError.
- On IEDB server-side rate limit or maintenance, callers should implement
  their own retry/backoff.

HLA-II Panels shipped with this module
---------------------------------------
  CORE15_HLA_ALLELES  — 15 alleles, ~90% world coverage, faster
  EXT27_HLA_ALLELES   — 27 alleles, ≥97% world coverage (default)

See: Sidney et al. (2008) Immunome Research, and
     Wang et al. (2010) BMC Bioinformatics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ── Optional dependency ───────────────────────────────────────────────────────
try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

IEDB_BASE = "https://tools-cluster-interface.iedb.org/tools_api"


# ─────────────────────────────────────────────────────────────────────────────
# HLA Class II allele panels
# ─────────────────────────────────────────────────────────────────────────────

# 15-allele core panel (~90% world population coverage)
CORE15_HLA_ALLELES: List[str] = [
    "HLA-DRB1*01:01", "HLA-DRB1*03:01", "HLA-DRB1*04:01",
    "HLA-DRB1*07:01", "HLA-DRB1*08:02", "HLA-DRB1*09:01",
    "HLA-DRB1*10:01", "HLA-DRB1*11:01", "HLA-DRB1*12:01",
    "HLA-DRB1*13:01", "HLA-DRB1*14:01", "HLA-DRB1*15:01",
    "HLA-DRB1*16:01", "HLA-DRB3*02:02", "HLA-DRB5*01:01",
]

# 27-allele extended panel (≥97% world population coverage, recommended)
EXT27_HLA_ALLELES: List[str] = [
    "HLA-DRB1*01:01", "HLA-DRB1*01:02",
    "HLA-DRB1*03:01", "HLA-DRB1*03:02",
    "HLA-DRB1*04:01", "HLA-DRB1*04:02", "HLA-DRB1*04:04", "HLA-DRB1*04:05",
    "HLA-DRB1*07:01",
    "HLA-DRB1*08:01", "HLA-DRB1*08:02",
    "HLA-DRB1*09:01", "HLA-DRB1*10:01",
    "HLA-DRB1*11:01", "HLA-DRB1*12:01",
    "HLA-DRB1*13:01", "HLA-DRB1*13:02",
    "HLA-DRB1*14:01", "HLA-DRB1*14:04",
    "HLA-DRB1*15:01", "HLA-DRB1*15:02",
    "HLA-DRB1*16:01",
    "HLA-DRB3*01:01", "HLA-DRB3*02:02",
    "HLA-DRB4*01:01",
    "HLA-DRB5*01:01", "HLA-DRB5*02:02",
]

DEFAULT_HLA_ALLELES = EXT27_HLA_ALLELES


# ─────────────────────────────────────────────────────────────────────────────
# Public types
# ─────────────────────────────────────────────────────────────────────────────

class IEDBError(RuntimeError):
    """Raised on any IEDB API failure (network, HTTP status, parse)."""


@dataclass
class IEDBRequestConfig:
    """
    Parameters forwarded to IEDB API.

    Attributes
    ----------
    method:   Prediction method. "recommended" → NetMHCIIpan EL 4.1 (MHC-II)
              or NetMHCpan EL 4.1 (MHC-I).
    length:   Peptide length(s). MHC-II: "15" or "11,12,13,14,15".
              MHC-I: "8,9,10". Use "asis" to disable sliding-window.
    species:  Human / mouse etc. (MHC-I only).
    timeout:  HTTP timeout in seconds.
    """
    method:  str           = "recommended"
    length:  Optional[str] = "15"
    species: Optional[str] = None
    timeout: int           = 120


@dataclass
class IEDBPrediction:
    """
    One row from the IEDB TSV response, normalised.

    All numeric fields are stored as float (NaN if parse fails).
    Raw dict is preserved in `raw`.
    """
    allele:       str
    start:        int
    end:          int
    peptide:      str
    percent_rank: float   # %-rank; < 2 = strong binder, < 10 = weak binder
    ic50:         float   # nM; < 50 = strong, < 500 = weak
    raw:          Dict    = field(default_factory=dict, repr=False)

    @property
    def is_strong_binder(self) -> bool:
        return self.percent_rank < 2.0 or self.ic50 < 50.0

    @property
    def is_weak_binder(self) -> bool:
        return (2.0 <= self.percent_rank < 10.0) or (50.0 <= self.ic50 < 500.0)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_tsv(text: str) -> List[Dict[str, str]]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    header = lines[0].split("\t")
    rows = []
    for ln in lines[1:]:
        cols = ln.split("\t")
        if len(cols) != len(header):
            continue
        rows.append(dict(zip(header, cols)))
    return rows


def _safe_float(value: str, default: float = float("nan")) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _normalise_rows(rows: List[Dict[str, str]]) -> List[IEDBPrediction]:
    """Convert raw TSV dicts → IEDBPrediction objects."""
    preds = []
    for row in rows:
        # IEDB field names vary slightly between API versions; try several keys
        allele  = row.get("allele",  row.get("hla",     ""))
        start   = int(row.get("start", row.get("pos", 1)))
        end     = int(row.get("end",   start + 14))
        peptide = row.get("peptide", row.get("seq", ""))
        rank    = _safe_float(row.get("rank",         row.get("percentile_rank", "999")))
        ic50    = _safe_float(row.get("ic50",         row.get("affinity",        "99999")))
        preds.append(IEDBPrediction(allele, start, end, peptide, rank, ic50, row))
    return preds


def _post_iedb(endpoint: str, data: Dict[str, str], timeout: int = 120) -> List[Dict[str, str]]:
    if not _HAS_REQUESTS:
        raise IEDBError("requests library is not installed. Run: pip install requests")
    url = f"{IEDB_BASE}/{endpoint.strip('/')}/"
    try:
        resp = requests.post(url, data=data, timeout=timeout)
    except Exception as e:
        raise IEDBError(f"Network error contacting IEDB: {e}") from e
    if resp.status_code != 200:
        raise IEDBError(
            f"IEDB returned HTTP {resp.status_code}\n"
            f"Response: {resp.text[:500]}"
        )
    return _parse_tsv(resp.text)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def predict_mhcii_binding(
    sequence: str,
    alleles:  List[str],
    config:   Optional[IEDBRequestConfig] = None,
) -> List[IEDBPrediction]:
    """
    MHC-II binding prediction via IEDB API.

    Parameters
    ----------
    sequence : Full VH or VL amino-acid sequence (or any protein sequence).
    alleles  : List of HLA-II alleles, e.g. EXT27_HLA_ALLELES.
    config   : IEDBRequestConfig (default: method=recommended, length=15).

    Returns
    -------
    List[IEDBPrediction], sorted by percent_rank ascending.

    Usage
    -----
    >>> from core.immunogenicity.iedb_client import predict_mhcii_binding, EXT27_HLA_ALLELES
    >>> preds = predict_mhcii_binding("EVQLVESGG...", EXT27_HLA_ALLELES)
    >>> strong = [p for p in preds if p.is_strong_binder]
    """
    if config is None:
        config = IEDBRequestConfig()
    data: Dict[str, str] = {
        "sequence_text": sequence,
        "method":        config.method or "recommended",
        "allele":        ",".join(alleles),
    }
    if config.length:
        data["length"] = config.length
    rows = _post_iedb("mhcii", data, timeout=config.timeout)
    preds = _normalise_rows(rows)
    return sorted(preds, key=lambda p: p.percent_rank)


def predict_mhci_binding(
    sequence: str,
    alleles:  List[str],
    config:   Optional[IEDBRequestConfig] = None,
) -> List[IEDBPrediction]:
    """
    MHC-I binding prediction via IEDB API.    For antibody immunogenicity, Class II (predict_mhcii_binding) is the
    primary concern.  This endpoint is provided for completeness and for
    CD8+ T-cell escape studies.
    """
    if config is None:
        config = IEDBRequestConfig(length="8,9,10")
    data: Dict[str, str] = {
        "sequence_text": sequence,
        "method":        config.method or "recommended",
        "allele":        ",".join(alleles),
    }
    if config.length:
        data["length"] = config.length
    if config.species:
        data["species"] = config.species
    rows = _post_iedb("mhci", data, timeout=config.timeout)
    preds = _normalise_rows(rows)
    return sorted(preds, key=lambda p: p.percent_rank)