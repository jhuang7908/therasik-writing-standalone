"""
core/vaccine_design/knowledge/adjuvants.py
──────────────────────────────────────────
Immune adjuvant knowledge base — clinically approved and advanced pipeline adjuvants.

Sources:
  - Pulendran B et al., Nat Rev Drug Discov 2021 (adjuvant mechanisms)
  - Del Giudice G et al., Semin Immunol 2018 (licensed adjuvants)
  - FDA/EMA product labels for adjuvanted vaccines
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Adjuvant:
    name: str
    aliases: List[str]
    category: str           # mineral_salt / emulsion / saponin / TLR_agonist / combo / other
    mechanism: str
    innate_receptors: List[str]   # TLR / STING / NLR / RIG-I targets
    immune_profile: str     # Th1 / Th2 / balanced / Th1-biased
    cd8_enhancement: str    # strong / moderate / weak / none
    approved_vaccines: List[Dict[str, str]]  # [{vaccine, indication, year}]
    safety_profile: str
    regulatory_status: str  # approved / Phase III / Phase II / Phase I / preclinical
    dose_range: str
    formulation_notes: str
    advantages: List[str]
    limitations: List[str]
    notes: str


ADJUVANT_DATABASE: List[Adjuvant] = [

    # ═══ MINERAL SALTS ═══════════════════════════════════════════════════

    Adjuvant(
        name="Aluminum salts (Alum)",
        aliases=["Alhydrogel", "Al(OH)₃", "AlPO₄", "aluminum hydroxide", "aluminum phosphate"],
        category="mineral_salt",
        mechanism="Depot effect (slow antigen release); NLRP3 inflammasome activation; enhances antigen uptake by APCs; promotes Th2 immune response.",
        innate_receptors=["NLRP3 inflammasome (indirect)"],
        immune_profile="Th2-biased (IgG1, IL-4, IL-5)",
        cd8_enhancement="weak (poor cross-presentation)",
        approved_vaccines=[
            {"vaccine": "DTaP/Tdap", "indication": "diphtheria/tetanus/pertussis", "year": "1926+"},
            {"vaccine": "Hepatitis A/B", "indication": "viral hepatitis", "year": "1986+"},
            {"vaccine": "HPV (Gardasil)", "indication": "HPV infection", "year": "2006"},
            {"vaccine": "Pneumococcal (PCV13/20)", "indication": "pneumococcal disease", "year": "2000+"},
        ],
        safety_profile="excellent (>90 years of use); injection site reactions (pain, redness); rare granuloma; no systemic safety concerns at standard doses",
        regulatory_status="approved (most widely used adjuvant globally)",
        dose_range="0.3-1.5 mg Al³⁺ per dose",
        formulation_notes="Antigen adsorbed onto aluminum salt particles (1-10 μm). Al(OH)₃ for positively charged antigens; AlPO₄ for negatively charged. Must maintain pH and prevent aggregation.",
        advantages=[
            "Longest safety track record of any adjuvant (since 1926)",
            "Low cost and widely available",
            "Compatible with most protein antigens",
            "Regulatory acceptance worldwide",
            "Stable at 2-8°C",
        ],
        limitations=[
            "Th2-biased — poor CD8 T cell and Th1 induction",
            "Inadequate for intracellular pathogens requiring cellular immunity",
            "Does not work well with polysaccharide antigens",
            "Cannot be frozen (irreversible aggregation)",
            "Insufficient for elderly/immunocompromised (weak immune potentiation)",
        ],
        notes="Default comparator adjuvant in clinical trials. Used in >80% of adjuvanted vaccines globally. For cancer/TB/HIV vaccines requiring Th1/CD8, alum alone is insufficient.",
    ),

    # ═══ OIL-IN-WATER EMULSIONS ══════════════════════════════════════════

    Adjuvant(
        name="MF59",
        aliases=["MF59C.1"],
        category="emulsion",
        mechanism="Oil-in-water squalene nanoemulsion (160 nm). Creates 'immunocompetent environment' at injection site: recruits neutrophils → monocytes → DCs. Enhances antigen uptake, transport to dLN, and GC reactions.",
        innate_receptors=["MyD88-independent; ASC/NLRP3 partial; ATP/muscle damage sensing"],
        immune_profile="balanced (Th1 + Th2; stronger than alum for both)",
        cd8_enhancement="moderate (enhanced cross-presentation via DC activation)",
        approved_vaccines=[
            {"vaccine": "Fluad (influenza)", "indication": "seasonal flu ≥65 years", "year": "1997 (EU), 2015 (US)"},
            {"vaccine": "aH5N1 (prepandemic)", "indication": "H5N1 pandemic preparedness", "year": "2010 (EU)"},
        ],
        safety_profile="well-tolerated; injection site pain/swelling more than alum; no long-term safety signals in >200 million doses",
        regulatory_status="approved",
        dose_range="0.25 mL per dose (standard formulation)",
        formulation_notes="Squalene 9.75 mg + Tween 80 1.175 mg + Span 85 1.175 mg per 0.25 mL. Microfluidized to 160 nm droplets. Mixed with antigen at point-of-use.",
        advantages=[
            "Stronger and broader immunity than alum",
            "Dose-sparing effect (critical for pandemic stockpiling)",
            "Good safety record (~30 years, >200 million doses)",
            "Enhances responses in elderly (approved for ≥65 years)",
            "Works with influenza split-virion and subunit antigens",
        ],
        limitations=[
            "Proprietary (Seqirus/Novartis) — availability constraints",
            "Not as strong for Th1/CD8 as AS01 or saponin adjuvants",
            "Squalene sourced from shark liver (ethical/supply concerns) — synthetic alternatives emerging",
        ],
        notes="Seqirus (Novartis successor) holds exclusive rights. WHO pandemic stockpile includes MF59-adjuvanted H5N1 vaccine. Synthetic squalene now available.",
    ),

    Adjuvant(
        name="AS03",
        aliases=["Adjuvant System 03"],
        category="emulsion",
        mechanism="Oil-in-water emulsion (squalene + DL-α-tocopherol + Tween 80). α-tocopherol (vitamin E) provides unique immunostimulatory activity: enhances NF-κB signaling in monocytes.",
        innate_receptors=["similar to MF59 + α-tocopherol-specific monocyte activation"],
        immune_profile="balanced (Th1 + Th2; very strong GC reactions)",
        cd8_enhancement="moderate",
        approved_vaccines=[
            {"vaccine": "Pandemrix (H1N1)", "indication": "2009 H1N1 pandemic flu", "year": "2009"},
            {"vaccine": "Arepanrix (H1N1)", "indication": "pandemic flu", "year": "2009"},
            {"vaccine": "Bimervax (COVID-19)", "indication": "COVID-19 booster (EU)", "year": "2023"},
        ],
        safety_profile="injection site reactions; fatigue; rare association with narcolepsy (Pandemrix in Scandinavia — likely antigen-specific, not adjuvant per se)",
        regulatory_status="approved (pandemic use + COVID booster)",
        dose_range="0.25 mL per dose",
        formulation_notes="Squalene 10.68 mg + DL-α-tocopherol 11.86 mg + Tween 80 4.85 mg per 0.25 mL. Two-vial system (antigen + adjuvant mixed at site).",
        advantages=[
            "Exceptional dose-sparing (up to 4-6x for pandemic flu)",
            "Strong germinal center and memory B cell induction",
            "Cross-reactive antibody broadening (important for influenza variants)",
        ],
        limitations=[
            "Narcolepsy signal with Pandemrix (resolved as antigen-related)",
            "Proprietary (GSK)",
            "Higher reactogenicity than alum",
        ],
        notes="Key pandemic preparedness adjuvant. AS03 enabled dose-sparing that stretched H1N1 vaccine supply 4-6 fold during 2009 pandemic.",
    ),

    # ═══ SAPONIN-BASED ═══════════════════════════════════════════════════

    Adjuvant(
        name="Matrix-M",
        aliases=["Matrix-M1"],
        category="saponin",
        mechanism="Saponin (Fraction-A + Fraction-C from Quillaja saponaria) formulated into 40 nm nanoparticles with cholesterol + phospholipid. Activates innate immunity, enhances antigen trafficking to dLN, promotes strong GC reactions.",
        innate_receptors=["NLRP3 inflammasome; caspase-1; IL-18 release; cholesterol-dependent membrane disruption"],
        immune_profile="balanced Th1/Th2 (strong Th1 component)",
        cd8_enhancement="moderate to strong (saponin-mediated cross-presentation)",
        approved_vaccines=[
            {"vaccine": "Nuvaxovid (NVX-CoV2373)", "indication": "COVID-19", "year": "2022"},
            {"vaccine": "R21/Matrix-M", "indication": "malaria (Plasmodium falciparum)", "year": "2023 (WHO recommended)"},
        ],
        safety_profile="injection site pain, fatigue, headache; generally well-tolerated; no serious safety signals",
        regulatory_status="approved",
        dose_range="50 μg Matrix-M per dose",
        formulation_notes="Novavax proprietary. ISCOM-like matrix (40 nm cage-like nanoparticles). Can be co-formulated with protein antigens.",
        advantages=[
            "Strong Th1 induction (better than alum for cellular immunity)",
            "Enhances antibody quality (affinity maturation, GC reactions)",
            "Nanoparticle format — no separate adjuvant vial needed",
            "Proven in malaria vaccine (R21: ~75% efficacy attributable in part to Matrix-M)",
            "Sustainable Quillaja saponin sourcing being developed (plant cell culture)",
        ],
        limitations=[
            "Proprietary (Novavax) — limited availability for third parties",
            "Quillaja tree sustainability concerns (wild harvest)",
            "Higher reactogenicity than alum",
        ],
        notes="Matrix-M's role in R21 malaria vaccine success is notable — same CSP antigen as RTS,S but Matrix-M >> AS01E for this formulation.",
    ),

    Adjuvant(
        name="AS01B / AS01E",
        aliases=["Adjuvant System 01B", "Adjuvant System 01E"],
        category="combo (saponin + TLR4 agonist in liposome)",
        mechanism="Liposome containing MPL (3-O-desacyl-4'-monophosphoryl lipid A, TLR4 agonist) + QS-21 (saponin, from Quillaja saponaria). Dual innate activation: TLR4 (MPL) + NLRP3/caspase-1 (QS-21). Liposome delivery targets APCs.",
        innate_receptors=["TLR4 (MPL)", "NLRP3/caspase-1 (QS-21)", "early IFN-γ from NK cells"],
        immune_profile="strongly Th1-biased (IFN-γ, CD4 Th1, cross-presentation)",
        cd8_enhancement="strong (QS-21 enhances MHC-I cross-presentation)",
        approved_vaccines=[
            {"vaccine": "Shingrix (HZ/su)", "indication": "herpes zoster (shingles) ≥50 years", "year": "2017"},
            {"vaccine": "Arexvy (RSVPreF3)", "indication": "RSV ≥60 years", "year": "2023"},
            {"vaccine": "Mosquirix (RTS,S)", "indication": "malaria (AS01E, lower QS-21 dose)", "year": "2021"},
            {"vaccine": "M72/AS01E", "indication": "TB (Phase IIb — 50% efficacy)", "year": "Phase III planned"},
        ],
        safety_profile="higher reactogenicity than alum (injection site pain, fever, fatigue are common); Grade 3 reactions in ~10%; no serious safety concerns (>100 million Shingrix doses)",
        regulatory_status="approved (AS01B in Shingrix, AS01E in Arexvy/Mosquirix)",
        dose_range="AS01B: MPL 50 μg + QS-21 50 μg; AS01E: MPL 25 μg + QS-21 25 μg (half-dose)",
        formulation_notes="MPL and QS-21 co-formulated in DOPC/cholesterol liposomes. Two-vial system: lyophilized antigen + liquid AS01. Reconstitute at point-of-use.",
        advantages=[
            "Strongest clinically approved adjuvant for T cell immunity",
            "Shingrix: 97% efficacy in ≥50 years, >90% in immunocompromised — benchmark",
            "Dual mechanism (TLR4 + saponin) provides robust Th1 polarization",
            "Effective in elderly and immunocompromised (critical populations)",
            "Cross-presentation enhancement for CD8 T cells",
        ],
        limitations=[
            "High reactogenicity (limits acceptability in healthy young adults)",
            "Complex formulation (liposome + two active components)",
            "Proprietary (GSK) — limited third-party access",
            "QS-21 supply constraints (Quillaja tree)",
            "High cost (~$150-200 per Shingrix course)",
        ],
        notes="AS01B/E is the gold standard for vaccines requiring strong cellular immunity. M72/AS01E's 50% efficacy against TB is the first new TB vaccine signal in 100 years.",
    ),

    # ═══ TLR AGONISTS ════════════════════════════════════════════════════

    Adjuvant(
        name="CpG-1018 (CpG-B ODN)",
        aliases=["CpG 1018", "ISS 1018", "cytidine-phosphate-guanosine ODN"],
        category="TLR_agonist",
        mechanism="Synthetic CpG-B class oligodeoxynucleotide (22-mer). Activates TLR9 in plasmacytoid DCs and B cells → type I IFN production, B cell proliferation, Th1 polarization.",
        innate_receptors=["TLR9 (endosomal)"],
        immune_profile="Th1-biased (IFN-α, IL-12, IgG2a)",
        cd8_enhancement="moderate (via TLR9-activated DC cross-presentation)",
        approved_vaccines=[
            {"vaccine": "Heplisav-B (HBsAg + CpG-1018)", "indication": "hepatitis B (adults)", "year": "2017"},
        ],
        safety_profile="well-tolerated; injection site reactions; mild systemic symptoms; no autoimmune signals (initial concern resolved after Phase III + post-marketing surveillance)",
        regulatory_status="approved",
        dose_range="3000 μg (3 mg) per dose",
        formulation_notes="Phosphorothioate backbone (nuclease-resistant). Mixed with antigen in saline. No lipid carrier needed.",
        advantages=[
            "Synthetic, fully defined molecule — batch consistency",
            "2-dose schedule for HBV (vs 3-dose with alum) — better compliance",
            "Superior seroprotection in diabetics and elderly (vs alum-HBV)",
            "Strong Th1 polarization without emulsion/liposome complexity",
            "Scalable synthetic manufacturing",
        ],
        limitations=[
            "Single approved product (limited clinical experience breadth)",
            "Requires high dose (3 mg) — moderate cost",
            "Th1-focused — may need combination for balanced response",
            "TLR9 expression varies across species (mouse >> human in pDC)",
        ],
        notes="Dynavax product. CpG-1018 enabled 2-dose HBV schedule and improved responses in hard-to-immunize populations. CpG-B class (vs CpG-A) selected for B cell activation.",
    ),

    Adjuvant(
        name="AS04 (MPL + Alum)",
        aliases=["Adjuvant System 04"],
        category="combo (TLR4 agonist + alum)",
        mechanism="3-O-desacyl-monophosphoryl lipid A (MPL, TLR4 agonist) adsorbed onto aluminum hydroxide. MPL provides Th1 signal; alum provides depot + Th2 component → balanced response.",
        innate_receptors=["TLR4 (cell surface) via TRIF-dependent pathway (biased signaling)"],
        immune_profile="balanced Th1/Th2 (Th1-shifted vs alum alone)",
        cd8_enhancement="weak to moderate",
        approved_vaccines=[
            {"vaccine": "Cervarix (HPV16/18)", "indication": "HPV infection/cervical cancer", "year": "2007"},
            {"vaccine": "Fendrix (HBsAg)", "indication": "hepatitis B (hemodialysis patients, EU only)", "year": "2005"},
        ],
        safety_profile="slightly higher reactogenicity than alum alone; excellent long-term safety (>100 million Cervarix doses)",
        regulatory_status="approved",
        dose_range="MPL 50 μg + Al(OH)₃ 500 μg per dose",
        formulation_notes="MPL adsorbed onto Al(OH)₃. Single-vial formulation (pre-mixed). MPL derived from Salmonella minnesota R595 LPS.",
        advantages=[
            "Proven cross-protective immunity (Cervarix cross-protects against HPV31/33/45)",
            "Simple formulation (pre-mixed, single vial)",
            "Enhances GC reactions and memory B cells vs alum alone",
            "Long-duration antibody response",
        ],
        limitations=[
            "Less potent than AS01 for cellular immunity",
            "Proprietary (GSK)",
            "MPL production from bacterial LPS is complex",
        ],
        notes="AS04 in Cervarix produces broader cross-protection against non-vaccine HPV types than Gardasil (alum only), attributed to stronger GC reactions and antibody affinity maturation.",
    ),

    # ═══ EMERGING / NOVEL ADJUVANTS ══════════════════════════════════════

    Adjuvant(
        name="STING agonists (cGAMP, ADU-S100, MSA-2)",
        aliases=["cyclic dinucleotides", "CDN", "cGAS-STING pathway agonists"],
        category="other (STING pathway)",
        mechanism="Activate STING (Stimulator of IFN Genes) → TBK1 → IRF3 → type I IFN production. Powerful induction of innate immunity, DC maturation, and cross-presentation.",
        innate_receptors=["STING (endoplasmic reticulum)"],
        immune_profile="strongly Th1 (type I IFN-driven)",
        cd8_enhancement="strong (potent cross-presentation enhancer)",
        approved_vaccines=[],
        safety_profile="Phase I/II — local inflammation, flu-like symptoms; dose-limiting toxicity at high doses (intratumoral)",
        regulatory_status="Phase I/II (vaccine adjuvant); Phase II (cancer immunotherapy)",
        dose_range="1-100 μg (route-dependent)",
        formulation_notes="cGAMP: endogenous ligand. Synthetic CDNs: ADU-S100 (Aduro), MK-1454 (Merck). Non-nucleotide: MSA-2 (oral bioavailable).",
        advantages=[
            "Potent CD8 T cell induction (strongest among emerging adjuvants)",
            "Bridges innate and adaptive immunity via type I IFN",
            "Effective for cancer vaccines and therapeutic applications",
            "Oral bioavailable versions in development (MSA-2)",
        ],
        limitations=[
            "Not yet approved as vaccine adjuvant",
            "Narrow therapeutic window (too much → immunopathology)",
            "Rapid degradation of CDN in vivo — requires formulation (LNP, hydrogel)",
            "STING polymorphisms in human populations (R232H) may affect response",
        ],
        notes="STING agonists are the most promising adjuvant class for cancer vaccines requiring CD8 T cell responses. BioNTech exploring STING agonist + mRNA combinations.",
    ),

    Adjuvant(
        name="Poly-ICLC (Hiltonol)",
        aliases=["polyinosinic-polycytidylic acid stabilized with poly-L-lysine and carboxymethylcellulose"],
        category="TLR_agonist",
        mechanism="Synthetic dsRNA analog. Activates TLR3 (endosomal) + MDA5/RIG-I (cytoplasmic) → type I IFN, DC maturation, strong Th1/CD8 T cell responses.",
        innate_receptors=["TLR3", "MDA5", "RIG-I"],
        immune_profile="Th1-biased (strong IFN-α/β)",
        cd8_enhancement="strong (dsRNA sensing in DC → cross-presentation)",
        approved_vaccines=[],
        safety_profile="flu-like symptoms (fever, fatigue, myalgia) — mimics viral infection; generally well-tolerated at 1-2 mg doses",
        regulatory_status="Phase II (cancer vaccines, HIV, influenza)",
        dose_range="1-2 mg per dose (IM or SC)",
        formulation_notes="Oncovir, Inc. Stabilized poly(I:C) formulation prevents degradation by RNases. Can be mixed with peptide/protein antigens.",
        advantages=[
            "Potent type I IFN inducer — 'viral mimic' adjuvant",
            "Strong CD8 T cell responses (ideal for cancer/HIV vaccines)",
            "Extensive Phase I/II data in cancer vaccine trials",
            "Non-proprietary formulation concept",
        ],
        limitations=[
            "Not yet approved for any vaccine",
            "Flu-like symptoms limit acceptability for prophylactic vaccines",
            "Batch-to-batch variability (polymer)",
        ],
        notes="Widely used in cancer neoantigen vaccine trials (e.g., NeoVax by Catherine Wu/Dana-Farber: personal neoantigen peptides + poly-ICLC → durable CD4/CD8 responses in melanoma, PMID: 28678778).",
    ),

    Adjuvant(
        name="LNP (Lipid Nanoparticle) as self-adjuvant",
        aliases=["ionizable LNP", "SM-102 LNP", "ALC-0315 LNP"],
        category="other (delivery + adjuvant)",
        mechanism="Ionizable lipid nanoparticles used for mRNA delivery ALSO function as adjuvants: (1) ionizable lipid activates intracellular innate sensors; (2) LNP formulation recruits neutrophils/monocytes to injection site; (3) IL-6 production independent of mRNA cargo.",
        innate_receptors=["IL-1 receptor (IL-1β release)", "NLRP3 (ionizable lipid)", "multiple DAMPs"],
        immune_profile="balanced Th1/Th2 (mRNA content provides additional Th1 via dsRNA sensing)",
        cd8_enhancement="moderate (from LNP alone); strong (with mRNA cargo — cytoplasmic translation → MHC-I)",
        approved_vaccines=[
            {"vaccine": "Comirnaty / Spikevax", "indication": "COVID-19 (LNP inherent adjuvant effect)", "year": "2020"},
        ],
        safety_profile="injection site reactions, fever, fatigue (attributed partly to LNP adjuvant effect, not just mRNA)",
        regulatory_status="approved (as delivery vehicle with intrinsic adjuvant properties)",
        dose_range="N/A (component of mRNA-LNP formulation)",
        formulation_notes="SM-102 (Moderna) or ALC-0315 (BioNTech): ionizable at pH<6.5 → endosomal escape. Standard 4-component LNP: ionizable lipid + DSPC + cholesterol + PEG-lipid.",
        advantages=[
            "No separate adjuvant needed for mRNA vaccines",
            "Dual function: delivery + immune activation",
            "Well-characterized and approved formulation",
        ],
        limitations=[
            "Reactogenicity (attributed to LNP innate activation)",
            "Anti-PEG antibodies after repeated dosing",
            "LNP distribution to liver (off-target expression)",
        ],
        notes="Recognition that LNP itself has adjuvant activity (Alameh et al., Immunity 2022) changed how mRNA vaccines are understood — it's not just mRNA, the vehicle contributes significantly to immunogenicity.",
    ),
]


def query_adjuvants(
    category: str = None,
    th1_strong: bool = False,
    cd8_strong: bool = False,
    approved_only: bool = False,
) -> List[Adjuvant]:
    """Query adjuvant database.

    Args:
        category: Filter by adjuvant category
        th1_strong: Only Th1 or Th1-biased adjuvants
        cd8_strong: Only adjuvants with strong CD8 enhancement
        approved_only: Only approved adjuvants
    """
    results = list(ADJUVANT_DATABASE)

    if category:
        c_lower = category.lower()
        results = [a for a in results if c_lower in a.category.lower()]

    if th1_strong:
        results = [a for a in results if "th1" in a.immune_profile.lower()]

    if cd8_strong:
        results = [a for a in results if "strong" in a.cd8_enhancement.lower()]

    if approved_only:
        results = [a for a in results if "approved" in a.regulatory_status.lower()]

    return results
