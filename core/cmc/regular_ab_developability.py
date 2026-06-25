"""
Regular antibody developability layer.

Client-facing output is intentionally result-oriented: values, reference
position, risk level, and engineering action. Internal calculation details are
kept out of the response.
"""
from __future__ import annotations

import json
import csv
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from core.cmc.adi_score import adi_interpretation, compute_adi
from core.cmc.cmc_metrics import CDRFingerprintEngine

ROOT = Path(__file__).resolve().parents[2]
NATURAL_REF = ROOT / "data" / "reference" / "Natural384_IgG_stats_v1.json"
ENGINEERED_REF = ROOT / "data" / "reference" / "AbRef458_27m_stats_v1.json"
# CDR Fingerprint references
CDR_FP_REF_VHVL = ROOT / "data" / "reference" / "CDR_physchem_AbRef458_v1.json"
CDR_FP_REF_VHH = ROOT / "data" / "reference" / "CDR_physchem_VHH71_v1.json"
# Natural Baseline stratified subsets (discovery_platform within genetically_human natural cohort).
NATURAL384_SUBSET_TRANSGENIC = ROOT / "data" / "reference" / "Natural384_subset_transgenic_animal_stats_v1.json"
NATURAL384_SUBSET_PHAGE = ROOT / "data" / "reference" / "Natural384_subset_phage_display_stats_v1.json"
NATURAL384_SUBSET_BCELL = ROOT / "data" / "reference" / "Natural384_subset_human_b_cell_derived_stats_v1.json"
CLINICAL_ATLAS = ROOT / "data" / "clinical_kb" / "Antibody_Atlas_1142_Aggregated.json"
NATURAL_ATLAS = ROOT / "data" / "natural_380_atlas" / "master_table.csv"
ENGINEERED_ATLAS = ROOT / "data" / "engineered_459_atlas" / "master_table.csv"

AA20 = frozenset("ACDEFGHIKLMNPQRSTVWY")

PARAMETER_SET_25: List[Dict[str, str]] = [
    {"key": "pI", "label": "pI", "domain": "physicochemical"},
    {"key": "GRAVY", "label": "GRAVY", "domain": "physicochemical"},
    {"key": "instability_index", "label": "Instability index", "domain": "physicochemical"},
    {"key": "net_charge_pH7", "label": "Net charge at pH 7", "domain": "physicochemical"},
    {"key": "charge_patch_max7", "label": "Charge patch", "domain": "physicochemical"},
    {"key": "Fv_charge_asymmetry", "label": "VH/VL charge asymmetry", "domain": "physicochemical"},
    {"key": "hydro_patch_max9", "label": "Hydrophobic patch", "domain": "physicochemical"},
    {"key": "SAP_score", "label": "Surface hydrophobicity risk", "domain": "physicochemical"},
    {"key": "agg_motifs", "label": "Aggregation motifs", "domain": "physicochemical"},
    {"key": "hydro_cluster_count", "label": "Hydrophobic cluster count", "domain": "physicochemical"},
    {"key": "glycosylation_sites", "label": "Glycosylation sites", "domain": "cdr_fingerprint"},
    {"key": "deamidation_sites", "label": "Deamidation sites", "domain": "cdr_fingerprint"},
    {"key": "isomerization_sites", "label": "Isomerization sites", "domain": "cdr_fingerprint"},
    {"key": "oxidation_sites", "label": "Oxidation sites", "domain": "cdr_fingerprint"},
    {"key": "free_cys", "label": "Free cysteine", "domain": "physicochemical"},
    {"key": "total_cdr_length", "label": "Total CDR length", "domain": "cdr_fingerprint"},
    {"key": "vh_cdr3_len", "label": "VH CDR3 length", "domain": "cdr_fingerprint"},
    {"key": "vl_cdr3_len", "label": "VL CDR3 length", "domain": "cdr_fingerprint"},
    {"key": "vh_cdr3_gravy", "label": "VH CDR3 GRAVY", "domain": "cdr_fingerprint"},
    {"key": "vl_cdr3_gravy", "label": "VL CDR3 GRAVY", "domain": "cdr_fingerprint"},
    {"key": "vh_cdr3_net_charge", "label": "VH CDR3 net charge", "domain": "cdr_fingerprint"},
    {"key": "vl_cdr3_net_charge", "label": "VL CDR3 net charge", "domain": "cdr_fingerprint"},
    {"key": "vh_cdr3_arom_density", "label": "VH CDR3 aromatic density", "domain": "cdr_fingerprint"},
    {"key": "vl_cdr3_arom_density", "label": "VL CDR3 aromatic density", "domain": "cdr_fingerprint"},
    {"key": "vh_all_cdr_gravy", "label": "VH Total CDR GRAVY", "domain": "cdr_fingerprint"},
    {"key": "vl_all_cdr_gravy", "label": "VL Total CDR GRAVY", "domain": "cdr_fingerprint"},
    {"key": "psh", "label": "Surface hydrophobic patch profile", "domain": "physicochemical"},
    {"key": "ppc", "label": "Positive charge patch profile", "domain": "physicochemical"},
    {"key": "pnc", "label": "Negative charge patch profile", "domain": "physicochemical"},
    {"key": "sfvcsp", "label": "Fv charge symmetry profile", "domain": "physicochemical"},
    {"key": "vh_vl_angle_deg", "label": "VH/VL orientation", "domain": "physicochemical"},
    {"key": "interface_n_pairs", "label": "VH/VL interface contacts", "domain": "physicochemical"},
    {"key": "interface_mean_dist_A", "label": "Mean interface distance", "domain": "physicochemical"},
    {"key": "interface_min_dist_A", "label": "Minimum interface distance", "domain": "physicochemical"},
    {"key": "vernier_sasa_total", "label": "Vernier exposure profile", "domain": "physicochemical"},
]

DESCRIPTIVE_PARAMETERS = [
    {"key": "antibody_origin", "label": "Antibody origin"},
    {"key": "format_class", "label": "Format class"},
]

LOWER_IS_BETTER = {
    "SAP_score",
    "Fv_charge_asymmetry",
    "agg_motifs",
    "hydro_cluster_count",
    "glycosylation_sites",
    "deamidation_sites",
    "isomerization_sites",
    "oxidation_sites",
    "free_cys",
    "psh",
    "ppc",
    "pnc",
    "sfvcsp",
    "vernier_sasa_total",
    "vh_cdr3_arom_density",
    "vl_cdr3_arom_density",
}

HARD_FAIL_PARAMETERS = {
    "free_cys",
    "glycosylation_sites",
    "SAP_score",
    "hydro_patch_max9",
    "psh",
    "ppc",
    "pnc",
    "Fv_charge_asymmetry",
    "vh_cdr3_arom_density",
    "vl_cdr3_arom_density",
}


def build_regular_ab_developability(
    *,
    vh_seq: str,
    vl_seq: str,
    origin: str,
    raw_metrics: Dict[str, Any],
    cdr_liabilities: Iterable[Dict[str, Any]],
    germline: Dict[str, Any],
    mutation_suggestions: Iterable[Dict[str, Any]],
    fv_pdb_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Build regular VH/VL CMC output using the owner-approved 25+2 vocabulary."""
    normalized_origin = _normalize_origin(origin)
    primary_ref_path, primary_ref_label, transgenic_using_fallback = _select_primary_reference(normalized_origin)
    primary_atlas_path = _select_primary_atlas(normalized_origin)
    primary_ref = _load_json(primary_ref_path)
    
    # Merge CDR fingerprint thresholds
    cdr_fp_ref_path = CDR_FP_REF_VHH if normalized_origin in {"camelid_vhh", "humanized_vhh", "clinical_vhh"} else CDR_FP_REF_VHVL
    if cdr_fp_ref_path.exists():
        cdr_fp_ref = _load_json(cdr_fp_ref_path)
        if "loci" in cdr_fp_ref:
            ref_m = primary_ref.setdefault("metrics", {})
            for locus, l_data in cdr_fp_ref["loci"].items():
                l_metrics = l_data.get("metrics", {})
                chain = "vh" if locus.startswith("vh") else "vl"
                for m_key, m_stats in l_metrics.items():
                    # Map locus + metric to parameter key
                    # e.g. vh_cdr3 + length -> vh_cdr3_len
                    # e.g. vh_cdr3 + gravy -> vh_cdr3_gravy
                    full_key = None
                    if m_key == "length": full_key = f"{chain}_cdr3_len"
                    elif m_key == "gravy": full_key = f"{chain}_cdr3_gravy"
                    elif m_key == "net_charge_pH7": full_key = f"{chain}_cdr3_net_charge"
                    elif m_key == "aromatic_fraction": full_key = f"{chain}_cdr3_arom_density"
                    
                    if full_key and locus.endswith("cdr3"):
                        ref_m[full_key] = m_stats
                
                # Total CDR load (all_cdr_gravy)
                l_metrics = l_data.get("metrics", {})
                if "gravy" in l_metrics and locus.endswith("all_cdr"):
                    chain = "vh" if locus.startswith("vh") else "vl"
                    ref_m[f"{chain}_all_cdr_gravy"] = l_metrics["gravy"]
    
    engineered_ref = _load_json(ENGINEERED_REF)
    natural_ref = _load_json(NATURAL_REF)
    if normalized_origin == "therapeutic_regular_antibody":
        primary_ref = _build_intersection_reference(natural_ref, engineered_ref)
        primary_ref_label = "Dual-reference intersection: natural cohort ∩ engineered clinical cohort"

    metrics = _normalize_metric_values(dict(raw_metrics or {}))
    
    # Extract CDR fingerprint
    cdr_fp = CDRFingerprintEngine.compute_fingerprint(vh_seq, vl_seq)
    metrics.update(cdr_fp)
    
    total_cdr_length = _estimate_total_cdr_length(vh_seq, vl_seq)
    if total_cdr_length is not None:
        metrics["total_cdr_length"] = total_cdr_length

    parameters = _annotate_parameters(
        metrics,
        primary_ref,
        origin=normalized_origin,
        natural_metrics=(natural_ref.get("metrics") or {})
        if normalized_origin == "therapeutic_regular_antibody"
        else None,
        engineered_metrics=(engineered_ref.get("metrics") or {})
        if normalized_origin == "therapeutic_regular_antibody"
        else None,
    )
    if normalized_origin == "therapeutic_regular_antibody":
        _attach_split_panel_ranges(parameters, natural_ref, engineered_ref)
    source_notes = _source_specific_notes(
        normalized_origin,
        metrics,
        transgenic_using_fallback=transgenic_using_fallback,
    )
    cdr_warnings, fr_findings = _split_cdr_fr_findings(cdr_liabilities)
    merged_suggestions = list(mutation_suggestions or [])
    merged_suggestions.extend(_suggestions_from_gated_high_metrics(parameters))
    fr_suggestions = _client_safe_suggestions(
        merged_suggestions,
        fr_findings,
        normalized_origin,
        vh_seq,
        vl_seq,
        metrics,
        primary_ref.get("metrics") if isinstance(primary_ref, dict) else {},
        pdb_path=fv_pdb_path,
    )
    ada_context = _ada_context(germline, vh_seq=vh_seq or "", vl_seq=vl_seq or "")
    input_sequence_basis = _input_sequence_basis(vh_seq, vl_seq)
    reference_sequence_basis = _atlas_sequence_basis(primary_atlas_path)

    ref_metrics = (primary_ref.get("metrics") or {}) if isinstance(primary_ref, dict) else {}
    developability_index = compute_adi(metrics, ref_metrics=ref_metrics) if ref_metrics else None
    risk_level = _risk_from_index_and_parameters(developability_index, parameters)
    overall_gate_status = _gate_from_risk(risk_level)
    hard_gate_failures = _hard_gate_failures(parameters)

    if normalized_origin == "therapeutic_regular_antibody":
        primary_stats_file_display = (
            "intersection(Natural Baseline ∩ Clinical Reference Cohort)"
        )
    else:
        primary_stats_file_display = (
            str(primary_ref_path.relative_to(ROOT))
            if primary_ref_path.exists()
            else str(primary_ref_path)
        )

    return {
        "format_class": "regular_vhvl",
        "antibody_origin": normalized_origin,
        "parameter_set": {
            "numeric_count": 25,
            "descriptive_count": 2,
            "numeric_parameters": PARAMETER_SET_25,
            "descriptive_parameters": DESCRIPTIVE_PARAMETERS,
        },
        "reference_context": {
            "primary": primary_ref_label,
            "primary_stats_file": primary_stats_file_display,
            "context": _context_references(normalized_origin),
            "sequence_basis": reference_sequence_basis,
            "origin_benchmark": _origin_benchmark(
                normalized_origin,
                primary_ref_label,
                primary_stats_file_display,
                transgenic_fallback=transgenic_using_fallback,
            ),
            "method_consistency_note": (
                "All reported values are interpreted only against reference distributions "
                "generated with the same internal calculation protocol. Cross-method "
                "thresholds are not mixed."
            ),
        },
        "developability_index": round(float(developability_index), 1) if developability_index is not None else None,
        "developability_interpretation": adi_interpretation(developability_index) if developability_index is not None else None,
        "risk_level": risk_level,
        "overall_gate_status": overall_gate_status,
        "hard_gate_failures": hard_gate_failures,
        "gate_policy": _gate_policy_summary(),
        "parameters": parameters,
        "input_sequence_basis": input_sequence_basis,
        "source_specific_notes": source_notes,
        "fr_modification_suggestions": fr_suggestions,
        "cdr_warnings": cdr_warnings,
        "ada_context": ada_context,
        "data_boundaries": [
            "CDR findings are advisory warnings unless a separate CDR redesign task is approved.",
            "Framework findings may be considered for conservative framework-region modification.",
            "Historical ADA entries are context only and are not clinical ADA predictions.",
        ],
    }


def refresh_regular_ab_fr_suggestions(
    regular_ab_block: Dict[str, Any],
    *,
    vh_seq: str,
    vl_seq: str,
    origin: str,
    cdr_liabilities: Iterable[Dict[str, Any]],
    base_mutation_suggestions: Iterable[Dict[str, Any]],
    ref_metrics: Dict[str, Any],
    pdb_path: Optional[str] = None,
) -> None:
    """
    Rebuild ``fr_modification_suggestions`` after structural metrics (e.g. pnc/ppc/psh)
    are patched into ``parameters``, optionally with an Fv PDB for SASA-aware site lists.
    """
    if not isinstance(regular_ab_block, dict):
        return
    norm = _normalize_origin(origin)
    params = regular_ab_block.get("parameters") or []
    if norm == "therapeutic_regular_antibody":
        _attach_split_panel_ranges(params, _load_json(NATURAL_REF), _load_json(ENGINEERED_REF))
    merged = list(base_mutation_suggestions or [])
    merged.extend(_suggestions_from_gated_high_metrics(params))
    _, fr_findings = _split_cdr_fr_findings(cdr_liabilities)
    metrics_map: Dict[str, Any] = {}
    for p in params:
        if isinstance(p, dict) and p.get("key") is not None and p.get("value") is not None:
            metrics_map[str(p["key"])] = p["value"]
    regular_ab_block["fr_modification_suggestions"] = _client_safe_suggestions(
        merged,
        fr_findings,
        norm,
        vh_seq,
        vl_seq,
        metrics_map,
        ref_metrics or {},
        pdb_path=pdb_path,
    )


def _normalize_origin(origin: str) -> str:
    o = (origin or "").strip().lower().replace("-", "_").replace(" ", "_")
    # Natural Baseline platform subsets
    if o in {
        "natural384_transgenic_animal",
        "natural384_transgenic",
        "fully_human_natural384_transgenic",
        "transgenic",
        "transgenic_mouse",
    }:
        return "natural384_transgenic_animal"
    if o in {
        "natural384_phage_display",
        "natural384_phage",
        "fully_human_natural384_phage",
        "phage_display",
        "phage",
    }:
        return "natural384_phage_display"
    if o in {
        "natural384_human_b_cell_derived",
        "natural384_b_cell",
        "natural384_human_b_cell",
        "fully_human_natural384_b_cell",
        "single_b_cell_sorting",
        "single_b_cell",
        "b_cell_sorting",
        "b_cell_derived",
        "b_cell",
        "human_b_cell",
    }:
        return "natural384_human_b_cell_derived"
    if o in {"fully_human", "human", "natural"}:
        return "fully_human"
    # Engineered clinical cohort ()
    if o in {"engineered", "engineered_vhvl", "clinical_engineered"}:
        return "engineered"
    # Dual-cohort intersection (Natural Baseline pooled ∩ engineered clinical)—not a discovery-platform label.
    if o in {
        "therapeutic_regular_antibody",
        "therapeutic_regular",
        "regular_antibody_intersection",
        "phage",
        "phage_display",
        "display",
    }:
        return "therapeutic_regular_antibody"
    if o in {
        "humanized_transgenic",
        "humanized_transgenic_mouse",
        "transgenic_humanized",
        "transgenic_mouse_humanized",
        "humanized_transgenic_platform",
    }:
        return "humanized_transgenic"
    if o in {"dog", "canine", "dog_clinical"}:
        return "dog_clinical"
    if o in {"cat", "feline", "cat_clinical"}:
        return "cat_clinical"
    return "humanized"


def _select_primary_reference(origin: str) -> Tuple[Path, str, bool]:
    """
    Returns (stats_path, primary_label, transgenic_using_engineered_fallback).

    External-facing labels intentionally omit cohort enumeration (e.g. 384 / 458);
    frozen filenames on disk stay canonical for provenance.
    """
    if origin == "fully_human":
        return NATURAL_REF, "Natural regular VH/VL reference", False
    if origin == "engineered":
        return ENGINEERED_REF, "Engineered clinical VH/VL reference", False
    # humanized_transgenic uses the same frozen distribution as natural384_transgenic_animal
    # (Natural Baseline discovery_platform=transgenic_animal subset).
    if origin in {"natural384_transgenic_animal", "humanized_transgenic"}:
        if NATURAL384_SUBSET_TRANSGENIC.exists():
            tg = _load_json(NATURAL384_SUBSET_TRANSGENIC)
            if (tg.get("metrics") or {}):
                return NATURAL384_SUBSET_TRANSGENIC, "Natural Baseline transgenic-animal subset reference", False
        return NATURAL_REF, "Natural Baseline pooled reference (transgenic subset unavailable)", True
    if origin == "natural384_phage_display":
        if NATURAL384_SUBSET_PHAGE.exists():
            pg = _load_json(NATURAL384_SUBSET_PHAGE)
            if (pg.get("metrics") or {}):
                return NATURAL384_SUBSET_PHAGE, "Natural Baseline phage-display subset reference", False
        return NATURAL_REF, "Natural Baseline pooled reference (phage subset unavailable)", True
    if origin == "natural384_human_b_cell_derived":
        if NATURAL384_SUBSET_BCELL.exists():
            bc = _load_json(NATURAL384_SUBSET_BCELL)
            if (bc.get("metrics") or {}):
                return NATURAL384_SUBSET_BCELL, "Natural Baseline human B-cell-derived subset reference", False
        return NATURAL_REF, "Natural Baseline pooled reference (B-cell subset unavailable)", True
    if origin == "dog_clinical":
        return ENGINEERED_REF, "Canine clinical VH/VL reference (human clinical proxy)", False
    if origin == "cat_clinical":
        return ENGINEERED_REF, "Feline clinical VH/VL reference (human clinical proxy)", False
    return ENGINEERED_REF, "Engineered clinical VH/VL reference", False


def load_effective_primary_reference(origin_raw: str) -> Dict[str, Any]:
    """
    Same primary reference JSON used by ``build_regular_ab_developability`` after
    intersection / fallback rules — for structural metric patching in ``cmc.py``.
    """
    norm = _normalize_origin(origin_raw)
    path, _, transgenic_fb = _select_primary_reference(norm)
    engineered_ref = _load_json(ENGINEERED_REF)
    natural_ref = _load_json(NATURAL_REF)
    if norm == "therapeutic_regular_antibody":
        return _build_intersection_reference(natural_ref, engineered_ref)
    primary = _load_json(path)
    return primary


def _build_intersection_reference(natural_ref: Dict[str, Any], engineered_ref: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the therapeutic regular-antibody benchmark as Natural Baseline ∩ Engineered Clinical Cohort.

    For each metric:
      normal interval p5-p95      = max(p5_natural, p5_engineered) -> min(p95_natural, p95_engineered)
      preferred interval p25-p75  = max(p25_natural, p25_engineered) -> min(p75_natural, p75_engineered)

    If a metric has no valid overlap, it is omitted rather than forcing a misleading range.
    """
    n_metrics = (natural_ref.get("metrics") or {}) if isinstance(natural_ref, dict) else {}
    e_metrics = (engineered_ref.get("metrics") or {}) if isinstance(engineered_ref, dict) else {}
    out_metrics: Dict[str, Any] = {}
    for key in sorted(set(n_metrics) & set(e_metrics)):
        nr = n_metrics.get(key) or {}
        er = e_metrics.get(key) or {}
        required = ("p5", "p25", "p50", "p75", "p95")
        if not all(isinstance(nr.get(k), (int, float)) and isinstance(er.get(k), (int, float)) for k in required):
            continue
        p5 = max(float(nr["p5"]), float(er["p5"]))
        p25 = max(float(nr["p25"]), float(er["p25"]))
        p75 = min(float(nr["p75"]), float(er["p75"]))
        p95 = min(float(nr["p95"]), float(er["p95"]))
        if p5 > p95:
            continue
        if p25 > p75:
            p25, p75 = p5, p95
        out_metrics[key] = {
            "p5": round(p5, 4),
            "p25": round(p25, 4),
            "p50": round((p25 + p75) / 2.0, 4),
            "p75": round(p75, 4),
            "p95": round(p95, 4),
            "n": int((natural_ref.get("n") or 384)) + int((engineered_ref.get("n") or 458)),
            "reference_mode": "intersection",
            "natural_p5": nr.get("p5"),
            "natural_p95": nr.get("p95"),
            "engineered_p5": er.get("p5"),
            "engineered_p95": er.get("p95"),
        }
    return {
        "_meta": {
            "name": "Natural Baseline intersect Engineered Clinical Cohort therapeutic regular antibody benchmark",
            "mode": "intersection",
            "normal_interval": "max(Natural p5, Engineered p5) to min(Natural p95, Engineered p95)",
            "preferred_interval": "max(Natural p25, Engineered p25) to min(Natural p75, Engineered p75)",
            "n_antibodies_context": int((natural_ref.get("n") or 384)) + int((engineered_ref.get("n") or 458)),
        },
        "n": int((natural_ref.get("n") or 384)) + int((engineered_ref.get("n") or 458)),
        "metrics": out_metrics,
    }


def _origin_benchmark(
    origin: str,
    primary_label: str,
    primary_stats_file: str,
    *,
    transgenic_fallback: bool = False,
) -> Dict[str, Any]:
    """
    Explicit per-origin benchmark policy for the 25+2 regular-antibody CMC panel.

    Same PARAMETER_SET_25 keys are always reported; what changes is which frozen
    distribution defines p5–p95 / p25–p75 gates and ADI alignment.
    """
    natural_rel = str(NATURAL_REF.relative_to(ROOT)) if NATURAL_REF.exists() else str(NATURAL_REF)
    eng_rel = str(ENGINEERED_REF.relative_to(ROOT)) if ENGINEERED_REF.exists() else str(ENGINEERED_REF)
    if origin == "fully_human":
        return {
            "origin_key":             origin,
            "benchmark_mode":         "natural384_only",
            "primary_label":          primary_label,
            "primary_stats_file":     primary_stats_file,
            "split_panel_files":      {"natural384": natural_rel},
            "gate_rule":              "PASS/WARN/HIGH vs natural cohort p5–p95 (lower-is-better metrics use upper-only logic).",
            "adi_alignment":          "ADI uses natural cohort reference_metrics (same frozen file as gates).",
            "secondary_context_note": "Engineered clinical panel is not used for primary gates on fully-human runs.",
        }
    if origin in {"natural384_transgenic_animal", "humanized_transgenic"}:
        sub_rel = (
            str(NATURAL384_SUBSET_TRANSGENIC.relative_to(ROOT))
            if NATURAL384_SUBSET_TRANSGENIC.exists()
            else str(NATURAL384_SUBSET_TRANSGENIC)
        )
        mode = "natural384_subset_transgenic_fallback" if transgenic_fallback else "natural384_subset_transgenic_animal"
        return {
            "origin_key": origin,
            "benchmark_mode": mode,
            "primary_label": primary_label,
            "primary_stats_file": primary_stats_file,
            "split_panel_files": {"natural384_platform_subset": sub_rel, "natural384_pooled": natural_rel},
            "gate_rule": (
                "PASS/WARN/HIGH vs Natural Baseline transgenic-animal subset p5–p95 when the subset file is installed; "
                "if missing, gates use the pooled Natural Baseline distribution."
                if not transgenic_fallback
                else "PASS/WARN/HIGH vs pooled Natural Baseline (subset file missing or empty)."
            ),
            "adi_alignment": "ADI uses the same frozen reference_metrics as the active primary gate.",
            "secondary_context_note": (
                "Subset isolates discovery_platform=transgenic_animal within the genetically human Natural Baseline cohort; "
                "humanized_transgenic uses this same frozen reference as natural384_transgenic_animal."
            ),
        }
    if origin == "natural384_phage_display":
        sub_rel = (
            str(NATURAL384_SUBSET_PHAGE.relative_to(ROOT))
            if NATURAL384_SUBSET_PHAGE.exists()
            else str(NATURAL384_SUBSET_PHAGE)
        )
        mode = "natural384_subset_phage_fallback" if transgenic_fallback else "natural384_subset_phage_display"
        return {
            "origin_key": origin,
            "benchmark_mode": mode,
            "primary_label": primary_label,
            "primary_stats_file": primary_stats_file,
            "split_panel_files": {"natural384_platform_subset": sub_rel, "natural384_pooled": natural_rel},
            "gate_rule": (
                "PASS/WARN/HIGH vs Natural Baseline phage-display subset p5–p95 when installed; "
                "if missing, gates use the pooled Natural Baseline distribution."
                if not transgenic_fallback
                else "PASS/WARN/HIGH vs pooled Natural Baseline (subset file missing or empty)."
            ),
            "adi_alignment": "ADI uses the same frozen reference_metrics as the active primary gate.",
            "secondary_context_note": (
                "Subset isolates discovery_platform=phage_display within the genetically human Natural Baseline cohort. "
                "Distinct from therapeutic_regular_antibody (Natural Baseline pooled ∩ engineered clinical intersection)."
            ),
        }
    if origin == "natural384_human_b_cell_derived":
        sub_rel = (
            str(NATURAL384_SUBSET_BCELL.relative_to(ROOT))
            if NATURAL384_SUBSET_BCELL.exists()
            else str(NATURAL384_SUBSET_BCELL)
        )
        mode = "natural384_subset_bcell_fallback" if transgenic_fallback else "natural384_subset_human_b_cell_derived"
        return {
            "origin_key": origin,
            "benchmark_mode": mode,
            "primary_label": primary_label,
            "primary_stats_file": primary_stats_file,
            "split_panel_files": {"natural384_platform_subset": sub_rel, "natural384_pooled": natural_rel},
            "gate_rule": (
                "PASS/WARN/HIGH vs Natural Baseline human B-cell-derived subset p5–p95 when installed; "
                "subset n≈39 — interpret outer bands with caution."
                if not transgenic_fallback
                else "PASS/WARN/HIGH vs pooled Natural Baseline (subset file missing or empty)."
            ),
            "adi_alignment": "ADI uses the same frozen reference_metrics as the active primary gate.",
            "secondary_context_note": (
                "Subset isolates discovery_platform=human_b_cell_derived within the genetically human Natural Baseline cohort."
            ),
        }
    if origin == "therapeutic_regular_antibody":
        return {
            "origin_key":        origin,
            "benchmark_mode":    "intersection_nat384_eng458",
            "primary_label":     primary_label,
            "primary_stats_file": primary_stats_file,
            "split_panel_files": {
                "natural384":    natural_rel,
                "engineered458": eng_rel,
            },
            "gate_rule": (
                "PASS/WARN/HIGH vs intersection p5–p95 per metric: "
                "max(Natural p5, Engineered p5) to min(Natural p95, Engineered p95)."
            ),
            "adi_alignment": (
                "ADI uses the intersection-merged reference_metrics (same construction as gates)."
            ),
            "per_parameter_split_ranges": True,
        }
    return {
        "origin_key":        origin,
        "benchmark_mode":    "engineered458_only",
        "primary_label":     primary_label,
        "primary_stats_file": primary_stats_file,
        "split_panel_files": {"engineered458": eng_rel},
        "gate_rule":         "PASS/WARN/HIGH vs engineered clinical cohort p5–p95.",
        "adi_alignment":     "ADI uses engineered clinical reference_metrics (same frozen file as gates).",
        "secondary_context_note": "Natural cohort may be shown as a naturalness baseline only (not the primary gate).",
    }


def _attach_split_panel_ranges(
    parameters: List[Dict[str, Any]],
    natural_ref: Dict[str, Any],
    engineered_ref: Dict[str, Any],
) -> None:
    """For therapeutic_regular_antibody: attach Natural vs Engineered p5–p95 strings alongside intersection normal_range."""
    nm = (natural_ref.get("metrics") or {}) if isinstance(natural_ref, dict) else {}
    em = (engineered_ref.get("metrics") or {}) if isinstance(engineered_ref, dict) else {}
    for p in parameters:
        key = p.get("key")
        if not key:
            continue
        nr = nm.get(key) or {}
        er = em.get(key) or {}
        p["natural384_normal_range"] = _range_label(nr.get("p5"), nr.get("p95"))
        p["engineered458_normal_range"] = _range_label(er.get("p5"), er.get("p95"))


def _select_primary_atlas(origin: str) -> Path:
    if origin in {
        "fully_human",
        "natural384_transgenic_animal",
        "humanized_transgenic",
        "natural384_phage_display",
        "natural384_human_b_cell_derived",
    }:
        return NATURAL_ATLAS
    return ENGINEERED_ATLAS


def _context_references(origin: str) -> List[str]:
    if origin == "fully_human":
        return [
            "Primary gate: natural fully-human VH/VL frozen distributions.",
            "Clinical ADA historical context when germline-linked entries exist.",
        ]
    if origin in {"natural384_transgenic_animal", "humanized_transgenic"}:
        return [
            "Primary gate: Natural Baseline transgenic-animal platform subset frozen distributions "
            "(humanized_transgenic uses the same reference as natural384_transgenic_animal).",
            "If the subset file is unavailable, the pooled Natural Baseline distribution is used as fallback.",
            "Clinical ADA historical context when germline-linked entries exist.",
        ]
    if origin == "natural384_phage_display":
        return [
            "Primary gate: Natural Baseline phage-display platform subset frozen distributions.",
            "If the subset file is unavailable, the pooled Natural Baseline distribution is used as fallback.",
            "Clinical ADA historical context when germline-linked entries exist.",
        ]
    if origin == "natural384_human_b_cell_derived":
        return [
            "Primary gate: Natural Baseline human B-cell-derived platform subset frozen distributions (small n).",
            "If the subset file is unavailable, the pooled Natural Baseline distribution is used as fallback.",
            "Clinical ADA historical context when germline-linked entries exist.",
        ]
    if origin == "therapeutic_regular_antibody":
        return [
            "Primary gate: therapeutic regular antibody benchmark — Natural Baseline pooled ∩ engineered clinical intersection per metric.",
            "Split natural vs engineered clinical p5–p95 ranges are attached per parameter row for transparency.",
            "Clinical ADA historical context when germline-linked entries exist.",
        ]
    return [
        "Primary gate: engineered clinical VH/VL frozen distributions.",
        "Secondary context: natural cohort naturalness baseline (display-only unless explicitly requested).",
        "Clinical ADA historical context when germline-linked entries exist.",
    ]


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _is_real_protein_sequence(seq: str, *, min_len: int = 80) -> bool:
    s = (seq or "").strip().upper()
    return len(s) >= min_len and all(aa in AA20 for aa in s)


def _input_sequence_basis(vh_seq: str, vl_seq: str) -> Dict[str, Any]:
    vh = (vh_seq or "").strip().upper()
    vl = (vl_seq or "").strip().upper()
    vh_ok = _is_real_protein_sequence(vh, min_len=90)
    vl_ok = _is_real_protein_sequence(vl, min_len=85)
    return {
        "submitted_vh_length": len(vh),
        "submitted_vl_length": len(vl),
        "submitted_vh_real_sequence": vh_ok,
        "submitted_vl_real_sequence": vl_ok,
        "analysis_sequence_backed": bool(vh_ok and vl_ok),
        "note": "Regular antibody CMC analysis requires real VH and VL amino-acid sequences.",
    }


def _atlas_sequence_basis(path: Path) -> Dict[str, Any]:
    total = 0
    sequence_backed = 0
    examples: List[str] = []
    try:
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total += 1
                vh = row.get("vh_seq") or row.get("arm1_heavy") or ""
                vl = row.get("vl_seq") or row.get("arm1_light") or ""
                if _is_real_protein_sequence(vh, min_len=90) and _is_real_protein_sequence(vl, min_len=85):
                    sequence_backed += 1
                    if len(examples) < 3:
                        examples.append(str(row.get("antibody_id") or row.get("name") or "reference_entry"))
    except Exception:
        pass
    return {
        "atlas_file": str(path.relative_to(ROOT)) if path.exists() else str(path),
        "total_records": total,
        "sequence_backed_records": sequence_backed,
        "sequence_backed": bool(sequence_backed and sequence_backed == total),
        "example_sequence_backed_entries": examples,
        "note": "Reference comparisons use sequence-backed atlas records generated under the same internal calculation protocol.",
    }


def _normalize_metric_values(raw: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in raw.items():
        if isinstance(v, list):
            out[k] = len(v)
        else:
            out[k] = v
    return out


def _estimate_total_cdr_length(vh_seq: str, vl_seq: str) -> Optional[int]:
    """Best-effort IMGT CDR length extraction; returns None if numbering is unavailable."""
    try:
        from core.numbering.imgt_anarcii import imgt_number_anarcii
        from core.vhh_humanization import split_regions

        total = 0
        for seq in ((vh_seq or "").strip().upper(), (vl_seq or "").strip().upper()):
            if not seq:
                continue
            regions = split_regions(imgt_number_anarcii(seq))
            total += sum(len(str(regions.get(k, ""))) for k in ("CDR1", "CDR2", "CDR3"))
        return total or None
    except Exception:
        return None


def _annotate_parameters(
    metrics: Dict[str, Any],
    ref_stats: Dict[str, Any],
    *,
    origin: str = "humanized",
    natural_metrics: Optional[Dict[str, Any]] = None,
    engineered_metrics: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    ref_metrics = ref_stats.get("metrics") or {}
    out: List[Dict[str, Any]] = []
    for spec in PARAMETER_SET_25:
        key = spec["key"]
        value = metrics.get(key)
        ref = ref_metrics.get(key) or {}
        if value is None:
            out.append({
                **spec,
                "value": None,
                "reference_position": "not_available",
                "risk": "NOT_RUN",
                "gate_status": "NOT_RUN",
                "range_type": _range_type(key),
                "range_definition": _range_definition(key),
                "interpretation": "Requires structure or supporting data for this run.",
            })
            continue
        scalar = _to_float(value)
        if scalar is None:
            out.append({
                **spec,
                "value": value,
                "reference_position": "not_available",
                "risk": "NOT_RUN",
                "gate_status": "NOT_RUN",
                "range_type": _range_type(key),
                "range_definition": _range_definition(key),
                "interpretation": "Value is not numeric in this run.",
            })
            continue
        use_split_phage = (
            origin == "therapeutic_regular_antibody"
            and not ref
            and natural_metrics
            and engineered_metrics
            and (natural_metrics.get(key) or {})
            and (engineered_metrics.get(key) or {})
        )
        if use_split_phage:
            nr = natural_metrics.get(key) or {}
            er = engineered_metrics.get(key) or {}
            risk, position, interp, low_hi = _risk_when_panels_do_not_overlap(key, scalar, nr, er)
            out.append({
                **spec,
                "value": round(scalar, 3),
                "reference_position": position,
                "risk": risk,
                "gate_status": _gate_from_risk(risk),
                "range_type": _range_type(key),
                "range_definition": _range_definition(key),
                "interpretation": interp,
                "normal_range": None,
                "normal_range_note": (
                    "No single p5–p95 intersection for this metric between Natural Baseline and Engineered Clinical Cohort; "
                    "risk compares the value against each cohort separately (see Nat / Eng lines below)."
                ),
                "preferred_range": None,
                "normal_low": low_hi[0],
                "normal_high": low_hi[1],
                "preferred_low": None,
                "preferred_high": None,
                "reference_mode": "split_cohorts_no_intersection",
            })
            continue

        risk, position = _risk_position(key, scalar, ref)
        out.append({
            **spec,
            "value": round(scalar, 3),
            "reference_position": position,
            "risk": risk,
            "gate_status": _gate_from_risk(risk),
            "range_type": _range_type(key),
            "range_definition": _range_definition(key),
            "interpretation": _metric_interpretation(key, risk),
            "normal_range": _range_label(ref.get("p5"), ref.get("p95")),
            "preferred_range": _range_label(ref.get("p25"), ref.get("p75")),
            "normal_low": ref.get("p5"),
            "normal_high": ref.get("p95"),
            "preferred_low": ref.get("p25"),
            "preferred_high": ref.get("p75"),
            "reference_mode": ref.get("reference_mode") or "single_panel",
        })
    return out


def _risk_when_panels_do_not_overlap(
    key: str,
    value: float,
    nr: Dict[str, Any],
    er: Dict[str, Any],
) -> Tuple[str, str, str, Tuple[Optional[float], Optional[float]]]:
    """
    When Natural vs Engineered cohorts have disjoint p5–p95 intervals (e.g. total CDR length),
    intersection stats omit the metric. Evaluate vs each panel and combine with explicit wording.
    """
    r_nat, pos_nat = _risk_position(key, value, nr)
    r_eng, pos_eng = _risk_position(key, value, er)
    rank = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "NOT_RUN": -1}

    worst = max((r_nat, r_eng), key=lambda x: rank.get(x, -1))
    # Library vs approved-mAb skew: opposite cohort verdicts → MODERATE (contextual), not a hard HIGH.
    if (r_nat == "LOW" and r_eng == "HIGH") or (r_nat == "HIGH" and r_eng == "LOW"):
        worst = "MODERATE"

    if key == "total_cdr_length":
        interp = (
            f"Total CDR span {int(round(value))} aa: vs Natural Baseline this sits in the {_band_words(r_nat, pos_nat)}; "
            f"vs Engineered Clinical Cohort (approved-style mAbs) it sits in the {_band_words(r_eng, pos_eng)}. "
            "The two cohorts do not share a common p5–p95 band—short libraries often align with natural spreads "
            "while clinical antibodies in AbRef skew longer; interpret as cohort context, not a missing metric."
        )
    else:
        interp = (
            f"Dual-cohort evaluation: Natural Baseline → {r_nat} ({pos_nat}); Engineered Clinical Cohort → {r_eng} ({pos_eng}). "
            "Panels do not overlap—see separate Nat / Eng ranges."
        )

    p5n, p95n = nr.get("p5"), nr.get("p95")
    p5e, p95e = er.get("p5"), er.get("p95")
    low_hi = (
        float(p5n) if isinstance(p5n, (int, float)) else None,
        float(p95n) if isinstance(p95n, (int, float)) else None,
    )
    return worst, "split_cohort_dual_band", interp, low_hi


def _band_words(risk: str, position: str) -> str:
    if risk == "LOW":
        return "core/broad reference band (typical)"
    if risk == "MODERATE":
        return "acceptable but outer band or elevated vs that cohort"
    if risk == "HIGH":
        return "outside that cohort’s p5–p95 band"
    return position.replace("_", " ")


def _range_label(low: Any, high: Any) -> Optional[str]:
    if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
        return None
    return f"{float(low):.3g}-{float(high):.3g}"


def _to_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _risk_position(key: str, value: float, ref: Dict[str, Any]) -> Tuple[str, str]:
    if not ref:
        return "NOT_RUN", "no_reference"
    p5, p25, p50, p75, p95 = (ref.get(x) for x in ("p5", "p25", "p50", "p75", "p95"))
    vals = [x for x in (p5, p25, p50, p75, p95) if isinstance(x, (int, float))]
    if len(vals) < 5:
        return "NOT_RUN", "incomplete_reference"

    if key in LOWER_IS_BETTER:
        if value <= p75:
            return "LOW", "favorable_to_typical"
        if value <= p95:
            return "MODERATE", "upper_reference_band"
        return "HIGH", "outside_reference_band"

    if p25 <= value <= p75:
        return "LOW", "central_reference_band"
    if p5 <= value <= p95:
        return "MODERATE", "outer_reference_band"
    return "HIGH", "outside_reference_band"


def _gate_from_risk(risk: str) -> str:
    return {
        "LOW": "PASS",
        "MODERATE": "WARN",
        "HIGH": "FAIL",
        "NOT_RUN": "NOT_RUN",
    }.get(str(risk or "").upper(), "NOT_RUN")


def _range_type(key: str) -> str:
    return "lower_is_better" if key in LOWER_IS_BETTER else "two_sided"


def _range_definition(key: str) -> Dict[str, str]:
    if key in LOWER_IS_BETTER:
        return {
            "pass": "value <= p75 of the selected source-matched reference distribution",
            "warn": "p75 < value <= p95 of the selected source-matched reference distribution",
            "fail": "value > p95 of the selected source-matched reference distribution",
            "not_run": "metric missing, non-numeric, unavailable reference, or structure not computed",
        }
    return {
        "pass": "p25 <= value <= p75 of the selected source-matched reference distribution",
        "warn": "p5 <= value < p25 or p75 < value <= p95 of the selected source-matched reference distribution",
        "fail": "value < p5 or value > p95 of the selected source-matched reference distribution",
        "not_run": "metric missing, non-numeric, unavailable reference, or structure not computed",
    }


def _hard_gate_failures(parameters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in parameters or []:
        key = str(p.get("key") or "")
        if key in HARD_FAIL_PARAMETERS and p.get("gate_status") == "FAIL":
            out.append({
                "key": key,
                "label": p.get("label") or key,
                "value": p.get("value"),
                "normal_range": p.get("normal_range"),
                "reason": "hard-gate parameter exceeded its source-matched normal range",
            })
    return out


def _gate_policy_summary() -> Dict[str, Any]:
    return {
        "parameter_gate_mapping": {
            "LOW": "PASS",
            "MODERATE": "WARN",
            "HIGH": "FAIL",
            "NOT_RUN": "NOT_RUN",
        },
        "normal_range": "p5-p95 of the selected source-matched frozen reference distribution",
        "preferred_range": "p25-p75 of the selected source-matched frozen reference distribution",
        "two_sided_parameters": "PASS in p25-p75; WARN in p5-p25 or p75-p95; FAIL outside p5-p95",
        "lower_is_better_parameters": "PASS at <=p75; WARN at p75-p95; FAIL above p95",
        "overall_gate": "Any hard-gate FAIL or >=2 parameter FAILs or ADI <40 => FAIL; one parameter FAIL, >=4 WARNs, or ADI <60 => WARN; otherwise PASS",
        "hard_fail_parameters": sorted(HARD_FAIL_PARAMETERS),
        "adi_rule": "ADI cannot override single-parameter FAILs; it can only worsen the overall gate.",
    }


def _metric_interpretation(key: str, risk: str) -> str:
    if risk == "LOW":
        return "Within the preferred regular-antibody reference region."
    if risk == "MODERATE":
        if key == "instability_index":
            return (
                "Within the broad p5–p95 band but outside the preferred core; Guruprasad-type indices "
                ">40 warrant motif review even when still inside the outer band."
            )
        return "Within the broader clinical reference space but should be monitored."
    if risk == "HIGH":
        if key in {"deamidation_sites", "isomerization_sites", "oxidation_sites", "glycosylation_sites", "free_cys"}:
            return "Chemical liability is elevated and should be reviewed by region."
        if key in {"hydro_patch_max9", "SAP_score", "agg_motifs", "hydro_cluster_count"}:
            return "Aggregation or expression risk is elevated."
        if key in {"pI", "net_charge_pH7", "charge_patch_max7", "Fv_charge_asymmetry"}:
            return "Charge-related manufacturability risk is elevated."
        return "Metric is outside the regular-antibody reference region."
    return "Not evaluated in this run."


def _source_specific_notes(
    origin: str,
    metrics: Dict[str, Any],
    *,
    transgenic_using_fallback: bool = False,
) -> List[Dict[str, str]]:
    notes: List[Dict[str, str]] = []
    if origin == "fully_human":
        notes.append({
            "level": "INFO",
            "text": "Fully human regular antibodies are reviewed for naturalness and clinical drug-space compatibility.",
        })
    elif origin == "humanized":
        notes.append({
            "level": "INFO",
            "text": (
                "Gene-engineered humanized antibodies use the engineered clinical VH/VL reference primary gate "
                "(approved-style mAb drug space), distinct from the fully-human natural cohort."
            ),
        })
    elif origin in {
        "natural384_transgenic_animal",
        "humanized_transgenic",
        "natural384_phage_display",
        "natural384_human_b_cell_derived",
    }:
        if transgenic_using_fallback:
            notes.append({
                "level": "WARN",
                "text": (
                    "Natural Baseline platform subset statistics file is missing or empty; gates use the pooled Natural Baseline "
                    "distribution until the subset reference is restored."
                ),
            })
        notes.append({
            "level": "INFO",
            "text": (
                "Natural Baseline platform subset benchmarks compare this antibody to the same discovery_platform slice "
                "within the genetically human Natural Baseline cohort (distinct from pooled Natural Baseline or engineered gates)."
            ),
        })
    elif origin == "therapeutic_regular_antibody":
        level = "WARN" if (_to_float(metrics.get("net_charge_pH7")) or 0.0) < -2.0 else "INFO"
        notes.append({
            "level": level,
            "text": (
                "Therapeutic regular antibody (dual-cohort intersection): review surface charge / expression bias risk "
                "before downstream engineering."
            ),
        })
        notes.append({
            "level": "INFO",
            "text": (
                "Reference standard: natural cohort ∩ engineered clinical cohort. The normal expression interval is the "
                "overlap of natural fully-human antibodies and engineered clinical antibodies: "
                "max(natural p5, engineered p5) to min(natural p95, engineered p95). Values inside this "
                "intersection are treated as normal-expression compatible; values outside the intersection "
                "are prioritized for conservative FR-only optimization."
            ),
        })
        notes.append({
            "level": "INFO",
            "text": (
                "When both pI and net-charge rows appear, the ↑/↓ hint is evaluated independently against "
                "each metric’s intersection gate; suggested FR substitutions may overlap because both tracks "
                "respond to surface charge."
            ),
        })
    return notes


def _suggestions_from_gated_high_metrics(parameters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create FR-oriented optimization targets for metrics at HIGH vs the active reference gate (all origins)."""
    actionable = {
        "pI",
        "net_charge_pH7",
        "charge_patch_max7",
        "ppc",
        "pnc",
        "psh",
        "GRAVY",
        "hydro_patch_max9",
        "SAP_score",
        "instability_index",
        "agg_motifs",
        "deamidation_sites",
        "isomerization_sites",
        "oxidation_sites",
        "glycosylation_sites",
        "free_cys",
    }
    out: List[Dict[str, Any]] = []
    seen: set = set()
    for p in parameters or []:
        key = str(p.get("key") or "")
        if key not in actionable or key in seen:
            continue
        if p.get("risk") != "HIGH":
            continue
        seen.add(key)
        out.append({
            "metric": key,
            "target_metric": key,
            "current_value": p.get("value"),
            "target_range": p.get("normal_range") or "intersection p5-p95",
            "gate": "FAIL",
            "direction": _direction_from_parameter_position(p),
        })
    return out


def _direction_from_parameter_position(parameter: Dict[str, Any]) -> str:
    value = _to_float(parameter.get("value"))
    low = _to_float(parameter.get("normal_low"))
    high = _to_float(parameter.get("normal_high"))
    if value is None or low is None or high is None:
        return ""
    if value > high:
        return "too_high"
    if value < low:
        return "too_low"
    return ""


def _split_cdr_fr_findings(liabilities: Iterable[Dict[str, Any]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    cdr: List[Dict[str, str]] = []
    fr: List[Dict[str, str]] = []
    for item in liabilities or []:
        label = str(item.get("type") or item.get("label") or "liability")
        region = str(item.get("region") or item.get("where") or "").upper()
        pos = item.get("pos")
        rec = {
            "finding": label,
            "region": region or "unassigned",
            "position": str(pos) if pos is not None else "—",
            "action": "Review in context.",
        }
        if "CDR" in region or label.lower().startswith(("deamidation", "isomerization", "oxidation")):
            rec["action"] = "CDR finding is advisory (functional CDRs often retain liabilities); do not modify without structural validation."
            cdr.append(rec)
        else:
            rec["action"] = "Framework-region finding may be considered for conservative modification."
            fr.append(rec)
    return cdr, fr


def _infer_too_high_low(metric: str, raw: Dict[str, Any], ref_metrics: Dict[str, Any]) -> Optional[str]:
    """Return 'too_high' or 'too_low' from numeric value vs Clinical Reference Cohort p5/p95, or None."""
    m = str(metric or "")
    r = (ref_metrics or {}).get(m) or {}
    if not isinstance(r, dict):
        return None
    p5, p95 = r.get("p5"), r.get("p95")
    if not isinstance(p5, (int, float)) or not isinstance(p95, (int, float)):
        return None
    val = raw.get(m)
    if val is None:
        return None
    try:
        fv = float(val)
    except (TypeError, ValueError):
        return None
    if fv > p95:
        return "too_high"
    if fv < p5:
        return "too_low"
    return None


def _client_safe_suggestions(
    mutation_suggestions: Iterable[Dict[str, Any]],
    fr_findings: List[Dict[str, str]],
    origin: str,
    vh_seq: str = "",
    vl_seq: str = "",
    raw_metrics: Optional[Dict[str, Any]] = None,
    ref_metrics: Optional[Dict[str, Any]] = None,
    pdb_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    # pI and net_charge_pH7 both target surface charge; merge into one combined suggestion row.
    CHARGE_GROUP = {"pI", "net_charge_pH7"}

    out: List[Dict[str, Any]] = []
    seen_metrics: set = set()
    charge_merged: Optional[Dict[str, Any]] = None  # holds the merged charge row once built

    for item in mutation_suggestions or []:
        metric = str(item.get("metric") or item.get("target_metric") or "developability_metric")
        if metric in seen_metrics:
            continue
        seen_metrics.add(metric)

        it = dict(item) if isinstance(item, dict) else {}
        if not it.get("sequence_candidates") and (vh_seq or vl_seq) and (raw_metrics is not None):
            direction = (it.get("direction") or "").lower()
            if direction not in ("too_high", "too_low") and ref_metrics is not None:
                direction = _infer_too_high_low(metric, raw_metrics, ref_metrics) or ""
            if direction in ("too_high", "too_low"):
                try:
                    from core.cmc.fr_mutation_sites import build_candidate_payload_for_metric
                    it["sequence_candidates"] = build_candidate_payload_for_metric(
                        metric, direction, vh_seq, vl_seq, pdb_path=pdb_path
                    )
                except Exception:
                    pass

        direction_for_label = (it.get("direction") or "").lower()
        if direction_for_label not in ("too_high", "too_low") and ref_metrics is not None:
            direction_for_label = _infer_too_high_low(metric, raw_metrics or {}, ref_metrics) or ""

        action = _safe_action_for_metric(metric, origin)
        current_val = it.get("current_value")
        target_range = str(it.get("target_range") or "").strip()

        if current_val is None and raw_metrics:
            cv0 = raw_metrics.get(metric)
            if cv0 is not None:
                current_val = cv0
        current_val_str: Optional[str] = None
        if current_val is not None:
            try:
                current_val_str = f"{float(current_val):.2f}".rstrip("0").rstrip(".")
            except (TypeError, ValueError):
                current_val_str = str(current_val)

        sc = it.get("sequence_candidates")
        slim: Dict[str, Any] = {}
        if isinstance(sc, dict) and sc:
            for k in (
                "fr_positive_charge_sites",
                "fr_negative_charge_sites",
                "fr_hydrophobic_runs",
                "fr_instability_sites",
                "enumeration_note",
                "mutation_policy",
            ):
                if k in sc and sc[k]:
                    slim[k] = sc[k]

        # ── Charge group merge (pI + net_charge → one combined row) ────────────
        if metric in CHARGE_GROUP:
            if charge_merged is None:
                # First charge metric: create the merged row
                charge_merged = {
                    "scope": "FR-only",
                    "target": "charge balance (pI + net charge)",
                    "metric_key": metric,
                    "direction": direction_for_label,
                    "priority": "HIGH" if str(item.get("gate", "")).upper() == "FAIL" else "MEDIUM",
                    "recommendation": _safe_action_for_metric("net_charge_pH7", origin),
                    "current_value": current_val_str,
                    "charge_details": [],
                }
                if target_range:
                    charge_merged["target_range"] = target_range
                if slim:
                    charge_merged["sequence_candidates"] = slim
                out.append(charge_merged)
            else:
                # Second charge metric: merge values and candidate sites only
                detail = f"{metric}: {current_val_str}" if current_val_str else metric
                charge_merged["charge_details"].append(detail)
                if slim:
                    # Merge candidate sites — deduplicate by (chain, index_1)
                    existing_sc = charge_merged.get("sequence_candidates") or {}
                    existing_sites = existing_sc.get("fr_positive_charge_sites") or []
                    existing_keys = {(s.get("chain"), s.get("index_1")) for s in existing_sites}
                    new_sites = slim.get("fr_positive_charge_sites") or []
                    for s in new_sites:
                        k2 = (s.get("chain"), s.get("index_1"))
                        if k2 not in existing_keys:
                            existing_sites.append(s)
                            existing_keys.add(k2)
                    if existing_sites:
                        if "sequence_candidates" not in charge_merged:
                            charge_merged["sequence_candidates"] = {}
                        charge_merged["sequence_candidates"]["fr_positive_charge_sites"] = existing_sites
                # Update priority to worst of the two
                if str(item.get("gate", "")).upper() == "FAIL":
                    charge_merged["priority"] = "HIGH"
            continue
        # ── End charge group ────────────────────────────────────────────────────

        entry: Dict[str, Any] = {
            "scope": "FR-only",
            "target": _safe_metric_label(metric, direction_for_label),
            "metric_key": metric,
            "direction": direction_for_label,
            "priority": "HIGH" if str(item.get("gate", "")).upper() == "FAIL" else "MEDIUM",
            "recommendation": action,
        }
        if current_val_str is not None:
            entry["current_value"] = current_val_str
        if target_range:
            entry["target_range"] = target_range
        if slim:
            entry["sequence_candidates"] = slim
        out.append(entry)

    if not out and fr_findings:
        out.append({
            "scope": "FR-only",
            "target": "Framework observations (no auto site list)",
            "priority": "MEDIUM",
            "recommendation": (
                "The liability scan recorded framework-region notes, but no HIGH-gated metric row produced "
                "an FR substitution shortlist for this response (or all candidate positions were filtered). "
                "Review the liability findings in context; this line alone is not a substitute for the 25-parameter gate outcome."
            ),
        })
    # ── F4: explain "no FR suggestions" when the overall status is not PASS ────
    # Smoke 2026-05-15: toripalimab returned overall_status=WARN (cdr_scan:deamidation)
    # but no FR-suggestion shortlist. The UI used to show "No FR modifications recommended"
    # with no explanation; clients couldn't tell whether the molecule was fine or whether
    # Smart-CMC failed. Append a structured `no_fr_reason` entry summarising the cause.
    if not out:
        reason = _infer_no_fr_reason(mutation_suggestions, fr_findings, raw_metrics, ref_metrics)
        if reason:
            out.append({
                "scope": "FR-only",
                "target": "No FR modifications recommended",
                "priority": "INFO",
                "no_fr_reason": reason,
                "recommendation": reason,
            })
    return out


def _infer_no_fr_reason(
    mutation_suggestions: Optional[List[Dict[str, Any]]],
    fr_findings: Optional[List[Dict[str, Any]]],
    raw_metrics: Optional[Dict[str, Any]],
    ref_metrics: Optional[Dict[str, Any]],
) -> Optional[str]:
    """
    Build a human-readable explanation for why no FR-only mutation row was emitted.
    The most common causes (Smoke 2026-05-15):
      - All flagged liabilities are CDR-internal (deamidation/isomerization sites in CDRs).
      - All flagged metrics are length-based (CDR length out of band; cannot be moved by point mutation).
      - All flagged metrics are structure-derived (e.g. PSH/PPC/PNC with no FR candidates after SASA filter).
      - The metric is already inside the safe zone (e.g. F2 charge trimmer returned 0 sites).
    """
    if not (mutation_suggestions or fr_findings):
        return None
    cdr_liab_keys = {"deamidation_sites", "isomerization_sites", "oxidation_sites", "glycosylation_sites"}
    cdr_only_count = 0
    length_count = 0
    structure_count = 0
    safe_zone_count = 0
    other_count = 0
    for it in (mutation_suggestions or []):
        metric = (it.get("metric") or it.get("target_metric") or "").lower()
        sc = it.get("sequence_candidates") or {}
        # Length-based metrics
        if "length" in metric or "cdr" in metric and "length" in metric:
            length_count += 1
            continue
        # Liability metrics — count CDR-internal residues only
        if metric in {"deamidation_sites", "isomerization_sites", "oxidation_sites"}:
            cdr_only_count += 1
            continue
        # Charge trimmer reported already-in-safe-zone
        if sc.get("safe_zone_stop", {}).get("stopped") == "already_in_safe_zone":
            safe_zone_count += 1
            continue
        # Structure-only metrics with empty FR site lists
        if metric in {"psh", "ppc", "pnc", "sap_score"}:
            has_any = any(sc.get(k) for k in (
                "fr_positive_charge_sites", "fr_negative_charge_sites",
                "fr_hydrophobic_runs", "fr_instability_sites",
            ))
            if not has_any:
                structure_count += 1
                continue
        other_count += 1
    parts: List[str] = []
    if cdr_only_count:
        parts.append(
            f"All flagged liabilities ({cdr_only_count} metric{'s' if cdr_only_count > 1 else ''}) "
            f"are CDR-internal (deamidation / isomerization / oxidation sites in CDR loops). "
            f"FR mutations cannot remove residues that the CDR sequence requires for antigen binding — "
            f"CDR redesign / affinity maturation is the appropriate service."
        )
    if length_count:
        parts.append(
            f"{length_count} flag is length-based (CDR or chain length out of the reference envelope). "
            f"Point mutations cannot shorten or lengthen a chain; this is a design parameter, not a CMC fix."
        )
    if structure_count:
        parts.append(
            f"{structure_count} structure-derived metric{'s' if structure_count > 1 else ''} "
            f"(PSH / PPC / PNC / SAP) flagged, but no surface-accessible FR residue passed the SASA / "
            f"Vernier filters. Consider full structural CMC review (premium tier)."
        )
    if safe_zone_count:
        parts.append(
            f"{safe_zone_count} charge metric{'s' if safe_zone_count > 1 else ''} are already inside "
            f"the AbRef clinical safe zone — further mutation would move them away from optimum."
        )
    if not parts:
        return None
    return " ".join(parts)


def _safe_metric_label(metric: str, direction: str = "") -> str:
    d_high = direction == "too_high"
    labels: Dict[str, str] = {
        "pI": "charge balance (pI {})".format("↓ reduce" if d_high else "↑ increase"),
        "net_charge_pH7": "charge balance (net charge {})".format("↓ reduce" if d_high else "↑ increase"),
        "charge_patch_max7": "charge patch",
        "ppc": "positive charge patch profile ({})".format("↓ reduce" if d_high else "↑ increase"),
        "pnc": "negative charge patch profile ({})".format("↓ reduce" if d_high else "↑ increase"),
        "psh": "surface hydrophobic patch profile ({})".format("↓ reduce" if d_high else "↑ increase"),
        "GRAVY": "hydrophobicity",
        "hydro_patch_max9": "hydrophobic patch",
        "SAP_score": "surface hydrophobicity",
        "instability_index": "sequence stability",
        "agg_motifs": "aggregation motif",
        "deamidation_sites": "chemical liability",
        "isomerization_sites": "chemical liability",
    }
    return labels.get(metric, metric)


def _safe_action_for_metric(metric: str, origin: str) -> str:
    if metric in {"pI", "net_charge_pH7", "charge_patch_max7", "ppc", "pnc"}:
        if origin in {"therapeutic_regular_antibody", "natural384_phage_display"}:
            return (
                "Prioritize FR-only charge balancing at non-critical surface residues "
                "to move pI/charge metrics toward the reference range before scale-up."
            )
        return (
            "Use conservative FR-only charge balancing at non-critical surface residues "
            "to improve pI and charge-patch metrics while preserving CDRs."
        )
    if metric in {"psh"}:
        return (
            "Reduce exposed FR hydrophobic patches via conservative substitutions at "
            "non-critical positions; keep CDR regions unchanged."
        )
    if metric in {"GRAVY", "hydro_patch_max9", "SAP_score", "agg_motifs"}:
        return (
            "Decrease FR surface hydrophobicity and aggregation-prone motifs using "
            "conservative FR substitutions, prioritizing developability without altering CDRs."
        )
    if metric == "instability_index":
        return (
            "Apply targeted FR substitutions at flagged non-critical positions to improve "
            "sequence-level stability while retaining binding architecture."
        )
    if metric in {"deamidation_sites", "isomerization_sites", "oxidation_sites", "glycosylation_sites", "free_cys"}:
        return (
            "Address chemical liabilities with FR-first cleanup; treat CDR findings as advisory "
            "and defer any CDR change to structure-validated follow-up."
        )
    return "Review flagged framework-region property using conservative substitutions only."


def _is_unknown_germline_token(g: Optional[str]) -> bool:
    if not g:
        return True
    return str(g).strip().lower() in ("", "unknown", "none", "n/a", "—")


def _atlas_row_by_sequence_match(vh_seq: str, vl_seq: str) -> Optional[Dict[str, Any]]:
    """Full atlas row when arm1 VH/VL sequences exactly match submitted Fv (same scan as identity ADA)."""
    vh = _normalize_aa_seq(vh_seq)
    vl = _normalize_aa_seq(vl_seq)
    if len(vh) < 90 or len(vl) < 85:
        return None
    atlas = _load_json(CLINICAL_ATLAS)
    if not isinstance(atlas, list):
        return None
    for row in atlas:
        if not isinstance(row, dict):
            continue
        if not _has_real_clinical_sequence(row):
            continue
        rh = _normalize_aa_seq(str(row.get("arm1_heavy") or row.get("vh_seq") or ""))
        rl = _normalize_aa_seq(str(row.get("arm1_light") or row.get("vl_seq") or ""))
        if rh == vh and rl == vl:
            return row
    return None


def _ada_context(
    germline: Dict[str, Any], *, vh_seq: str = "", vl_seq: str = ""
) -> Dict[str, Any]:
    vh = germline.get("VH") or {}
    vl = germline.get("VL") or {}
    vh_gene = str(vh.get("top_match") or vh.get("top_match_id") or "")
    vl_gene = str(vl.get("top_match") or vl.get("top_match_id") or "")
    vh_family = _family(vh_gene)
    vl_family = _family(vl_gene)
    refs = _matching_ada_entries(vh_gene, vl_gene, vh_family, vl_family)
    id_refs = _sequence_identity_ada_rows(vh_seq, vl_seq)
    merged = _merge_ada_refs(id_refs, refs, max_n=5)
    # When germline assignment fails for VH but Fv matches an approved atlas sequence, show that drug's VH/VL germline from the atlas row (label consistency).
    id_row = _atlas_row_by_sequence_match(vh_seq, vl_seq)
    vh_display = None if _is_unknown_germline_token(vh_gene) else vh_gene.strip()
    vl_display = None if _is_unknown_germline_token(vl_gene) else vl_gene.strip()
    if id_row:
        if _is_unknown_germline_token(vh_display):
            vh_display = str(id_row.get("vh_germline") or "").strip() or vh_display
        if _is_unknown_germline_token(vl_display):
            vl_display = str(id_row.get("vl_germline") or "").strip() or vl_display
    return {
        "data_linkage_only": True,
        "non_predictive": True,
        "vh_germline": vh_display or None,
        "vl_germline": vl_display or None,
        "matched_clinical_entries": merged,
        "interpretation": (
            "Historical ADA records are shown only when similar germline context exists. "
            "They do not predict clinical ADA for the submitted antibody. "
            "When Fv sequences exactly match a sequence-backed approved-molecule record, that entry is shown as a label-level reference (not a patient-level forecast)."
        ),
    }


def _family(gene: str) -> str:
    gene = (gene or "").split("*")[0]
    return gene


def _matching_ada_entries(vh_gene: str, vl_gene: str, vh_family: str, vl_family: str) -> List[Dict[str, Any]]:
    atlas = _load_json(CLINICAL_ATLAS)
    if not isinstance(atlas, list):
        return []
    out: List[Dict[str, Any]] = []
    for row in atlas:
        if not isinstance(row, dict):
            continue
        if not _has_real_clinical_sequence(row):
            continue
        ada = str(row.get("ada_display") or row.get("ada_pct") or "").strip()
        if not ada:
            continue
        rvh = str(row.get("vh_germline") or "")
        rvl = str(row.get("vl_germline") or "")
        rvhf = str(row.get("vh_family") or _family(rvh))
        rvlf = str(row.get("vl_family") or _family(rvl))
        tier = None
        if vh_gene and vl_gene and rvh == vh_gene and rvl == vl_gene:
            tier = "VH+VL germline match"
        elif vh_gene and rvh == vh_gene:
            tier = "VH germline match"
        elif vl_gene and rvl == vl_gene:
            tier = "VL germline match"
        elif vh_family and vl_family and rvhf == vh_family and rvlf == vl_family:
            tier = "VH+VL family match"
        elif vh_family and rvhf == vh_family:
            tier = "VH family match"
        elif vl_family and rvlf == vl_family:
            tier = "VL family match"
        if tier:
            out.append({
                "name": row.get("name"),
                "match_type": tier,
                "ada_display": ada,
                "target": row.get("targets") or None,
                "format": row.get("format") or None,
            })
        if len(out) >= 5:
            break
    return out


def _normalize_aa_seq(s: str) -> str:
    return "".join(str(s or "").strip().upper().split())


def _sequence_identity_ada_rows(vh_seq: str, vl_seq: str) -> List[Dict[str, Any]]:
    """When submitted VH+VL exactly match an atlas arm1 pair, surface drug-label ADA excerpt."""
    vh = _normalize_aa_seq(vh_seq)
    vl = _normalize_aa_seq(vl_seq)
    if len(vh) < 90 or len(vl) < 85:
        return []
    atlas = _load_json(CLINICAL_ATLAS)
    if not isinstance(atlas, list):
        return []
    out: List[Dict[str, Any]] = []
    for row in atlas:
        if not isinstance(row, dict):
            continue
        if not _has_real_clinical_sequence(row):
            continue
        rh = _normalize_aa_seq(str(row.get("arm1_heavy") or row.get("vh_seq") or ""))
        rl = _normalize_aa_seq(str(row.get("arm1_light") or row.get("vl_seq") or ""))
        if rh != vh or rl != vl:
            continue
        ada = str(row.get("ada_display") or row.get("ada_pct") or "").strip()
        if not ada:
            continue
        out.append(
            {
                "name": row.get("name"),
                "match_type": "Sequence identity — approved molecule reference",
                "ada_display": ada,
                "target": row.get("targets") or None,
                "format": row.get("format") or None,
            }
        )
        break
    return out


def _merge_ada_refs(primary: List[Dict[str, Any]], secondary: List[Dict[str, Any]], *, max_n: int) -> List[Dict[str, Any]]:
    seen: set = set()
    out: List[Dict[str, Any]] = []
    for bucket in (primary, secondary):
        for r in bucket:
            if not isinstance(r, dict):
                continue
            n = str(r.get("name") or "").strip()
            key = n or str(id(r))
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
            if len(out) >= max_n:
                return out
    return out


def _has_real_clinical_sequence(row: Dict[str, Any]) -> bool:
    heavy = str(row.get("arm1_heavy") or row.get("vh_seq") or "")
    light = str(row.get("arm1_light") or row.get("vl_seq") or "")
    # Regular antibody ADA context requires sequence-backed VH+VL entries.
    return _is_real_protein_sequence(heavy, min_len=90) and _is_real_protein_sequence(light, min_len=85)


def _risk_from_index_and_parameters(index: Optional[float], parameters: List[Dict[str, Any]]) -> str:
    high = sum(1 for p in parameters if p.get("risk") == "HIGH")
    moderate = sum(1 for p in parameters if p.get("risk") == "MODERATE")
    hard_high = any(
        p.get("key") in HARD_FAIL_PARAMETERS and p.get("risk") == "HIGH"
        for p in parameters
    )
    if hard_high or high >= 2 or (index is not None and index < 40):
        return "HIGH"
    if high == 1 or moderate >= 4 or (index is not None and index < 60):
        return "MODERATE"
    return "LOW"
