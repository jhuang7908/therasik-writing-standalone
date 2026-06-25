"""
cmc_metrics.py — InSynBio AbEngineCore CMC Metrics Module
==========================================================
Sequence-based CMC metric computation for VHH and scFv sequences.
Uses BioPython ProteinAnalysis as computation engine.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from Bio.SeqUtils.ProtParam import ProteinAnalysis

# Hydrophobic residues for SAP/patch calculations
_HYDRO = frozenset("AILMFWV")
_CHARGED = frozenset("KRDE")


def compute_pI(seq: str) -> float:
    return round(ProteinAnalysis(seq.upper()).isoelectric_point(), 2)


def compute_GRAVY(seq: str) -> float:
    return round(ProteinAnalysis(seq.upper()).gravy(), 3)


def compute_instability_index(seq: str) -> float:
    return round(ProteinAnalysis(seq.upper()).instability_index(), 1)


def compute_net_charge(seq: str, pH: float = 7.0) -> float:
    return round(ProteinAnalysis(seq.upper()).charge_at_pH(pH), 2)


def compute_hydro_patch_max9(seq: str) -> float:
    """Max fraction of hydrophobic residues in any 9-mer window."""
    s = seq.upper()
    if len(s) < 9:
        return round(sum(1 for a in s if a in _HYDRO) / 9.0, 3)
    return round(
        max(sum(1 for a in s[i:i+9] if a in _HYDRO) / 9.0
            for i in range(len(s) - 8)), 3
    )


def compute_charge_patch_max7(seq: str) -> float:
    """
    Max absolute net charge in any 7-mer window.
    Matches AbRef-458 reference scale (p5=2.0, p95=4.0).
    Formula: |sum(K+R+0.1*H) - sum(D+E)| per 7-mer.
    """
    s = seq.upper()
    _POS = frozenset("KR")
    _NEG = frozenset("DE")

    def _abs_net(w: str) -> float:
        pos = sum(1 for a in w if a in _POS) + 0.1 * w.count("H")
        neg = sum(1 for a in w if a in _NEG)
        return abs(pos - neg)

    if len(s) < 7:
        return round(_abs_net(s), 2)
    return round(max(_abs_net(s[i:i+7]) for i in range(len(s) - 6)), 2)


def compute_aggregation_motifs(seq: str) -> int:
    """Count windows of >=3 consecutive hydrophobic residues (agg_motifs)."""
    count = run = 0
    for aa in seq.upper():
        if aa in _HYDRO:
            run += 1
            if run >= 3:
                count += 1
        else:
            run = 0
    return count


def compute_hydro_cluster_count(seq: str) -> int:
    """Count distinct runs of >=3 consecutive hydrophobic residues."""
    count = 0
    in_run = False
    run_len = 0
    for aa in seq.upper():
        if aa in _HYDRO:
            run_len += 1
            if run_len == 3:
                count += 1
                in_run = True
        else:
            run_len = 0
            in_run = False
    return count


def compute_sap_7mer_proxy(seq: str) -> float:
    """
    Sequence-proxy SAP: max fraction of AILMFWV in any 7-mer window
    (same 7-mer definition as vhh_cmc_engine._sap_proxy; IgG Fv = VH+VL).
    """
    _h = frozenset("AILMFWV")
    s = (seq or "").upper()
    if not s:
        return 0.0
    if len(s) < 7:
        return round(sum(1 for a in s if a in _h) / 7.0, 3)
    return round(
        max(
            sum(1 for a in s[i : i + 7] if a in _h) / 7.0
            for i in range(len(s) - 6)
        ),
        3,
    )


def compute_fv_charge_asymmetry(vh_seq: str, vl_seq: str) -> float:
    """
    |q_VH - q_VL| at pH 7, each chain analyzed separately
    (standard Fv charge asymmetry proxy; lower = better).
    """
    vh = (vh_seq or "").strip().upper()
    vl = (vl_seq or "").strip().upper()
    if not vh or not vl:
        return 0.0
    try:
        pah = ProteinAnalysis(vh)
        pal = ProteinAnalysis(vl)
        ch = pah.charge_at_pH(7.0)
        cl = pal.charge_at_pH(7.0)
        return round(abs(ch - cl), 3)
    except Exception:
        return 0.0


def compute_chemical_liabilities(seq: str, vh_len: int = 0) -> Dict[str, List[int]]:
    """
    Compute positions of chemical liability sites.
    Returns 0-based positions.
    """
    s = seq.upper()
    result: Dict[str, List[int]] = {
        "glycosylation_sites": [],
        "deamidation_sites": [],
        "isomerization_sites": [],
        "oxidation_sites": [],
        "free_cys": [],
    }

    # N-glycosylation: NXS or NXT (X != P)
    for m in re.finditer(r"N[^P][ST]", s):
        result["glycosylation_sites"].append(m.start())

    # Deamidation: NG or NS (asparagine liability)
    for m in re.finditer(r"N[GS]", s):
        result["deamidation_sites"].append(m.start())

    # Isomerization: DG or DS (aspartate liability)
    for m in re.finditer(r"D[GS]", s):
        result["isomerization_sites"].append(m.start())

    # Oxidation: all M and W residues
    for i, aa in enumerate(s):
        if aa in ("M", "W"):
            result["oxidation_sites"].append(i)

    # Free Cys: all C residues (canonical disulfide filter applied upstream)
    for i, aa in enumerate(s):
        if aa == "C":
            result["free_cys"].append(i)

    return result


class CDRFingerprintEngine:
    """Extract CDR-specific physicochemical fingerprints."""

    @staticmethod
    def compute_fingerprint(vh_seq: str, vl_seq: str) -> Dict[str, Any]:
        """
        Compute CDR-specific metrics for VH and VL.
        Returns a dict of metrics (length, gravy, net_charge, aromatic_density).
        """
        from core.cmc.igg_cmc_segmentation import segment_vh_vl_imgt
        seg = segment_vh_vl_imgt(vh_seq, vl_seq)
        
        out = {}
        for chain in ["VH", "VL"]:
            c_seg = seg.get(chain, {})
            c1 = c_seg.get("CDR1", "")
            c2 = c_seg.get("CDR2", "")
            c3 = c_seg.get("CDR3", "")
            all_cdr = c1 + c2 + c3
            
            out[f"{chain.lower()}_cdr3_len"] = len(c3)
            out[f"{chain.lower()}_cdr3_gravy"] = compute_GRAVY(c3) if c3 else 0.0
            out[f"{chain.lower()}_cdr3_net_charge"] = compute_net_charge(c3) if c3 else 0.0
            
            # Aromatic density: W, F, Y
            arom = sum(1 for aa in c3 if aa in "WFY")
            out[f"{chain.lower()}_cdr3_arom_density"] = round(arom / len(c3), 3) if c3 else 0.0
            
            # Total CDR load
            out[f"{chain.lower()}_all_cdr_gravy"] = compute_GRAVY(all_cdr) if all_cdr else 0.0
            
        return out


# ─────────────────────────────────────────────────────────────────────────────
# CMCMetricEngine — unified interface used by cmc_advisor_module.py
# ─────────────────────────────────────────────────────────────────────────────

class CMCMetricEngine:
    """Compute all CMC metrics for a VH+VL pair in one call."""

    @staticmethod
    def compute_metrics(
        vh_seq: str,
        vl_seq: str,
        stored_metrics: Any = None,
        structure_path: Any = None,
    ) -> Dict[str, Any]:
        """
        Compute sequence-based CMC metrics for a VH+VL antibody.

        Reuses values from stored_metrics when provided (avoids recomputing).
        structure_path is accepted for API compatibility but not used in this
        sequence-only implementation.
        """
        import re
        stored = stored_metrics or {}
        raw_combined = (vh_seq + vl_seq).upper()
        combined = re.sub(r"[^ACDEFGHIKLMNPQRSTVWY]", "", raw_combined)

        try:
            from Bio.SeqUtils.ProtParam import ProteinAnalysis as _PA
        except ImportError:
            return {"_biopython_missing": True}

        def _get(key, default_fn):
            if key in stored:
                return stored[key]
            try:
                return default_fn()
            except Exception:
                return None

        analysis = _PA(combined) if combined else None

        pI               = _get("pI",               lambda: round(analysis.isoelectric_point(), 2))
        GRAVY            = _get("GRAVY",             lambda: round(analysis.gravy(), 3))
        instability      = _get("instability_index", lambda: round(analysis.instability_index(), 1))
        net_charge       = _get("net_charge_pH7",    lambda: round(analysis.charge_at_pH(7.0), 2))
        hydro9           = _get("hydro_patch_max9",  lambda: compute_hydro_patch_max9(combined))
        charge7          = _get("charge_patch_max7", lambda: compute_charge_patch_max7(combined))
        agg_motifs       = _get("agg_motifs",        lambda: compute_aggregation_motifs(combined))
        hydro_clusters   = _get("hydro_cluster_count", lambda: compute_hydro_cluster_count(combined))

        liabilities      = compute_chemical_liabilities(combined, vh_len=len(vh_seq))
        deam_sites       = _get("deamidation_sites",   lambda: liabilities["deamidation_sites"])
        isom_sites       = _get("isomerization_sites", lambda: liabilities["isomerization_sites"])
        glyc_sites       = _get("glycosylation_sites", lambda: liabilities["glycosylation_sites"])
        ox_sites         = _get("oxidation_sites",     lambda: liabilities["oxidation_sites"])
        free_cys_sites   = _get("free_cys",            lambda: liabilities["free_cys"])

        sap = _get(
            "SAP_score",
            lambda: compute_sap_7mer_proxy(combined),
        )
        fv_asym = _get(
            "Fv_charge_asymmetry",
            lambda: compute_fv_charge_asymmetry(vh_seq, vl_seq),
        )

        return {
            "pI":                    pI,
            "GRAVY":                 GRAVY,
            "instability_index":     instability,
            "net_charge_pH7":        net_charge,
            "hydro_patch_max9":      hydro9,
            "charge_patch_max7":     charge7,
            "SAP_score":             sap,
            "Fv_charge_asymmetry":   fv_asym,
            "agg_motifs":            agg_motifs,
            "hydro_cluster_count":   hydro_clusters,
            "deamidation_sites":     deam_sites,
            "isomerization_sites":   isom_sites,
            "glycosylation_sites":   glyc_sites,
            "oxidation_sites":       ox_sites,
            "free_cys":              free_cys_sites,
        }
