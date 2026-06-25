"""
mhcii_analyzer.py — InSynBio AbEngineCore v1.0
===============================================
MHC Class II immunogenicity analysis for antibody sequences.

Pipeline
--------
1. Sliding-window peptide generation
   • 15-mer windows (configurable) across the full V-region sequence.
   • Both VH and VL processed independently, then merged.

2. IEDB API prediction (online) or offline fallback
   • 27 HLA-II alleles (EXT27, ≥97% world population coverage).
   • Returns percent_rank and IC50 per (peptide × allele).

3. Peptide-allele matrix construction
   • Matrix shape: (n_peptides) × (27 alleles).
   • Cell value: percent_rank (lower = stronger binder).
   • NaN for alleles with no prediction (IEDB skips non-binding).

4. Cluster analysis (numpy only, no sklearn required)
   • Hierarchical agglomerative clustering on the peptide vectors
     using average-linkage Euclidean distance.
   • Implemented as pure numpy (no scipy dependency required).
   • Clusters label groups of peptides with similar cross-allele binding.

5. Immunogenicity scoring per cluster and per peptide
   • Allele coverage: fraction of 27 alleles with percent_rank < threshold.
   • Cluster risk:  HIGH  (≥ 4 alleles, strong binder in any),
                   MEDIUM (≥ 2 alleles),
                   LOW    (< 2 alleles or only weak binders).
   • Sequence TCIA score: sum of (strong_binders / n_alleles) across clusters.

6. Region mapping
   • Each epitope is mapped back to VH/VL and CDR/FR region.
   • CDR ranges use Kabat numbering (H1:26-35, H2:50-65, H3:95-102,
     L1:24-34, L2:50-56, L3:89-97).

Offline fallback (no IEDB / no network)
-----------------------------------------
When IEDB is unavailable, a heuristic MHC-II propensity is used:
  - Anchor positions (1, 4, 6, 9 of 9-mer core) weighted by aa binding score.
  - BLOSUM62-derived hydrophobicity for core positions.
  - Conservative estimate — use only for comparison, never for decisions.

Usage
-----
    from core.immunogenicity.mhcii_analyzer import MHCII_Analyzer

    analyzer = MHCII_Analyzer(
        vh_seq="EVQLVESGG...", vl_seq="DIQMTQSPS...",
        use_iedb=True,          # False → offline fallback
        n_clusters=5,           # number of peptide clusters
    )
    result = analyzer.run()

    print(result.tcia_score)           # float
    print(result.risk_level)           # "HIGH" / "MEDIUM" / "LOW"
    print(result.top_epitopes[:5])     # List[EpitopeHit]
    print(result.cluster_summary)      # Dict
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from core.immunogenicity.iedb_client import (
    EXT27_HLA_ALLELES,
    CORE15_HLA_ALLELES,
    IEDBError,
    IEDBPrediction,
    IEDBRequestConfig,
    predict_mhcii_binding,
)

# ── CDR Kabat boundaries (position in sequence, 0-based after Kabat numbering) ─
# Used for region annotation; applied to sequence index (not Kabat number).
# These are *approximate* residue offsets from VH/VL N-terminus for typical
# ~120 aa V-regions.  ANARCI-based numbering is more accurate but not required.
_KABAT_VH = {"FR1": (0,  25), "CDR1": (25, 35), "FR2": (35, 49),
             "CDR2": (49, 65), "FR3": (65, 94),  "CDR3": (94, 102), "FR4": (102, 113)}
_KABAT_VL = {"FR1": (0,  23), "CDR1": (23, 34),  "FR2": (34, 49),
             "CDR2": (49, 56), "FR3": (56, 88),   "CDR3": (88, 97),  "FR4": (97, 108)}


# ─────────────────────────────────────────────────────────────────────────────
# Residue property scales
# ─────────────────────────────────────────────────────────────────────────────

# Parker (1986) hydrophilicity scale (higher = more hydrophilic / surface-prone)
_PARKER_HYDROPHILICITY: Dict[str, float] = {
    "R": 3.0, "K": 3.0, "D": 3.0, "E": 3.0, "N": 0.2, "Q": 0.2,
    "S": 0.6, "T": 0.7, "H": 1.1, "Y": 0.4, "W": -3.4,
    "A": -1.6, "C": -2.0, "F": -3.7, "G": -1.0, "I": -3.1,
    "L": -2.8, "M": -3.4, "P": 0.0, "V": -2.6,
}

# ─────────────────────────────────────────────────────────────────────────────
# Result types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EpitopeHit:
    """One predicted T-cell epitope from the analysis."""
    peptide:        str
    start:          int            # 0-based offset in source sequence
    chain:          str            # "VH" or "VL"
    region:         str            # e.g. "CDR2", "FR3"
    n_alleles_hit:  int            # alleles with percent_rank < 10
    n_strong:       int            # alleles with percent_rank < 2
    best_rank:      float          # lowest percent_rank across alleles
    best_allele:    str            # allele with lowest rank
    cluster_id:     int            # cluster label (from agglomerative clustering)
    risk:           str            # "HIGH" / "MEDIUM" / "LOW"
    is_germline:    bool = False   # True if peptide exists in human germline (tolerated)
    tolerance:      float = 0.0    # Germline frequency score (0.0-1.0)
    hydrophilicity: float = 0.0    # Mean Parker hydrophilicity score


@dataclass
class MHCII_Result:
    """Full MHC-II immunogenicity result for one antibody."""
    # Input
    vh_seq:          str
    vl_seq:          str
    alleles_used:    List[str]
    method:          str           # "iedb_online" or "offline_heuristic"

    # Scores
    tcia_score:      float         # T-cell immunogenicity score (0–1)
    risk_level:      str           # "HIGH" / "MEDIUM" / "LOW"

    # Epitopes
    top_epitopes:    List[EpitopeHit]
    all_epitopes:    List[EpitopeHit]

    # Cluster analysis
    n_clusters:      int
    cluster_summary: Dict          # cluster_id → {n_peptides, risk, top_peptide}

    # Coverage
    allele_coverage:  Dict[str, float]   # allele → fraction of peptides binding

    # Flags
    flags:           List[str] = field(default_factory=list)

    # Developer audit (internal only): layered funnel counts + thresholds
    funnel_stats:    Dict[str, Any] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# Main analyzer
# ─────────────────────────────────────────────────────────────────────────────

class MHCII_Analyzer:
    """
    MHC Class II immunogenicity analyzer for antibody VH + VL sequences.

    Parameters
    ----------
    vh_seq      : VH amino-acid sequence (FASTA, no header)
    vl_seq      : VL amino-acid sequence (FASTA, no header)
    use_iedb    : If True, call IEDB API.  If False, use offline heuristic.
    allele_panel: List of HLA alleles.  Default: EXT27_HLA_ALLELES (27).
    peptide_len : Sliding window length.  Default: 15 (standard MHC-II epitope).
    n_clusters  : Target number of clusters for agglomerative clustering.
    strong_rank : Percent-rank threshold for "strong binder" (default 2.0).
    weak_rank   : Percent-rank threshold for "weak binder" (default 10.0).
    """

    def __init__(
        self,
        vh_seq:       str,
        vl_seq:       str,
        use_iedb:     bool             = True,
        allele_panel: Optional[List[str]] = None,
        peptide_len:  int              = 15,
        n_clusters:   int              = 5,
        strong_rank:  float            = 2.0,
        weak_rank:    float            = 10.0,
    ):
        self.vh_seq      = vh_seq.strip().upper()
        self.vl_seq      = vl_seq.strip().upper() if vl_seq else ""
        self.use_iedb    = use_iedb
        self.alleles     = allele_panel if allele_panel is not None else EXT27_HLA_ALLELES
        self.peptide_len = peptide_len
        self.n_clusters  = n_clusters
        self.strong_rank = strong_rank
        self.weak_rank   = weak_rank

    @staticmethod
    def analyze_sequence(seq: str, use_iedb: bool = False) -> Dict[str, Any]:
        """Convenience wrapper for single-sequence analysis (offline by default)."""
        # Split into VH/VL if possible, or treat as single chain
        # For simplicity, if no VL, we pass empty string.
        # But TCIA usually needs VH+VL.
        # Here we just run it as a single chain if it's long enough.
        analyzer = MHCII_Analyzer(vh_seq=seq, vl_seq="", use_iedb=use_iedb)
        res = analyzer.run()
        return {
            "score": res.tcia_score,
            "risk_level": res.risk_level,
            "n_high": sum(1 for e in res.all_epitopes if e.risk == "HIGH"),
            "n_medium": sum(1 for e in res.all_epitopes if e.risk == "MEDIUM"),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Public entry point
    # ──────────────────────────────────────────────────────────────────────────

    def run(self, is_vhh: bool = False) -> MHCII_Result:
        """Execute full pipeline and return MHCII_Result."""
        # Step 1: generate peptides
        vh_peptides = self._sliding_window(self.vh_seq, "VH")
        vl_peptides = self._sliding_window(self.vl_seq, "VL") if self.vl_seq else []
        all_peptides = vh_peptides + vl_peptides
        
        if not all_peptides:
            return self._empty_result("No peptides generated (sequences too short?)")
        
        # Step 2: predict binding
        preds_vh, method = self._predict(self.vh_seq, "VH")
        preds_vl, _      = self._predict(self.vl_seq, "VL") if self.vl_seq else ({}, method)
        
        # Step 3: build peptide-allele matrix
        pep_keys_vh = [p[0] for p in vh_peptides]
        pep_keys_vl = [p[0] for p in vl_peptides]
        matrix_vh, allele_idx = self._build_matrix(pep_keys_vh, preds_vh)
        matrix_vl, _          = self._build_matrix(pep_keys_vl, preds_vl)
        full_matrix = np.vstack([matrix_vh, matrix_vl]) if matrix_vl.size else matrix_vh
        
        # Step 4-7: Funnel-style analysis (layered filtering → clustering on remaining risk set)
        # 4. annotate binders (no clustering yet)
        dummy_labels = np.full(full_matrix.shape[0], -1, dtype=int)
        epitopes, ep_peptide_idx = self._annotate_epitopes(all_peptides, full_matrix, allele_idx, dummy_labels)
        
        # 5. funnel filters: FR-only → hydrophilicity → germline tolerance → risk (HIGH/MEDIUM)
        relevant_matrix_idx: List[int] = []
        for ep, midx in zip(epitopes, ep_peptide_idx):
            if (
                "FR" in ep.region
                and ep.hydrophilicity > -0.5
                and (not ep.is_germline)
                and ep.risk in ("HIGH", "MEDIUM")
            ):
                relevant_matrix_idx.append(int(midx))
        
        # 6. clustering on the remaining risk set
        label_map: Dict[int, int] = {}
        if relevant_matrix_idx:
            sub = full_matrix[relevant_matrix_idx, :]
            sub_labels = self._cluster(sub)
            for i, midx in enumerate(relevant_matrix_idx):
                label_map[int(midx)] = int(sub_labels[i])
        
        for ep, midx in zip(epitopes, ep_peptide_idx):
            ep.cluster_id = label_map.get(int(midx), -1)
        
        scored = [e for e in epitopes if e.cluster_id >= 0]
        
        # 7. score + summarise (on filtered set; audit retains full binders list)
        tcia = self._tcia_score(scored)
        risk = self._risk_level(tcia, scored)
        cluster_summary = self._summarise_clusters(epitopes)
        
        # Step 8: allele coverage
        allele_cov = self._allele_coverage(full_matrix, allele_idx)
        
        flags = ["INFO:PIPELINE_STYLE_FUNNEL_V1"] + self._flags(epitopes, tcia, is_vhh=is_vhh)

        # Developer audit: layered funnel counts (VH/VL) + key thresholds
        def _counts(xs: List[EpitopeHit]) -> Dict[str, int]:
            return {
                "total": len(xs),
                "VH": sum(1 for e in xs if e.chain == "VH"),
                "VL": sum(1 for e in xs if e.chain == "VL"),
            }

        st_all = list(epitopes)
        st_fr = [e for e in st_all if "FR" in e.region]
        st_fr_hydro = [e for e in st_fr if e.hydrophilicity > -0.5]
        st_fr_hydro_non_germ = [e for e in st_fr_hydro if not e.is_germline]
        st_fr_hydro_non_germ_risk = [e for e in st_fr_hydro_non_germ if e.risk in ("HIGH", "MEDIUM")]
        st_clustered = [e for e in st_fr_hydro_non_germ_risk if e.cluster_id >= 0]

        funnel_stats: Dict[str, Any] = {
            "thresholds": {
                "hydrophilicity_parker_gt": -0.5,
                "risk_kept": ["HIGH", "MEDIUM"],
                "region_kept": "FR*",
                "germline_policy": "exclude_is_germline_true",
            },
            "stages": [
                {"stage": "binders_any_region", **_counts(st_all)},
                {"stage": "FR_only", **_counts(st_fr)},
                {"stage": "FR_hydrophilic", **_counts(st_fr_hydro)},
                {"stage": "FR_hydrophilic_non_germline", **_counts(st_fr_hydro_non_germ)},
                {"stage": "FR_hydrophilic_non_germline_risk_hi_med", **_counts(st_fr_hydro_non_germ_risk)},
                {"stage": "clustered_bottom_set", **_counts(st_clustered)},
            ],
            "n_clusters_bottom": len(set(e.cluster_id for e in st_clustered)) if st_clustered else 0,
        }

        return MHCII_Result(
            vh_seq         = self.vh_seq,
            vl_seq         = self.vl_seq,
            alleles_used   = self.alleles,
            method         = method,
            tcia_score     = round(tcia, 4),
            risk_level     = risk,
            top_epitopes   = sorted(scored, key=lambda e: e.best_rank)[:10],
            all_epitopes   = epitopes,
            n_clusters     = len(set(label_map.values())) if label_map else 0,
            cluster_summary= cluster_summary,
            allele_coverage= allele_cov,
            flags          = flags,
            funnel_stats   = funnel_stats,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Step 1: sliding window
    # ──────────────────────────────────────────────────────────────────────────

    def _sliding_window(self, seq: str, chain: str) -> List[Tuple[str, int, str, str]]:
        """
        Returns list of (peptide, start, chain, region) tuples.
        """
        kabat = _KABAT_VH if chain == "VH" else _KABAT_VL
        results = []
        for i in range(len(seq) - self.peptide_len + 1):
            pep = seq[i: i + self.peptide_len]
            region = _region_of(i, kabat)
            results.append((pep, i, chain, region))
        return results

    # ──────────────────────────────────────────────────────────────────────────
    # Step 2: predict
    # ──────────────────────────────────────────────────────────────────────────

    def _predict(self, seq: str, chain: str) -> Tuple[Dict[str, List[IEDBPrediction]], str]:
        """
        Returns ({peptide: [IEDBPrediction]}, method_string).
        """
        if not seq:
            return {}, "offline_heuristic"

        if self.use_iedb:
            try:
                preds = predict_mhcii_binding(
                    seq, self.alleles,
                    IEDBRequestConfig(method="recommended", length=str(self.peptide_len))
                )
                by_peptide: Dict[str, List[IEDBPrediction]] = {}
                for p in preds:
                    by_peptide.setdefault(p.peptide, []).append(p)
                return by_peptide, "iedb_online"
            except IEDBError as e:
                warnings.warn(f"[IEDB] {chain} prediction failed: {e}. Falling back to offline.")

        # Offline heuristic
        by_peptide = {}
        for i in range(len(seq) - self.peptide_len + 1):
            pep = seq[i: i + self.peptide_len]
            fake_preds = _offline_heuristic_preds(pep, self.alleles, i)
            by_peptide[pep] = fake_preds
        return by_peptide, "offline_heuristic"

    # ──────────────────────────────────────────────────────────────────────────
    # Step 3: matrix
    # ──────────────────────────────────────────────────────────────────────────

    def _build_matrix(
        self,
        peptide_keys: List[str],
        preds: Dict[str, List[IEDBPrediction]],
    ) -> Tuple[np.ndarray, Dict[str, int]]:
        """
        Returns matrix (n_pep × n_allele), allele→col index.
        Missing values filled with 100.0 (no binding).
        """
        allele_idx = {a: i for i, a in enumerate(self.alleles)}
        n = len(peptide_keys)
        k = len(self.alleles)
        mat = np.full((n, k), 100.0)  # default: no binding (100% rank)

        for row, pep in enumerate(peptide_keys):
            for pred in preds.get(pep, []):
                col = allele_idx.get(pred.allele)
                if col is not None:
                    mat[row, col] = min(mat[row, col], pred.percent_rank)

        return mat, allele_idx

    # ──────────────────────────────────────────────────────────────────────────
    # Step 4: cluster (pure numpy, no sklearn)
    # ──────────────────────────────────────────────────────────────────────────

    def _cluster(self, matrix: np.ndarray) -> np.ndarray:
        """
        Agglomerative clustering (average linkage) using pure numpy.
        Returns cluster label array of shape (n_peptides,).
        Falls back to single cluster if matrix is too small.
        """
        n = matrix.shape[0]
        k = min(self.n_clusters, n)
        if k <= 1 or n <= k:
            return np.zeros(n, dtype=int)

        # Replace NaN / very large values with 100 for distance computation
        mat = np.where(np.isnan(matrix), 100.0, matrix)

        # Compute pairwise Euclidean distance matrix
        # D[i,j] = Euclidean distance between row i and row j
        diff = mat[:, None, :] - mat[None, :, :]   # (n, n, k)
        D = np.sqrt((diff ** 2).sum(axis=2))        # (n, n)

        # Average-linkage agglomerative clustering
        labels = np.arange(n)
        cluster_members: Dict[int, List[int]] = {i: [i] for i in range(n)}
        cluster_dists = D.copy().astype(float)
        np.fill_diagonal(cluster_dists, np.inf)

        n_clusters_now = n
        merge_history: List[Tuple[int, int]] = []

        while n_clusters_now > k:
            # Find closest pair
            idx = np.unravel_index(np.argmin(cluster_dists), cluster_dists.shape)
            ci, cj = int(idx[0]), int(idx[1])
            if ci == cj:
                break
            # Merge cj → ci
            merged = cluster_members[ci] + cluster_members[cj]
            cluster_members[ci] = merged
            # Update distances (average linkage)
            for cx in list(cluster_members.keys()):
                if cx == ci or cx == cj:
                    continue
                members_cx = cluster_members[cx]
                avg_d = np.mean([D[a, b] for a in merged for b in members_cx])
                cluster_dists[ci, cx] = avg_d
                cluster_dists[cx, ci] = avg_d
            # Remove cj
            cluster_dists[cj, :] = np.inf
            cluster_dists[:, cj] = np.inf
            del cluster_members[cj]
            n_clusters_now -= 1
            merge_history.append((ci, cj))

        # Assign final labels
        final_labels = np.full(n, -1, dtype=int)
        for label_id, (cid, members) in enumerate(cluster_members.items()):
            for m in members:
                final_labels[m] = label_id

        return final_labels

    # ──────────────────────────────────────────────────────────────────────────
    # Step 5: annotate epitopes
    # ──────────────────────────────────────────────────────────────────────────

    def _annotate_epitopes(
        self,
        all_peptides:  List[Tuple[str, int, str, str]],
        matrix:        np.ndarray,
        allele_idx:    Dict[str, int],
        labels:        np.ndarray,
    ) -> Tuple[List[EpitopeHit], List[int]]:
        # Initialize germline filter
        from core.immunogenicity.germline_filter import GermlineFilter
        gf = GermlineFilter()

        hits = []
        idxs: List[int] = []
        for i, (pep, start, chain, region) in enumerate(all_peptides):
            row = matrix[i]
            strong = int(np.sum(row < self.strong_rank))
            weak   = int(np.sum(row < self.weak_rank))
            if weak == 0:
                continue   # skip non-binders entirely
            
            # Germline check
            is_germline = gf.is_germline(pep)
            tolerance = gf.get_tolerance_score(pep)
            
            # Hydrophilicity check
            # Mean Parker score > 1.0 implies exposed/hydrophilic surface
            # We only cluster/flag if it is hydrophilic (surface exposed)
            hydro_score = sum(_PARKER_HYDROPHILICITY.get(aa, 0.0) for aa in pep) / len(pep)
            
            best_rank = float(np.min(row))
            best_col  = int(np.argmin(row))
            best_allele = self.alleles[best_col] if best_col < len(self.alleles) else ""

            risk = "LOW"
            if strong >= 4:
                risk = "HIGH"
            elif strong >= 2 or weak >= 6:
                risk = "MEDIUM"
            
            # Downgrade risk if hydrophobic (buried)
            # If hydro_score < -0.5, it's likely buried and not accessible to BCR/MHC processing in the same way?
            # Actually, MHC-II processing involves degradation, so buried residues ARE presented.
            # BUT the user asked: "..."
            # This implies we should IGNORE hydrophobic/buried peptides for the *clustering* analysis?
            # Or maybe they mean B-cell epitopes?
            # "MHC II..." is scientifically debatable (MHC sees processed peptides).
            # But I will follow the instruction: filter for hydrophilicity.
            # Let's say we only keep "surface-prone" peptides for the high-risk set.
            # Threshold: Parker > -0.5 (neutral to hydrophilic).
            
            hits.append(EpitopeHit(
                peptide       = pep,
                start         = start,
                chain         = chain,
                region        = region,
                n_alleles_hit = weak,
                n_strong      = strong,
                best_rank     = best_rank,
                best_allele   = best_allele,
                cluster_id    = int(labels[i]),
                risk          = risk,
                is_germline   = is_germline,
                tolerance     = tolerance,
                hydrophilicity= hydro_score, # New field
            ))
            idxs.append(i)
        return hits, idxs

    # ──────────────────────────────────────────────────────────────────────────
    # Step 6: TCIA score
    # ──────────────────────────────────────────────────────────────────────────

    def _tcia_score(self, epitopes: List[EpitopeHit]) -> float:
        """
        T-Cell Immunogenicity Assessment (TCIA) score, 0–1.
        Ignores peptides marked as is_germline (tolerated).
        """
        # Filter out germline peptides for scoring
        non_germline = [e for e in epitopes if not e.is_germline]
        
        if not non_germline:
            return 0.0
            
        n_alleles = len(self.alleles)
        scores = [e.n_alleles_hit / n_alleles for e in non_germline]
        # Weight HIGH-risk epitopes more
        weights = [3.0 if e.risk == "HIGH" else 2.0 if e.risk == "MEDIUM" else 1.0
                   for e in non_germline]
        return sum(s * w for s, w in zip(scores, weights)) / sum(weights)

    def _risk_level(self, tcia: float, epitopes: List[EpitopeHit]) -> str:
        # Only count non-germline epitopes for risk assessment
        non_germline = [e for e in epitopes if not e.is_germline]
        
        n_high = sum(1 for e in non_germline if e.risk == "HIGH")
        if tcia >= 0.15 or n_high >= 3:
            return "HIGH"
        elif tcia >= 0.05 or n_high >= 1:
            return "MEDIUM"
        else:
            return "LOW"

    # ──────────────────────────────────────────────────────────────────────────
    # Step 7: cluster summary
    # ──────────────────────────────────────────────────────────────────────────

    def _summarise_clusters(self, epitopes: List[EpitopeHit]) -> Dict:
        summary: Dict[int, Dict] = {}
        # Filter for clustering summary:
        # 1. FR only (ignore CDR)
        # 2. Strong binders (risk != LOW)
        # 3. Not germline (tolerated)
        # 4. Hydrophilic (surface)
        
        relevant_epitopes = [
            e for e in epitopes 
            if "FR" in e.region 
            and e.risk in ("HIGH", "MEDIUM")
            and not e.is_germline
            and e.hydrophilicity > -0.5  # Only surface-prone
        ]
        
        # We only summarize clusters that contain at least one "relevant" epitope
        relevant_clusters = set(e.cluster_id for e in relevant_epitopes)
        relevant_set = set(id(e) for e in relevant_epitopes)
        
        for ep in epitopes:
            cid = ep.cluster_id
            if cid not in relevant_clusters:
                continue
                
            if cid not in summary:
                summary[cid] = {"n_peptides": 0, "high": 0, "medium": 0, "low": 0,
                                  "top_peptide": ep.peptide, "top_rank": ep.best_rank,
                                  "top_allele": ep.best_allele, "top_region": ep.region,
                                  # Developer-friendly spans: where this cluster sits in VH/VL (1-based positions)
                                  "span_by_chain": {},
                                  "regions": {},
                                }
            summary[cid]["n_peptides"] += 1
            summary[cid][ep.risk.lower()] += 1
            if ep.best_rank < summary[cid]["top_rank"]:
                summary[cid].update(top_peptide=ep.peptide, top_rank=ep.best_rank,
                                     top_allele=ep.best_allele, top_region=ep.region)

            # Span/region bookkeeping only for the funnel-bottom relevant set
            if id(ep) in relevant_set:
                start1 = int(ep.start) + 1
                end1 = int(ep.start) + len(ep.peptide)
                byc = summary[cid].get("span_by_chain") or {}
                if ep.chain not in byc:
                    byc[ep.chain] = {"start_1based_min": start1, "end_1based_max": end1}
                else:
                    byc[ep.chain]["start_1based_min"] = min(int(byc[ep.chain]["start_1based_min"]), start1)
                    byc[ep.chain]["end_1based_max"] = max(int(byc[ep.chain]["end_1based_max"]), end1)
                summary[cid]["span_by_chain"] = byc

                regs = summary[cid].get("regions") or {}
                regs[ep.region] = int(regs.get(ep.region, 0)) + 1
                summary[cid]["regions"] = regs
        for cid in summary:
            d = summary[cid]
            if d["high"] >= 2:
                d["cluster_risk"] = "HIGH"
            elif d["high"] >= 1 or d["medium"] >= 2:
                d["cluster_risk"] = "MEDIUM"
            else:
                d["cluster_risk"] = "LOW"
        return summary

    # ──────────────────────────────────────────────────────────────────────────
    # Step 8: allele coverage
    # ──────────────────────────────────────────────────────────────────────────

    def _allele_coverage(
        self,
        matrix:    np.ndarray,
        allele_idx: Dict[str, int],
    ) -> Dict[str, float]:
        """
        For each HLA allele, fraction of all 15-mer peptides that bind
        (percent_rank < weak_rank threshold = 10%).
        """
        coverage = {}
        n = matrix.shape[0]
        if n == 0:
            return coverage
        for allele, col in allele_idx.items():
            frac = float(np.mean(matrix[:, col] < self.weak_rank))
            coverage[allele] = round(frac, 4)
        return coverage

    # ──────────────────────────────────────────────────────────────────────────
    # Flags
    # ──────────────────────────────────────────────────────────────────────────

    def _flags(self, epitopes: List[EpitopeHit], tcia: float, is_vhh: bool = False) -> List[str]:
        flags = []
        # Filter out germline (tolerated) epitopes for flagging
        non_germline = [e for e in epitopes if not e.is_germline]
        
        # Only check FR regions for high risk (ignore CDRs per user request)
        # AND only check hydrophilic (surface) regions
        fr_high = []
        for e in non_germline:
            if e.risk != "HIGH" or "FR" not in e.region or e.hydrophilicity <= -0.5:
                continue
            
            # VHH Hallmark exemption (Kabat 44, 45, 47)
            if is_vhh:
                # 15-mer window starting at 'start' covers positions [start, start+14]
                # Hallmark positions in VH 0-based Kabat approximate: 44->43, 45->44, 47->46
                # NOTE: These are approximate offsets. Accurate mapping requires ANARCI.
                # However, hallmark sites are always in FR2.
                hallmark_indices = {43, 44, 46} 
                window_indices = set(range(e.start, e.start + 15))
                if e.chain == "VH" and (window_indices & hallmark_indices):
                    continue
            
            fr_high.append(e)
        
        if fr_high:
            label = "AUDIT" if is_vhh else "WARN"
            msg = "stability-induced engineering sites" if is_vhh else "high-risk neo-epitopes"
            flags.append(
                f"{label}:HIGH_RISK_FR_EPITOPE — {len(fr_high)} {msg} in hydrophilic FR."
            )

        if tcia < 0.02:
            flags.append("INFO:LOW_TCIA — Sequence has low predicted T-cell immunogenicity.")
        
        # Only check broad binders in FR
        broad_fr = []
        for e in non_germline:
            if e.n_alleles_hit < 15 or "FR" not in e.region or e.hydrophilicity <= -0.5:
                continue
                
            # VHH Hallmark exemption for broad binders too
            if is_vhh:
                hallmark_indices = {43, 44, 46}
                window_indices = set(range(e.start, e.start + 15))
                if e.chain == "VH" and (window_indices & hallmark_indices):
                    continue
            broad_fr.append(e)

        if broad_fr:
            label = "AUDIT" if is_vhh else "WARN"
            msg = "stability-induced broad binders" if is_vhh else "neo-peptides"
            flags.append(
                f"{label}:BROAD_BINDER_FR — {len(broad_fr)} {msg} in hydrophilic FR bind ≥15/27 alleles."
            )
            
        # Add info about tolerated epitopes
        n_tolerated = sum(1 for e in epitopes if e.is_germline and e.risk in ("HIGH", "MEDIUM"))
        if n_tolerated > 0:
            flags.append(f"INFO:TOLERATED_EPITOPES — {n_tolerated} strong binders identified as human germline (ignored in risk score).")
            
        return flags

    # ──────────────────────────────────────────────────────────────────────────
    # Error result
    # ──────────────────────────────────────────────────────────────────────────

    def _empty_result(self, reason: str) -> MHCII_Result:
        return MHCII_Result(
            vh_seq=self.vh_seq, vl_seq=self.vl_seq,
            alleles_used=self.alleles, method="none",
            tcia_score=0.0, risk_level="UNKNOWN",
            top_epitopes=[], all_epitopes=[],
            n_clusters=0, cluster_summary={}, allele_coverage={},
            flags=[f"ERROR:{reason}"],
            funnel_stats={"error": reason, "stages": []},
        )


# ─────────────────────────────────────────────────────────────────────────────
# Offline heuristic (no IEDB)
# ─────────────────────────────────────────────────────────────────────────────

# MHC-II binding groove: positions 1, 4, 6, 9 of 9-mer core are "anchor"
# We use a simple hydrophobicity score at core anchor positions as proxy.
# Reference: Rammensee et al. (1999) Immunogenetics.
_MHC2_HYDRO = {
    "A": 1.8,  "V": 4.2,  "I": 4.5,  "L": 3.8,  "M": 1.9,
    "F": 2.8,  "W": -0.9, "P": -1.6, "G": -0.4, "S": -0.8,
    "T": -0.7, "C": 2.5,  "Y": -1.3, "H": -3.2, "D": -3.5,
    "E": -3.5, "N": -3.5, "Q": -3.5, "K": -3.9, "R": -4.5,
}
_ANCHOR = [0, 3, 5, 8]   # 0-based positions in 9-mer core


def _offline_heuristic_preds(
    peptide: str,
    alleles:  List[str],
    start:    int,
) -> List[IEDBPrediction]:
    """
    Fast offline MHC-II binding heuristic.
    Uses hydrophobicity at anchor positions of sliding 9-mer cores.
    Returns IEDBPrediction with synthetic percent_rank.
    This is a conservative screen only — not a validated predictor.
    """
    from core.immunogenicity.iedb_client import IEDBPrediction

    scores = []
    for j in range(len(peptide) - 8):
        core = peptide[j: j + 9]
        score = sum(_MHC2_HYDRO.get(core[a], 0.0) for a in _ANCHOR)
        scores.append(score)

    if not scores:
        return []

    best_score = max(scores)
    # Convert: higher hydrophobicity → lower percent_rank (better binder)
    # Empirical calibration: score 8.0 → rank ~1%, score 0 → rank ~50%
    raw_rank = max(1.0, 50.0 - best_score * 6.0)
    rank_noise = 5.0   # allele variability placeholder

    preds = []
    for i, allele in enumerate(alleles):
        # Add pseudo-allele variation
        allele_rank = raw_rank + (i % 5) * rank_noise - 2.0 * rank_noise
        allele_rank = max(0.1, min(100.0, allele_rank))
        preds.append(IEDBPrediction(
            allele       = allele,
            start        = start + 1,
            end          = start + len(peptide),
            peptide      = peptide,
            percent_rank = round(allele_rank, 2),
            ic50         = round(math.exp(math.log(50000) * allele_rank / 100), 1),
            raw          = {"source": "offline_heuristic"},
        ))
    return preds


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _region_of(position: int, kabat: Dict[str, Tuple[int, int]]) -> str:
    for region, (lo, hi) in kabat.items():
        if lo <= position < hi:
            return region
    return "FR4" if position >= max(hi for _, (_, hi) in kabat.items()) else "unknown"
