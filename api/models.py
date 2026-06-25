"""
api/models.py  —  Pydantic request / response schemas for all 5 endpoints
"""
from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ── Shared ────────────────────────────────────────────────────────────────────

class JobStatus(BaseModel):
    job_id: str
    status: str                       # queued | running | done | failed
    progress: int = 0                 # 0–100
    progress_note: Optional[str] = None  # human-readable stage (long jobs; poll UI)
    elapsed_sec: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    report_url: Optional[str] = None  # /files/{job_id}/humanization_report.html
    error: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None  # e.g. zip_url, pdf_report_url; VHH: fasta_url


# ── Humanization: VH/VL ───────────────────────────────────────────────────────

class VHVLRequest(BaseModel):
    vh_sequence: str = Field(..., description="Donor-species VH amino acid sequence")
    vl_sequence: str = Field(..., description="Donor-species VL amino acid sequence")
    project_name: str = Field(
        "",
        description="Optional project / sequence label for reports and archive mirror; when blank the server uses job_id.",
    )
    source_species: str = Field("mouse", description="Source species routed to V4.8.0 donor_species: mouse | rat")
    report_format: str = Field(
        "both",
        description=(
            "pdf | html | both — which report artifact(s) to generate. "
            "Delivery ZIP always includes README + FASTAs + optional PDBs, and packs whichever "
            "report file(s) were produced (PDF and/or HTML)."
        ),
    )
    report_language: str = Field(
        "en",
        description="Ignored in public deployment: VH/VL customer HTML/PDF are English-only.",
    )
    repair_mode: str = Field("standard", description="standard | rescue")
    back_mutation_strategy: str = Field("standard", description="standard | structure_guided | aggressive")
    dry_run_structure: bool = Field(False, description="If True, skips structure modeling")
    skip_iedb: bool = Field(True, description="If True, skips IEDB immunogenicity prediction")
    surface_reshape_on_qc_fail: bool = Field(
        True,
        description=(
            "When True: if framework compatibility is poor or checklist outcome is WARN/FAIL, "
            "evaluate V5.4 structure-driven FR surface reshaping as a CDR-preserving fallback. "
            "Does not bundle AbEvaluator."
        ),
    )
    integrated_cmc: Literal["minimal", "full"] = Field(
        "minimal",
        description=(
            "Deprecated: post-humanization AbEvaluator bundling was removed from VH/VL jobs. "
            "Value is ignored — use the standalone CMC IgG endpoint for AbRef-458 / full advisor."
        ),
    )

class VHVLResult(BaseModel):
    """Key parameters returned after VH/VL humanization."""
    # Identity & framework
    vh_germline: str
    vh_germline_identity: Optional[float]   # % identity to selected human germline
    vl_germline: str
    vl_germline_identity: Optional[float]

    # CDR
    cdr_canonical_class: Optional[str]      # e.g. "H1-13 H2-10 H3-9 L1-11 L2-7 L3-9"
    cdrs: Dict[str, str]                    # {H1: "GFTFSS", H2: ..., L1: ..., ...}

    # Humanness
    ablang_score: Optional[float]           # mean log-likelihood (higher = more human)
    framework_human_identity_vh: Optional[float]
    framework_human_identity_vl: Optional[float]

    # Vernier
    vernier_risk_positions: List[str]       # e.g. ["VH-H37", "VH-L78"]
    backmutation_count: int

    # Structure (IgFold if available, else DRY_RUN)
    structure_computed: bool
    rmsd_to_reference: Optional[float]     # Å, vs mouse parent

    # Checklist
    checklist_status: str                  # PASS | WARN | FAIL
    checklist_phases_passed: int
    flags: List[str]

    # Top candidate sequences
    humanized_vh: str
    humanized_vl: str
    candidates: List[Dict[str, Any]]       # rank, vh, vl, identity, ablang

    # Clinical antibodies with matching VH/VL germline (ThErA-SAbDAb + ADA panel); optional in JobStatus.result
    clinical_precedents: Optional[List[Dict[str, Any]]] = None
    clinical_reference: Optional[Dict[str, Any]] = None


# ── Humanization: VHH ────────────────────────────────────────────────────────

class VHHRequest(BaseModel):
    vhh_sequence: str = Field(..., description="Camelid/alpaca VHH amino acid sequence")
    source_species: str = Field("alpaca", description="alpaca | camel | llama | dog")
    strategy: str = Field("A", description="A=conservative | B=moderate | C=aggressive | all")
    top_k: int = Field(3, description="Number of top candidates to return")
    report_format: str = Field("pdf", description="pdf | html | both")
    project_name: str = Field("demo", description="Client project label (paired with sequence_name for reports)")
    sequence_name: Optional[str] = Field(
        None,
        description="Sequence / clone / sample ID — primary label in HTML report when set",
    )

# ── Annotation: VHH Segmentation & Germline ───────────────────────────────────

class AnnotateVHHRequest(BaseModel):
    vhh_sequence: str = Field(..., description="VHH amino acid sequence (100–150 aa)")
    scheme: str = Field(
        "imgt",
        description="Numbering scheme: imgt | kabat | chothia",
    )
    species: str = Field(
        "alpaca",
        description="Species for hallmark assignment: alpaca | camel | llama | dog"
    )
    include_hallmarks: bool = Field(
        True,
        description="Include four-site display (IMGT 37 context + FR2 hallmark 44/45/47).",
    )
    include_germline_match: bool = Field(True, description="Find best matching template from clinical VHH library")

class AnnotateVHHResponse(BaseModel):
    """VHH segmentation result (IMGT/Kabat/Chothia)."""
    vhh_sequence: str
    scheme: str
    numbering: List[Dict[str, Any]]  # [{pos: int, ins: str, aa: str}, ...]
    regions: Dict[str, str]  # {CDR1, CDR2, CDR3, FR1, FR2, FR3, FR4}
    hallmarks: Optional[Dict[int, str]] = None  # {"37": "...", "44": "...", "45": "...", "47": "..."}
    germline_match: Optional[Dict[str, Any]] = None  # {scaffold_id, fr_identity, ...}
    segmentation_provenance: Dict[str, Any]


class VHHResult(BaseModel):
    # Four-site display: IMGT 37 context + FR2 hallmark 44/45/47
    hallmark_37: str     # CDR1 context residue (not an engineered FR2 hallmark gate)
    hallmark_44: str     # FR2 hallmark residue
    hallmark_45: str     # FR2 hallmark residue
    hallmark_47: str     # FR2 hallmark residue
    hallmarks_ok: bool

    # CDR
    cdr1_seq: str
    cdr2_seq: str
    cdr3_seq: str
    cdr3_length: int
    cdr3_canonical: Optional[str]

    # Framework
    human_vh3_germline: str             # closest human VH3 germline
    human_vh3_identity: Optional[float] # %
    fr2_identity: Optional[float]       # FR2 is most critical for VHH humanization
    strategy_applied: str               # A | B | C

    # Humanness
    ablang_score: Optional[float]
    humanness_score: Optional[float]   # 0–100

    # Structure
    structure_computed: bool
    sap_score: Optional[float]         # spatial aggregation propensity

    # QA
    checklist_status: str
    flags: List[str]
    lead_selection: Optional[Dict[str, Any]] = None           # V2.7 lead-selection audit (selected_rank, reasons)
    donor_mini_cmc: Optional[Dict[str, Any]] = None           # V2.8 donor baseline CMC (pre-humanization)
    donor_prescreen_flags: Optional[List[str]] = None         # V2.8 pre-screen flags for sequence-intrinsic CMC issues
    feasibility_prescreen: Optional[Dict[str, Any]] = None    # V3.0 pre-screen gate (hard-gate capable)
    cmc_advisory: Optional[List[Dict[str, Any]]] = None       # V3.0 CMC optimization advisory list

    # Candidates
    humanized_sequence: str
    candidates: List[Dict[str, Any]]   # rank, sequence, identity, ablang, panel


# ── CMC: IgG / VH+VL ─────────────────────────────────────────────────────────

class CMCIgGRequest(BaseModel):
    vh_sequence: str
    vl_sequence: str
    antibody_type: str = Field(
        "IgG1",
        description=(
            "IgG1 | IgG2 | IgG4 | humanized | fully_human | therapeutic_regular_antibody | "
            "phage_display (deprecated alias for therapeutic_regular_antibody) | "
            "humanized_transgenic | natural384_transgenic_animal | "
            "natural384_phage_display | natural384_human_b_cell_derived | scFv"
        ),
    )
    project_name: str = "demo"
    report_format: str = "html"
    predict_fv_structure: bool = Field(
        True,
        description="In-silico Fv modeling is recommended for SASA-filtered FR candidate sites. Set to False for quick sequence-only prediction.",
    )
    smart_cmc: bool = Field(False, description="Enable Smart-CMC optimization suggestions (premium feature)")

class CMCIgGResult(BaseModel):
    # Core biophysical
    pI_fab: Optional[float]
    GRAVY: Optional[float]
    instability_index: Optional[float]
    hydro_patch_max9: Optional[float]
    charge_patch_max7: Optional[float]
    net_charge_pH7: Optional[float]

    # Sequence liabilities
    n_deamidation: int
    n_isomerization: int
    n_oxidation: int
    n_glycosylation: int
    liability_flags: List[str]

    # Germline identity (human AbRef-458 reference)
    germline_identity_vh: Optional[float]
    germline_identity_vl: Optional[float]

    # Immunogenicity
    immunogenicity_risk: str            # low | medium | high
    n_mhcii_clusters_high_medium: int

    # Clinical comparison (AbRef clinical panel)
    clinical_score: Optional[float]     # 0–100 percentile vs approved mAbs
    clinical_population: Optional[str]  # e.g. "top_25_pct"
    abref_percentile: Optional[float]

    # Overall
    overall_status: str                 # PASS | WARN | FAIL
    overall_flags: List[str]
    cmc_n_warn: int
    cmc_n_fail: int
    mutation_suggestions: List[Dict[str, Any]]


# ── CMC: VHH ─────────────────────────────────────────────────────────────────

class CMCVHHRequest(BaseModel):
    vhh_sequence: str
    project_name: str = "demo"
    report_format: str = "html"
    sdab_origin: str = Field(
        "camelid_vhh",
        description=(
            "Source/format of the VHH domain — selects the correct clinical reference panel:\n"
            "  'camelid_vhh'   → VHH clinical panel [default]\n"
            "  'humanized_vhh' → same as camelid_vhh (humanized camelid-derived)\n"
            "  'clinical_vhh'  → VHH clinical strict subset\n"
            "  'engineered_vh' → Engineered autonomous VH panel\n"
            "  'transgenic_sdab' → Transgenic sdAb reference (6 metrics)"
        ),
    )
    run_structure: bool = Field(
        True,
        description=(
            "When True: run NanoBodyBuilder2 structure prediction and compute "
            "structure-derived metrics (pLDDT, SASA-based SAP, surface patch indices psh/ppc/pnc, "
            "CDR loop exposure). Adds ~60–120 s to runtime. Default is True to match IgG CMC rigor."
        ),
    )
    smart_cmc: bool = Field(False, description="Enable Smart-CMC optimization suggestions (premium feature)")

class CMCVHHResult(BaseModel):
    # 14 metrics (VHH clinical reference)
    pI: Optional[float]
    GRAVY: Optional[float]
    instability_index: Optional[float]
    net_charge_pH7: Optional[float]
    hydro_patch_max9: Optional[float]
    charge_patch_max7: Optional[float]
    SAP_score: Optional[float]
    agg_motifs: Optional[int]
    hydro_cluster_count: Optional[int]
    glycosylation_sites: Optional[int]
    deamidation_sites: Optional[int]
    isomerization_sites: Optional[int]
    oxidation_sites: Optional[int]
    free_cys: Optional[int]

    # ADI (Antibody Developability Index)
    adi_score: Optional[float]          # 0–100, higher = better
    adi_grade: Optional[str]            # A | B | C | D

    # Percentile vs VHH42 clinical reference
    percentile_ranks: Dict[str, float]  # {pI: 65, GRAVY: 72, ...}

    # Flags
    flags: List[str]
    overall_status: str


# ── CMC: Bispecific VHH ───────────────────────────────────────────────────────

class CMCBispecificRequest(BaseModel):
    arm1_sequence: str = Field(..., description="VHH arm 1 sequence")
    arm2_sequence: str = Field(..., description="VHH arm 2 sequence")
    arm1_target: str = Field("Target_A", description="Antigen A name")
    arm2_target: str = Field("Target_B", description="Antigen B name")
    linker: str = Field("(G4S)3", description="Linker sequence or shorthand")
    project_name: str = "demo"
    report_format: str = "html"
    sdab_origin: str = Field(
        "camelid_vhh",
        description=(
            "Source/format of the VHH arms — selects the reference panel for both arms:\n"
            "  'camelid_vhh' / 'humanized_vhh' → VHH42 (default)\n"
            "  'engineered_vh' → Atlas-24\n"
            "  'transgenic_sdab' → Transgenic sdAb reference"
        ),
    )
    run_structure: bool = Field(
        True,
        description=(
            "When True: run NanoBodyBuilder2 per arm and compute structure-derived metrics "
            "(pLDDT, SASA SAP, psh/ppc/pnc, CDR exposure). Adds ~60–120 s per arm. Default is True."
        ),
    )
    smart_cmc: bool = Field(False, description="Enable Smart-CMC optimization suggestions (premium feature)")

class CMCBispecificResult(BaseModel):
    # Per-arm
    arm1: CMCVHHResult
    arm2: CMCVHHResult

    # Fusion-level
    fusion_pI: Optional[float]
    fusion_GRAVY: Optional[float]
    fusion_instability: Optional[float]
    pI_delta: Optional[float]           # |arm1.pI - arm2.pI|, affects purification

    # SmartLink recommendation
    recommended_linker: str
    linker_rationale: str

    # ER expression model
    er_expression_score: Optional[float]  # predicted relative expression

    # Overall
    overall_status: str
    flags: List[str]


# ── Bispecific Pairing Score (4-way p-AbNatiV) ───────────────────────────────

class BispecificPairingScoreRequest(BaseModel):
    vh_a: str = Field(..., description="Binder A VH sequence")
    vl_a: str = Field("", description="Binder A VL sequence (empty for VHH)")
    vh_b: str = Field(..., description="Binder B VH sequence")
    vl_b: str = Field("", description="Binder B VL sequence (empty for VHH)")
    project_name: str = "BsAb"

class BispecificPairingScoreResult(BaseModel):
    pairs: Dict[str, Any]
    pairing_selectivity_delta_a: Optional[float]
    pairing_selectivity_delta_b: Optional[float]
    overall_pairing_risk: str   # LOW | MODERATE | HIGH


# ── Annotation: VH/VL IMGT segmentation (server stack; public label: ANARCI) ────

class AnnotateVHVLRequest(BaseModel):
    vh_sequence: str = Field(..., description="VH amino acid sequence")
    vl_sequence: str = Field(..., description="VL amino acid sequence")
    scheme: str = Field(
        default="imgt",
        description="Numbering scheme: imgt | kabat | chothia (all computed with ANARCI-class server stack).",
    )
    species: str = Field(
        default="mouse",
        description="Germline library species key: human | mouse | rat | rabbit | dog | alpaca",
    )
    include_germline: bool = Field(
        default=True,
        description="If true, add closest IGHV / IGKV|IGLV vs species library (quick identity).",
    )


class AnnotateVHVLResponse(BaseModel):
    vh_regions: Dict[str, str]
    vl_regions: Dict[str, str]
    scheme: str = "imgt"
    engine: str = Field(
        default="anarci",
        description="Public numbering engine label (ANARCI-class IMGT; interoperable with standard ANARCI outputs).",
    )
    elapsed_sec: float
    germline: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Closest V-gene hits (when include_germline was true).",
    )
    vh_numbering: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Per-residue labels for VH: pos, ins, aa (scheme = response.scheme).",
    )
    vl_numbering: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Per-residue labels for VL: pos, ins, aa.",
    )


# ── Structure: Fv ImmuneBuilder (ABodyBuilder2) ───────────────────────────────

class FvPairItem(BaseModel):
    pair_id: str = Field("pair1", max_length=64, description="Identifier for outputs / filenames")
    vh: str = Field(..., min_length=90, max_length=150)
    vl: str = Field(..., min_length=85, max_length=135)


class FvImmuneBuilderRequest(BaseModel):
    pairs: List[FvPairItem] = Field(
        ...,
        min_length=1,
        max_length=15,
        description="One or more VH/VL pairs; each runs ABodyBuilder2 independently.",
    )


class VhhStructureRequest(BaseModel):
    vhh_sequence: str = Field(..., min_length=90, max_length=200, description="VHH / nanobody amino-acid sequence.")
    sequence_name: Optional[str] = Field(None, max_length=80, description="Optional label for the output PDB and report.")


# ── Recheck: customer sequence QA + virtual assessment ───────────────────────

class RecheckVHVLRequest(BaseModel):
    mouse_vh: str = Field(..., description="Donor (mouse/rat/rabbit) VH amino-acid sequence")
    mouse_vl: str = Field(..., description="Donor (mouse/rat/rabbit) VL amino-acid sequence")
    candidate_vh: str = Field(..., description="Customer-provided humanized VH candidate")
    candidate_vl: str = Field(..., description="Customer-provided humanized VL candidate")
    project_name: str = Field(
        "",
        description="Optional project/sequence label. Blank falls back to job_id.",
    )
    source_species: str = Field("mouse", description="mouse | rat | rabbit")
    clean_mode: Literal["detect", "suggest", "auto"] = Field(
        "detect",
        description=(
            "detect: report removable regions only; "
            "suggest: return suggested cleaned sequence but do not apply; "
            "auto: apply cleaning before evaluation."
        ),
    )
    run_structure: bool = Field(
        True,
        description="Run structure-based conservation checks (ABodyBuilder2 + RMSD/angle).",
    )
    report_format: str = Field("html", description="html | pdf | both (current: html)")


class RecheckVHHRequest(BaseModel):
    donor_vhh: str = Field(..., description="Donor VHH amino-acid sequence")
    candidate_vhh: str = Field(..., description="Customer-provided humanized VHH candidate")
    project_name: str = Field(
        "",
        description="Optional project/sequence label. Blank falls back to job_id.",
    )
    source_species: str = Field("alpaca", description="alpaca | camel | llama | dog")
    clean_mode: Literal["detect", "suggest", "auto"] = Field(
        "detect",
        description=(
            "detect: report removable regions only; "
            "suggest: return suggested cleaned sequence but do not apply; "
            "auto: apply cleaning before evaluation."
        ),
    )
    run_structure: bool = Field(
        True,
        description="Run structure-based conservation checks (NanoBodyBuilder2 + CDR RMSD).",
    )
    report_format: str = Field("html", description="html | pdf | both (current: html)")


class RecheckResult(BaseModel):
    overall_status: str  # PASS | WARN | FAIL
    project_name: str
    clean_mode: str
    input_qc: Dict[str, Any]
    cleaning_actions: Dict[str, Any]
    structure_qc: Dict[str, Any]
    mini_cmc: Dict[str, Any]
    hpr_index: Dict[str, Any]
    naturalness: Dict[str, Any]
    recommendation: str

# ── CAR-T Assembler ────────────────────────────────────────────────────────────

class CartCassetteSpec(BaseModel):
    """A single co-expressed ORF cassette downstream of the CAR.

    `linker_to_prev` decides whether this cassette stays on the SAME transcript
    as the previous ORF (2A / IRES) or starts a NEW transcript driven by its
    own promoter ('new_promoter'). The engine groups cassettes into transcripts
    based on this field.
    """
    id: str = Field(..., description="Component ID from registry OR custom AA sequence")
    category: str = Field("Cassette", description="Display category: Safety Switch / Armored Payload / Logic Gate / Engineering Module / Regulatory")
    sp: Optional[str] = Field(None, description="Per-cassette SP override (for secreted / membrane-bound ORFs). Leave blank to inherit none.")
    linker_to_prev: Literal["T2A", "P2A", "F2A", "E2A", "IRES", "new_promoter"] = Field(
        "T2A",
        description="How this cassette is joined to the previous ORF. 2A/IRES = same transcript; new_promoter = new transcript",
    )
    # Optional per-cassette promoter (only honored if linker_to_prev == 'new_promoter')
    promoter: Optional[str] = Field(None, description="Promoter ID for this transcript when linker_to_prev == 'new_promoter'")


class CartAssemblerRequest(BaseModel):
    # ── CAR ORF core (legacy field names retained for backward compatibility) ──
    binder: str = Field(..., description="Binder sequence or registry ID")
    hinge: str = Field(..., description="Hinge sequence or registry ID")
    tm: str = Field(..., description="Transmembrane sequence or registry ID")
    costim: str = Field(..., description="Costimulatory ID(s) — single ID, comma-separated for tandem (e.g. 'CD28_cyto,4-1BB_cyto'), or empty")
    activation: str = Field(..., description="Activation / Signal-1 sequence or registry ID")
    project_name: str = Field("CAR", description="Construct name")
    # ── CAR ORF N-terminus / internal ──────────────────────────────────────────
    sp:      Optional[str] = Field(None, description="Signal peptide (defaults to CD8α-SP when omitted)")
    linker:  Optional[str] = Field(None, description="scFv VH–VL G4S linker (internal to Binder; informational)")

    # ── Vector architecture (NEW; optional with sensible defaults) ─────────────
    vector_mode: Literal["lentivirus", "aav", "retrovirus", "mRNA-LNP", "transposon"] = Field(
        "lentivirus",
        description="Delivery / cloning backbone. Drives which regulatory elements wrap each transcript.",
    )
    promoter: Optional[str] = Field(None, description="Primary promoter ID for the CAR transcript (default: EF1a_Promoter for lentivirus)")
    polyA: Optional[str] = Field(None, description="polyA signal ID (default: BGH_polyA for lentivirus/AAV; '120A_tail' for mRNA)")
    wpre: Optional[str]   = Field(None, description="WPRE post-CDS enhancer ID (lentivirus only; default: WPRE)")
    utr_5: Optional[str]  = Field(None, description="5' UTR ID (mRNA-LNP only)")
    utr_3: Optional[str]  = Field(None, description="3' UTR ID (mRNA-LNP only)")

    # ── Co-expressed cassettes (NEW structured list) ───────────────────────────
    cassettes: Optional[List[CartCassetteSpec]] = Field(
        None,
        description="Ordered list of co-expressed ORF cassettes. If provided, supersedes the legacy safety/armored/reg/logic/engmod fields.",
    )

    # ── Legacy flat-slot cassettes (kept for backward compatibility) ──────────
    safety:  Optional[str] = Field(None, description="[LEGACY] Safety switch (iCasp9 / EGFRt / RQR8) — use `cassettes` for full control")
    armored: Optional[str] = Field(None, description="[LEGACY] Armored payload (IL-15 / IL-7 / IL-12 / CCL19)")
    reg:     Optional[str] = Field(None, description="[LEGACY] Regulatory element (informational; NOT inserted into CAR ORF)")
    logic:   Optional[str] = Field(None, description="[LEGACY] Logic gate / switch (SynNotch / iCAR / SUPRA)")
    engmod:  Optional[str] = Field(None, description="[LEGACY] Engineering module (TRAC KO, anti-exhaustion, etc.)")


class CartComponentDetail(BaseModel):
    category: str
    provided_input: str
    resolved_name: str
    sequence: str
    source: str
    tier: str
    registry_id: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class CartTranscript(BaseModel):
    """A single mRNA transcript within the vector. May contain >1 ORF if joined by 2A/IRES."""
    name: str
    kind: str = Field(..., description="'car_orf' | 'cassette'")
    components: List[CartComponentDetail]
    protein_sequence: str
    cdna_sequence: str = Field("", description="Back-translated cDNA of the ORF body only (human codon optimized)")
    protein_length: int = 0
    cdna_length: int = 0
    # ── Vector regulatory wrapping (NEW) ──────────────────────────────────────
    promoter: Optional[str] = Field(None, description="Promoter name driving this transcript")
    utr_5: Optional[str] = Field(None, description="5' UTR name (mRNA-LNP)")
    utr_3: Optional[str] = Field(None, description="3' UTR name (mRNA-LNP)")
    wpre: Optional[str] = Field(None, description="WPRE name (lentivirus)")
    polyA: Optional[str] = Field(None, description="polyA signal name")
    inner_linkers: List[str] = Field(default_factory=list,
        description="Intra-transcript linker types between ORFs ('T2A','P2A','F2A','E2A','IRES'); len == len(components)-1 (per ORF, not per component)")
    orf_count: int = Field(1, description="Number of ORFs in this transcript (1 = no 2A/IRES splitting)")


class CartAssemblerResult(BaseModel):
    construct_name: str
    full_sequence: str = Field("", description="[LEGACY] Concatenated CAR ORF protein")
    components: List[CartComponentDetail]
    assembly_warnings: List[str]
    overall_status: str
    transcripts: List[CartTranscript] = Field(default_factory=list,
        description="All transcripts in the vector, in 5'→3' order")
    full_vector_protein: str = Field("", description="All ORFs joined by their actual 2A peptides (polyprotein view, ignores IRES/promoter splits)")
    full_vector_cdna: str = Field("", description="Full vector cDNA (all transcripts including 2A linker codons; IRES/promoter boundaries marked)")
    vector_mode: Optional[str] = Field(None, description="Echo of input vector_mode")

