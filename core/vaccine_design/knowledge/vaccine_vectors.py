"""
core/vaccine_design/knowledge/vaccine_vectors.py
────────────────────────────────────────────────
Clinical vaccine vector/platform knowledge base.

Covers all major delivery platforms used in approved or Phase III vaccines,
with engineering parameters relevant to mRNA/vector design decisions.

Sources:
  - Pollard AJ & Bijker EM, Nat Rev Immunol 2021
  - Chaudhary N et al., Nat Rev Drug Discov 2024 (mRNA delivery)
  - FDA/EMA approved product labels
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class VaccineVector:
    name: str
    category: str           # mRNA-LNP / viral_vector / protein_subunit / VLP / DNA / whole_pathogen / conjugate
    description: str
    approved_products: List[str]
    immune_response: str    # humoral / cellular / both
    cd8_induction: str      # strong / moderate / weak / none
    manufacturing: str      # cell-free / cell-based / egg-based / chemical
    cold_chain: str         # -80C / -20C / 2-8C / room_temp
    dose_schedule: str
    onset_of_immunity: str
    duration_of_immunity: str
    capacity_kb: str        # insert size capacity
    pre_existing_immunity: str   # anti-vector immunity concern
    safety_profile: str
    cost_per_dose: str
    scalability: str        # high / medium / low
    advantages: List[str]
    limitations: List[str]
    design_parameters: Dict[str, str]  # key engineering parameters
    notes: str


VACCINE_VECTORS: List[VaccineVector] = [

    # ═══ NUCLEIC ACID PLATFORMS ══════════════════════════════════════════

    VaccineVector(
        name="mRNA-LNP (modified mRNA in lipid nanoparticle)",
        category="mRNA-LNP",
        description="In vitro transcribed mRNA encoding antigen, encapsulated in ionizable lipid nanoparticles (LNP). N1-methylpseudouridine (m1Ψ) modification reduces innate sensing. Cell-free manufacturing.",
        approved_products=["Comirnaty (BNT162b2)", "Spikevax (mRNA-1273)", "mResvia (mRNA-1345)"],
        immune_response="both (strong humoral + cellular)",
        cd8_induction="strong (cytoplasmic expression → MHC-I presentation)",
        manufacturing="cell-free (IVT + LNP encapsulation)",
        cold_chain="-20°C (current); 2-8°C (next-gen lyophilized formulations)",
        dose_schedule="2-dose primary (21-28 days apart) + boosters",
        onset_of_immunity="7-14 days after 2nd dose",
        duration_of_immunity="6-12 months (waning, boosters needed)",
        capacity_kb="up to ~10 kb mRNA (practical: 1-4 kb for single antigen)",
        pre_existing_immunity="none (no anti-vector immunity)",
        safety_profile="reactogenicity (fever, myalgia common); rare myocarditis (young males); no genome integration risk",
        cost_per_dose="$15-30 (high-income); Gavi negotiated $7",
        scalability="high (cell-free, rapid scale-up in weeks)",
        advantages=[
            "Fastest development timeline (weeks from sequence to candidate)",
            "No anti-vector immunity — unlimited re-dosing",
            "Strong CD8 T cell induction (cytoplasmic expression)",
            "Cell-free manufacturing — no cell culture contamination risk",
            "Sequence easily updated for variants",
            "Self-adjuvanting (LNP + dsRNA byproducts activate innate immunity)",
        ],
        limitations=[
            "Cold chain requirement (-20°C or colder)",
            "Short mRNA half-life in vivo (~24-72h expression)",
            "LNP reactogenicity (PEG-lipid allergies in rare cases)",
            "Anti-PEG antibodies may reduce efficacy of repeat dosing",
            "Limited insert size (~10 kb max)",
            "Higher cost than traditional vaccines",
        ],
        design_parameters={
            "5'cap": "Cap1 (m7GpppA 2'-OMe) — CleanCap® technology",
            "5'UTR": "Optimized for translation (α-globin or custom UTR); avoid uAUGs",
            "CDS": "Codon-optimized for human; deplete uridine; minimize CpG",
            "3'UTR": "Dual β-globin 3'UTR (Moderna) or AES-mtRNR1 (BioNTech)",
            "polyA": "100-150 nt segmented poly(A) tail (A30LA70 for BNT)",
            "modification": "N1-methylpseudouridine (m1Ψ) — full U→m1Ψ substitution",
            "LNP_composition": "Ionizable lipid (SM-102/ALC-0315) : DSPC : cholesterol : PEG-lipid = 50:10:38.5:1.5 mol%",
            "LNP_size": "80-100 nm diameter",
            "encapsulation": ">90% encapsulation efficiency",
        },
        notes="Dominant platform post-COVID. BioNTech and Moderna are leaders. Key innovation: m1Ψ modification (Karikó & Weissman, Nobel 2023) + LNP delivery.",
    ),

    VaccineVector(
        name="Self-amplifying RNA (saRNA / replicon)",
        category="mRNA-LNP",
        description="mRNA with alphavirus replicon (nsP1-4 replicase) enabling self-amplification in host cells. Lower dose needed but higher innate immune activation.",
        approved_products=["ARCT-154 (ARCT saRNA, approved in Japan 2023 for COVID-19)"],
        immune_response="both",
        cd8_induction="strong (prolonged expression + dsRNA intermediates)",
        manufacturing="cell-free (IVT)",
        cold_chain="2-8°C (more stable than conventional mRNA due to lower dose)",
        dose_schedule="1-2 doses",
        onset_of_immunity="14-21 days",
        duration_of_immunity="potentially longer than conventional mRNA (sustained expression)",
        capacity_kb="~2-4 kb antigen insert (replicon adds ~7 kb backbone)",
        pre_existing_immunity="none",
        safety_profile="higher reactogenicity than conventional mRNA (dsRNA replication intermediates)",
        cost_per_dose="$5-15 (lower dose = lower cost)",
        scalability="very high (10-100x lower dose → more doses per batch)",
        advantages=[
            "10-100x lower dose needed vs conventional mRNA",
            "Prolonged antigen expression (days to weeks)",
            "Stronger innate immune activation (self-adjuvanting)",
            "Lower manufacturing cost per dose",
        ],
        limitations=[
            "Larger construct (~12 kb total) — harder to encapsulate",
            "Higher reactogenicity",
            "Less clinical experience than conventional mRNA",
            "Cannot use m1Ψ modification (replicase requires unmodified U)",
        ],
        design_parameters={
            "backbone": "Venezuelan equine encephalitis (VEE) or Sindbis replicon (nsP1-4)",
            "subgenomic_promoter": "26S subgenomic promoter drives antigen expression",
            "antigen_insert": "Codon-optimized, placed downstream of 26S promoter",
            "LNP": "Similar to conventional mRNA-LNP but larger particle size (~100-150 nm)",
        },
        notes="ARCT-154 (Arcturus/CSL) is the first approved saRNA vaccine. Gritstone and Imperial College also developing saRNA platforms.",
    ),

    VaccineVector(
        name="DNA vaccine (plasmid + electroporation)",
        category="DNA",
        description="Plasmid DNA encoding antigen under CMV/CAG promoter, delivered via intramuscular injection + electroporation to enhance uptake.",
        approved_products=["ZyCoV-D (Cadila, India — COVID-19, intradermal needle-free)", "Inovio INO-4800 (EUA Philippines)"],
        immune_response="both (but generally weaker than mRNA without EP)",
        cd8_induction="moderate (requires nuclear entry for transcription)",
        manufacturing="bacterial fermentation (E. coli) — very low cost",
        cold_chain="2-8°C or room temperature (highly stable)",
        dose_schedule="2-3 doses + electroporation",
        onset_of_immunity="14-28 days",
        duration_of_immunity="months (potentially durable due to sustained expression)",
        capacity_kb=">10 kb (no practical size limit)",
        pre_existing_immunity="none",
        safety_profile="excellent safety record; electroporation causes local pain; theoretical integration risk (extremely low in practice)",
        cost_per_dose="$1-5 (cheapest platform)",
        scalability="very high (bacterial fermentation, room-temp stable)",
        advantages=[
            "Room temperature stable — no cold chain needed",
            "Cheapest manufacturing cost",
            "No size limit for insert",
            "Excellent safety record (>20 years of clinical data)",
            "Easy to design multi-antigen constructs",
        ],
        limitations=[
            "Lower immunogenicity than mRNA (needs electroporation)",
            "Electroporation device adds complexity and cost",
            "Slow nuclear import reduces efficiency",
            "Few approved products (limited regulatory track record)",
        ],
        design_parameters={
            "promoter": "CMV immediate-early or CAG hybrid promoter",
            "kozak": "Strong Kozak sequence (GCCACCAUGG)",
            "codon_optimization": "Human codon-optimized CDS",
            "polyA_signal": "BGH or SV40 poly(A) signal",
            "backbone": "Minimize CpG in backbone (minicircle DNA) or use CpG-free vector",
            "delivery": "CELLECTRA® EP device (Inovio) or PharmaJet Tropis® (needle-free)",
        },
        notes="VGX-3100 (HPV E6/E7 DNA + EP) is most advanced therapeutic DNA vaccine. Inovio INO-4800 (COVID) showed T cell responses but struggled with efficacy endpoints.",
    ),

    # ═══ VIRAL VECTOR PLATFORMS ══════════════════════════════════════════

    VaccineVector(
        name="Adenovirus vector (human Ad5, Ad26; chimpanzee ChAdOx1)",
        category="viral_vector",
        description="Replication-deficient adenovirus (E1/E3 deleted) expressing antigen from transgene cassette. Strong innate immune activation via DNA sensing pathways.",
        approved_products=["Vaxzevria (ChAdOx1-S)", "Jcovden (Ad26.COV2.S)", "Convidecia (Ad5-nCoV)", "Zabdeno (Ad26.ZEBOV)", "Ervebo-related"],
        immune_response="both (very strong cellular)",
        cd8_induction="strong (DNA enters nucleus → robust MHC-I cross-presentation)",
        manufacturing="cell-based (HEK293/PER.C6 cells)",
        cold_chain="2-8°C (liquid); room temperature possible (lyophilized)",
        dose_schedule="1-2 doses (heterologous boost recommended for Ad vectors)",
        onset_of_immunity="14 days (single dose sufficient for many Ad26 vaccines)",
        duration_of_immunity="months to years (stronger durability than mRNA for T cells)",
        capacity_kb="~7-8 kb (E1/E3 deleted); ~36 kb (gutless/helper-dependent)",
        pre_existing_immunity="HIGH for Ad5 (40-90% global seroprevalence); LOW for Ad26 (~25%); VERY LOW for ChAdOx1 (chimpanzee origin)",
        safety_profile="generally well-tolerated; rare TTS (thrombosis with thrombocytopenia) with ChAdOx1/Ad26; anti-PF4 autoantibodies",
        cost_per_dose="$3-10",
        scalability="medium (cell-based, but well-established at scale)",
        advantages=[
            "Strong and durable CD8 T cell responses",
            "Single dose may be sufficient (Ad26)",
            "Stable at 2-8°C (lyophilized: room temp)",
            "Proven in Ebola, COVID, HIV trials — extensive clinical data",
            "ChAdOx1/Ad26 avoid human Ad5 pre-existing immunity issue",
        ],
        limitations=[
            "Anti-vector immunity limits re-dosing with same vector",
            "Ad5 high seroprevalence globally (especially Africa, Asia)",
            "TTS safety signal (rare but serious)",
            "Cell-based manufacturing slower than mRNA",
            "~7 kb insert size limit (standard E1/E3 deleted)",
        ],
        design_parameters={
            "vector_choice": "Ad26 (low seroprevalence) or ChAdOx1 (chimpanzee, no human seroprevalence)",
            "promoter": "CMV promoter for transgene expression",
            "transgene": "Codon-optimized antigen; prefusion stabilization for viral glycoproteins",
            "E1_deletion": "Mandatory (replication-deficient); supplied in trans by production cell line",
            "production_cell": "PER.C6 (Janssen/Ad26) or HEK293 (Oxford/ChAdOx1) or T-REx-293",
        },
        notes="Heterologous prime-boost (e.g., ChAd prime → mRNA boost) may be optimal strategy. Anti-vector immunity is the main limitation for homologous boosting.",
    ),

    VaccineVector(
        name="Modified Vaccinia Ankara (MVA)",
        category="viral_vector",
        description="Highly attenuated poxvirus vector (>6 passages in chicken embryo fibroblasts, lost 15% of genome). Cannot replicate in human cells. Large insert capacity.",
        approved_products=["Mvabea (MVA-BN-Filo, Ebola boost)", "Jynneos/Imvanex (MVA-BN, smallpox/mpox)", "MVA-BN-RSV (Phase III)"],
        immune_response="both",
        cd8_induction="strong (large genome activates multiple innate pathways)",
        manufacturing="cell-based (chicken embryo fibroblasts, DF-1 cells, AGE1.CR.pIX)",
        cold_chain="-20°C (liquid); room temperature (lyophilized)",
        dose_schedule="typically boost in heterologous prime-boost regimens",
        onset_of_immunity="14 days",
        duration_of_immunity="months to years",
        capacity_kb="~25 kb (very large insert capacity)",
        pre_existing_immunity="low in post-smallpox vaccination era (<40 years old); moderate in older adults",
        safety_profile="excellent (cannot replicate in immunocompromised); safe in HIV+ individuals",
        cost_per_dose="$5-20",
        scalability="medium",
        advantages=[
            "Very large insert capacity (~25 kb) — multi-antigen constructs",
            "Cannot replicate in human cells — safe in immunocompromised",
            "Strong innate immune activation",
            "Low pre-existing immunity in younger populations",
            "Proven heterologous boost partner for Ad26 (Ebola, HIV regimens)",
        ],
        limitations=[
            "Manufacturing complexity (cell-based, lower yields than Ad vectors)",
            "Pre-existing immunity in older adults (smallpox vaccination)",
            "Single-use vector (anti-vector immunity after first exposure)",
        ],
        design_parameters={
            "insertion_sites": "del III, TK locus, or IGR (intergenic regions)",
            "promoter": "p7.5 (early/late) or mH5 (strong early/late) poxvirus promoter",
            "multi_antigen": "Multiple expression cassettes possible due to large capacity",
        },
        notes="MVA is the standard heterologous boost partner. Ad26-prime + MVA-boost is the backbone of J&J's Ebola and HIV vaccine programs.",
    ),

    VaccineVector(
        name="VSV (Vesicular Stomatitis Virus) vector",
        category="viral_vector",
        description="Replication-competent recombinant VSV where VSV G protein is replaced with target pathogen glycoprotein. Single-dose, strong mucosal immunity.",
        approved_products=["Ervebo (rVSV-ZEBOV-GP, Ebola)"],
        immune_response="both (strong humoral; moderate T cell)",
        cd8_induction="moderate",
        manufacturing="cell-based (Vero cells)",
        cold_chain="-80°C to -60°C (liquid)",
        dose_schedule="single dose",
        onset_of_immunity="~10 days (rapid for ring vaccination)",
        duration_of_immunity="≥2 years (Ebola data)",
        capacity_kb="~4-5 kb (glycoprotein replacement)",
        pre_existing_immunity="very low (VSV rare in humans)",
        safety_profile="arthritis, rash (transient viral replication); contraindicated in severely immunocompromised",
        cost_per_dose="$10-20",
        scalability="medium",
        advantages=[
            "Single dose — rapid immunity onset",
            "Replication-competent — strong immune response",
            "No pre-existing immunity in humans",
            "Proven in outbreak response (Ebola ring vaccination)",
        ],
        limitations=[
            "Replication-competent — not suitable for immunocompromised",
            "Cold chain (-60°C or colder)",
            "Limited insert size",
            "Transient viral symptoms (arthritis, vesicular lesions)",
        ],
        design_parameters={
            "backbone": "Indiana serotype VSV with G gene deleted",
            "glycoprotein": "Target pathogen GP replaces VSV G (provides tropism + immunity)",
        },
        notes="Proof of concept for replication-competent vector vaccines. Investigated for SARS-CoV-2, Marburg, Lassa.",
    ),

    # ═══ PROTEIN-BASED PLATFORMS ═════════════════════════════════════════

    VaccineVector(
        name="Recombinant protein subunit + adjuvant",
        category="protein_subunit",
        description="Purified recombinant protein antigen (produced in CHO, insect, yeast, or plant cells) formulated with adjuvant to enhance immunogenicity.",
        approved_products=["Nuvaxovid (NVX-CoV2373 + Matrix-M)", "Shingrix (gE + AS01B)", "Heplisav-B (HBsAg + CpG-1018)", "Arexvy (RSVPreF3 + AS01E)", "Bimervax (RBD-dimer + AS03)"],
        immune_response="primarily humoral (adjuvant-dependent T cell component)",
        cd8_induction="weak (exogenous protein → MHC-II primarily; cross-presentation limited)",
        manufacturing="cell-based (CHO/baculovirus/yeast/plant); purification-intensive",
        cold_chain="2-8°C (most formulations)",
        dose_schedule="2-3 doses (adjuvant-dependent)",
        onset_of_immunity="14-28 days after 2nd dose",
        duration_of_immunity="years (with potent adjuvant: Shingrix >10 years)",
        capacity_kb="N/A (protein, not genetic payload)",
        pre_existing_immunity="none",
        safety_profile="excellent (decades of experience); adjuvant-dependent reactogenicity",
        cost_per_dose="$5-50 (adjuvant cost is major driver)",
        scalability="high (established biopharma manufacturing)",
        advantages=[
            "Well-understood regulatory pathway (decades of experience)",
            "Stable at 2-8°C",
            "No genetic material — no integration risk",
            "Flexible adjuvant selection to tune immune response",
            "Can be produced in multiple expression systems",
        ],
        limitations=[
            "Weak CD8 T cell induction without specialized adjuvants",
            "Requires adjuvant (adds cost, complexity, and reactogenicity)",
            "Slower development (protein expression + purification optimization)",
            "Conformation-dependent epitopes may be lost during purification",
        ],
        design_parameters={
            "expression_system": "CHO (mammalian, glycosylation); Sf9/High Five (baculovirus); Pichia/S. cerevisiae (yeast); N. benthamiana (plant)",
            "antigen_design": "Prefusion stabilization (2P mutation for coronavirus/RSV); domain-focused (RBD vs full-length)",
            "adjuvant_pairing": "Matrix-M (saponin), AS01B/E (MPL+QS-21), AS03 (squalene), CpG-1018, Alum",
            "formulation": "Nanoparticle display (SpyCatcher, ferritin, mi3) enhances B cell response",
        },
        notes="Nanoparticle display of antigens (e.g., ferritin-RBD, SpyCatcher-VLP) is a major innovation, enhancing B cell activation through multivalent engagement.",
    ),

    VaccineVector(
        name="Virus-Like Particle (VLP)",
        category="VLP",
        description="Self-assembling protein nanoparticles that mimic virus structure but contain no genetic material. Repetitive surface display of antigens triggers strong B cell responses.",
        approved_products=["Gardasil 9 (HPV L1 VLP)", "Cervarix (HPV L1 VLP + AS04)", "Engerix-B/Recombivax (HBsAg VLP)", "Mosquirix/RTS,S (CSP-HBsAg VLP)", "Hecolin (HEV p239 VLP)"],
        immune_response="strong humoral (B cell activation via BCR crosslinking)",
        cd8_induction="weak to moderate (cross-presentation depends on size and composition)",
        manufacturing="cell-based (yeast, insect cells, plant cells)",
        cold_chain="2-8°C",
        dose_schedule="2-3 doses",
        onset_of_immunity="14-28 days after 2nd dose",
        duration_of_immunity="years to decades (HPV: >14 years; HBV: >30 years)",
        capacity_kb="N/A (protein assembly, surface display of antigens)",
        pre_existing_immunity="none (unless carrier VLP has been used before, e.g., HBsAg)",
        safety_profile="excellent (no genetic material, no replication)",
        cost_per_dose="$2-20",
        scalability="high (yeast/plant expression well-established)",
        advantages=[
            "Highly immunogenic (multivalent, repetitive epitope display)",
            "Proven long-term durability (HPV: single vaccination may suffice for lifetime)",
            "No genetic material — inherently safe",
            "Can display foreign antigens (e.g., RTS,S: malaria CSP on HBsAg VLP)",
            "Elicit strong germinal center reactions",
        ],
        limitations=[
            "Limited to surface-displayed antigens (conformational B cell epitopes)",
            "Self-assembly requirements constrain antigen design",
            "Weak CD8 T cell induction for intracellular antigens",
            "Manufacturing optimization for correct VLP assembly can be challenging",
        ],
        design_parameters={
            "scaffold": "HBsAg (22nm), HPV L1 (55nm), bacteriophage AP205/Qβ (28nm), ferritin (12nm), mi3 (28nm)",
            "display": "Genetic fusion, SpyCatcher/SpyTag conjugation, or chemical coupling",
            "valency": "60-360 copies per particle (optimal for B cell crosslinking)",
        },
        notes="VLP technology dates to 1981 (HBV). SpyCatcher/SpyTag plug-and-display VLP system enables rapid antigen swapping.",
    ),

    # ═══ WHOLE PATHOGEN PLATFORMS ════════════════════════════════════════

    VaccineVector(
        name="Live Attenuated Vaccine (LAV)",
        category="whole_pathogen",
        description="Weakened but replication-competent pathogen. Mimics natural infection, inducing broad humoral + cellular + mucosal immunity.",
        approved_products=["MMR (measles/mumps/rubella)", "OPV (oral polio)", "YF-17D (yellow fever)", "BCG (TB)", "Varicella (Varivax)", "Rotavirus (RotaTeq/Rotarix)", "FluMist (LAIV)"],
        immune_response="both (humoral + cellular + mucosal)",
        cd8_induction="strong (intracellular replication → full MHC-I presentation)",
        manufacturing="cell-based (Vero, MRC-5, chick embryo, egg)",
        cold_chain="2-8°C to -20°C (varies by product)",
        dose_schedule="1-2 doses (often lifelong immunity)",
        onset_of_immunity="7-14 days",
        duration_of_immunity="decades to lifetime (measles, YF-17D)",
        capacity_kb="N/A (full pathogen genome)",
        pre_existing_immunity="N/A (target pathogen itself)",
        safety_profile="contraindicated in immunocompromised; rare reversion to virulence (OPV); excellent safety in immunocompetent",
        cost_per_dose="$0.5-5 (cheapest vaccine class)",
        scalability="high (decades of manufacturing experience)",
        advantages=[
            "Broadest immune response (humoral + cellular + mucosal + innate memory)",
            "Often single dose → lifelong immunity",
            "Cheapest to manufacture",
            "Natural antigen presentation (all proteins, correct conformation)",
            "Induces trained immunity (BCG non-specific effects)",
        ],
        limitations=[
            "Contraindicated in immunocompromised/pregnant",
            "Risk of reversion to virulence (OPV → cVDPV)",
            "Cannot be used for all pathogens (BSL-4, slow-growing, oncogenic)",
            "Cold chain sensitive",
            "Long development time (serial passage for attenuation)",
        ],
        design_parameters={
            "attenuation": "Serial passage in non-human cells (classical); codon-pair deoptimization (modern); deletion of virulence genes (rational design)",
            "genetic_stability": "Monitor for reversion mutations at each passage",
        },
        notes="YF-17D is the gold standard LAV — single dose, lifelong immunity, manufactured since 1937. Modern rational attenuation (codon-pair deoptimization) enables designer LAVs.",
    ),

    VaccineVector(
        name="Inactivated whole-virus vaccine",
        category="whole_pathogen",
        description="Chemically or physically inactivated pathogen retaining surface antigen structure. Safe but weaker cellular immunity than LAV.",
        approved_products=["IPV (inactivated polio)", "CoronaVac (COVID)", "BBIBP-CorV (COVID)", "Hepatitis A (Havrix)", "Rabies (Imovax)", "Japanese encephalitis (Ixiaro)", "Influenza (Fluzone)"],
        immune_response="primarily humoral (weaker T cell component)",
        cd8_induction="weak (no intracellular replication)",
        manufacturing="cell-based (Vero) + chemical inactivation (β-propiolactone, formaldehyde)",
        cold_chain="2-8°C",
        dose_schedule="2-3 doses + boosters",
        onset_of_immunity="14-28 days",
        duration_of_immunity="months to years (boosters needed)",
        capacity_kb="N/A",
        pre_existing_immunity="N/A",
        safety_profile="excellent (no replication); alum adjuvant reaction",
        cost_per_dose="$2-15",
        scalability="high (well-established, particularly Sinovac/Sinopharm for COVID)",
        advantages=[
            "Simple, well-understood technology",
            "Safe in immunocompromised",
            "Broad antigen repertoire (all viral proteins preserved)",
            "Room temperature stability possible",
        ],
        limitations=[
            "Weaker cellular immunity",
            "Requires adjuvant",
            "Multiple doses needed",
            "Inactivation may damage conformational epitopes",
            "Requires BSL-3/4 for pathogen growth (high-containment for dangerous pathogens)",
        ],
        design_parameters={
            "inactivation": "β-propiolactone (preferred for envelope viruses) or formaldehyde (classical)",
            "adjuvant": "Alum (most common) or novel adjuvants for enhanced response",
            "QC": "Verify complete inactivation; confirm antigen integrity post-inactivation",
        },
        notes="Backbone of traditional vaccinology. CoronaVac/BBIBP-CorV were critical for global COVID vaccination (>5 billion doses in China, Asia, South America).",
    ),
]


def query_vectors(
    category: str = None,
    cd8_strong: bool = False,
    cold_chain_friendly: bool = False,
    approved_only: bool = False,
) -> List[VaccineVector]:
    """Query vaccine vector database.

    Args:
        category: Filter by platform category
        cd8_strong: Only return platforms with strong CD8 induction
        cold_chain_friendly: Only 2-8°C or room temp platforms
        approved_only: Only return vectors with approved products
    """
    results = list(VACCINE_VECTORS)

    if category:
        c_lower = category.lower()
        results = [v for v in results if c_lower in v.category.lower()
                   or c_lower in v.name.lower()]

    if cd8_strong:
        results = [v for v in results if "strong" in v.cd8_induction.lower()]

    if cold_chain_friendly:
        results = [v for v in results
                   if "2-8" in v.cold_chain or "room" in v.cold_chain.lower()]

    if approved_only:
        results = [v for v in results if v.approved_products]

    return results
