"""
core/vaccine_design/knowledge/taa_database.py
─────────────────────────────────────────────
NCI-ranked Tumor-Associated Antigens (TAA) knowledge base.

Primary source:
  Cheever MA et al., "The prioritization of cancer antigens: a National
  Cancer Institute pilot project for the acceleration of translational
  research." Clin Cancer Res. 2009;15(17):5323-37. PMID: 19723653

Ranking criteria (NCI 9-dimension score):
  1. Therapeutic function        2. Immunogenicity
  3. Role in oncogenicity        4. Specificity
  5. Expression level/% +cells   6. Stem cell expression
  7. Number of patients          8. Number of epitopes
  9. Cellular location

Extended with:
  - Known HLA-restricted epitopes (IEDB validated)
  - Clinical trial status (ClinicalTrials.gov 2025)
  - FDA-approved therapies targeting each antigen
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TumorAntigen:
    name: str
    aliases: List[str]
    gene: str
    uniprot: str
    nci_rank: int               # 1-75, NCI pilot project ranking
    nci_score: float            # weighted composite (0-1)
    cancer_types: List[str]
    expression_normal: str      # tissue expression in normal cells
    specificity: str            # TSA / TAA / CTA / overexpressed
    cellular_location: str      # surface / intracellular / secreted
    known_epitopes_mhc1: List[Dict[str, str]]  # [{peptide, hla, pmid}]
    known_epitopes_mhc2: List[Dict[str, str]]
    clinical_trials: int        # approximate active trials
    fda_approved_therapy: str   # approved drug targeting this antigen, if any
    notes: str


# ── NCI Top-75 Tumor Antigens (selected top-30 with epitope details) ────────

TAA_DATABASE: List[TumorAntigen] = [

    # ── Rank 1 ──
    TumorAntigen(
        name="WT1", aliases=["Wilms Tumor 1"], gene="WT1", uniprot="P19544",
        nci_rank=1, nci_score=0.96,
        cancer_types=["AML", "ALL", "CML", "MDS", "mesothelioma", "ovarian", "breast"],
        expression_normal="kidney podocytes, Sertoli cells (low)",
        specificity="overexpressed",
        cellular_location="intracellular (transcription factor)",
        known_epitopes_mhc1=[
            {"peptide": "RMFPNAPYL", "hla": "HLA-A*02:01", "pmid": "11230453"},
            {"peptide": "SLGEQQYSV", "hla": "HLA-A*02:01", "pmid": "16293753"},
            {"peptide": "CMTWNQMNL", "hla": "HLA-A*24:02", "pmid": "15240708"},
            {"peptide": "CYTWNQMNL", "hla": "HLA-A*24:02", "pmid": "15240708"},
            {"peptide": "ALLPAVPSL", "hla": "HLA-A*02:01", "pmid": "19117770"},
        ],
        known_epitopes_mhc2=[
            {"peptide": "SGQARMFPNAPYLPSC", "hla": "HLA-DR*04:01", "pmid": "22156686"},
        ],
        clinical_trials=85,
        fda_approved_therapy="None (multiple Phase II/III ongoing)",
        notes="Highest NCI rank. Galinpepimut-S (WT1 vaccine) in Phase III for AML.",
    ),

    # ── Rank 2 ──
    TumorAntigen(
        name="MUC1", aliases=["Mucin 1", "CA 15-3", "CD227"], gene="MUC1", uniprot="P15941",
        nci_rank=2, nci_score=0.93,
        cancer_types=["breast", "pancreatic", "ovarian", "lung", "colorectal"],
        expression_normal="apical surface of epithelial cells (polarized, low)",
        specificity="overexpressed + aberrant glycosylation",
        cellular_location="surface (type I transmembrane)",
        known_epitopes_mhc1=[
            {"peptide": "STAPPVHNV", "hla": "HLA-A*02:01", "pmid": "18187655"},
            {"peptide": "LLLLTVLTV", "hla": "HLA-A*02:01", "pmid": "11698310"},
        ],
        known_epitopes_mhc2=[
            {"peptide": "PGSTAPPAHGVTSA", "hla": "HLA-DR*03:01", "pmid": "15800933"},
        ],
        clinical_trials=65,
        fda_approved_therapy="None (TG4010, tecemotide Phase III completed)",
        notes="Aberrant glycosylation in tumors exposes neoepitopes. VNTR tandem repeat region is immunodominant.",
    ),

    # ── Rank 3 ──
    TumorAntigen(
        name="LMP2", aliases=["PSMB9", "LMP2"], gene="PSMB9", uniprot="P28065",
        nci_rank=3, nci_score=0.91,
        cancer_types=["EBV+ lymphoma", "nasopharyngeal", "Hodgkin lymphoma"],
        expression_normal="EBV-transformed B cells",
        specificity="viral antigen (EBV latent)",
        cellular_location="intracellular",
        known_epitopes_mhc1=[
            {"peptide": "CLGGLLTMV", "hla": "HLA-A*02:01", "pmid": "9862324"},
            {"peptide": "FLYALALLL", "hla": "HLA-A*02:01", "pmid": "11865180"},
        ],
        known_epitopes_mhc2=[],
        clinical_trials=20,
        fda_approved_therapy="None",
        notes="EBV latent membrane protein. Strong immunogenicity in EBV-seropositive patients.",
    ),

    # ── Rank 4 ──
    TumorAntigen(
        name="HPV E6/E7", aliases=["HPV16 E6", "HPV16 E7", "HPV18 E6/E7"],
        gene="HPV16_E6/E7", uniprot="P03126/P03129",
        nci_rank=4, nci_score=0.90,
        cancer_types=["cervical", "oropharyngeal", "anal", "penile"],
        expression_normal="none (viral oncogene)",
        specificity="TSA (tumor-specific, viral)",
        cellular_location="intracellular",
        known_epitopes_mhc1=[
            {"peptide": "YMLDLQPET", "hla": "HLA-A*02:01", "pmid": "8551569"},
            {"peptide": "TLGIVCPI", "hla": "HLA-A*02:01", "pmid": "8551569"},
            {"peptide": "LLMGTLGIV", "hla": "HLA-A*02:01", "pmid": "11511362"},
        ],
        known_epitopes_mhc2=[
            {"peptide": "DKKQRFHNIRGR", "hla": "HLA-DR*15:01", "pmid": "17699132"},
        ],
        clinical_trials=70,
        fda_approved_therapy="Gardasil/Cervarix (prophylactic); therapeutic vaccines in Phase II/III",
        notes="Ideal TSA: 100% tumor-specific (viral), required for malignant phenotype. VGX-3100 (DNA vaccine) Phase III.",
    ),

    # ── Rank 5 ──
    TumorAntigen(
        name="EGFRvIII", aliases=["EGFR variant III", "de2-7 EGFR"],
        gene="EGFR", uniprot="P00533 (variant)",
        nci_rank=5, nci_score=0.89,
        cancer_types=["glioblastoma", "NSCLC", "breast"],
        expression_normal="none (tumor-specific deletion mutant)",
        specificity="TSA (neoantigen from in-frame deletion)",
        cellular_location="surface",
        known_epitopes_mhc1=[
            {"peptide": "LEEKKGNYV", "hla": "HLA-A*02:01", "pmid": "16452189"},
        ],
        known_epitopes_mhc2=[],
        clinical_trials=30,
        fda_approved_therapy="None (rindopepimut Phase III failed in GBM)",
        notes="Exon 2-7 deletion creates junction neoepitope PEPvIII (LEEKKGNYVVTDH). 25-30% GBM express EGFRvIII.",
    ),

    # ── Rank 6 ──
    TumorAntigen(
        name="HER-2/neu", aliases=["ErbB2", "CD340"], gene="ERBB2", uniprot="P04626",
        nci_rank=6, nci_score=0.88,
        cancer_types=["breast", "gastric", "ovarian", "NSCLC"],
        expression_normal="low in many epithelial tissues",
        specificity="overexpressed",
        cellular_location="surface (type I receptor tyrosine kinase)",
        known_epitopes_mhc1=[
            {"peptide": "KIFGSLAFL", "hla": "HLA-A*02:01", "pmid": "9501071"},
            {"peptide": "IISAVVGIL", "hla": "HLA-A*02:01", "pmid": "10197636"},
            {"peptide": "RLLQETELV", "hla": "HLA-A*02:01", "pmid": "10493815"},
        ],
        known_epitopes_mhc2=[
            {"peptide": "PESFDGDPASNTAPLQP", "hla": "HLA-DR*04:01", "pmid": "15210795"},
        ],
        clinical_trials=45,
        fda_approved_therapy="Trastuzumab, pertuzumab (antibodies); NeuVax (E75 peptide vaccine) Phase III",
        notes="E75 peptide (KIFGSLAFL) is the most clinically advanced cancer peptide vaccine. GP2 and AE37 peptides also in trials.",
    ),

    # ── Rank 7 ──
    TumorAntigen(
        name="EpCAM", aliases=["CD326", "TACSTD1", "ESA"], gene="EPCAM", uniprot="P16422",
        nci_rank=7, nci_score=0.87,
        cancer_types=["colorectal", "breast", "gastric", "ovarian", "pancreatic"],
        expression_normal="basolateral surface of epithelial cells",
        specificity="overexpressed",
        cellular_location="surface",
        known_epitopes_mhc1=[],
        known_epitopes_mhc2=[],
        clinical_trials=25,
        fda_approved_therapy="Catumaxomab (EpCAM×CD3 bispecific, EU-approved then withdrawn)",
        notes="Highly expressed on carcinomas. Adecatumumab and solitomab in clinical development.",
    ),

    # ── Rank 8 ──
    TumorAntigen(
        name="MAGE-A3", aliases=["MAGE-3"], gene="MAGEA3", uniprot="P43357",
        nci_rank=8, nci_score=0.86,
        cancer_types=["melanoma", "NSCLC", "bladder", "head and neck", "esophageal"],
        expression_normal="testis, placenta only (cancer-testis antigen)",
        specificity="CTA (cancer-testis antigen)",
        cellular_location="intracellular",
        known_epitopes_mhc1=[
            {"peptide": "FLWGPRALV", "hla": "HLA-A*02:01", "pmid": "8127712"},
            {"peptide": "KVAELVHFL", "hla": "HLA-A*02:01", "pmid": "15210795"},
            {"peptide": "EVDPIGHLY", "hla": "HLA-A*01:01", "pmid": "9101116"},
        ],
        known_epitopes_mhc2=[
            {"peptide": "TSYVKVLHHMVKISG", "hla": "HLA-DP*04:01", "pmid": "16651402"},
        ],
        clinical_trials=40,
        fda_approved_therapy="None (recMAGE-A3+AS15 Phase III MAGRIT failed in NSCLC)",
        notes="CTA: restricted normal expression (testis is immune-privileged). 30-50% NSCLC, 75% melanoma express MAGE-A3.",
    ),

    # ── Rank 9 ──
    TumorAntigen(
        name="NY-ESO-1", aliases=["CTAG1B", "LAGE-2"], gene="CTAG1B", uniprot="P78358",
        nci_rank=9, nci_score=0.85,
        cancer_types=["melanoma", "synovial sarcoma", "ovarian", "NSCLC", "bladder"],
        expression_normal="testis only (CTA)",
        specificity="CTA",
        cellular_location="intracellular",
        known_epitopes_mhc1=[
            {"peptide": "SLLMWITQC", "hla": "HLA-A*02:01", "pmid": "10069067"},
            {"peptide": "MLMAQEALAFL", "hla": "HLA-A*02:01", "pmid": "18593946"},
            {"peptide": "ASGPGGGAPR", "hla": "HLA-B*07:02", "pmid": "15452051"},
        ],
        known_epitopes_mhc2=[
            {"peptide": "VLLKEFTVSGNI", "hla": "HLA-DR*04:01", "pmid": "11714766"},
            {"peptide": "SLLMWITQCFLPVF", "hla": "HLA-DP*04:01", "pmid": "14984037"},
        ],
        clinical_trials=55,
        fda_approved_therapy="None (IMCgp100/tebentafusp is for gp100, not NY-ESO-1 directly)",
        notes="Spontaneous humoral + cellular immunity in >50% patients. Most immunogenic CTA. TCR-T cell therapy (afamitresgene autoleucel) Phase III for synovial sarcoma.",
    ),

    # ── Rank 10 ──
    TumorAntigen(
        name="PSA", aliases=["Prostate-Specific Antigen", "KLK3"],
        gene="KLK3", uniprot="P07288",
        nci_rank=10, nci_score=0.84,
        cancer_types=["prostate"],
        expression_normal="prostate epithelium (tissue-restricted)",
        specificity="tissue-specific overexpressed",
        cellular_location="secreted",
        known_epitopes_mhc1=[
            {"peptide": "FLTPKKLQCV", "hla": "HLA-A*02:01", "pmid": "9442402"},
            {"peptide": "VISNDVCAQV", "hla": "HLA-A*02:01", "pmid": "12438341"},
        ],
        known_epitopes_mhc2=[],
        clinical_trials=40,
        fda_approved_therapy="Sipuleucel-T (Provenge, targets PAP not PSA directly); PROSTVAC Phase III completed",
        notes="PROSTVAC (PSA-TRICOM) Phase III failed but showed trend in intermediate-risk patients.",
    ),

    # ── Rank 11-15 ──
    TumorAntigen(
        name="PAP", aliases=["Prostatic Acid Phosphatase"], gene="ACPP", uniprot="P15309",
        nci_rank=11, nci_score=0.83,
        cancer_types=["prostate"],
        expression_normal="prostate (tissue-restricted)",
        specificity="tissue-specific",
        cellular_location="secreted / surface",
        known_epitopes_mhc1=[
            {"peptide": "TLMSAMTNL", "hla": "HLA-A*02:01", "pmid": "10623779"},
        ],
        known_epitopes_mhc2=[],
        clinical_trials=20,
        fda_approved_therapy="Sipuleucel-T (Provenge) — FDA approved 2010, first cancer vaccine",
        notes="Provenge: autologous DC pulsed with PAP-GM-CSF fusion. OS benefit ~4 months in mCRPC.",
    ),

    TumorAntigen(
        name="CEA", aliases=["Carcinoembryonic Antigen", "CEACAM5", "CD66e"],
        gene="CEACAM5", uniprot="P06731",
        nci_rank=12, nci_score=0.82,
        cancer_types=["colorectal", "pancreatic", "gastric", "lung", "breast"],
        expression_normal="fetal GI tissue; low in adult colon",
        specificity="oncofetal antigen / overexpressed",
        cellular_location="surface (GPI-anchored)",
        known_epitopes_mhc1=[
            {"peptide": "YLSGANLNL", "hla": "HLA-A*02:01", "pmid": "8977218"},
            {"peptide": "IMIGVLVGV", "hla": "HLA-A*02:01", "pmid": "11069025"},
        ],
        known_epitopes_mhc2=[],
        clinical_trials=35,
        fda_approved_therapy="None (multiple Phase II vaccines)",
        notes="CAP-1 peptide (YLSGANLNL) extensively tested. Heteroclitic variant CAP1-6D (N→D at P6) showed enhanced immunogenicity.",
    ),

    TumorAntigen(
        name="gp100", aliases=["PMEL", "ME20", "Melanocyte Protein PMEL"],
        gene="PMEL", uniprot="P40967",
        nci_rank=13, nci_score=0.81,
        cancer_types=["melanoma"],
        expression_normal="melanocytes (differentiation antigen)",
        specificity="differentiation antigen",
        cellular_location="intracellular (melanosome)",
        known_epitopes_mhc1=[
            {"peptide": "ITDQVPFSV", "hla": "HLA-A*02:01", "pmid": "8178753"},
            {"peptide": "KTWGQYWQV", "hla": "HLA-A*02:01", "pmid": "8634413"},
            {"peptide": "YLEPGPVTA", "hla": "HLA-A*02:01", "pmid": "8634413"},
            {"peptide": "IMDQVPFSV", "hla": "HLA-A*02:01", "pmid": "9501071"},
        ],
        known_epitopes_mhc2=[
            {"peptide": "WNRQLYPEWTEAQRL", "hla": "HLA-DR*04:01", "pmid": "10871869"},
        ],
        clinical_trials=30,
        fda_approved_therapy="Tebentafusp (Kimmtrak) — FDA 2022, gp100-directed bispecific TCR-CD3",
        notes="gp100₂₀₉₋₂₁₇ (ITDQVPFSV) + heteroclitic T210M (IMDQVPFSV) is the canonical heteroclitic vaccine example. Tebentafusp is first TCR-based therapy approved.",
    ),

    TumorAntigen(
        name="MART-1/Melan-A", aliases=["MLANA", "Melan-A"],
        gene="MLANA", uniprot="Q16655",
        nci_rank=14, nci_score=0.80,
        cancer_types=["melanoma"],
        expression_normal="melanocytes (differentiation antigen)",
        specificity="differentiation antigen",
        cellular_location="intracellular (melanosome)",
        known_epitopes_mhc1=[
            {"peptide": "EAAGIGILTV", "hla": "HLA-A*02:01", "pmid": "8977218"},
            {"peptide": "AAGIGILTV", "hla": "HLA-A*02:01", "pmid": "8634413"},
            {"peptide": "ELAGIGILTV", "hla": "HLA-A*02:01", "pmid": "9501071"},
        ],
        known_epitopes_mhc2=[],
        clinical_trials=25,
        fda_approved_therapy="None",
        notes="MART-1₂₆₋₃₅ (EAAGIGILTV) and heteroclitic A27L (ELAGIGILTV) widely used in melanoma vaccine trials. High-frequency T cell precursors in A*02:01+ individuals.",
    ),

    TumorAntigen(
        name="Tyrosinase", aliases=["TYR"],
        gene="TYR", uniprot="P14679",
        nci_rank=15, nci_score=0.79,
        cancer_types=["melanoma"],
        expression_normal="melanocytes (differentiation antigen)",
        specificity="differentiation antigen",
        cellular_location="intracellular (melanosome)",
        known_epitopes_mhc1=[
            {"peptide": "YMDGTMSQV", "hla": "HLA-A*02:01", "pmid": "8178753"},
            {"peptide": "MLLAVLYCL", "hla": "HLA-A*02:01", "pmid": "8634413"},
        ],
        known_epitopes_mhc2=[
            {"peptide": "QNILLSNAPLGPQFP", "hla": "HLA-DR*04:01", "pmid": "11714766"},
        ],
        clinical_trials=20,
        fda_approved_therapy="None",
        notes="Often combined with gp100 and MART-1 in multi-peptide melanoma vaccines.",
    ),

    # ── Rank 16-20 ──
    TumorAntigen(
        name="Survivin", aliases=["BIRC5"], gene="BIRC5", uniprot="O15392",
        nci_rank=16, nci_score=0.78,
        cancer_types=["most solid tumors", "AML", "ALL"],
        expression_normal="fetal tissue; absent in adult differentiated cells",
        specificity="overexpressed (anti-apoptotic)",
        cellular_location="intracellular",
        known_epitopes_mhc1=[
            {"peptide": "ELTLGEFLKL", "hla": "HLA-A*02:01", "pmid": "11950874"},
            {"peptide": "TLPPAWQPFL", "hla": "HLA-B*35:01", "pmid": "18188404"},
        ],
        known_epitopes_mhc2=[],
        clinical_trials=15,
        fda_approved_therapy="None",
        notes="Essential for mitosis → oncogenicity-driven expression. SurVaxM (SVN53-67/M57-KLH) Phase II in GBM.",
    ),

    TumorAntigen(
        name="PSMA", aliases=["FOLH1", "GCPII"], gene="FOLH1", uniprot="Q04609",
        nci_rank=17, nci_score=0.77,
        cancer_types=["prostate", "also neovasculature of solid tumors"],
        expression_normal="prostate, kidney, brain (low), small intestine",
        specificity="overexpressed + neovasculature",
        cellular_location="surface (type II transmembrane)",
        known_epitopes_mhc1=[
            {"peptide": "LLHETDSAV", "hla": "HLA-A*02:01", "pmid": "10361024"},
        ],
        known_epitopes_mhc2=[],
        clinical_trials=60,
        fda_approved_therapy="⁶⁸Ga-PSMA-11 (diagnostic), ¹⁷⁷Lu-PSMA-617 (Pluvicto, radioligand)",
        notes="Major target for prostate cancer. PSMA-targeted CAR-T and bispecifics in Phase I/II.",
    ),

    TumorAntigen(
        name="GD2", aliases=["Disialoganglioside GD2"], gene="ST8SIA1/B4GALNT1",
        uniprot="N/A (glycolipid)",
        nci_rank=18, nci_score=0.76,
        cancer_types=["neuroblastoma", "melanoma", "osteosarcoma", "SCLC"],
        expression_normal="neurons, peripheral nerves (limited access)",
        specificity="overexpressed glycolipid",
        cellular_location="surface (glycolipid)",
        known_epitopes_mhc1=[],
        known_epitopes_mhc2=[],
        clinical_trials=35,
        fda_approved_therapy="Dinutuximab (Unituxin) — FDA 2015 for neuroblastoma",
        notes="Glycolipid antigen — not directly targetable by peptide vaccines but important for antibody/CAR-T. Included for completeness.",
    ),

    TumorAntigen(
        name="Mesothelin", aliases=["MSLN"], gene="MSLN", uniprot="Q13421",
        nci_rank=19, nci_score=0.75,
        cancer_types=["mesothelioma", "pancreatic", "ovarian", "lung"],
        expression_normal="mesothelial cells (pleura, peritoneum, pericardium)",
        specificity="overexpressed",
        cellular_location="surface (GPI-anchored)",
        known_epitopes_mhc1=[
            {"peptide": "SLLFLLFSL", "hla": "HLA-A*02:01", "pmid": "16849531"},
        ],
        known_epitopes_mhc2=[],
        clinical_trials=40,
        fda_approved_therapy="None (CRS-207 Listeria vaccine Phase II, anetumab ravtansine)",
        notes="CRS-207: live attenuated Listeria expressing mesothelin. Tested with GVAX in pancreatic cancer.",
    ),

    TumorAntigen(
        name="MAGE-A1", aliases=["MAGE-1"], gene="MAGEA1", uniprot="P43355",
        nci_rank=20, nci_score=0.74,
        cancer_types=["melanoma", "NSCLC", "bladder", "head and neck"],
        expression_normal="testis only (CTA)",
        specificity="CTA",
        cellular_location="intracellular",
        known_epitopes_mhc1=[
            {"peptide": "EADPTGHSY", "hla": "HLA-A*01:01", "pmid": "8127712"},
            {"peptide": "KVLEYVIKV", "hla": "HLA-A*02:01", "pmid": "12697842"},
        ],
        known_epitopes_mhc2=[],
        clinical_trials=15,
        fda_approved_therapy="None",
        notes="First human tumor antigen identified by T cells (Boon et al., 1991).",
    ),

    # ── Rank 21-30 (abbreviated) ──
    TumorAntigen(
        name="AFP", aliases=["Alpha-Fetoprotein"], gene="AFP", uniprot="P02771",
        nci_rank=21, nci_score=0.73,
        cancer_types=["hepatocellular carcinoma", "germ cell tumors"],
        expression_normal="fetal liver (oncofetal)",
        specificity="oncofetal antigen",
        cellular_location="secreted",
        known_epitopes_mhc1=[
            {"peptide": "FMNKFIYEI", "hla": "HLA-A*02:01", "pmid": "10400683"},
            {"peptide": "GVALQTMKQ", "hla": "HLA-A*02:01", "pmid": "15546158"},
        ],
        known_epitopes_mhc2=[],
        clinical_trials=15,
        fda_approved_therapy="None",
        notes="AFP-derived peptide vaccines in Phase I/II for HCC.",
    ),

    TumorAntigen(
        name="MUC16", aliases=["CA-125"], gene="MUC16", uniprot="Q8WXI7",
        nci_rank=22, nci_score=0.72,
        cancer_types=["ovarian", "fallopian tube", "primary peritoneal"],
        expression_normal="ovarian surface epithelium (low)",
        specificity="overexpressed",
        cellular_location="surface",
        known_epitopes_mhc1=[],
        known_epitopes_mhc2=[],
        clinical_trials=20,
        fda_approved_therapy="None (oregovomab Phase III, MITO-END2)",
        notes="CA-125 is the shed form used as serum biomarker. Oregovomab (anti-CA-125) as vaccine-like immunotherapy.",
    ),

    TumorAntigen(
        name="5T4", aliases=["TPBG", "Trophoblast Glycoprotein"],
        gene="TPBG", uniprot="Q13641",
        nci_rank=23, nci_score=0.71,
        cancer_types=["colorectal", "gastric", "ovarian", "NSCLC"],
        expression_normal="trophoblast (pregnancy)",
        specificity="oncofetal",
        cellular_location="surface",
        known_epitopes_mhc1=[],
        known_epitopes_mhc2=[],
        clinical_trials=10,
        fda_approved_therapy="None (TroVax/MVA-5T4 Phase III TRIST trial failed in RCC)",
        notes="MVA-5T4 (TroVax): Modified Vaccinia Ankara expressing 5T4.",
    ),

    TumorAntigen(
        name="GPC3", aliases=["Glypican-3"], gene="GPC3", uniprot="P51654",
        nci_rank=24, nci_score=0.70,
        cancer_types=["hepatocellular carcinoma", "hepatoblastoma"],
        expression_normal="fetal liver, placenta (oncofetal, absent in adult liver)",
        specificity="oncofetal",
        cellular_location="surface (GPI-anchored)",
        known_epitopes_mhc1=[
            {"peptide": "EYILSLEEL", "hla": "HLA-A*24:02", "pmid": "16849531"},
            {"peptide": "FVGEFFTDV", "hla": "HLA-A*02:01", "pmid": "22447840"},
        ],
        known_epitopes_mhc2=[],
        clinical_trials=25,
        fda_approved_therapy="None (GPC3 peptide vaccine Phase II in HCC; codrituzumab Phase II)",
        notes="Highly HCC-specific. GPC3₂₉₈₋₃₀₆ peptide vaccine showed correlation between CTL response and OS.",
    ),

    TumorAntigen(
        name="KRAS", aliases=["K-Ras4B"], gene="KRAS", uniprot="P01116",
        nci_rank=25, nci_score=0.69,
        cancer_types=["pancreatic", "colorectal", "NSCLC"],
        expression_normal="ubiquitous (but mutations are tumor-specific)",
        specificity="TSA (mutant neoantigen)",
        cellular_location="intracellular (membrane-associated GTPase)",
        known_epitopes_mhc1=[
            # KRAS G12D (Gly→Asp at codon 12): ...KLVVVGA[D]GV... — distinct from G12V
            {"peptide": "KLVVVGADGV", "hla": "HLA-A*02:01", "pmid": "9521099",
             "mutation": "G12D", "wt_peptide": "KLVVVGAGGV"},
            # KRAS G12V (Gly→Val at codon 12): ...KLVVVGA[V]GV... — distinct from G12D
            {"peptide": "KLVVVGAVGV", "hla": "HLA-A*02:01", "pmid": "9521099",
             "mutation": "G12V", "wt_peptide": "KLVVVGAGGV"},
            # KRAS G12D — HLA-A*11:01 restricted (10-mer, shifted window)
            {"peptide": "VVVGADGVGK", "hla": "HLA-A*11:01", "pmid": "33106677",
             "mutation": "G12D", "wt_peptide": "VVVGAGGVGK"},
            # KRAS G12D — HLA-A*11:01 restricted (9-mer)
            {"peptide": "VVGADGVGKS", "hla": "HLA-A*11:01", "pmid": "33106677",
             "mutation": "G12D", "wt_peptide": "VVGAGGVGKS"},
        ],
        known_epitopes_mhc2=[
            # KRAS G12D — MHC-II (16-mer); note: WT sequence is KLVVVGAGGVGKSALT
            {"peptide": "KLVVVGADGVGKSALT", "hla": "HLA-DR*11:01", "pmid": "7693660",
             "mutation": "G12D", "wt_peptide": "KLVVVGAGGVGKSALT"},
        ],
        clinical_trials=20,
        fda_approved_therapy="None (mRNA-5671/V941 Moderna+Merck Phase I for KRAS-mutant cancers)",
        notes=(
            "G12D, G12V, G12C hotspot mutations. mRNA-5671: personalized KRAS neoantigen mRNA vaccine "
            "with pembrolizumab. IMPORTANT: G12D and G12V epitopes are distinct — always specify "
            "mutation field when querying. WT KRAS residue 12 = Gly (G), "
            "WT sequence around codon 12: KLVVVGAGGVGKSALT."
        ),
    ),

    TumorAntigen(
        name="p53", aliases=["TP53", "Tumor Protein P53"], gene="TP53", uniprot="P04637",
        nci_rank=26, nci_score=0.68,
        cancer_types=["~50% of all solid tumors"],
        expression_normal="all cells (low, rapid turnover)",
        specificity="overexpressed (mutant accumulation) + neoantigen",
        cellular_location="intracellular (nuclear)",
        known_epitopes_mhc1=[
            {"peptide": "LLGRNSFEV", "hla": "HLA-A*02:01", "pmid": "8977218"},
            {"peptide": "RMPEAAPPV", "hla": "HLA-A*02:01", "pmid": "8977218"},
            {"peptide": "STPPPGTRV", "hla": "HLA-A*02:01", "pmid": "10593463"},
        ],
        known_epitopes_mhc2=[
            {"peptide": "VVRCPHERCTEGAT", "hla": "HLA-DR*04:01", "pmid": "11714766"},
        ],
        clinical_trials=20,
        fda_approved_therapy="None (p53-SLP vaccine Phase II in ovarian cancer)",
        notes="Mutant p53 accumulates in tumors. Both WT (overexpressed) and mutant-specific epitopes studied.",
    ),

    TumorAntigen(
        name="IDH1 R132H", aliases=["Isocitrate Dehydrogenase 1 R132H"],
        gene="IDH1", uniprot="O75874 (R132H mutant)",
        nci_rank=27, nci_score=0.67,
        cancer_types=["low-grade glioma", "AML", "cholangiocarcinoma"],
        expression_normal="none (somatic mutation neoantigen)",
        specificity="TSA (driver mutation neoantigen)",
        cellular_location="intracellular (cytoplasmic enzyme)",
        known_epitopes_mhc1=[],
        known_epitopes_mhc2=[
            {"peptide": "GWVKPIIIGHHAYGD", "hla": "HLA-DR*01:01", "pmid": "25135958"},
        ],
        clinical_trials=10,
        fda_approved_therapy="None (NOA-16 IDH1-vac Phase I in glioma — positive results 2021)",
        notes="IDH1 R132H present in >70% grade II-III gliomas. NOA-16: 20-mer peptide vaccine induced MHC-II response.",
    ),

    TumorAntigen(
        name="Claudin 18.2", aliases=["CLDN18.2"], gene="CLDN18", uniprot="P56856",
        nci_rank=28, nci_score=0.66,
        cancer_types=["gastric", "pancreatic", "esophageal"],
        expression_normal="stomach epithelium (tight junction, buried)",
        specificity="overexpressed + surface-exposed in tumors",
        cellular_location="surface (tight junction protein)",
        known_epitopes_mhc1=[],
        known_epitopes_mhc2=[],
        clinical_trials=35,
        fda_approved_therapy="Zolbetuximab (Vyloy) — FDA 2024 for gastric cancer",
        notes="First-in-class anti-CLDN18.2 mAb. mRNA vaccine approaches being explored.",
    ),

    TumorAntigen(
        name="TERT", aliases=["Telomerase Reverse Transcriptase", "hTERT"],
        gene="TERT", uniprot="O14746",
        nci_rank=29, nci_score=0.65,
        cancer_types=["~85-90% of all cancers"],
        expression_normal="stem cells, activated lymphocytes (low)",
        specificity="overexpressed",
        cellular_location="intracellular (nuclear)",
        known_epitopes_mhc1=[
            {"peptide": "ILAKFLHWL", "hla": "HLA-A*02:01", "pmid": "11278890"},
            {"peptide": "RLVDDFLLV", "hla": "HLA-A*02:01", "pmid": "12393573"},
        ],
        known_epitopes_mhc2=[
            {"peptide": "EARPALLTSRLRFIPK", "hla": "HLA-DR*07:01", "pmid": "17028178"},
        ],
        clinical_trials=20,
        fda_approved_therapy="None (GV1001 Phase III in pancreatic cancer; UV1 Phase II)",
        notes="Near-universal tumor antigen. GV1001: 16-mer hTERT peptide. UV1: 3-peptide hTERT vaccine.",
    ),

    TumorAntigen(
        name="RAS (general)", aliases=["H-Ras", "N-Ras", "NRAS"], gene="NRAS/HRAS",
        uniprot="P01111/P01112",
        nci_rank=30, nci_score=0.64,
        cancer_types=["melanoma (NRAS)", "thyroid", "AML", "bladder"],
        expression_normal="ubiquitous (mutations tumor-specific)",
        specificity="TSA (mutant neoantigen)",
        cellular_location="intracellular",
        known_epitopes_mhc1=[
            {"peptide": "ILDTAGQEEY", "hla": "HLA-A*01:01", "pmid": "7693660"},
        ],
        known_epitopes_mhc2=[],
        clinical_trials=10,
        fda_approved_therapy="None",
        notes="NRAS Q61 mutations in ~20% melanoma. Often co-targeted with KRAS in RAS vaccine approaches.",
    ),
]


# ── Query Functions ──────────────────────────────────────────────────────────

def query_taa(
    cancer_type: str = None,
    specificity: str = None,
    has_mhc1_epitopes: bool = False,
    max_rank: int = 75,
    allele: str = None,
) -> List[TumorAntigen]:
    """Query TAA database with filters.

    Args:
        cancer_type: Filter by cancer type (case-insensitive substring match)
        specificity: Filter by TSA/TAA/CTA/overexpressed/differentiation
        has_mhc1_epitopes: Only return antigens with known MHC-I epitopes
        max_rank: Only return antigens ranked ≤ this value
        allele: Filter for antigens with epitopes restricted to this HLA allele
    """
    results = [t for t in TAA_DATABASE if t.nci_rank <= max_rank]

    if cancer_type:
        ct_lower = cancer_type.lower()
        results = [t for t in results
                   if any(ct_lower in c.lower() for c in t.cancer_types)]

    if specificity:
        sp_lower = specificity.lower()
        results = [t for t in results if sp_lower in t.specificity.lower()]

    if has_mhc1_epitopes:
        results = [t for t in results if t.known_epitopes_mhc1]

    if allele:
        results = [t for t in results
                   if any(e["hla"] == allele for e in t.known_epitopes_mhc1)]

    return results
