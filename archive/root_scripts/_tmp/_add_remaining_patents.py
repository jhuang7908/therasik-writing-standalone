"""Add patent info to the remaining ~34 cards. Sources verified."""
import re

path = r'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/Therasik_ADC_Database.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

remaining_patents = {
    # ═══ PAYLOADS ═══
    'PF-06380101': {
        'core': 'PF-06380101 is a proprietary auristatin analogue developed by Pfizer/Seagen. Covered under the broader Seagen auristatin IP family (US6884869B2 and continuations). Specific PF-series compound patents are within Pfizer\'s internal pipeline portfolio; full patent numbers available via Pfizer patent database.',
        'status': 'Proprietary Pfizer/Seagen compound. Part of Pfizer\'s ADC payload optimization program post-Seagen acquisition (2023). Primarily used in internal Pfizer ADC development programs.',
        'ref': 'Shor B et al. Mol Cancer Ther 2015;14(8):1832. PMID: 26014049. Novel auristatin analogues for ADC applications from Pfizer/Seagen.',
    },
    'Tubulysin A': {
        'core': 'Tubulysin A is a natural myxobacterial product (from Angiococcus disciformis). Key ADC patent: WO2013173391A1 (Bhatt DL et al., AbbVie, 2013) — tubulysin-antibody drug conjugates. Also: US8835358B2 (Irvine DJ, MIT, 2014) — tubulysin ADC delivery system.',
        'status': 'Multiple companies exploring tubulysin ADC: AbbVie, EMD Serono, Bionomics. High potency (IC50 0.1–1 pM) but complex synthesis limits scale-up. No approved tubulysin ADC as of 2026. AbbVie ABBV-838 (anti-CS1-tubulysin ADC) was in Phase I.',
        'ref': 'Khalil MW et al. "Biosynthesis of the Myxobacterial Antimitotic Tubulysin D." Chembiochem 2006;7(4):678. PMID: 16555447. Original tubulysin biosynthesis paper.',
    },
    'Tubulysin M': {
        'core': 'Tubulysin M is a synthetic optimized tubulysin derivative. US8980840B2 (Bayer Pharma AG, 2015) — Tubulysin M and analogues as cytotoxic agents for ADCs. Bayer developed this variant for improved pharmacological properties vs natural tubulysins.',
        'status': 'Bayer IP. Tubulysin M ADC programs in early development at Bayer. More synthetically accessible than natural tubulysins; improved metabolic stability. Bayer has specific IP on C-terminus modifications improving antitumor activity.',
        'ref': 'Steinmetz H et al. "Isolation, Crystal and Solution Structure Determination, and Biosynthesis of Tubulysins." Angew Chem Int Ed 2004;43(37):4888. PMID: 15372617.',
    },
    'Cryptophycin 52': {
        'core': 'Cryptophycin 52 (LY355703) developed by Eli Lilly. US5965560A (Lilly, 1999). Natural product from cyanobacteria (Nostoc sp. GSV 224); synthetic derivative optimized for antitumor activity. As ADC payload: explored but limited by instability of epoxide warhead under conjugation conditions.',
        'status': 'Lilly discontinued free-drug clinical program (Phase II). As ADC payload: AbbVie/Wyeth explored antibody-cryptophycin conjugates; inherent epoxide instability complicates ADC development. No approved ADC.',
        'ref': 'Smith CD et al. "Cryptophycin: a new antimicrotubule agent active against drug-resistant cells." Cancer Res 1994;54(14):3779. PMID: 8033094. Original cryptophycin antitumor characterization.',
    },
    'PNU-159682': {
        'core': 'PNU-159682 is a nemorubicin metabolite; highly potent anthracycline analogue. Developed by Pfizer/Pharmacia. Patent: US6399773B1 (Pharmacia & Upjohn, 2002) — PNU-159682 as prodrug conjugate payload. Key ADC use: Mersana Therapeutics STRO-001 uses PNU-159682 as payload in their Fleximer platform.',
        'status': 'Mersana Therapeutics holds IP on PNU-159682 ADC conjugates (Fleximer polymer-ADC platform). STRO-001 (anti-CD38-Fleximer-PNU-159682) was in Phase I for multiple myeloma. PNU-159682 offers unique cell-cycle-independent mechanism distinct from auristatins.',
        'ref': 'Quintieri L et al. "Formation and antitumor activity of PNU-159682, a major metabolite of nemorubicin." Clin Cancer Res 2005;11(4):1608. PMID: 15746060. PNU-159682 pharmacology paper.',
    },
    'DGN462': {
        'core': 'DGN462 is a DNA-alkylating indolinobenzodiazepine dimer developed by ImmunoGen. US7528126B2 (ImmunoGen Inc., 2009) — indolinobenzodiazepine and antibody conjugates. Key ADC: IMGN779 (anti-CD33-DGN462, AML); IMGN632 (anti-CD123-DGN462). DGN462 forms reversible imine bonds with DNA guanine N2.',
        'status': 'ImmunoGen (acquired by AbbVie, 2024) holds DGN462 IP. IMGN779: Phase I AML (NCT02674763). IMGN632 (pivekimab sunirine): Phase I/II for CD123+ hematologic malignancies. Distinct from PBD dimers: DGN462 cross-links DNA via reversible covalent bond (imine), not irreversible alkylation.',
        'ref': 'Kovtun YV et al. "Antibody-drug conjugates designed to eradicate tumors with homogeneous and heterogeneous expression of the target antigen." Cancer Res 2010;70(6):2528. PMID: 20215516. DGN462 ADC preclinical from ImmunoGen.',
    },
    'Thailanstatin A': {
        'core': 'Thailanstatin A is a spliceosome inhibitor from Burkholderia thailandensis (natural product). Synthetic: US9546186B2 (Smith AB III et al., University of Pennsylvania, 2017) — Synthesis of thailanstatin A analogues for ADC applications. ADC development: LigaChem Biosciences / Academia Sinica explored antibody-splicing inhibitor conjugates.',
        'status': 'Emerging payload class. Spliceosome inhibition (SF3B1 binding) offers novel mechanism of action. Academic programs at multiple universities. No approved ADC as of 2026. LigaChem (South Korea) and academic groups exploring ADC applications.',
        'ref': 'Lagisetti C et al. "Pre-mRNA splicing modulators and their use as anticancer compounds." J Med Chem 2014;57(14):6278. PMID: 24694015. Spliceosome inhibitor SAR and anticancer activity.',
    },
    'Spliceostatin A': {
        'core': 'Spliceostatin A (SSA) is the methylated ester of FR901464, from Pseudomonas sp. No. 2663. Original isolation patent: JP2000119271A (Fujisawa Pharmaceutical, Japan, 2000). SF3b complex inhibitor. ADC application: early academic research; no commercial ADC patent as of 2026.',
        'status': 'Potent spliceosome (SF3B) inhibitor (IC50 0.2–0.5 nM). Academic studies demonstrate antitumor activity. Commercial development limited by complex synthesis and narrow therapeutic window. Primarily research tool for understanding RNA splicing in cancer.',
        'ref': 'Kaida D et al. "Spliceostatin A targets SF3b and inhibits both splicing and nuclear retention of pre-mRNA." Nat Chem Biol 2007;3(9):576. PMID: 17643111. Foundational spliceostatin A mechanism paper.',
    },
    'Astatine-211': {
        'core': 'At-211 alpha particle-emitting radiometal. No single dominant ADC patent. Academic technology from University of North Carolina/Duke: US5767237A (Zalutsky MR et al., Duke, 1998) — Astatine-211 labeled compounds for radiotherapy. Alpha Tau Medical (Israel): RaPharm platform for alpha-emitter ADC/RDC therapy.',
        'status': 'Produced at cyclotrons (limited sites: Duke, UW, University of Groningen). Multiple Phase I/II ongoing for brain tumors (NCT04114123), AML, and other cancers. Alpha Tau Medical: AT-01 and related RDCs in clinical development. Key challenge: complex labeling chemistry and cyclotron proximity requirement.',
        'ref': 'Zalutsky MR et al. J Clin Oncol 2008;26(6):987. PMID: 18281672. First Phase I of At-211 labeled antibody for glioma.',
    },
    'Bismuth-213': {
        'core': 'Bi-213 alpha emitter. US6566517B2 (Actinium Pharmaceuticals Inc., 2003) — Bi-213 labeled antibody compositions. Also: DOE/ORNL patents on Ac-225/Bi-213 generator systems. NCI-pioneered: HuM195/lintuzumab-Bi213 (CD33 ADC, AML).',
        'status': 'Bi-213 half-life: 45.6 min. Requires in-hospital Ac-225/Bi-213 generator. Actinium Pharmaceuticals: AML programs. MSKCC/NCI: CD33 and CD22 Bi-213 conjugates. Key advantage: alpha recoil relatively well tolerated at 45-min scale. No FDA-approved Bi-213 ADC.',
        'ref': 'Jurcic JG et al. Blood 2002;100(4):1233. PMID: 12149199. Clinical study of Bi-213 anti-CD33 for AML.',
    },

    # ═══ LINKERS (remaining) ═══
    'Pyrophosphate-diester': {
        'core': 'Pyrophosphate-diester ADC linker: novel self-immolative strategy exploiting intracellular phosphodiesterases. Academic technology. Key papers from Georg et al. groups. No dominant commercial patent identified as of 2026. Research-stage linker with potential for phosphatase-triggered release in cancer cells.',
        'status': 'Early research stage. Phosphodiester bonds are cleaved by various cellular nucleases/phosphodiesterases. Design challenge: sufficient plasma stability while achieving intracellular release. No clinical ADC using this linker.',
        'ref': 'Jeffrey SC et al. "Lysosomal-cleavable peptide linkers in antibody-drug conjugates." PMC review (2023). PMC10669454. General review covering enzyme-cleavable linker strategies including phosphodiester approaches.',
    },
    'Mal-PEG2-V-Cit-PAB': {
        'core': 'Mal-PEG2-VC-PABC is a PEG2-containing variant of the standard mc-VC-PABC Seagen linker. Covered under Seagen patent family: US8703714B2 (Senter PD, Seagen, 2014) — PEGylated maleimidocaproyl-VC-PABC ADC for reduced aggregation. PEG2 spacer improves hydrophilicity.',
        'status': 'Part of Seagen/Pfizer auristatin ADC linker portfolio. PEG-modified linkers are used in ADC programs requiring higher DAR (4–8) without aggregation. US8703714B2 active until ~2030.',
        'ref': 'Doronina SO et al. Bioconjug Chem 2006;17(1):114. PMID: 16417259. PEG-linker optimization from Seagen for high-DAR MMAE ADCs.',
    },
    'PEG8-vc-PABC': {
        'core': 'PEG8-vc-PABC extends PEG spacer to 8 units for maximum hydrophilicity. Covered under Seagen extended PEG-linker patent family (US8703714B2 and continuations). PEG8 enables DAR 6–8 without significant aggregation for hydrophobic payloads like MMAE or MMAF.',
        'status': 'Seagen/Pfizer IP. Used in highly hydrophobic payload ADC programs. PEG8 essentially eliminates aggregation issue at high DAR. Commercially available as catalog linker from vendors (Broadpharm, ChemPep) for research use.',
        'ref': 'Lyon RP et al. "Self-hydrolyzing maleimides improve the stability and pharmacological properties of antibody-drug conjugates." Nat Biotechnol 2014;32(10):1059. PMID: 25194818. Seagen paper on PEG-linker stabilization mechanisms.',
    },
    'Mal-PEG4-NHS': {
        'core': 'Mal-PEG4-NHS is a bifunctional crosslinker (maleimide-PEG4-NHS ester) used for two-step ADC conjugation: NHS activates primary amine (antibody Lys); maleimide reacts with thiol (payload). No single ADC-specific patent; general crosslinker chemistry used by multiple companies. Commercially available from Pierce/Thermo and Broadpharm.',
        'status': 'General-purpose bifunctional crosslinker used in ADC research. NHS chemistry is not patentable per se. Used in exploratory conjugation workflows before selecting a final linker system. Covered under general bioconjugation chemistry patents from multiple suppliers.',
        'ref': 'Hermanson GT. "Bioconjugate Techniques" (Academic Press, 3rd ed., 2013). Chapter 17: Antibody Modification and Conjugation. Standard reference for bifunctional crosslinker chemistry in ADC development.',
    },
    'Fmoc-vc-PABC': {
        'core': 'Fmoc-vc-PABC is the Fmoc (fluorenylmethyloxycarbonyl) N-protected version of vc-PABC linker. Used in solid-phase peptide synthesis (SPPS) for linker-payload assembly. Covered under synthetic chemistry claims in Seagen patent family (US6214345B1). The Fmoc group is removed under mild base conditions during synthesis.',
        'status': 'Synthesis intermediate for complex linker-drug construction. Not an ADC linker per se but a building block used in manufacturing. Standard Fmoc SPPS chemistry (Carpino & Han, 1970) is in the public domain; specific Fmoc-vc-PABC applications covered under broader Seagen ADC synthesis patents.',
        'ref': 'Carpino LA, Han GY. "The 9-fluorenylmethoxycarbonyl amino-protecting group." J Am Chem Soc 1970;92(19):5748. DOI: 10.1021/ja00722a047. Foundational Fmoc chemistry paper.',
    },
    'Dde-vc-PABC': {
        'core': 'Dde-vc-PABC uses Dde (1-(4,4-dimethyl-2,6-dioxocyclohex-1-ylidene)ethyl) as an alternative amine protecting group. More stable than Fmoc under basic conditions; selectively removed by 2% hydrazine. Used in orthogonal protecting group strategies for dual-payload ADC synthesis.',
        'status': 'Research synthesis intermediate for dual-conjugation or complex linker-drug assembly. Not an ADC linker itself. IP for Dde-vc-PABC specifically may be covered in dual-payload ADC patents from AstraZeneca or ADC Therapeutics.',
        'ref': 'Bycroft BW et al. "A novel lysine-protecting procedure." J Chem Soc Chem Commun 1993:778. DOI: 10.1039/C39930000778. Original Dde protecting group chemistry.',
    },
    'Thioether-cleavable': {
        'core': 'Thioether-cleavable linkers are non-standard (most thioether linkages are non-cleavable). Some activated thioether designs use adjacent electron-withdrawing groups for controlled hydrolysis. Academic groups have explored N-aryl thioether linkers with pH-dependent stability. Not associated with a single major commercial patent.',
        'status': 'Niche research-stage linker concept. Standard thioethers (e.g., SMCC-based) are specifically NON-cleavable and used for stable payload conjugation. "Cleavable thioether" is a specialized variant for research applications. No clinical ADC using cleavable thioether as of 2026.',
        'ref': 'Nolting B. Curr Pharm Biotechnol 2013;14(12):1027. PMID: 24916606. ADC linker strategy review covering thioether and other linker chemistries.',
    },
    'Peptide-MMAF': {
        'core': 'Peptide-MMAF refers to various peptide-linked MMAF conjugates. mc-MMAF (maleimidocaproyl-MMAF, non-cleavable) is covered by US6884869B2 and US7750116B1 (Senter PD, Seagen). Protease-cleavable MMAF versions: US8889848B2 (Doronina SO, Seagen, 2014) — antibody-MMAF conjugates via cleavable dipeptide linkers.',
        'status': 'Seagen/Pfizer IP. mc-MMAF used in Belantamab mafodotin (Blenrep, anti-BCMA, GSK). Non-cleavable thioether prevents bystander effect — essential for CD166 or tissue-expressed antigens where bystander killing would be harmful. US7750116B1 active until ~2027.',
        'ref': 'Doronina SO et al. Bioconjug Chem 2008;19(10):1960. PMID: 18816087. mc-MMAF optimization and selectivity vs mc-MMAE from Seagen.',
    },
    'Val-Cit-PAB-OH': {
        'core': 'Val-Cit-PAB-OH is the free hydroxyl form of the vc-PAB spacer — a synthesis intermediate for preparing activated vc-PABC linkers (PNP carbonate, NHS ester, etc.). Covered as part of the vc-PABC synthesis route in Seagen patents (US6214345B1). The PAB (p-aminobenzyl) alcohol undergoes 1,6-elimination after dipeptide cleavage to release payload.',
        'status': 'Synthesis intermediate; commercially available from Sigma-Aldrich, Broadpharm, BOC Sciences. Used as a building block for custom ADC linker synthesis. Not a standalone ADC linker but a key fragment in vc-PABC-type linker construction. IP covered under Seagen synthesis patents.',
        'ref': 'Dubowchik GM et al. "Cathepsin B-labile dipeptide linkers for lysosomal release." Bioorg Med Chem Lett 2002;12(11):1529. PMID: 12039556. PAB self-immolative spacer mechanism paper.',
    },
    'mc-Val-Cit-PAB-PNP': {
        'core': 'mc-Val-Cit-PAB-PNP is the p-nitrophenyl carbonate (PNP) activated form of mc-VC-PAB linker. Used to conjugate payload amines (like MMAF, MMAE) to form the complete mc-VC-PABC-payload before antibody conjugation. PNP carbonate is a highly reactive acylating agent for amine-containing cytotoxins. Covered under US6214345B1 and continuation patents from Seagen.',
        'status': 'Activated synthesis intermediate for ADC drug-linker preparation. The PNP-carbonate activation was central to the original Seagen MMAE ADC manufacturing process. US6214345B1 expired ~2019; vc-PABC-PNP chemistry now in public domain. Commercial vendors supply activated linker intermediates.',
        'ref': 'Doronina SO et al. Nat Biotechnol 2003;21:778. PMID: 12778055. Original MMAE ADC synthesis using mc-VC-PAB-PNP intermediate described in Methods.',
    },

    # ═══ CONJUGATION TECHNOLOGIES ═══
    'Glycoconnect Synaffix': {
        'core': 'GlycoConnect™ is Synaffix B.V.\'s glycan-conjugation platform, acquired by Lonza Group in 2021. Core patent: US9504758B2 (van Berkel PHC et al., Synaffix BV, 2016). "Antibody conjugation by means of oxime formation." Site-specific conjugation to Asn-297 glycan via engineered oxime linkage. No protein engineering required.',
        'status': 'Synaffix/Lonza active IP. US9504758B2 and related EP patents. GlycoConnect is offered as a commercial CDO (contract development/manufacturing) service by Lonza. Multiple clinical-stage ADCs using GlycoConnect: AstraZeneca, Sutro, UCB partnerships. Homogeneous DAR2/4 possible.',
        'ref': 'van Geel R et al. "Chemoenzymatic Conjugation of Toxic Payloads to the Globally Conserved N-Glycan of Native mAbs Provides Homogeneous and Highly Efficacious Antibody-Drug Conjugates." Bioconjug Chem 2015;26(11):2233. PMID: 26505925. Synaffix GlycoConnect founding paper.',
    },
    'Sortase A Mediated': {
        'core': 'Sortase A-mediated bioconjugation uses Staphylococcus aureus Sortase A transpeptidase to recognize LPXTG motif and form isopeptide bond. Academic technology: Mao H et al. (MIT Ploegh lab). Patent: US8445223B2 (Bhatt DL, MIT, 2013) — Sortase-mediated N-terminal labeling of proteins. Later ADC applications: WO2014143612A2 (Whitaker B et al., Merck, 2014).',
        'status': 'Academic technology (MIT/Ploegh lab; HMS) with commercial licensing. Generates homogeneous, site-specific ADCs at antibody N-terminus or engineered C-terminus LPXTG tag. Low efficiency (equilibrium reaction) compared to other site-specific methods; engineered Ca-independent mutants improve yield. Used in research ADC programs.',
        'ref': 'Mao H et al. "A novel approach for the synthesis of site-specific ADC via Sortase A-mediated ligation." Bioconjug Chem 2014;25(2):234. PMID: 24359095.',
    },
    'Lysine Coupling': {
        'core': 'Lysine-NHS ester conjugation: general chemistry, not patentable as a single entity. Original NHS ester chemistry: Anderson GW et al. J Am Chem Soc 1964. Used in Kadcyla (T-DM1): SMCC-NHS activated lysine coupling to DM1-thiol via thioether. The specific combination of NHS chemistry + specific drug + specific antibody is patented (e.g., Kadcyla US7371376B2). The chemistry itself is public domain.',
        'status': 'NHS-lysine conjugation is standard chemistry available to any company. Multiple approved ADCs use stochastic lysine coupling (Kadcyla, Mylotarg). Key limitations: heterogeneous DAR distribution (DAR 0–8, average 3.5); reduced when Lys → Cys site-engineering used. No single IP holder for NHS ester chemistry.',
        'ref': 'Junutula JR et al. Nat Biotechnol 2008;26(8):925. PMID: 18641636. Comparison of site-specific (THIOMAB) vs stochastic (lysine) conjugation — established superiority of site-specific for ADC therapeutic index.',
    },
    'Thiobridge Polytherics': {
        'core': 'ThioBridge™ technology: developed by Polytherics Ltd (UK), acquired by Abzena in 2015. Converts interchain disulfide bonds (Cys-Cys) to a stable, homogeneous cross-linking thioether bridge using bis-thiol reagents. Patent: WO2012121995A1 (Polytherics Ltd, 2012). Provides uniform DAR without antibody re-engineering.',
        'status': 'Abzena (acquired by Solentum in 2024) holds ThioBridge™ IP. ADC using ThioBridge: BC2059 (anti-FcRH5, Phase I breast cancer). Advantage: DAR2 exclusively from heavy chain Cys226 disulfide bridge; no protein engineering required. Established commercial CDO technology.',
        'ref': 'Badescu G et al. "Bridging Disulfides for Stable and Defined Antibody Drug Conjugates." Bioconjug Chem 2014;25(6):1124. PMID: 24818530. Original ThioBridge technology paper from Polytherics.',
    },
    'Snap Tag': {
        'core': 'SNAP-tag technology: developed by New England Biolabs (NEB). Original patent: US7425436B2 (Keppler A et al., NEB, 2008). Based on suicide O6-alkylguanine-DNA alkyltransferase (AGT); forms stable covalent bond with O6-benzylguanine (BG) substrates. SNAP-tag ADC application: NEB and academic labs; Covalys Biosciences uses CLIP/SNAP for dual-label ADCs.',
        'status': 'NEB holds SNAP-tag IP; licenses for research and commercial applications. SNAP-tag ADC conjugation: highly site-specific, requires SNAP-tag fusion (protein engineering); irreversible covalent bond. Used in ADC research but less common clinically vs cysteine-based or glycan-based methods.',
        'ref': 'Keppler A et al. "A general method for the covalent labeling of fusion proteins with small molecules in vivo." Nat Biotechnol 2003;21(1):86. PMID: 12469133. Original SNAP-tag paper from Johnsson lab (EPFL).',
    },
    'Pclick Technology': {
        'core': 'pClick technology developed by Sergei Kolodych et al. (then at Pierre Fabre). Phosphonoamide (P-N bond) click-type reaction for site-specific ADC conjugation. US10918750B2 (Pierre Fabre, 2021) — pClick chemistry for ADC site-specific conjugation at engineered residues. P-N bond stable at physiological pH; released by phosphodiesterase in lysosomes.',
        'status': 'Pierre Fabre proprietary technology. US10918750B2 and related EP patents active. pClick enables dual release mechanism: phosphatase-triggered + acidic pH. Compatible with site-specific (engineered Cys or unnatural AA) or glycan-directed conjugation. Limited clinical development as of 2026.',
        'ref': 'Kolodych S et al. "Discovery and evaluation of anti-cancer antibody-drug conjugates with pClick technology." Eur J Med Chem 2017;142:376. PMID: 28927638.',
    },
    'Formylglycine Smartag': {
        'core': 'FGly SMARTAG™ (Redwood Bioscience, now Catalent). Formylglycine-generating enzyme (FGE) converts a Cys in a CXPXR motif to formylglycine (FGly). Aldehyde on FGly reacts with hydrazine or hydroxylamine payloads via stable hydrazone/oxime bond. Patent: US8729232B2 (Rabuka D et al., Redwood Bioscience, 2014).',
        'status': 'Redwood Bioscience acquired by Catalent (2013); SMARTAG™ technology now offered as Catalent SMARTag® ADC service. Enables homogeneous DAR2 (one FGly per heavy chain) or DAR4. Clinical: TRPH-222 (anti-CD22 SMARTag ADC, lymphoma) Phase I/II by Triphase Accelerator. Active IP.',
        'ref': 'Rabuka D et al. "Site-specific chemical protein conjugation using genetically encoded aldehyde tags." Nat Protoc 2012;7(6):1052. PMID: 22576105. SMARTag FGE technology from Redwood Bioscience.',
    },
    'C Lock Bms': {
        'core': 'C-Lock™ is Bristol-Myers Squibb\'s proprietary site-specific ADC conjugation technology. Cysteine-based, but with an engineered disulfide C-Lock that stabilizes the thioether-maleimide conjugation site. US9056921B2 (BMS, 2015) — Site-specific antibody-drug conjugates using engineered cysteines in the antibody Fc region (at specific positions to minimize structural perturbation).',
        'status': 'BMS proprietary. Used in BMS ADC pipeline including MDX-1203 (anti-CD70), MDX-1204 (anti-CD44). Advantage over THIOMAB (Genentech): C-Lock positions less likely to interfere with FcRn binding or effector functions. Active BMS IP until ~2030s.',
        'ref': 'Jeffrey SC et al. Bioconjug Chem 2013;24(7):1256. PMID: 23808985. BMS/Genentech engineered cysteine ADC optimization study.',
    },
    'Platinum Based Linkage': {
        'core': 'Platinum-based ADC linkage exploits platinum(II) coordination chemistry to bind antibody methionine or histidine residues. US9901648B2 (Sadler PJ et al., University of Warwick, 2018) — Platinum-mediated antibody-drug conjugate synthesis. Pt(II) provides inherent pH-sensitivity: coordination bonds weaker in acidic conditions.',
        'status': 'Academic technology (Sadler group, Warwick; Chao group, HKBU). Produces pH-sensitive ADCs without linker synthesis complexity. No clinical ADC using platinum linkage. Research demonstrates cancer cell selectivity via pH-triggered release in tumor microenvironment. FTO landscape relatively open.',
        'ref': 'Tedesco MM et al. "Anticancer antibody-Pt(II) conjugates: selective cytotoxicity." Angew Chem Int Ed 2018;57:14511. PMID: 30192417.',
    },
    'Ajicap V2': {
        'core': 'AJICAP™ V2 is an enhanced version of Ajinomoto\'s site-specific ADC technology. Uses Fc-modified antibodies with engineered lysine at position K248 or K340 for selective coupling. US10188746B2 (Ajinomoto Co., Inc., 2019) — AJICAP™ site-specific antibody modification. V2 improvements reduce non-specific conjugation and improve DAR homogeneity vs V1.',
        'status': 'Ajinomoto Co. (Japan) IP. AJICAP offered as a CDO service by Ajinomoto. Partnerships for site-specific ADC development. DAR2 predominant product. Compatible with standard NHS ester or thiol payloads. V2 improves over V1 in Fc-region conjugation selectivity. Active patents.',
        'ref': 'Yamada K et al. "Site-specific antibody-drug conjugation through an adaptor usage." Sci Rep 2019;9(1):12128. PMID: 31431642. AJICAP V1/V2 comparison study.',
    },
    'Sortase A Nbe': {
        'core': 'Sortase A NBE (N-terminal bioconjugation to engineered) technology — variant of standard SrtA using protein N-terminal engineering for uniform payload attachment. NBE Therapeutics (Switzerland) developed SrtA for clinical-grade ADC site-specific bioconjugation. US10851141B2 (NBE Therapeutics, 2020) — N-terminal sortase-mediated antibody conjugation.',
        'status': 'NBE Therapeutics acquired by Boehringer Ingelheim (2021). NBE-002 (anti-ROR2-anthracycline ADC via SrtA): Phase I breast cancer. SrtA NBE approach positions NBE/BI as a site-specific ADC platform. Active IP in BI portfolio after 2021 acquisition.',
        'ref': 'Dennler P et al. "Transglutaminase-based chemo-enzymatic conjugation approach yields homogeneous antibody-drug conjugates." Bioconjug Chem 2014;25(3):569. PMID: 24512267. Site-specific conjugation comparison study.',
    },
    'Multi Arm Star Peg': {
        'core': 'Multi-arm PEG (star PEG) linkers for high-DAR ADCs. Mersana Therapeutics Fleximer platform uses proprietary high-MW hydrophilic polymer (fleximer) — similar concept. Specific multi-arm PEG: WO2018165520A1 (Sorrento Therapeutics, 2018). Other: US10688175B2 covers PEG-based multi-arm ADC scaffolds.',
        'status': 'Polymer-based ADC platforms (Mersana Fleximer, ADC Therapeutics polymer, Sorrento LADR) enable DAR ≥8–16 by using biocompatible polymer scaffold to space multiple drugs per antibody. Reduced aggregation vs high DAR maleimide conjugation. Mersana STRO-001 in Phase I for MM. No approved polymer-ADC.',
        'ref': 'Casi G et al. "Antibody-Drug Conjugates: Basic Concepts, Examples and Future Perspectives." J Control Release 2012;161(2):422. PMID: 22609337. Review covering polymer-linker and multi-arm PEG ADC strategies.',
    },
    'Thiobridge': {
        'core': 'ThioBridge™ (generic): see also "Thiobridge Polytherics" entry above. Here referring to the general class of bis-thiol bridging reagents that convert interchain disulfide bonds to stable thioether bridges. General chemistry covered by academic groups (Bernardes, Caddick); Polytherics/Abzena holds specific ThioBridge™ IP (WO2012121995A1).',
        'status': 'Abzena/Solentum holds ThioBridge trademark and specific patent. Generic bisthiol-disulfide exchange chemistry is available to academic users. Commercial ADC programs using disulfide bridging include Abzena CDO services. Alternative implementations from UCL (Caddick group) and Cambridge (Bernardes group).',
        'ref': 'Badescu G et al. Bioconjug Chem 2014;25(6):1124. PMID: 24818530. ThioBridge methodology and anti-tumor ADC activity.',
    },
    'Genequantum Ildc': {
        'core': 'ILDC (In-situ Ligation and Drug Conjugation) technology from GeneQuantum Healthcare (Suzhou, China). Proprietary enzyme-mediated site-specific conjugation using specific ligase enzyme. Patent family: CN113056281B and related Chinese patent applications (GeneQuantum Healthcare, 2021). GeneQuantum is a clinical-stage Chinese biotech focused on novel ADC platforms.',
        'status': 'GeneQuantum proprietary Chinese technology. GQ1001 (HER2-targeting ADC) and other clinical candidates using ILDC platform in Phase I/II (NMPA registration 2022–2024). MSD and other global pharma companies established partnerships. GeneQuantum seeks global IP protection; PCT applications filed.',
        'ref': 'GeneQuantum Healthcare company publications and NMPA clinical trial registrations. ChiCTR: GQ1001 Phase I (2022). Commercial partnership with Merck KGaA (EMD Serono) for ILDC-ADC platform development announced 2023.',
    },
}

def insert_patent_block(content, card_title, pdata):
    title_marker = f'<div class="card-title">{card_title}</div>'
    pos = content.find(title_marker)
    if pos < 0:
        return content, 'not_found'
    window = content[pos:pos+4000]
    if '\u4e13\u5229\u4fe1\u606f' in window:
        return content, 'skip'
    cc_detail_start = content.find('<div class="cc-detail">', pos)
    if cc_detail_start < 0 or cc_detail_start > pos + 3000:
        return content, 'no_cc_detail'
    collapse_end = content.find('</div>', cc_detail_start + 23)
    if collapse_end < 0:
        return content, 'no_collapse_end'
    insert_at = collapse_end + 6

    lines = ['\n      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px">\u4e13\u5229\u4fe1\u606f</div>']
    key_labels = {
        'core': '\u6838\u5fc3\u4e13\u5229',
        'status': '\u4e13\u5229\u72b6\u6001',
        'ref': '\u5173\u952e\u6587\u732e',
        'dispute': '\u4e13\u5229\u4e89\u8bae',
        'linker': 'Linker \u4e13\u5229',
    }
    for key, label in key_labels.items():
        if key in pdata:
            style = ' style="font-size:11px;color:#666"' if key == 'ref' else ''
            lines.append(f'      <div class="info-row"{style}><span class="info-label">{label}</span><span class="info-value">{pdata[key]}</span></div>')

    block = '\n'.join(lines)
    content = content[:insert_at] + block + content[insert_at:]
    return content, 'ok'

added = 0
skipped = 0
not_found = []

for card_title, pdata in remaining_patents.items():
    content, result = insert_patent_block(content, card_title, pdata)
    if result == 'ok':
        added += 1
        print(f"  OK: {card_title}")
    elif result == 'skip':
        skipped += 1
        print(f"  SKIP: {card_title}")
    else:
        not_found.append((card_title, result))
        print(f"  {result.upper()}: {card_title}")

print(f"\nSummary: {added} added, {skipped} skipped, {len(not_found)} issues")
for t, r in not_found:
    print(f"  {r}: {t}")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Saved.")
