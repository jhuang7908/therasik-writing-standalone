"""
core/vaccine_design/mhc2_predictor.py
──────────────────────────────────────
MHC-II epitope prediction — IEDB API wrapper (free, online).

ACCURACY NOTICE
===============
MHC-II prediction is fundamentally harder than MHC-I:
  - No well-defined anchor positions (9-mer core shifts within 13-25mer)
  - High conformational flexibility of MHC-II peptide binding groove
  - IEDB consensus method AUC ~0.80 (vs MHCflurry Class-I AUC ~0.92)
  - Best used for ranking/prioritization, not absolute cut-offs

Prediction methods (IEDB consensus):
  - NetMHCIIpan 4.3 (requires separate license; NOT called here)
  - NN-align 2.0  (published, free)
  - SMM-align (free)
  - Sturniolo (free)
  - IEDB_recommended: consensus of available free methods

Usage
-----
    pred = MHC2Predictor()
    results = pred.predict(peptides=["PKYVKQNTLKLAT"], alleles=["HLA-DRB1*04:01"])
    for r in results:
        print(r.peptide, r.allele, r.rank_percentile, r.rank_label)

    # Batch scan a protein
    df = pred.scan_protein("MFVFLVLLPLVSSQCVNL...", allele="HLA-DRB1*04:01")

Environment: conda activate vaccine (requires internet for IEDB API calls)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
import urllib.request
import urllib.parse
import urllib.error
import json

__version__ = "1.0.0"

logger = logging.getLogger(__name__)

# ── IEDB MHC-II prediction API ───────────────────────────────────────────────
IEDB_MHCII_URL = "https://tools-cluster-interface.iedb.org/tools_api/mhcii/"

# Recommended sliding window lengths for MHC-II (15-mer is canonical core+flanks)
DEFAULT_LENGTHS = [15]

# Default allele panel covering major global HLA-DR alleles (~75% global coverage)
DEFAULT_DR_ALLELES = [
    "HLA-DRB1*04:01",  # European ~12%, RA association
    "HLA-DRB1*01:01",  # European ~12%
    "HLA-DRB1*15:01",  # European ~16%, MS association
    "HLA-DRB1*07:01",  # European ~10%
    "HLA-DRB1*11:01",  # African/Mediterranean ~10%
    "HLA-DRB1*03:01",  # European ~10%, T1D association
    "HLA-DRB1*09:01",  # East Asian ~15%
    "HLA-DRB1*12:01",  # East Asian ~8%
]

# Binding strength thresholds (IEDB percentile rank)
# Lower = stronger binder; SB < 10%, WB 10-20% (IEDB standard)
SB_THRESHOLD = 10.0   # strong binder
WB_THRESHOLD = 20.0   # weak binder


@dataclass
class MHC2Hit:
    peptide: str
    allele: str
    start: int              # 1-indexed position in input sequence
    core: str               # predicted 9-mer binding core
    rank_percentile: float  # IEDB percentile rank (lower = stronger)
    ic50_nm: float          # predicted IC50 (nM) — less reliable than rank
    rank_label: str         # SB / WB / NB


@dataclass
class MHC2ScanResult:
    sequence: str
    allele: str
    method: str
    hits: List[MHC2Hit]
    strong_binders: int
    weak_binders: int
    error: Optional[str] = None


class MHC2Predictor:
    """IEDB MHC-II epitope predictor — online API, free for research use.

    Accuracy note:
        MHCflurry 2.x currently supports MHC-I only. Until a validated
        local MHC-II predictor is available (e.g., a future MHCflurry version),
        this module uses the IEDB consensus API (PMID: 23661696).
        Expect AUC ~0.80 on independent benchmarks.
        Use for relative ranking, not absolute IC50 values.
    """

    def __init__(
        self,
        method: str = "IEDB_recommended",
        sb_threshold: float = SB_THRESHOLD,
        wb_threshold: float = WB_THRESHOLD,
        timeout_sec: int = 60,
        retry: int = 2,
    ):
        self.method = method
        self.sb_threshold = sb_threshold
        self.wb_threshold = wb_threshold
        self.timeout = timeout_sec
        self.retry = retry

    # ── single allele scan ────────────────────────────────────────────────

    def scan_protein(
        self,
        protein_seq: str,
        allele: str = "HLA-DRB1*04:01",
        length: int = 15,
    ) -> MHC2ScanResult:
        """Scan a protein sequence for MHC-II epitopes against one allele.

        Calls IEDB prediction API, returns ranked results.
        Requires internet connection.
        """
        protein_seq = protein_seq.upper().replace(" ", "").replace("\n", "")
        hits, error = self._call_iedb(protein_seq, allele, length)
        if error:
            logger.warning(f"IEDB API error for {allele}: {error}")
        return MHC2ScanResult(
            sequence=protein_seq,
            allele=allele,
            method=self.method,
            hits=sorted(hits, key=lambda h: h.rank_percentile),
            strong_binders=sum(1 for h in hits if h.rank_label == "SB"),
            weak_binders=sum(1 for h in hits if h.rank_label == "WB"),
            error=error,
        )

    # ── multi-allele panel scan ───────────────────────────────────────────

    def scan_panel(
        self,
        protein_seq: str,
        alleles: Optional[List[str]] = None,
        length: int = 15,
        top_n_per_allele: int = 10,
    ) -> List[MHC2ScanResult]:
        """Scan against a panel of DR alleles. Returns one result per allele."""
        alleles = alleles or DEFAULT_DR_ALLELES
        results = []
        for allele in alleles:
            logger.info(f"  MHC-II scan: {allele} ...")
            result = self.scan_protein(protein_seq, allele, length)
            if top_n_per_allele and result.hits:
                result.hits = result.hits[:top_n_per_allele]
            results.append(result)
            time.sleep(0.5)  # be polite to IEDB API
        return results

    # ── predict a list of peptides ────────────────────────────────────────

    def predict_peptides(
        self,
        peptides: List[str],
        allele: str = "HLA-DRB1*04:01",
    ) -> List[MHC2Hit]:
        """Predict binding for specific peptide sequences.

        Useful for checking known or designed peptides.
        """
        hits = []
        for pep in peptides:
            result_hits, err = self._call_iedb(pep, allele, len(pep))
            if err:
                logger.warning(f"IEDB API error for {pep}/{allele}: {err}")
                continue
            if result_hits:
                hits.extend(result_hits)
        return sorted(hits, key=lambda h: h.rank_percentile)

    # ── IEDB API call ─────────────────────────────────────────────────────

    def _call_iedb(
        self, seq: str, allele: str, length: int
    ) -> tuple[List[MHC2Hit], Optional[str]]:
        """POST to IEDB MHC-II prediction endpoint. Returns (hits, error_msg)."""
        data = urllib.parse.urlencode({
            "method": self.method,
            "sequence_text": seq,
            "allele": allele,
            "length": str(length),
        }).encode("utf-8")

        for attempt in range(self.retry + 1):
            try:
                req = urllib.request.Request(
                    IEDB_MHCII_URL,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode("utf-8")
                    return self._parse_response(raw, allele)
            except urllib.error.HTTPError as e:
                err = f"HTTP {e.code}: {e.reason}"
                if attempt < self.retry:
                    time.sleep(2 ** attempt)
                    continue
                return [], err
            except urllib.error.URLError as e:
                err = f"Network error: {e.reason}"
                if attempt < self.retry:
                    time.sleep(2 ** attempt)
                    continue
                return [], err
            except Exception as e:
                return [], str(e)
        return [], "max_retries_exceeded"

    def _parse_response(
        self, raw: str, allele: str
    ) -> tuple[List[MHC2Hit], Optional[str]]:
        """Parse tab-separated IEDB response into MHC2Hit list."""
        hits = []
        lines = [ln for ln in raw.strip().split("\n") if ln and not ln.startswith("allele")]
        for line in lines:
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            try:
                start = int(parts[1]) if parts[1].isdigit() else 0
                peptide = parts[4].strip()
                core = parts[5].strip() if len(parts) > 5 else peptide[:9]
                ic50 = float(parts[7]) if len(parts) > 7 else 9999.0
                rank = float(parts[8]) if len(parts) > 8 else 100.0
                rank_label = (
                    "SB" if rank < self.sb_threshold
                    else ("WB" if rank < self.wb_threshold else "NB")
                )
                hits.append(MHC2Hit(
                    peptide=peptide, allele=allele, start=start,
                    core=core, rank_percentile=round(rank, 3),
                    ic50_nm=round(ic50, 1), rank_label=rank_label,
                ))
            except (ValueError, IndexError):
                continue
        return hits, None

    # ── utility: get top binders across allele panel ──────────────────────

    def top_cross_reactive_binders(
        self,
        protein_seq: str,
        alleles: Optional[List[str]] = None,
        sb_only: bool = False,
        top_n: int = 20,
    ) -> List[dict]:
        """Return peptides that bind across ≥2 alleles (broad coverage).

        Returns list of dicts sorted by number of alleles covered descending.
        Useful for selecting MHC-II epitopes for multi-epitope vaccines.
        """
        panel_results = self.scan_panel(protein_seq, alleles)

        pep_alleles: Dict[str, list] = {}
        for result in panel_results:
            for hit in result.hits:
                if sb_only and hit.rank_label != "SB":
                    continue
                if hit.peptide not in pep_alleles:
                    pep_alleles[hit.peptide] = []
                pep_alleles[hit.peptide].append({
                    "allele": result.allele,
                    "rank_percentile": hit.rank_percentile,
                    "ic50_nm": hit.ic50_nm,
                    "rank_label": hit.rank_label,
                    "start": hit.start,
                })

        combined = [
            {
                "peptide": pep,
                "allele_count": len(alleles_data),
                "alleles": alleles_data,
                "best_rank": min(a["rank_percentile"] for a in alleles_data),
            }
            for pep, alleles_data in pep_alleles.items()
            if len(alleles_data) >= 2
        ]
        combined.sort(key=lambda x: (-x["allele_count"], x["best_rank"]))
        return combined[:top_n]
