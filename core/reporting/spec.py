"""
spec.py — InSynBio Report Contract
====================================
Defines the minimum metadata, naming rules, and section skeleton that
every InSynBio report must satisfy.

This is the SINGLE SOURCE OF TRUTH for report structure.
Project-specific generators should import from here rather than
hard-coding metadata or naming conventions.

Version history:
  v1.0  2026-04-02  Initial: ReportSpec, ReportFamily, generic CHAPTER_SKELETON
  v1.1  2026-04-02  Added per-family CHAPTER_SKELETONS dict, ChapterEntry schema,
                    ReportSpec.chapter_schema() — BioChatter integration support
  v1.2  2026-04-02  Added methodology_reliability chapter to all client schemas;
                    dual-report architecture formalised (CLIENT vs INTERNAL)
  v1.3  2026-04-06  Added 4 new ReportFamily values and chapter skeletons:
                    HAPTEN_VAM (12 ch), ADC_DESIGN (10 ch), VACCINE_DESIGN (11 ch),
                    EPIDESIGN (10 ch). All include _EVIDENCE_TRACEABILITY +
                    _METHODOLOGY_RELIABILITY. Replaces GENERAL fallback for these
                    analysis types.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Optional


class ReportFamily(str, Enum):
    """Exhaustive list of report types generated across InSynBio projects."""
    VHVL_HUMANIZATION = "vhvl_humanization"
    VHH_HUMANIZATION  = "vhh_humanization"
    VHH_CMC           = "vhh_cmc"
    BISPECIFIC_CMC    = "bispecific_cmc"
    VAM               = "vam"
    HAPTEN_VAM        = "hapten_vam"        # v1.3 — small-molecule antigen VAM (Scenario D)
    CAR_DESIGN        = "car_design"
    ADC_DESIGN        = "adc_design"        # v1.3 — antibody-drug conjugate design
    VACCINE_DESIGN    = "vaccine_design"    # v1.3 — multi-epitope vaccine construct
    EPIDESIGN         = "epidesign"         # v1.3 — pMHC-TCR peptide antigen design
    STRUCTURE_RUN     = "structure_run"
    GENERAL           = "general"


class Audience(str, Enum):
    CLIENT   = "client"
    INTERNAL = "internal"
    COMBINED = "combined"


# ---------------------------------------------------------------------------
# Chapter schema — per-family section definitions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ChapterEntry:
    """Schema for a single report chapter.

    Attributes
    ----------
    key:            Machine-readable ID (used in filenames, BioChatter queries).
    title_zh:       Canonical Chinese section heading.
    title_en:       Canonical English section heading.
    required:       If True, the chapter MUST appear in every report of this family.
    audience:       Which audience sees this chapter (None = all audiences).
    required_fields: List of data fields that must be present (for BioChatter validation).
    description:    One-sentence summary of chapter content.
    """
    key: str
    title_zh: str
    title_en: str
    required: bool = True
    audience: Optional[str] = None          # None = all; "client" | "internal"
    required_fields: tuple[str, ...] = ()
    description: str = ""


# ── Shared chapter: evidence traceability (injected into every report) ──────
_EVIDENCE_TRACEABILITY = ChapterEntry(
    key="evidence_traceability",
    title_zh="",
    title_en="Evidence Traceability & Trust Level",
    required=True,
    audience=None,
    required_fields=("ada_tier", "evidence_source"),
    description=(
        "ADA 、PMID/FDA 、"
        "。 EvidenceGate 。"
    ),
)

# ── Shared chapter injected into every client-facing report ─────────────────
_METHODOLOGY_RELIABILITY = ChapterEntry(
    key="methodology_reliability",
    title_zh="",
    title_en="Methodology Reliability Statement",
    required=True,
    audience=None,          # present in both CLIENT and INTERNAL; content differs
    required_fields=("benchmark_reference", "confidence_statement"),
    description=(
        "、、"
        "。；。"
    ),
)

# ── Generic fallback ────────────────────────────────────────────────────────
_GENERIC: list[ChapterEntry] = [
    ChapterEntry("cover",                    "",         "Cover",                    True),
    ChapterEntry("executive_summary",        "",      "Executive Summary",         True,
                 required_fields=("conclusion", "recommendation")),
    ChapterEntry("main_analysis",            "",      "Main Analysis",             True),
    _EVIDENCE_TRACEABILITY,
    _METHODOLOGY_RELIABILITY,
    ChapterEntry("risk_limitations",         "",    "Risks & Limitations",       True),
    ChapterEntry("conclusions_recommendations", "", "Conclusions & Recommendations", True,
                 required_fields=("final_recommendation",)),
    ChapterEntry("appendix",                 "",         "Appendix",                  False),
]

# ── VH/VL Humanization (CURSOR_REPORT_ENGINE V4.1, 13 mandatory chapters) ──
_VHVL_HUM: list[ChapterEntry] = [
    ChapterEntry("cover",                "",             "Cover",                     True),
    ChapterEntry("overview",             "",             "Overview",                  True,
                 required_fields=("antibody_name", "target", "species")),
    ChapterEntry("input_qc",             "QC",       "Input Sequence QC",         True,
                 required_fields=("vh_seq", "vl_seq", "length_check")),
    ChapterEntry("imgt_segmentation",    "IMGT",     "IMGT Segmentation",         True,
                 required_fields=("cdr1","cdr2","cdr3","fr1","fr2","fr3","fr4")),
    ChapterEntry("germline_match",       "Germline",     "Germline Match & Interpretation", True,
                 required_fields=("vh_germline","vl_germline","identity_pct")),
    ChapterEntry("vernier_zone",         "Vernier Zone", "Vernier Zone Analysis",     True,
                 required_fields=("vernier_positions", "backmutation_rationale")),
    ChapterEntry("hallmark_check",       "Hallmark",     "VH/VHH Hallmark Check",     True),
    ChapterEntry("cmc_liabilities",      "CMC",          "CMC Liabilities",           True,
                 required_fields=("liability_list", "severity")),
    ChapterEntry("immunogenicity",       "",         "Immunogenicity",            True,
                 required_fields=("iedb_score", "t_cell_epitopes")),
    ChapterEntry("developability",       "",       "Developability",            True,
                 required_fields=("pi", "gravy", "instability_index")),
    ChapterEntry("mutation_tiers",       "",         "Mutation Tiers (0–3)",      True,
                 required_fields=("tier0","tier1","tier2","tier3"),
                 description="Tier 0=, 1=, 2=, 3="),
    ChapterEntry("final_sequences",      "",     "Three Final Sequences",     True,
                 required_fields=("seq1","seq2","seq3"),
                 description="Seq1=T1, Seq2=T1+T2, Seq3=T1+T3"),
    ChapterEntry("optional_menu",        "",     "Optional Mutation Menu",    True),
    _EVIDENCE_TRACEABILITY,
    _METHODOLOGY_RELIABILITY,
    ChapterEntry("conclusions_recommendations", "",  "Final Recommendations",     True,
                 required_fields=("recommended_sequence",)),
    ChapterEntry("glossary",             "",           "Glossary",                  True),
    ChapterEntry("appendix",             "",             "Appendix",                  False,
                 audience="internal"),
]

# ── VHH Humanization ────────────────────────────────────────────────────────
_VHH_HUM: list[ChapterEntry] = [
    ChapterEntry("cover",                "",             "Cover",                     True),
    ChapterEntry("overview",             "",             "Overview",                  True,
                 required_fields=("vhh_name", "target", "strategy")),
    ChapterEntry("input_qc",             "QC",       "Input Sequence QC",         True,
                 required_fields=("vhh_seq", "length_check", "hallmark_check")),
    ChapterEntry("imgt_segmentation",    "IMGT",     "IMGT Segmentation",         True,
                 required_fields=("cdr1","cdr2","cdr3","fr1","fr2","fr3","fr4")),
    ChapterEntry("germline_match",       "Germline",     "Germline Match",            True,
                 required_fields=("vh_germline","identity_pct")),
    ChapterEntry("tier_analysis",        "Tier",     "Tier Position Analysis",    True,
                 required_fields=("tier0","tier1","tier2","tier3"),
                 description="Tier 0=7 Hallmark+Vernier; 1=8 +Vernier; 2=14 ; 3=5 FR1"),
    ChapterEntry("vernier_zone",         "Vernier Zone", "Vernier Zone Analysis",     True,
                 required_fields=("anchor_positions", "tuning_positions")),
    ChapterEntry("cmc_liabilities",      "CMC",          "CMC Liabilities",           True,
                 required_fields=("pi","gravy","adi_score")),
    ChapterEntry("immunogenicity",       "",         "Immunogenicity",            True),
    ChapterEntry("three_strategies",     "",       "Three Humanization Strategies", True,
                 required_fields=("S1","S2","S3"),
                 description="S1=Tier0(7mut), S2=Tier0+1(15mut), S3=Tier0+1+2(29mut)"),
    _EVIDENCE_TRACEABILITY,
    _METHODOLOGY_RELIABILITY,
    ChapterEntry("conclusions_recommendations", "",  "Final Recommendations",     True,
                 required_fields=("recommended_strategy",)),
    ChapterEntry("glossary",             "",           "Glossary",                  True),
    ChapterEntry("appendix",             "",             "Appendix",                  False,
                 audience="internal"),
]

# ── VHH CMC ─────────────────────────────────────────────────────────────────
_VHH_CMC: list[ChapterEntry] = [
    ChapterEntry("cover",                "",             "Cover",                     True),
    ChapterEntry("executive_summary",    "",         "Executive Summary",         True,
                 required_fields=("adi_score", "overall_flag")),
    ChapterEntry("sequence_input",       "QC",     "Sequence Input & QC",       True,
                 required_fields=("vhh_seq","length","numbering")),
    ChapterEntry("metric_panel",         "15",       "15-Metric CMC Panel",       True,
                 required_fields=("pi","gravy","instability","net_charge",
                                  "hydro_patch","charge_patch","sap_score",
                                  "agg_motifs","free_cys","liability_count")),
    ChapterEntry("adi_scoring",          "ADI",          "ADI Score",                 True,
                 required_fields=("adi_score","adi_category"),
                 description="Flag-discrete: PASS=100/WARN=50/FAIL=0, VHH42 reference"),
    ChapterEntry("developability",       "",       "Developability Assessment", True,
                 required_fields=("pass_count","warn_count","fail_count")),
    _EVIDENCE_TRACEABILITY,
    _METHODOLOGY_RELIABILITY,
    ChapterEntry("risk_limitations",     "",       "Risks & Limitations",       True),
    ChapterEntry("conclusions_recommendations", "","Conclusions",               True,
                 required_fields=("go_nogo",)),
    ChapterEntry("appendix",             "",             "Appendix",                  False,
                 audience="internal",
                 required_fields=("raw_scores",)),
]

# ── Bispecific CMC ───────────────────────────────────────────────────────────
_BISPECIFIC_CMC: list[ChapterEntry] = [
    ChapterEntry("cover",                "",             "Cover",                     True),
    ChapterEntry("executive_summary",    "",         "Executive Summary",         True,
                 required_fields=("arm_a_adi","arm_b_adi","smartlink_recommendation")),
    ChapterEntry("arm_a_cmc",            "Arm A CMC",    "Arm A CMC Assessment",      True,
                 required_fields=("arm_a_metrics",)),
    ChapterEntry("arm_b_cmc",            "Arm B CMC",    "Arm B CMC Assessment",      True,
                 required_fields=("arm_b_metrics",)),
    ChapterEntry("fusion_pi_matrix",     "pI",       "Fusion pI Matrix",          True,
                 required_fields=("linker_panel","fusion_pi_table","er_flag"),
                 description="≥5 linkers; ER expression flag pI>8.5"),
    ChapterEntry("smartlink_recommendation", "SmartLink", "SmartLink™ Recommendation", True,
                 required_fields=("primary_linker","runner_up_linker")),
    _EVIDENCE_TRACEABILITY,
    _METHODOLOGY_RELIABILITY,
    ChapterEntry("risk_limitations",     "",       "Risks & Limitations",       True),
    ChapterEntry("conclusions_recommendations", "", "Conclusions",              True,
                 required_fields=("recommended_construct",)),
    ChapterEntry("appendix",             "",             "Appendix",                  False,
                 audience="internal"),
]

# ── Virtual Affinity Maturation ─────────────────────────────────────────────
_VAM: list[ChapterEntry] = [
    ChapterEntry("cover",                "",             "Cover",                     True),
    ChapterEntry("executive_summary",    "",         "Executive Summary",         True,
                 required_fields=("antibody_name","target","top_candidate","ddg_improvement"),
                 description="：、ΔΔG、"),
    ChapterEntry("structure_quality",    "",     "Structure Quality Assessment", True,
                 required_fields=("structure_source","ipTM","pLDDT_interface",
                                  "bsa","cluster_concentration"),
                 description="、AF2/HADDOCK3"),
    ChapterEntry("interface_analysis",   "",     "Interface Contact Analysis", True,
                 required_fields=("contact_residues","contact_count_per_residue","bsa_total"),
                 description="；"),
    ChapterEntry("mutation_scan_l1",     "L1",       "Mutation Scan — Tier 1 (EvoEF2)", True,
                 required_fields=("scan_scope","total_mutations_evaluated",
                                  "l1_candidates","evoef2_ddg_range"),
                 description="EvoEF2；=0"),
    ChapterEntry("stability_sequence_filter", "", "Stability & Sequence Filter (L2)", True,
                 required_fields=("thermompnn_vetoes","ablang_warnings","l2_passing"),
                 description="ThermoMPNN(>+0.5)；AbLang/AntiFold"),
    ChapterEntry("cmc_gate",             "CMC",    "CMC Developability Gate",   True,
                 required_fields=("pi_shifts","cmc_vetoes","cmc_passing"),
                 description="pI；GRAVY；"),
    ChapterEntry("precision_energy",     "MM/GBSA",      "Precision Energy (MM/GBSA)", True,
                 required_fields=("wt_baseline","candidates_ddg","batch_id"),
                 description="Phase 4 ；WT；"),
    ChapterEntry("double_mutation",      "",     "Double Mutation Epistasis", False,
                 required_fields=("pair_candidates","nonadditivity_term","epistasis_flag"),
                 description="Phase 4.5 ；Cβ–Cβ≤25Å；<-5 kcal/mol"),
    ChapterEntry("final_candidates",     "",     "Final Candidate Sequences", True,
                 required_fields=("candidate_rank","sequences","mutations","ddg_final"),
                 description="；Kabat；WT"),
    _EVIDENCE_TRACEABILITY,
    _METHODOLOGY_RELIABILITY,
    ChapterEntry("risk_limitations",     "",       "Risks & Limitations",       True,
                 required_fields=("structure_confidence","tool_limitations"),
                 description="；"),
    ChapterEntry("conclusions_recommendations", "", "Conclusions & Recommendations", True,
                 required_fields=("recommended_candidate","next_steps")),
    ChapterEntry("appendix",             "",             "Appendix",                  False,
                 audience="internal",
                 required_fields=("raw_evoef2_csv","raw_mmgbsa_csv",
                                  "thermompnn_results","ablang_results")),
]

# ── CAR-T Design ─────────────────────────────────────────────────────────────
_CAR_DESIGN: list[ChapterEntry] = [
    ChapterEntry("cover",                "",             "Cover",                     True),
    ChapterEntry("executive_summary",    "",         "Executive Summary",         True,
                 required_fields=("target","car_construct","key_features")),
    ChapterEntry("target_analysis",      "",         "Target Analysis",           True,
                 required_fields=("target_name","expression_profile","epitope_region")),
    ChapterEntry("binder_design",        "",       "Antigen-Binding Domain Design", True,
                 required_fields=("scfv_or_vhh","vh_seq","vl_seq_or_na",
                                  "linker","orientation"),
                 description="scFvVHH；VH-linker-VL；"),
    ChapterEntry("construct_design",     "Construct", "Full CAR Construct Design", True,
                 required_fields=("signal_peptide","binder","hinge","tm_domain",
                                  "co_stimulatory","cd3z","full_sequence"),
                 description="→→→→→CD3ζ"),
    ChapterEntry("cmc_assessment",       "CMC",    "CMC Developability",        True,
                 required_fields=("pi","gravy","adi_score","liabilities")),
    ChapterEntry("immunogenicity",       "",     "Immunogenicity Assessment", True),
    ChapterEntry("structural_model",     "",         "Structural Model",          False,
                 required_fields=("af2_ipTM","model_source"),
                 description="AF2-Multimer；"),
    _EVIDENCE_TRACEABILITY,
    _METHODOLOGY_RELIABILITY,
    ChapterEntry("risk_limitations",     "",       "Risks & Limitations",       True),
    ChapterEntry("conclusions_recommendations", "", "Conclusions & Recommendations", True,
                 required_fields=("recommended_construct","validation_plan")),
    ChapterEntry("appendix",             "",             "Appendix",                  False,
                 audience="internal"),
]

# ── Structure Run ────────────────────────────────────────────────────────────
_STRUCTURE_RUN: list[ChapterEntry] = [
    ChapterEntry("cover",                "",             "Cover",                     True),
    ChapterEntry("executive_summary",    "",         "Executive Summary",         True),
    ChapterEntry("input_structures",     "",         "Input Structures",          True,
                 required_fields=("pdb_sources","chain_ids","resolution_or_model")),
    ChapterEntry("docking_results",      "",         "Docking Results",           True,
                 required_fields=("cluster_count","best_cluster_score",
                                  "cluster_concentration","irmsd","fnat","dockq")),
    ChapterEntry("interface_quality",    "",         "Interface Quality",         True,
                 required_fields=("bsa","ipTM","contact_residues")),
    _EVIDENCE_TRACEABILITY,
    _METHODOLOGY_RELIABILITY,
    ChapterEntry("risk_limitations",     "",       "Risks & Limitations",       True),
    ChapterEntry("conclusions_recommendations", "", "Conclusions",              True),
    ChapterEntry("appendix",             "",             "Appendix",                  False,
                 audience="internal",
                 required_fields=("all_cluster_scores",)),
]


# ── Hapten VAM (Scenario D — small molecule antigen) ─────────────────────────
_HAPTEN_VAM: list[ChapterEntry] = [
    ChapterEntry("cover",                "",             "Cover",                     True),
    ChapterEntry("executive_summary",    "",         "Executive Summary",         True,
                 required_fields=("antibody_name", "hapten", "top_candidate", "ddg_improvement"),
                 description="：、ΔΔG、CMC、"),
    ChapterEntry("structure_docking",    "",   "Structure Modeling & Docking", True,
                 required_fields=("structure_tool", "docking_tool", "best_pose_score",
                                  "cluster_concentration"),
                 description="ABodyBuilder2；Vina；HallucinationGuard DOCKING_SCORE"),
    ChapterEntry("numbering_map",        "IMGT-", "IMGT–Linear Position Map",  True,
                 required_fields=("imgt_positions", "linear_positions", "numbering_tool"),
                 description="；IMGT-to-linear；"),
    ChapterEntry("contact_analysis",     "",     "Contact Interface Analysis", True,
                 required_fields=("contact_residues", "cdr_contact_ratio", "cutoff_angstrom"),
                 description="4Å；CDR(≥50%)；"),
    ChapterEntry("ala_scan",             "",       "Alanine Scan (EvoEF2)",     True,
                 required_fields=("scan_positions", "ala_ddg_range", "hotspot_residues"),
                 description="Ala；ΔΔG；HallucinationGuard SEQ_BACK_CHECK"),
    ChapterEntry("saturation_scan",      "",     "Saturation Scan",           True,
                 required_fields=("hotspot_positions", "best_mutations", "evoef2_ddg_top10"),
                 description="；Top-10；EVOEF2_ARTIFACT"),
    ChapterEntry("combo_scan",           "",     "Combination Mutation Scan", True,
                 required_fields=("combo_candidates", "combo_ddg", "epistasis_flag"),
                 description="/；；MUTANT_DIFF"),
    ChapterEntry("cmc_gate",             "CMC",    "CMC Developability Gate",   True,
                 required_fields=("pi_wt", "pi_mutant", "ii_wt", "ii_mutant", "cmc_status"),
                 description="CMC：pI 4.0–9.5，II<45；WT"),
    ChapterEntry("hallucination_audit",  "",       "HallucinationGuard Audit",  True,
                 required_fields=("audit_file", "hard_abort_count", "warn_count"),
                 description="_hallucination_audit.json；HARD ABORT=0"),
    _EVIDENCE_TRACEABILITY,
    _METHODOLOGY_RELIABILITY,
    ChapterEntry("risk_limitations",     "",       "Risks & Limitations",       True,
                 required_fields=("vina_accuracy", "evoef2_accuracy", "experimental_validation"),
                 description="；EvoEF2 hapten；"),
    ChapterEntry("final_candidates",     "",     "Final Candidate Sequences", True,
                 required_fields=("candidate_rank", "sequences", "mutations",
                                  "ddg_final", "cmc_pi", "cmc_ii"),
                 description="；FASTA；MUTANT_DIFF"),
    ChapterEntry("conclusions_recommendations", "", "Conclusions",              True,
                 required_fields=("recommended_candidate", "next_steps")),
    ChapterEntry("appendix",             "",             "Appendix",                  False,
                 audience="internal",
                 required_fields=("ala_scan_csv", "sat_scan_csv", "combo_scan_csv",
                                  "hallucination_audit_json")),
]

# ── ADC Design ────────────────────────────────────────────────────────────────
_ADC_DESIGN: list[ChapterEntry] = [
    ChapterEntry("cover",                "",             "Cover",                     True),
    ChapterEntry("executive_summary",    "",         "Executive Summary",         True,
                 required_fields=("target", "recommended_adc", "dar", "linker", "payload"),
                 description="ADC；DAR；；FTO"),
    ChapterEntry("target_analysis",      "",         "Target Validation",         True,
                 required_fields=("target_name", "target_tier", "expression_profile",
                                  "internalization_rate"),
                 description="Tier；；；"),
    ChapterEntry("binder_selection",     "",       "Antibody Binder Selection", True,
                 required_fields=("binder_name", "affinity_kd", "humanization_status",
                                  "cdc_adcc_status"),
                 description="；；；Fc"),
    ChapterEntry("linker_design",        "",       "Linker Design",             True,
                 required_fields=("linker_type", "linker_stability", "cleavage_mechanism"),
                 description="vs；；DAR"),
    ChapterEntry("payload_selection",    "",         "Payload Selection",         True,
                 required_fields=("payload_name", "moa", "payload_tier",
                                  "bystander_effect", "resistance_risk"),
                 description="；Tier；；"),
    ChapterEntry("adc_proposal",         "ADC",      "ADC Proposal Summary",      True,
                 required_fields=("rank", "safety_warnings", "FTO_alerts",
                                  "precedent_programs", "scoring"),
                 description="ADCProposal schema；Top-3"),
    ChapterEntry("cmc_assessment",       "CMC",      "CMC Manufacturability",     True,
                 required_fields=("dar_range", "aggregation_risk", "conjugation_site"),
                 description="DAR 2–4 PASS；>8 FAIL；"),
    ChapterEntry("safety_fto",           "FTO",      "Safety & FTO",              True,
                 required_fields=("safety_warning_list", "fto_alert_list"),
                 description="Tier-1+；ADC FTO"),
    _EVIDENCE_TRACEABILITY,
    _METHODOLOGY_RELIABILITY,
    ChapterEntry("risk_limitations",     "",       "Risks & Limitations",       True),
    ChapterEntry("conclusions_recommendations", "", "Conclusions",              True,
                 required_fields=("recommended_adc", "development_roadmap")),
    ChapterEntry("appendix",             "",             "Appendix",                  False,
                 audience="internal",
                 required_fields=("decision_tree_trace", "raw_scores")),
]

# ── Multi-Epitope Vaccine Design ──────────────────────────────────────────────
_VACCINE_DESIGN: list[ChapterEntry] = [
    ChapterEntry("cover",                "",             "Cover",                     True),
    ChapterEntry("executive_summary",    "",         "Executive Summary",         True,
                 required_fields=("vaccine_name", "n_epitopes", "population_coverage",
                                  "junction_new_binders"),
                 description="：、、(<3)"),
    ChapterEntry("epitope_collection",   "",         "Epitope Collection",        True,
                 required_fields=("mhci_epitopes", "mhcii_epitopes", "source_antigens",
                                  "prediction_tools"),
                 description="MHC-I / MHC-II ；IC50；HLA"),
    ChapterEntry("spacer_design",        "",     "Spacer Design",             True,
                 required_fields=("spacer_library", "spacer_assignments"),
                 description="AAY(MHC-I)、GPGPG(MHC-II)、PADRE；，"),
    ChapterEntry("junction_check",       "", "Junction Neoepitope Check", True,
                 required_fields=("junction_sequences", "new_binder_count", "junction_status"),
                 description="15-mer；new_binders>2→FAIL"),
    ChapterEntry("ordering_optimization","",         "Epitope Ordering Optimization", True,
                 required_fields=("ordering_algorithm", "final_order", "optimization_score")),
    ChapterEntry("construct_assembly",   "",       "Construct Assembly",        True,
                 required_fields=("signal_peptide", "full_sequence", "mitd_fusion",
                                  "construct_length"),
                 description="→→→MITD；；"),
    ChapterEntry("codon_optimization",   "",       "Codon Optimization",        True,
                 required_fields=("target_expression_system", "cai_score", "mrna_sequence"),
                 description="CAI≥0.8；"),
    ChapterEntry("population_coverage",  "",       "Population Coverage",       True,
                 required_fields=("mhci_coverage_pct", "mhcii_coverage_pct",
                                  "supertype_distribution"),
                 description="MHC-I≥70% PASS；MHC-II≥50% PASS"),
    _EVIDENCE_TRACEABILITY,
    _METHODOLOGY_RELIABILITY,
    ChapterEntry("risk_limitations",     "",       "Risks & Limitations",       True,
                 required_fields=("prediction_accuracy", "experimental_validation_plan")),
    ChapterEntry("conclusions_recommendations", "", "Conclusions",              True,
                 required_fields=("recommended_construct", "immunization_schedule")),
    ChapterEntry("appendix",             "",             "Appendix",                  False,
                 audience="internal",
                 required_fields=("all_epitopes_csv", "junction_scan_csv",
                                  "codon_optimization_log")),
]

# ── EpiDesignCore — pMHC-TCR Peptide Antigen Design ──────────────────────────
_EPIDESIGN: list[ChapterEntry] = [
    ChapterEntry("cover",                "",             "Cover",                     True),
    ChapterEntry("executive_summary",    "",         "Executive Summary",         True,
                 required_fields=("target_hla", "peptide_name", "best_ic50",
                                  "dockq_score", "recommendation"),
                 description="：HLA、DockQ、"),
    ChapterEntry("hla_target",           "HLA", "HLA Target & Disease Context", True,
                 required_fields=("hla_allele", "disease_indication", "epitope_source_protein"),
                 description="HLA；；"),
    ChapterEntry("peptide_design",       "",       "Peptide Design",            True,
                 required_fields=("peptide_sequence", "peptide_length", "anchor_residues"),
                 description="AfDesign/BindCraft；"),
    ChapterEntry("mhc_binding",          "MHC",    "MHC Binding Affinity",      True,
                 required_fields=("predicted_ic50", "mhcflurry_score", "netmhcpan_score",
                                  "binding_percentile_rank"),
                 description="MHCflurry + NetMHCpan；IC50<50nM"),
    ChapterEntry("structure_quality",    "pMHC",   "pMHC Complex Structure",    True,
                 required_fields=("structure_source", "ipTM", "pLDDT_peptide",
                                  "bsa", "dockq"),
                 description="AfDesign/HADDOCK3；DockQ≥0.4"),
    ChapterEntry("tcr_compatibility",    "TCR",    "TCR Compatibility",         True,
                 required_fields=("tcr_contact_residues", "exposure_score"),
                 description="TCR；"),
    ChapterEntry("cross_reactivity",     "",   "Cross-Reactivity Assessment", True,
                 required_fields=("blast_results", "human_proteome_similarity",
                                  "autoimmune_risk_flag"),
                 description="BLAST；>70%→WARN"),
    _EVIDENCE_TRACEABILITY,
    _METHODOLOGY_RELIABILITY,
    ChapterEntry("risk_limitations",     "",       "Risks & Limitations",       True,
                 required_fields=("prediction_accuracy", "immunodominance_caveat")),
    ChapterEntry("conclusions_recommendations", "", "Conclusions",              True,
                 required_fields=("recommended_peptide", "validation_assay")),
    ChapterEntry("appendix",             "",             "Appendix",                  False,
                 audience="internal",
                 required_fields=("afdesign_trajectory", "haddock3_clusters",
                                  "mhcflurry_full_table")),
]

# Master lookup: ReportFamily → ordered chapter list
CHAPTER_SKELETONS: dict[ReportFamily, list[ChapterEntry]] = {
    ReportFamily.VHVL_HUMANIZATION : _VHVL_HUM,
    ReportFamily.VHH_HUMANIZATION  : _VHH_HUM,
    ReportFamily.VHH_CMC            : _VHH_CMC,
    ReportFamily.BISPECIFIC_CMC     : _BISPECIFIC_CMC,
    ReportFamily.VAM                : _VAM,
    ReportFamily.HAPTEN_VAM         : _HAPTEN_VAM,
    ReportFamily.CAR_DESIGN         : _CAR_DESIGN,
    ReportFamily.ADC_DESIGN         : _ADC_DESIGN,
    ReportFamily.VACCINE_DESIGN     : _VACCINE_DESIGN,
    ReportFamily.EPIDESIGN          : _EPIDESIGN,
    ReportFamily.STRUCTURE_RUN      : _STRUCTURE_RUN,
    ReportFamily.GENERAL            : _GENERIC,
}

# Legacy flat list — kept for backward compatibility
CHAPTER_SKELETON = [c.key for c in _GENERIC]


# ---------------------------------------------------------------------------
# ReportSpec
# ---------------------------------------------------------------------------

@dataclass
class ReportSpec:
    """Metadata contract that every report must carry.

    Construct one at report-generation time; pass to renderers so that
    cover pages, headers, footers, and filenames are all consistent.
    """
    report_id: str                              # e.g. "ISB-MAL-CARM-001"
    project_id: str                             # e.g. "malaria_CAR_M"
    family: ReportFamily = ReportFamily.GENERAL
    audience: Audience = Audience.COMBINED
    version: str = "v1.0"
    report_date: date = field(default_factory=date.today)
    confidentiality: str = " · "
    institution: str = "InSynBio"
    engine: str = "ACTES"
    title: str = ""
    subtitle: str = ""
    extra_meta: dict = field(default_factory=dict)

    # ── chapter schema ───────────────────────────────────────────────────

    def chapter_schema(
        self,
        audience_filter: Optional[str] = None,
        required_only: bool = False,
    ) -> list[ChapterEntry]:
        """Return the ordered chapter list for this report's family.

        Parameters
        ----------
        audience_filter : str | None
            If set ("client" | "internal"), exclude chapters whose
            ``audience`` field doesn't match.  None = return all chapters.
        required_only : bool
            If True, return only chapters where ``required=True``.

        Returns
        -------
        list[ChapterEntry]
            Ordered chapters filtered by the given criteria.

        Notes
        -----
        BioChatter can call this method to validate that a report draft
        contains all mandatory sections and required data fields before
        delivery.  Example::

            spec = ReportSpec("ISB-001", "my_project", ReportFamily.VAM)
            for ch in spec.chapter_schema(required_only=True):
                print(ch.key, ch.required_fields)
        """
        chapters = CHAPTER_SKELETONS.get(self.family, _GENERIC)
        if required_only:
            chapters = [c for c in chapters if c.required]
        if audience_filter is not None:
            chapters = [
                c for c in chapters
                if c.audience is None or c.audience == audience_filter
            ]
        return chapters

    def validate_content(self, content: dict) -> list[str]:
        """Check that ``content`` dict satisfies all required fields.

        Parameters
        ----------
        content : dict
            Mapping of field names to values.  Used by BioChatter to
            verify a generated report before rendering.

        Returns
        -------
        list[str]
            List of missing field names.  Empty list = report is complete.
        """
        missing: list[str] = []
        for ch in self.chapter_schema(required_only=True):
            for f in ch.required_fields:
                if f not in content or content[f] is None:
                    missing.append(f"{ch.key}.{f}")
        return missing

    # ── derived helpers ──────────────────────────────────────────────────

    def filename_stem(self) -> str:
        """Standard filename: {project_id}_{family}_{audience}_v{n}"""
        return (
            f"{self.project_id}_{self.family.value}"
            f"_{self.audience.value}_{self.version}"
        )

    def md_path(self, out_dir: str | Path = ".") -> Path:
        return Path(out_dir) / f"{self.filename_stem()}.md"

    def pdf_path(self, out_dir: str | Path = ".") -> Path:
        return Path(out_dir) / f"{self.filename_stem()}.pdf"

    def html_path(self, out_dir: str | Path = ".") -> Path:
        return Path(out_dir) / f"{self.filename_stem()}.html"

    def header_left(self) -> str:
        return f"{self.report_id}  {self.title}" if self.title else self.report_id

    def header_right(self) -> str:
        return (
            f"{self.institution} {self.engine}  ·  "
            f"{self.report_date.isoformat()}  ·  "
        )

    def footer_center(self, page_no: int) -> str:
        return f"— {page_no} —"

    def cover_meta_rows(self) -> list[list[str]]:
        rows = [["", self.report_id]]
        for k, v in self.extra_meta.items():
            rows.append([k, str(v)])
        rows += [
            ["", self.version],
            ["", self.report_date.isoformat()],
            ["", f"{self.institution} {self.engine}"],
            ["", self.confidentiality],
        ]
        return rows
