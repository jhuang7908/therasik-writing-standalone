"""
core/vaccine_design/knowledge/infectious_antigens.py
────────────────────────────────────────────────────
Infectious disease vaccine antigen knowledge base.

Covers: major pathogens with clinically validated vaccine antigens,
key epitopes, and approved/pipeline vaccines.

Sources:
  - WHO EUL/PQ vaccines list (2025)
  - IEDB pathogen-specific epitope data
  - FDA/EMA approved vaccine product labels
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class InfectiousAntigen:
    pathogen: str
    pathogen_type: str      # virus / bacterium / parasite / fungus
    disease: str
    antigen_name: str
    gene: str
    protein_length_aa: int
    key_domains: List[str]  # functional domains critical for immunity
    known_epitopes_mhc1: List[Dict[str, str]]
    known_epitopes_mhc2: List[Dict[str, str]]
    b_cell_epitopes: List[str]
    approved_vaccines: List[Dict[str, str]]    # [{name, platform, year, notes}]
    pipeline_vaccines: List[Dict[str, str]]
    immune_correlate: str   # neutralizing Ab / T cell / both
    global_burden: str
    notes: str


INFECTIOUS_ANTIGENS: List[InfectiousAntigen] = [

    # ═══ RESPIRATORY VIRUSES ═════════════════════════════════════════════

    InfectiousAntigen(
        pathogen="SARS-CoV-2",
        pathogen_type="virus (betacoronavirus)",
        disease="COVID-19",
        antigen_name="Spike Protein (S)",
        gene="S", protein_length_aa=1273,
        key_domains=["RBD (319-541)", "NTD (13-305)", "S2 fusion (686-1273)", "S1/S2 cleavage site"],
        known_epitopes_mhc1=[
            {"peptide": "YLQPRTFLL", "hla": "HLA-A*02:01", "region": "S269-277", "pmid": "32398275"},
            {"peptide": "NYNYLYRLF", "hla": "HLA-A*24:02", "region": "S448-456", "pmid": "32908270"},
            {"peptide": "QYIKWPWYI", "hla": "HLA-A*24:02", "region": "S1208-1216", "pmid": "32908270"},
        ],
        known_epitopes_mhc2=[
            {"peptide": "GKQGNFKNLREFVFK", "hla": "HLA-DR*15:01", "region": "S539-553 (RBD)", "pmid": "32707573"},
        ],
        b_cell_epitopes=["RBD (ACE2 binding interface)", "NTD supersite (N3/N5 loops)"],
        approved_vaccines=[
            {"name": "BNT162b2 (Comirnaty)", "platform": "mRNA-LNP", "year": "2020", "notes": "Pfizer/BioNTech. Prefusion-stabilized S (K986P+V987P). ~95% efficacy (original strain)"},
            {"name": "mRNA-1273 (Spikevax)", "platform": "mRNA-LNP", "year": "2020", "notes": "Moderna. Same 2P stabilization. ~94% efficacy"},
            {"name": "ChAdOx1 (Vaxzevria)", "platform": "ChAd viral vector", "year": "2021", "notes": "AstraZeneca/Oxford. Chimpanzee adenovirus vector"},
            {"name": "Ad26.COV2.S (Jcovden)", "platform": "Ad26 viral vector", "year": "2021", "notes": "J&J. Single dose. Prefusion-stabilized S"},
            {"name": "NVX-CoV2373 (Nuvaxovid)", "platform": "Protein subunit + Matrix-M", "year": "2022", "notes": "Novavax. Recombinant S + saponin adjuvant"},
        ],
        pipeline_vaccines=[
            {"name": "mRNA-1283", "platform": "next-gen mRNA", "notes": "Moderna. RBD+NTD bivalent, refrigerator-stable"},
        ],
        immune_correlate="Neutralizing antibodies (anti-RBD) + S-specific CD4/CD8 T cells",
        global_burden=">770 million confirmed cases, >7 million deaths (WHO 2024)",
        notes="2P mutation (K986P+V987P) locks S in prefusion conformation — critical for all approved vaccines. Variant evolution drives updated boosters.",
    ),

    InfectiousAntigen(
        pathogen="Influenza A/B",
        pathogen_type="virus (orthomyxovirus)",
        disease="Seasonal influenza / Pandemic influenza",
        antigen_name="Hemagglutinin (HA)",
        gene="HA", protein_length_aa=566,
        key_domains=["HA1 globular head (receptor binding)", "HA2 stalk (fusion, conserved)"],
        known_epitopes_mhc1=[
            {"peptide": "GILGFVFTL", "hla": "HLA-A*02:01", "region": "M1₅₈₋₆₆ (matrix)", "pmid": "9862324"},
        ],
        known_epitopes_mhc2=[
            {"peptide": "PKYVKQNTLKLAT", "hla": "HLA-DR*04:01", "region": "HA₃₀₆₋₃₁₈", "pmid": "7964474"},
        ],
        b_cell_epitopes=["HA head (antigenic sites Sa, Sb, Ca1, Ca2, Cb)", "HA stalk (universal target)"],
        approved_vaccines=[
            {"name": "QIV (Fluzone, Fluarix)", "platform": "Inactivated split-virion", "year": "annual", "notes": "Quadrivalent: 2×A (H1N1+H3N2) + 2×B (Yamagata+Victoria lineage). Egg/cell-based"},
            {"name": "FluMist", "platform": "LAIV (live attenuated)", "year": "2003", "notes": "Intranasal. Cold-adapted attenuated virus"},
            {"name": "Flublok", "platform": "Recombinant HA protein", "year": "2013", "notes": "Sanofi. rHA produced in insect cells (baculovirus). Egg-free"},
            {"name": "Fluad", "platform": "Inactivated + MF59 adjuvant", "year": "2015 (US)", "notes": "Seqirus. For ≥65 years. MF59 squalene adjuvant enhances response"},
        ],
        pipeline_vaccines=[
            {"name": "mRNA-1010", "platform": "mRNA", "notes": "Moderna. Seasonal QIV mRNA vaccine. Phase III"},
            {"name": "HA stalk-based", "platform": "various (nanoparticle, chimeric HA)", "notes": "Universal flu vaccine targeting conserved stalk domain"},
        ],
        immune_correlate="HAI titer ≥1:40 (seroprotection); anti-stalk Ab for breadth; CD8 T cells for cross-protection",
        global_burden="~1 billion infections/year, 290-650K deaths (WHO)",
        notes="Annual strain updating required due to antigenic drift/shift. Universal vaccine targeting HA stalk or M2e is a major goal.",
    ),

    InfectiousAntigen(
        pathogen="RSV (Respiratory Syncytial Virus)",
        pathogen_type="virus (pneumovirus)",
        disease="Bronchiolitis, pneumonia (infants, elderly)",
        antigen_name="Fusion protein (F)",
        gene="F", protein_length_aa=574,
        key_domains=["Prefusion F (site Ø, V)", "Postfusion F (site I, II, IV)"],
        known_epitopes_mhc1=[],
        known_epitopes_mhc2=[],
        b_cell_epitopes=["Antigenic site Ø (prefusion-specific, residues 62-69 + 196-209)", "Site V (prefusion)"],
        approved_vaccines=[
            {"name": "Arexvy (RSVPreF3-AS01E)", "platform": "Protein subunit + AS01E adjuvant", "year": "2023", "notes": "GSK. Prefusion F + AS01E. For ≥60 years. ~83% efficacy"},
            {"name": "Abrysvo (RSVpreF)", "platform": "Protein subunit (bivalent)", "year": "2023", "notes": "Pfizer. RSV A+B prefusion F dimer. For ≥60 years AND maternal immunization. ~82% efficacy"},
            {"name": "mResvia (mRNA-1345)", "platform": "mRNA-LNP", "year": "2024", "notes": "Moderna. mRNA encoding prefusion-stabilized F. For ≥60 years. ~84% efficacy"},
        ],
        pipeline_vaccines=[],
        immune_correlate="Prefusion F-specific neutralizing antibodies (anti-site Ø) + palivizumab-competing Ab",
        global_burden="~33 million LRTI in children <5/year; ~120,000 deaths (primarily developing countries)",
        notes="DS-Cav1 structure-based design (McLellan 2013) was breakthrough: stabilized prefusion F enabled all approved RSV vaccines. Maternal vaccination protects neonates.",
    ),

    # ═══ ONCOGENIC VIRUSES ═══════════════════════════════════════════════

    InfectiousAntigen(
        pathogen="HPV (Human Papillomavirus)",
        pathogen_type="virus (papillomavirus)",
        disease="Cervical cancer, oropharyngeal cancer, genital warts",
        antigen_name="L1 capsid protein (prophylactic) / E6+E7 oncoproteins (therapeutic)",
        gene="L1 / E6 / E7", protein_length_aa=531,
        key_domains=["L1 VLP surface loops (prophylactic)", "E6 p53-binding domain", "E7 Rb-binding domain"],
        known_epitopes_mhc1=[
            {"peptide": "YMLDLQPET", "hla": "HLA-A*02:01", "region": "E7₁₁₋₂₀", "pmid": "8551569"},
            {"peptide": "LLMGTLGIV", "hla": "HLA-A*02:01", "region": "E7₈₂₋₉₀", "pmid": "11511362"},
        ],
        known_epitopes_mhc2=[
            {"peptide": "DKKQRFHNIRGR", "hla": "HLA-DR*15:01", "region": "E6₁₂₇₋₁₃₈", "pmid": "17699132"},
        ],
        b_cell_epitopes=["L1 VLP conformational epitopes (type-specific neutralizing Ab)"],
        approved_vaccines=[
            {"name": "Gardasil 9", "platform": "VLP (L1 recombinant)", "year": "2014", "notes": "Merck. 9-valent (HPV 6,11,16,18,31,33,45,52,58). ~97% efficacy. Prevents ~90% cervical cancers"},
            {"name": "Cervarix", "platform": "VLP + AS04 adjuvant", "year": "2009", "notes": "GSK. Bivalent (HPV 16,18) + AS04 (alum+MPL). Cross-protection against related types"},
        ],
        pipeline_vaccines=[
            {"name": "VGX-3100", "platform": "DNA vaccine (therapeutic)", "notes": "Inovio. DNA encoding HPV16/18 E6+E7. Phase III for CIN2/3"},
            {"name": "ISA101b", "platform": "SLP (synthetic long peptide)", "notes": "ISA Pharmaceuticals. HPV16 E6/E7 overlapping long peptides + anti-PD-1"},
        ],
        immune_correlate="Prophylactic: anti-L1 neutralizing Ab; Therapeutic: E6/E7-specific CD8 CTL",
        global_burden="~604,000 new cervical cancer cases/year, 342,000 deaths (WHO 2020). HPV causes ~5% of all cancers",
        notes="Most successful cancer prevention vaccine. Therapeutic vaccines target E6/E7 (retained in all HPV+ cancers as they maintain malignant phenotype).",
    ),

    InfectiousAntigen(
        pathogen="HBV (Hepatitis B Virus)",
        pathogen_type="virus (hepadnavirus)",
        disease="Hepatitis B, cirrhosis, hepatocellular carcinoma",
        antigen_name="HBsAg (Hepatitis B Surface Antigen)",
        gene="S (preS1/preS2/S)", protein_length_aa=226,
        key_domains=["'a' determinant (aa 124-147, major neutralization epitope)", "preS1 (NTCP receptor binding)"],
        known_epitopes_mhc1=[
            {"peptide": "FLPSDFFPSV", "hla": "HLA-A*02:01", "region": "HBcAg₁₈₋₂₇ (core)", "pmid": "1373230"},
            {"peptide": "IPQSLDSWWTSL", "hla": "HLA-A*02:01", "region": "Env₃₃₅₋₃₄₃", "pmid": "10203472"},
        ],
        known_epitopes_mhc2=[],
        b_cell_epitopes=["HBsAg 'a' determinant (conformational)", "preS1 21-47 (NTCP binding)"],
        approved_vaccines=[
            {"name": "Engerix-B", "platform": "Recombinant HBsAg (yeast)", "year": "1986", "notes": "GSK. Alum-adjuvanted. 3-dose schedule. >95% seroprotection"},
            {"name": "Heplisav-B", "platform": "Recombinant HBsAg + CpG-1018", "year": "2017", "notes": "Dynavax. CpG-B TLR9 agonist adjuvant. 2-dose schedule, superior in diabetics"},
            {"name": "PreHevbrio", "platform": "Recombinant 3-antigen (preS1+preS2+S)", "year": "2021", "notes": "VBI Vaccines. Mammalian cell-derived, includes preS1/preS2 domains. 3-dose"},
        ],
        pipeline_vaccines=[
            {"name": "Therapeutic HBV vaccines", "platform": "various (mRNA, DNA, protein)", "notes": "Targeting functional cure of chronic HBV. VTP-300 (ChAd/MVA) Phase II"},
        ],
        immune_correlate="Anti-HBs ≥10 mIU/mL (seroprotection); HBV-specific CD8 T cells for therapeutic cure",
        global_burden="~296 million chronic HBV carriers; ~820,000 deaths/year (WHO 2019). Leading cause of HCC",
        notes="First recombinant vaccine (1986). Therapeutic vaccines for chronic HBV aim to restore T cell exhaustion — major unmet need.",
    ),

    # ═══ TROPICAL / GLOBAL HEALTH ════════════════════════════════════════

    InfectiousAntigen(
        pathogen="Plasmodium falciparum",
        pathogen_type="parasite (apicomplexan)",
        disease="Malaria",
        antigen_name="Circumsporozoite Protein (CSP)",
        gene="CSP", protein_length_aa=397,
        key_domains=["Central NANP repeat region (B cell epitope)", "C-terminal TSR domain (T cell epitopes)", "N-terminal (Region I, hepatocyte invasion)"],
        known_epitopes_mhc1=[
            {"peptide": "YLNKIQNSL", "hla": "HLA-B*53:01", "region": "CSP T cell epitope Th2R", "pmid": "2067571"},
        ],
        known_epitopes_mhc2=[
            {"peptide": "EYLNKIQNSLSTEWSP", "hla": "HLA-DR (multiple)", "region": "CSP C-term universal T", "pmid": "1373230"},
        ],
        b_cell_epitopes=["NANP repeat (immunodominant, strain-transcending)"],
        approved_vaccines=[
            {"name": "RTS,S/AS01E (Mosquirix)", "platform": "Protein subunit (VLP-like) + AS01E", "year": "2021 (WHO recommended)", "notes": "GSK. CSP NANP repeats + C-term fused to HBsAg VLP. ~36% efficacy over 4 years"},
            {"name": "R21/Matrix-M", "platform": "Protein subunit (VLP) + Matrix-M", "year": "2023 (WHO recommended)", "notes": "Oxford. Improved CSP-HBsAg ratio vs RTS,S. ~75% efficacy at 1 year"},
        ],
        pipeline_vaccines=[
            {"name": "PfSPZ Vaccine", "platform": "Whole attenuated sporozoite", "notes": "Sanaria. IV radiation-attenuated sporozoites. ~100% short-term sterile immunity (controlled human malaria)"},
            {"name": "mRNA malaria vaccines", "platform": "mRNA-LNP", "notes": "BioNTech/Moderna exploring CSP + additional antigens in mRNA format"},
        ],
        immune_correlate="Anti-NANP IgG titer + CSP-specific CD4 T cells + liver-stage CD8 T cells",
        global_burden="~249 million cases, ~608,000 deaths/year (WHO 2022). ~95% in sub-Saharan Africa",
        notes="R21/Matrix-M is a game-changer: first malaria vaccine with >75% efficacy. Multi-stage (sporozoite + blood-stage) approaches under development.",
    ),

    InfectiousAntigen(
        pathogen="Mycobacterium tuberculosis",
        pathogen_type="bacterium (mycobacterium)",
        disease="Tuberculosis (TB)",
        antigen_name="Ag85B + ESAT-6",
        gene="Rv1886c (Ag85B) / Rv3875 (ESAT-6)", protein_length_aa=325,
        key_domains=["Ag85B fibronectin-binding domain", "ESAT-6 (early secretory antigenic target)"],
        known_epitopes_mhc1=[
            {"peptide": "AMASTEGNV", "hla": "HLA-A*02:01", "region": "Ag85B₁₉₉₋₂₀₇", "pmid": "11390432"},
        ],
        known_epitopes_mhc2=[
            {"peptide": "FQDAYNAAGGHNAVF", "hla": "HLA-DR (multiple)", "region": "Ag85B₂₄₁₋₂₅₅", "pmid": "15564569"},
            {"peptide": "EQQWNFAGIEAAASA", "hla": "HLA-DR", "region": "ESAT-6₁₋₂₀", "pmid": "11160310"},
        ],
        b_cell_epitopes=["Limited role — TB immunity is primarily T cell mediated"],
        approved_vaccines=[
            {"name": "BCG (Bacille Calmette-Guérin)", "platform": "Live attenuated (M. bovis)", "year": "1921", "notes": "WHO EPI. Variable efficacy 0-80% in adults. Protects against disseminated TB in children"},
        ],
        pipeline_vaccines=[
            {"name": "M72/AS01E", "platform": "Protein subunit + AS01E", "notes": "GSK/Gates MRI. 50% efficacy in Phase IIb (POI trial). Antigens: Mtb32A + Mtb39A. Phase III planned"},
            {"name": "VPM1002", "platform": "Recombinant BCG (rBCG)", "notes": "Serum Institute. BCG ΔureC::hly (listeriolysin). Phase III in neonates"},
            {"name": "BNT164", "platform": "mRNA", "notes": "BioNTech. mRNA-based TB vaccine. Phase I"},
        ],
        immune_correlate="Th1 (IFN-γ producing CD4 T cells) + CD8 CTL; Ab role uncertain",
        global_burden="~10.6 million new cases, ~1.3 million deaths/year (WHO 2022). Leading infectious disease killer",
        notes="M72/AS01E is the most advanced new TB vaccine in 100 years. BCG replacement and booster strategies both pursued.",
    ),

    # ═══ HEMORRHAGIC / EMERGING VIRUSES ══════════════════════════════════

    InfectiousAntigen(
        pathogen="Ebola virus (Zaire ebolavirus)",
        pathogen_type="virus (filovirus)",
        disease="Ebola virus disease (EVD)",
        antigen_name="Glycoprotein (GP)",
        gene="GP", protein_length_aa=676,
        key_domains=["GP1 (receptor binding)", "GP2 (fusion)", "Mucin-like domain (immune evasion)"],
        known_epitopes_mhc1=[],
        known_epitopes_mhc2=[],
        b_cell_epitopes=["GP1 receptor binding site", "GP1/GP2 interface", "Base region (mAb114, REGN-EB3 epitopes)"],
        approved_vaccines=[
            {"name": "Ervebo (rVSV-ZEBOV)", "platform": "Recombinant VSV vector", "year": "2019", "notes": "Merck. VSV backbone with EBOV GP replacing VSV G. Ring vaccination in DRC outbreak. ~97.5% efficacy"},
            {"name": "Zabdeno + Mvabea", "platform": "Ad26 + MVA (heterologous prime-boost)", "year": "2020 (EU)", "notes": "J&J. Ad26.ZEBOV prime + MVA-BN-Filo boost. 2-dose, 56-day interval"},
        ],
        pipeline_vaccines=[],
        immune_correlate="Anti-GP IgG (binding Ab); GP-specific CD4/CD8 T cells",
        global_burden="~35,000 total cases since 1976; 28,646 in 2013-2016 West Africa outbreak",
        notes="Ervebo: first replication-competent viral vector vaccine approved for humans. Ring vaccination strategy was key to outbreak control.",
    ),

    # ═══ SEXUALLY TRANSMITTED / CHRONIC ══════════════════════════════════

    InfectiousAntigen(
        pathogen="HIV-1",
        pathogen_type="virus (lentivirus)",
        disease="HIV/AIDS",
        antigen_name="Envelope glycoprotein (Env: gp120/gp41)",
        gene="env", protein_length_aa=856,
        key_domains=["gp120 V1-V5 variable loops", "gp120 CD4 binding site (CD4bs)", "gp41 MPER", "gp120 V3 (co-receptor binding)"],
        known_epitopes_mhc1=[
            {"peptide": "SLYNTVATL", "hla": "HLA-A*02:01", "region": "Gag p17₇₇₋₈₅", "pmid": "7964474"},
            {"peptide": "ILKEPVHGV", "hla": "HLA-A*02:01", "region": "Pol RT₄₇₆₋₄₈₄", "pmid": "8104398"},
        ],
        known_epitopes_mhc2=[],
        b_cell_epitopes=["CD4bs (VRC01-class bnAbs)", "V1V2 apex (PG9/PG16)", "V3 glycan (PGT121/10-1074)", "MPER (4E10, 10E8)"],
        approved_vaccines=[],
        pipeline_vaccines=[
            {"name": "mRNA-1644", "platform": "mRNA (germline-targeting)", "notes": "Moderna/IAVI. eOD-GT8 60mer priming for VRC01-class bnAb lineage. Phase I"},
            {"name": "HVTN 302 (mosaic)", "platform": "Ad26 + protein boost", "notes": "J&J/HVTN. Mosaic Env antigens. HVTN 706 (Mosaico) Phase III was discontinued 2023"},
        ],
        immune_correlate="Broadly neutralizing antibodies (bnAbs) + Env-specific CD4 T cells; no vaccine has achieved durable protection",
        global_burden="~39 million people living with HIV; ~630,000 deaths/year (UNAIDS 2023)",
        notes="HIV vaccine remains the greatest unsolved challenge in vaccinology. Germline-targeting sequential immunization (Schief/IAVI approach) is most promising current strategy.",
    ),
]


def query_infectious(
    pathogen: str = None,
    pathogen_type: str = None,
    has_approved_vaccine: bool = False,
    platform: str = None,
) -> List[InfectiousAntigen]:
    """Query infectious disease antigen database.

    Args:
        pathogen: Filter by pathogen name (substring match)
        pathogen_type: Filter by virus/bacterium/parasite/fungus
        has_approved_vaccine: Only return pathogens with approved vaccines
        platform: Filter by vaccine platform (e.g. 'mRNA', 'VLP', 'viral vector')
    """
    results = list(INFECTIOUS_ANTIGENS)

    if pathogen:
        p_lower = pathogen.lower()
        results = [a for a in results if p_lower in a.pathogen.lower()
                   or p_lower in a.disease.lower()]

    if pathogen_type:
        pt_lower = pathogen_type.lower()
        results = [a for a in results if pt_lower in a.pathogen_type.lower()]

    if has_approved_vaccine:
        results = [a for a in results if a.approved_vaccines]

    if platform:
        pl_lower = platform.lower()
        results = [a for a in results
                   if any(pl_lower in v.get("platform", "").lower()
                          for v in a.approved_vaccines + a.pipeline_vaccines)]

    return results
