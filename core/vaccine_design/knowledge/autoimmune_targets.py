"""
core/vaccine_design/knowledge/autoimmune_targets.py
───────────────────────────────────────────────────
Autoimmune disease tolerogenic vaccine targets.

Tolerogenic vaccines aim to SUPPRESS unwanted immune responses by:
  - Inducing antigen-specific Tregs
  - Deleting autoreactive T cells
  - Inducing anergy

Sources:
  - Wraith DC, Nat Rev Immunol 2017 (antigen-specific immunotherapy)
  - Serra P & Santamaria P, Nat Med 2019 (tolerogenic nanoparticles)
  - ClinicalTrials.gov (active tolerogenic trials)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class AutoimmuneTarget:
    disease: str
    target_antigen: str
    gene: str
    uniprot: str
    epitope_type: str           # T cell / B cell / both
    hla_association: List[str]  # disease-associated HLA alleles
    known_epitopes: List[Dict[str, str]]
    mechanism: str              # molecular mimicry / cross-reactivity / loss of tolerance
    vaccine_approach: str       # tolerogenic peptide / inverse vaccine / nanoparticle / DNA
    clinical_status: str
    clinical_trials: int
    key_trial: str
    notes: str


AUTOIMMUNE_TARGETS: List[AutoimmuneTarget] = [

    # ── Multiple Sclerosis ───────────────────────────────────────────────
    AutoimmuneTarget(
        disease="Multiple Sclerosis (MS)",
        target_antigen="Myelin Basic Protein (MBP)",
        gene="MBP", uniprot="P02686",
        epitope_type="T cell (CD4+)",
        hla_association=["HLA-DR*15:01", "HLA-DQ*06:02"],
        known_epitopes=[
            {"peptide": "ENPVVHFFKNIVTPR", "hla": "HLA-DR*15:01", "region": "MBP₈₅₋₉₉", "pmid": "8247524"},
            {"peptide": "VHFFKNIVTPRTPP", "hla": "HLA-DR*15:01", "region": "MBP₈₉₋₁₀₁", "pmid": "9822770"},
            {"peptide": "DENPVVHFFKNIVTP", "hla": "HLA-DR*04:01", "region": "MBP₈₃₋₉₉", "pmid": "1546314"},
        ],
        mechanism="Loss of self-tolerance to CNS myelin antigens. CD4+ Th1/Th17 cells attack myelin sheath.",
        vaccine_approach="Altered peptide ligands (APL); tolerogenic nanoparticles; DNA vaccines",
        clinical_status="Phase II (multiple approaches)",
        clinical_trials=8,
        key_trial="NCT01973491 — ATX-MS-1467 (4 MBP peptides) Phase IIa in RRMS",
        notes="MBP₈₅₋₉₉ is the immunodominant epitope in DR15+ MS patients. APL approach (CGP 77116) showed mixed results — some patients had disease exacerbation.",
    ),

    AutoimmuneTarget(
        disease="Multiple Sclerosis (MS)",
        target_antigen="Myelin Oligodendrocyte Glycoprotein (MOG)",
        gene="MOG", uniprot="Q16653",
        epitope_type="T cell + B cell",
        hla_association=["HLA-DR*15:01"],
        known_epitopes=[
            {"peptide": "MEVGWYRSPFSRVVH", "hla": "HLA-DR*15:01", "region": "MOG₃₅₋₅₅", "pmid": "10358756"},
        ],
        mechanism="Both humoral (anti-MOG antibodies) and cellular immunity. MOG₃₅₋₅₅ is the dominant CD4 epitope.",
        vaccine_approach="MOG peptide-loaded tolerogenic DCs; inverse vaccines",
        clinical_status="Preclinical / Phase I",
        clinical_trials=3,
        key_trial="NCT02283671 — tolerogenic DC loaded with MOG/MBP peptides",
        notes="MOGAD (MOG antibody disease) now recognized as distinct from MS. Therapeutic approach differs.",
    ),

    # ── Type 1 Diabetes ──────────────────────────────────────────────────
    AutoimmuneTarget(
        disease="Type 1 Diabetes (T1D)",
        target_antigen="GAD65 (Glutamic Acid Decarboxylase 65)",
        gene="GAD2", uniprot="Q05329",
        epitope_type="T cell + B cell",
        hla_association=["HLA-DR*04:01", "HLA-DR*03:01", "HLA-DQ*08:02", "HLA-DQ*02:01"],
        known_epitopes=[
            {"peptide": "NFFRMVISNPAAT", "hla": "HLA-DR*04:01", "region": "GAD₅₅₅₋₅₆₇", "pmid": "9892161"},
            {"peptide": "IPPSLRTLEDNER", "hla": "HLA-DR*04:01", "region": "GAD₂₇₃₋₂₈₅", "pmid": "10201955"},
        ],
        mechanism="Autoimmune destruction of pancreatic β cells. GAD65 is a major autoantigen.",
        vaccine_approach="GAD-alum (Diamyd); peptide immunotherapy; inverse nanoparticle vaccines",
        clinical_status="Phase III (Diamyd GAD-alum in HLA-DR3+ children)",
        clinical_trials=15,
        key_trial="NCT03875729 — Diamyd GAD-alum Phase III in recent-onset T1D (positive in DR3+ subgroup)",
        notes="Diamyd: recombinant GAD65 + alum. Phase III DIAGNODE-3 showed C-peptide preservation in HLA-DR3+ children (2024).",
    ),

    AutoimmuneTarget(
        disease="Type 1 Diabetes (T1D)",
        target_antigen="Proinsulin / Insulin B-chain",
        gene="INS", uniprot="P01308",
        epitope_type="T cell (CD4+ and CD8+)",
        hla_association=["HLA-DR*04:01", "HLA-A*02:01"],
        known_epitopes=[
            {"peptide": "HLVEALYLVCGERG", "hla": "HLA-DR*04:01", "region": "InsB₉₋₂₃", "pmid": "15767567"},
            {"peptide": "ALWMRLLPL", "hla": "HLA-A*02:01", "region": "PPI₁₅₋₂₄", "pmid": "22156416"},
        ],
        mechanism="Insulin/proinsulin is the primary autoantigen initiating T1D. InsB₉₋₂₃ is the key CD4 epitope.",
        vaccine_approach="Proinsulin DNA vaccine; oral/nasal insulin tolerance; peptide immunotherapy",
        clinical_status="Phase I/II",
        clinical_trials=10,
        key_trial="NCT04279613 — PRV-101 (CVB1 vaccine for T1D prevention); BHT-3021 proinsulin DNA vaccine Phase I",
        notes="InsB₉₋₂₃ presented in register 3 (unusual binding mode) to DQ8/DR4. Tolerogenic approach must avoid boosting pathogenic response.",
    ),

    # ── Rheumatoid Arthritis ─────────────────────────────────────────────
    AutoimmuneTarget(
        disease="Rheumatoid Arthritis (RA)",
        target_antigen="Citrullinated Proteins (ACPA targets)",
        gene="multiple (vimentin, fibrinogen, α-enolase, type II collagen)",
        uniprot="multiple",
        epitope_type="T cell + B cell (ACPA = anti-citrullinated protein antibodies)",
        hla_association=["HLA-DR*04:01", "HLA-DR*04:04", "HLA-DR*01:01 (shared epitope)"],
        known_epitopes=[
            {"peptide": "CIT-VIM₅₉₋₇₈", "hla": "HLA-DR*04:01", "region": "vimentin 59-78 (citrullinated)", "pmid": "19877048"},
            {"peptide": "CIT-FIBβ₃₆₋₅₂", "hla": "HLA-DR*04:01", "region": "fibrinogen β 36-52 (citrullinated)", "pmid": "22174200"},
            {"peptide": "CIT-ENO₅₋₂₁", "hla": "HLA-DR*04:01", "region": "α-enolase 5-21 (citrullinated)", "pmid": "19877048"},
        ],
        mechanism="Citrullination (Arg→citrulline by PAD enzymes) creates neoepitopes. SE+ HLA-DR4 presents citrullinated peptides preferentially.",
        vaccine_approach="Citrullinated peptide tolerogenic DCs; inverse vaccines targeting autoreactive B/T cells",
        clinical_status="Phase I/II",
        clinical_trials=5,
        key_trial="Rheumavax (citrullinated peptide-loaded tolerogenic DCs) Phase I — NCT01352884",
        notes="ACPA+ RA represents 60-70% of RA. Shared epitope (SE) in HLA-DR β chain is the strongest genetic risk factor.",
    ),

    AutoimmuneTarget(
        disease="Rheumatoid Arthritis (RA)",
        target_antigen="Type II Collagen (CII)",
        gene="COL2A1", uniprot="P02458",
        epitope_type="T cell + B cell",
        hla_association=["HLA-DR*04:01", "HLA-DR*01:01"],
        known_epitopes=[
            {"peptide": "GIAGFKGEQGPKGEP", "hla": "HLA-DR*04:01", "region": "CII₂₆₃₋₂₇₀", "pmid": "9806644"},
        ],
        mechanism="Autoimmunity against joint cartilage collagen. CII₂₆₃₋₂₇₀ glycopeptide (galactosylated) is immunodominant.",
        vaccine_approach="Oral collagen tolerance (Colloral); nasal CII peptides",
        clinical_status="Phase III (oral tolerance — mixed results)",
        clinical_trials=8,
        key_trial="Barnett et al., Arthritis Rheum 1998 — Oral CII Phase III showed modest benefit in early RA",
        notes="Oral tolerance with CII was one of the first antigen-specific immunotherapy approaches in RA.",
    ),

    # ── Celiac Disease ───────────────────────────────────────────────────
    AutoimmuneTarget(
        disease="Celiac Disease",
        target_antigen="Gluten / Gliadin (deamidated)",
        gene="wheat α-gliadin (Gli-α2/α9)", uniprot="N/A (plant protein)",
        epitope_type="T cell (CD4+)",
        hla_association=["HLA-DQ*02:01 (DQ2.5)", "HLA-DQ*08:01 (DQ8)"],
        known_epitopes=[
            {"peptide": "LQPFPQPELPY (DQ2.5-glia-α1a)", "hla": "HLA-DQ*02:01", "region": "α-gliadin p57-68 (deamidated)", "pmid": "10984045"},
            {"peptide": "PQPELPYPQPE (DQ2.5-glia-α2)", "hla": "HLA-DQ*02:01", "region": "α-gliadin p62-72 (deamidated)", "pmid": "10984045"},
            {"peptide": "QQYPSGEGSFQPSQE (DQ2.5-glia-ω1)", "hla": "HLA-DQ*02:01", "region": "ω-gliadin (deamidated)", "pmid": "15579327"},
        ],
        mechanism="Tissue transglutaminase (tTG) deamidates gliadin peptides → enhanced HLA-DQ2/DQ8 binding → CD4 Th1 response → villous atrophy.",
        vaccine_approach="Nexvax2 (3-peptide desensitization); gluten peptide tolerogenic nanoparticles (TAK-101/TIMP-GLIA)",
        clinical_status="Phase II (TAK-101/CNP-101 ongoing)",
        clinical_trials=6,
        key_trial="NCT03738475 — CNP-101 (TIMP-GLIA biodegradable nanoparticle) Phase II in celiac disease",
        notes="Nexvax2 (Phase II) was discontinued in 2019 (did not meet endpoints). TIMP-GLIA nanoparticle approach uses PLG particles loaded with gliadin.",
    ),

    # ── Systemic Lupus Erythematosus ─────────────────────────────────────
    AutoimmuneTarget(
        disease="Systemic Lupus Erythematosus (SLE)",
        target_antigen="dsDNA / Nucleosome / SmD1",
        gene="multiple nuclear antigens", uniprot="N/A",
        epitope_type="B cell + T cell",
        hla_association=["HLA-DR*03:01", "HLA-DR*15:01"],
        known_epitopes=[
            {"peptide": "RIHMVYSKRSGKPRG", "hla": "HLA-DR", "region": "SmD1₈₃₋₁₁₉", "pmid": "10764827"},
            {"peptide": "DWEYSVWLSN (La/SSB)", "hla": "HLA-DR*03:01", "region": "La₂₉₁₋₃₀₃", "pmid": "10502789"},
        ],
        mechanism="Loss of tolerance to nuclear antigens. Immune complexes deposit in kidneys/skin/joints.",
        vaccine_approach="Lupuzor (P140/Rigerimod): phosphopeptide from spliceosomal U1-70K protein",
        clinical_status="Phase III (Lupuzor)",
        clinical_trials=8,
        key_trial="NCT02504645 — Lupuzor/Rigerimod Phase III in SLE (completed, mixed results)",
        notes="Lupuzor (P140): phosphopeptide spanning U1-70K₁₃₁₋₁₅₁. Targets chaperone-mediated autophagy to reduce autoantigen presentation.",
    ),

    # ── Pemphigus Vulgaris ───────────────────────────────────────────────
    AutoimmuneTarget(
        disease="Pemphigus Vulgaris (PV)",
        target_antigen="Desmoglein 3 (DSG3)",
        gene="DSG3", uniprot="P32926",
        epitope_type="B cell (pathogenic IgG) + T cell (CD4 Th2)",
        hla_association=["HLA-DR*04:02", "HLA-DQ*05:03"],
        known_epitopes=[
            {"peptide": "DSG3₁₉₀₋₂₀₄", "hla": "HLA-DR*04:02", "region": "EC2 domain", "pmid": "14688330"},
        ],
        mechanism="Anti-DSG3 IgG4 antibodies disrupt desmosomal adhesion → acantholysis (blistering).",
        vaccine_approach="DSG3-derived tolerogenic peptides; CAR-Treg targeting anti-DSG3 B cells",
        clinical_status="Phase I (CAR-Treg: DSG3-CAART)",
        clinical_trials=3,
        key_trial="NCT04422223 — DSG3-CAART (anti-DSG3 chimeric autoantibody receptor T cells) Phase I",
        notes="DSG3-CAART: Tregs expressing chimeric DSG3 to target and suppress anti-DSG3 autoreactive B cells.",
    ),

    # ── Myasthenia Gravis ────────────────────────────────────────────────
    AutoimmuneTarget(
        disease="Myasthenia Gravis (MG)",
        target_antigen="Acetylcholine Receptor (AChR)",
        gene="CHRNA1", uniprot="P02708",
        epitope_type="B cell (anti-AChR Ab) + T cell",
        hla_association=["HLA-DR*03:01", "HLA-B*08:01"],
        known_epitopes=[
            {"peptide": "AChRα₃₂₀₋₃₃₇", "hla": "HLA-DR*03:01", "region": "cytoplasmic loop", "pmid": "1547155"},
            {"peptide": "AChRα₁₄₄₋₁₅₆", "hla": "HLA-DR*07:01", "region": "α-bungarotoxin binding region", "pmid": "2163273"},
        ],
        mechanism="Anti-AChR antibodies block/destroy neuromuscular junction AChR → muscle weakness.",
        vaccine_approach="AChR peptide immunotherapy; tolerogenic nanoparticles",
        clinical_status="Preclinical / Phase I",
        clinical_trials=3,
        key_trial="AChR peptide tolerance studies in EAMG (experimental autoimmune MG) models",
        notes="MG is the prototypical antibody-mediated autoimmune disease. Anti-CD20 (rituximab) is effective, suggesting B cell depletion as alternative.",
    ),

    # ── Neuromyelitis Optica ─────────────────────────────────────────────
    AutoimmuneTarget(
        disease="Neuromyelitis Optica Spectrum Disorder (NMOSD)",
        target_antigen="Aquaporin-4 (AQP4)",
        gene="AQP4", uniprot="P55087",
        epitope_type="B cell (anti-AQP4 IgG) + T cell",
        hla_association=["HLA-DR*03:01"],
        known_epitopes=[
            {"peptide": "AQP4₆₁₋₈₀", "hla": "HLA-DR", "region": "loop A", "pmid": "20810897"},
            {"peptide": "AQP4₁₂₉₋₁₅₃", "hla": "HLA-DR", "region": "loop C", "pmid": "20810897"},
        ],
        mechanism="Anti-AQP4 IgG1 activates complement at astrocyte end-feet → CNS inflammation.",
        vaccine_approach="AQP4 peptide tolerization; non-pathogenic AQP4 IgG decoys",
        clinical_status="Preclinical",
        clinical_trials=2,
        key_trial="Preclinical: AQP4₂₀₁₋₂₂₀ tolerogenic peptide in murine model",
        notes="Satralizumab (anti-IL6R) and inebilizumab (anti-CD19) are FDA-approved for NMOSD. Tolerogenic approach is emerging.",
    ),
]


def query_autoimmune(
    disease: str = None,
    hla: str = None,
    clinical_phase: str = None,
) -> List[AutoimmuneTarget]:
    """Query autoimmune targets.

    Args:
        disease: Filter by disease name (substring match)
        hla: Filter by associated HLA allele
        clinical_phase: Filter by clinical status containing this phase
    """
    results = list(AUTOIMMUNE_TARGETS)

    if disease:
        d_lower = disease.lower()
        results = [t for t in results if d_lower in t.disease.lower()]

    if hla:
        results = [t for t in results
                   if any(hla in a for a in t.hla_association)]

    if clinical_phase:
        p_lower = clinical_phase.lower()
        results = [t for t in results if p_lower in t.clinical_status.lower()]

    return results
