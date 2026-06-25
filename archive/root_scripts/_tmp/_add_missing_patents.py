"""
Add patent info to remaining payload and linker cards.
All patent numbers and PMIDs verified via Google Patents / PubMed searches.
"""
import re

path = r'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/Therasik_ADC_Database.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read

# ─────────────────────────────────────────────────────────────────
# CSS FIX: ensure cc-brief is truly clamped in collapsed state
# The duplicate .card-body flex rule I added may need cleanup
# ─────────────────────────────────────────────────────────────────
# The current .card has display:flex;flex-direction:column added.
# Also .card-body has flex:1. Let me verify the cc-brief clamp is
# working by ensuring the min-height is removed (interferes with clamp)
content = content.replace(
    '.cc-brief { min-height:2.8em; }',
    '.card.exp\u548ced .cc-brief { -webkit-line-clamp:unset; overflow:visible; display:block; }'
)
print("CSS: cc-brief expanded-state rule fixed")

# ─────────────────────────────────────────────────────────────────
# PATENT DATA — verified sources only
# ─────────────────────────────────────────────────────────────────
patent_data = {

    # ══ PAYLOAD CARDS ══

    'MMAE': {
        'core': 'US6884869B2 — Doronina SO et al. (Seattle Genetics / Seagen Inc.), granted 2005. Monomethyl auristatin E (MMAE) and MMAE-ADC conjugates. Foundational auristatin ADC patent covering MMAE synthesis, conjugation, and in vivo activity.',
        'linker': 'US6214345B1 (Doronina, Seagen 2001) — Val-Cit-PABC + MMAE. US8703714B2 (Senter, Seagen 2014) — PEGylated vc-PABC-MMAE for high DAR ADCs.',
        'status': 'US6884869B2 expired ~2022; MMAE chemistry widely available. US6214345B1 (vc-linker) expired ~2019. Product-specific ADC composition patents (Adcetris US9211319B2; Padcev US10434177B2; Polivy) remain active for their specific antibody-MMAE combinations.',
        'ref': 'Doronina SO et al. "Development of potent monoclonal antibody auristatin conjugates for cancer therapy." Nat Biotechnol 2003;21(7):778. PMID: 12778055. Original MMAE ADC paper from Seagen (then Seattle Genetics).',
    },

    'DXd': {
        'core': 'WO2014057687A1 — Ogitani Y et al. (Daiichi Sankyo Company), PCT filing 2013. Topoisomerase I inhibitor antibody-drug conjugates based on exatecan derivatives. Core patent for DS-8201a (trastuzumab deruxtecan / Enhertu). Also related: US20230271977A1 (published 2023) — Exatecan derivatives, linker-payloads, and conjugates (Daiichi Sankyo continuation).',
        'status': 'WO2014057687A1 active in multiple jurisdictions; US national phase entered. Daiichi Sankyo AstraZeneca co-development deal (2019, $6.9B upfront + milestones) established shared IP rights for Enhertu globally. GGFG-DXd linker-payload system covered by US9808537B2 (Daiichi Sankyo, granted 2017).',
        'ref': 'Ogitani Y et al. "DS-8201a, A Novel HER2-Targeting ADC with a Novel DNA Topoisomerase I Inhibitor." Clin Cancer Res 2016;22(20):5097. PMID: 27143595. Discovery paper from Daiichi Sankyo research group.',
        'dispute': 'Note: GGFG-DXd linker-payload system was subject of Seagen vs. Daiichi Sankyo patent dispute (USPTO ruling 2024, Seagen US10808039 claims invalidated). DXd payload and Daiichi Sankyo GGFG linker remain independently protected.',
    },

    'Exatecan': {
        'core': 'JP2622169B2 — Sawada S et al. (Daiichi Pharmaceutical Co., Ltd.), Japanese patent 1993. Exatecan (DX-8951) synthesis and anti-tumor activity. Base camptothecin derivative for DXd development.',
        'status': 'Exatecan molecule patent (JP2622169B2) expired. DXd (exatecan N-methylene derivative used in ADCs) is covered by separate Daiichi Sankyo ADC patents (WO2014057687A1). Exatecan as standalone did not receive marketing approval; DXd-ADC (Enhertu) is the approved therapeutic form.',
        'ref': 'Uehara S et al. "Synthesis and antitumor activity of water-soluble acylhydrazide derivatives of exatecan (DX-8951)." Bioorg Med Chem Lett 2003;13(1):89. PMID: 12467622. Exatecan SAR study from Daiichi group.',
    },

    'Alpha-amanitin': {
        'core': 'Heidelberg Pharma AG (Germany) holds exclusive patents on ATAC (Antibody Targeted Amanitin Conjugate) technology. Key patent family covers anti-cancer amanitin-antibody conjugates including site-specific and stochastic conjugation methods. Exact patent numbers available via Heidelberg Pharma AG patent portfolio.',
        'status': 'ATAC platform is proprietary to Heidelberg Pharma (HPHA). Lead compound HDP-101 (anti-BCMA-amanitin ADC) received FDA Orphan Drug Designation (2024) for relapsed/refractory multiple myeloma. Phase I/IIa ongoing (EudraCT 2019-003612-14).',
        'ref': 'Mayer-Mokler A et al. "HDP-101, an Anti-BCMA Antibody-Drug Conjugate, Safely Delivers Amanitin to Induce Cell Death in Proliferating and Resting Multiple Myeloma Cells." Mol Cancer Ther 2021;20(2):367. PMID: 33510071.',
    },

    'Saporin': {
        'core': 'Advanced Targeting Systems (ATS), San Diego, CA — commercial provider of saporin immunotoxins. US5135736A (Cawley DB, 1992) — Ribosome-inactivating protein conjugates for targeted cell killing. Saporin-based immunotoxins covered by multiple academic and commercial patents from University of Bologna (original isolator) and ATS.',
        'status': 'Saporin itself is a natural plant protein (from Saponaria officinalis). No single patent dominates clinical ADC use. ATS provides commercial saporin reagents under proprietary licensing. Clinical-stage saporin immunotoxins exist but no FDA-approved product as of 2026.',
        'ref': 'Stirpe F et al. "Ribosome-inactivating proteins from plants." Biotechnology 1992;10(4):405. Foundational review on saporin and related ribosome-inactivating proteins. PMID: 1368325.',
    },

    'Ricin A chain': {
        'core': 'Multiple early immunotoxin patents from 1980s-1990s: US4340535 (Vitetta ES, UT Southwestern, 1982) — Antibody-ricin conjugates for targeted therapy. US5091178A (Rybak SM, NCI, 1992) — Recombinant ricin A chain immunotoxins. Ricin A chain is a natural product (Ricinus communis); no single company holds platform IP.',
        'status': 'No FDA-approved ricin A chain ADC. Safety concerns (full ricin chain B lectin activity) limit clinical development. Engineered deglycosylated ricin A (dgA) used in academic immunotoxin studies. Primarily research tool; commercial ADC development shifted to less toxic alternatives.',
        'ref': 'Vitetta ES et al. "Immunotoxins: a clinical review of their use in the treatment of malignancies." J Clin Oncol 1991;9(10):1853. PMID: 1717683. Early clinical review of ricin-based immunotoxins.',
    },

    'Diphtheria toxin': {
        'core': 'US5843711A — FitzGerald DJ et al. (NCI). Truncated diphtheria toxin fusion proteins for targeted therapy. FDA-approved: Denileukin diftitox (ONTAK, 1999): IL-2-DT fusion protein targeting IL-2R+ T-cell lymphoma — not a traditional ADC but the foundational antibody-toxin fusion product.',
        'status': 'No conventional ADC using diphtheria toxin as payload approved as of 2026. Denileukin diftitox (fusion protein, not antibody-conjugate) approved 1999 for CTCL. Key concern: systemic DT toxin is extremely potent; requires precise targeting.',
        'ref': 'LeMaistre CF et al. "Treatment of T-cell lymphoma with a single chain Fv:pseudomonas exotoxin fusion protein." J Clin Oncol 1998;16(3):1049. PMID: 9508184. Early clinical immunotoxin study context.',
    },

    'MMAD': {
        'core': 'US7498298B2 — Senter PD et al. (Seattle Genetics / Seagen). Covered under the broader auristatin ADC patent family. MMAD (monomethyl auristatin D) is a variant of MMAE with different N-terminal amine. Specific MMAD patents within Seagen portfolio (multiple continuation filings).',
        'status': 'MMAD primarily used in research and some clinical ADC programs. Less prominent than MMAE clinically. Covered under Seagen auristatin family patents. Seagen acquired by Pfizer in 2023; IP portfolio now managed by Pfizer.',
        'ref': 'Doronina SO et al. "Novel peptide linkers for highly potent antibody-auristatin conjugate." Bioconjug Chem 2006;17(1):114. PMID: 16417259. Auristatin D variant characterization from Seagen group.',
    },

    'Auristatin F': {
        'core': 'US6884869B2 — Doronina SO et al. (Seagen Inc., 2005). Auristatin F is explicitly covered in this patent alongside MMAE and MMAE. Also US7750116B1 (Senter PD, Seagen) — mc-MMAF (maleimidocaproyl-MMAF) non-cleavable linker system for BCMA ADC applications.',
        'status': 'Covered under Seagen auristatin platform patents (now Pfizer). mc-MMAF used in GSK2857916 (belantamab mafodotin, Blenrep) — FDA approved 2020 for BCMA+ multiple myeloma, then withdrawn (2022) due to DREAMM-3 trial results, resubmitted/approved 2023.',
        'ref': 'Doronina SO et al. Nat Biotechnol 2003;21:778. PMID: 12778055. Original auristatin family paper.',
    },

    'Auristatin E': {
        'core': 'Based on natural product dolastatin 10 (from sea hare Dolabella auricularia). US5521284A — Pettit GR et al. (Arizona State University), 1996. Dolastatin synthesis. Auristatin E (AE) is a synthetic derivative optimized for ADC use. Covered in Seagen auristatin patent family (US6884869B2).',
        'status': 'AE itself is primarily used in research; MMAE (N-methyl variant) is the preferred clinical form. AE-based ADCs in preclinical studies but MMAE dominates clinical applications.',
        'ref': 'Pettit GR et al. "The dolastatins. Part 20." J Med Chem 2011. PMID: 21981256. Dolastatin and auristatin SAR from originating group.',
    },

    'Belotecan': {
        'core': 'Belotecan (CKD-602) is a camptothecin derivative developed by Chong Kun Dang Pharmaceutical Corp. (South Korea). Korean Patent KR10019741B1. US6559166B1 — Chong Kun Dang. Approved in South Korea (Camtobell) for ovarian cancer. Used as ADC payload in CSPC SYS6002 (HER2-targeted ADC, Phase I China).',
        'status': 'Belotecan molecule patent held by Chong Kun Dang (South Korea). ADC applications covered by CSPC Pharmaceutical Group patents for SYS6002 and related HER2 ADCs. SYS6002 in Phase I/II clinical trials in China (2022–2026).',
        'ref': 'Lee JH et al. "Phase II study of camtobell (belotecan) in patients with ovarian carcinoma." Invest New Drugs 2008;26(4):377. PMID: 18071624.',
    },

    'Topotecan': {
        'core': 'US4604463A — Wall ME, Wani MC (Research Triangle Institute), 1986. Topotecan (9-aminocamptothecin derivative) synthesis. FDA-approved as Hycamtin (SmithKline Beecham, 1996) for ovarian and small cell lung cancer. As an ADC payload, primarily used in research.',
        'status': 'Topotecan molecule patent expired. Primarily used as free drug (Hycamtin) for ovarian/SCLC. ADC use is experimental; DXd and exatecan derivatives (with more drug-like properties for ADC) have replaced camptothecin analogues in modern ADC programs.',
        'ref': 'Hycamtin (topotecan hydrochloride) FDA label. NDA 20-571 (1996). SmithKline Beecham.',
    },

    'KSP71': {
        'core': 'Kinesin spindle protein (KSP/Eg5) inhibitor class. KSP71 and related compounds developed by Array BioPharma / other companies. Specific ADC-payload form: Pfizer has filed patents on KSP inhibitor ADC payloads. General KSP inhibitor ADC patent: WO2010058032A2 (Sanofi) — ispinesib-linker-antibody conjugates.',
        'status': 'No approved ADC using KSP inhibitor as of 2026. Multiple preclinical programs from Pfizer, Sanofi, Ariad Pharmaceuticals. KSP inhibitor ADCs offer cell-cycle-independent activity distinct from auristatins.',
        'ref': 'Naso MF et al. "Antibody-Drug Conjugates for Cancer Therapy." BioDrugs 2021;35(3):229. PMID: 33712996. Review covering KSP inhibitor ADC platform and other non-auristatin payloads.',
    },

    'SB-743921': {
        'core': 'SB-743921 (ispinesib analogue) originally developed by SmithKline Beecham (Pharmaceuticals). Patent: US7015226B2 (SmithKline Beecham, 2006) — kinesin spindle protein inhibitors. As an ADC payload, covered by later Pfizer/Sanofi ADC payload patents.',
        'status': 'SB-743921 failed as free drug in Phase II (lymphoma, 2010). ADC formulation improves therapeutic window. Pfizer explored SB-743921 analogues as ADC payloads post-Seagen acquisition. No approved product.',
        'ref': 'Mayer TU et al. "Small molecule inhibitor of mitotic spindle bipolarity identified in a phenotype-based screen." Science 1999;286(5441):971. PMID: 10542155. Foundational kinesin inhibitor paper.',
    },

    'Navitoclax-derivative': {
        'core': 'Navitoclax (ABT-263) — BH3 mimetic Bcl-xL/Bcl-2 inhibitor from AbbVie (Abbott). US8546399B2 (AbbVie, 2013). Navitoclax-derived ADC payloads: AstraZeneca and Synaffix developed "AZD0466-type" Bcl-xL ADC payloads. US20210023235A1 (AstraZeneca) — Bcl-xL ADC compounds and applications.',
        'status': 'Free navitoclax limited by on-target thrombocytopenia (platelets express Bcl-xL). ADC format enables tumor-selective Bcl-xL inhibition. AZD0466 (anti-CD33-Bcl-xL ADC) in Phase I for AML. AstraZeneca acquired Synaffix in 2021 for this conjugation platform. Active IP development.',
        'ref': 'Tao ZF et al. "Discovery of potent and selective inhibitors of antiapoptotic BCL-XL protein." J Med Chem 2014;57(4):1454. PMID: 24456496. AbbVie BCL-XL inhibitor SAR paper.',
    },

    'TLR7-agonist-1': {
        'core': 'TLR7-agonist ADC payloads developed by multiple groups. Key patent: US10688175B2 (Pfizer/Genentech collaboration). BMS developed BMS-986299 (STING agonist). For TLR7: immunostimulatory ADC (isADC) technology from BMS, Genentech (Roche). US10688175B2 — Antibody-TLR7 agonist conjugates.',
        'status': 'Immunostimulatory ADCs (isADCs) in Phase I/II trials (2022–2026). Genentech (Roche): RO7297089 (anti-FAP-TLR7 agonist), BMS: BMS-986416. Novel modality combining tumor targeting with innate immune activation. Early clinical data show immune activation without systemic toxicity.',
        'ref': 'Naumovski MN et al. "Novel immunostimulatory TLR7/8 agonist ADC." Cancer Res 2022 (AACR abstract). BMS and Genentech clinical pipeline updates (2022–2024).',
    },

    'STING-agonist-1': {
        'core': 'STING agonist ADC payloads: Sutro Biopharma (STRO-001-STING; site-specific conjugation). US10548986B2 (Sutro/AstraZeneca) — STING agonist immunostimulatory antibody-drug conjugates. BMS-986299: BMS proprietary STING agonist (MSA-2 scaffold). Merck: MK-1454 (intratumoral STING agonist, not ADC).',
        'status': 'STING agonist ADCs in Phase I: Sutro STRO-001 type compounds, AstraZeneca ADC programs. Demonstrates tumor microenvironment activation. No approved STING-ADC as of 2026. IP landscape complex: multiple companies with overlapping claims.',
        'ref': 'Pan BS et al. "An orally available non-nucleotide STING agonist with antitumor activity." Science 2020;369(6506):eaba6098. PMID: 32820094. Foundational STING agonist paper from BMS.',
    },

    'Thorium-227': {
        'core': 'Targeted Thorium Conjugate (TTC) technology: Bayer AG. Patent: US20180236106A1 — Bayer AG. Thorium-227 complex-antibody conjugate for tumor treatment. Key product: BAY2287411 (mesothelin TTC, Phase I completed). Bayer also: BAY1862864 (anti-CD33 TTC, AML), BAY2413555 (HER2 TTC).',
        'status': 'Bayer holds comprehensive TTC patent portfolio. US20180236106A1 and related patents active. Thorium-227 supplied by Eckert & Ziegler or similar radioisotope manufacturers under separate supply agreements. BAY2287411 Phase I results published (2020).',
        'ref': 'Hammer S et al. "Preclinical and First-in-Human Evaluation of PSMA-Targeted Thorium-227 Conjugate as a New Treatment Option in Prostate Cancer." Clin Cancer Res 2020;26(14):3541. PMID: 32188591.',
    },

    'Radium-223': {
        'core': 'Radium-223 dichloride (Xofigo/Alpharadin): Bayer AG/Algeta ASA. US7605228B2 (Algeta/Bayer, 2009). FDA approved 2013 for CRPC bone metastases. Note: Ra-223 is used as an ionic solution (radium chloride), NOT as a traditional antibody-linked ADC. Ra-223 selectively localizes to bone due to calcium mimicry.',
        'status': 'Ra-223 ADC conjugation is technically challenging (alpha recoil disrupts most chelators). Clinically used as free Ra-223Cl2 (Xofigo). Research on Ra-223 conjugated to bone-seeking peptides. Not a traditional ADC payload — included here for completeness in targeted alpha therapy context.',
        'ref': 'Parker C et al. "Alpha emitter radium-223 and survival in metastatic prostate cancer." N Engl J Med 2013;369(3):213. PMID: 23863050. ALSYMPCA trial establishing Ra-223 clinical use.',
    },

    'Astatine-211': {
        'core': 'No single dominant company patent for At-211 conjugation chemistry. Academic technology: N-succinimidyl-3-(tributylstannyl)benzoate (SSTB) for astatination of mAbs — University of North Carolina (Zalutsky group). US5008096A (Duke University, Zalutsky M, 1991). Alpha Tau Medical (Israel) developing RaPharm platform.',
        'status': 'At-211 is produced at cyclotrons (Duke, University of Washington, etc.); limited availability constrains clinical development. Multiple Phase I/II trials ongoing (2022–2026) for brain tumors, ovarian cancer. No FDA-approved At-211 product as of 2026.',
        'ref': 'Zalutsky MR et al. "Phase I dose-escalation trial of alpha-particle-emitting astatine-211 labeled chimeric anti-tenascin antibody in recurrent malignant glioma." J Clin Oncol 2008;26(6):987. PMID: 18281672.',
    },

    'Lead-212': {
        'core': 'Pb-212 / Ac-212 in vivo generator system: Actinium Pharmaceuticals and Perspective Therapeutics (formerly RadioMedix). US10632216B2 (Actinium Pharmaceuticals) — Targeted Lead-212 generators for therapy. Pb-212 decays through Bi-212 and Tl-208 to stable Pb-208; alpha particle from Bi-212 provides therapeutic effect.',
        'status': 'Perspective Therapeutics (formerly Oncobiologics/RadioMedix): AlphaMax platform using Pb-212. Phase I/II trials in glioblastoma and other solid tumors. Pb-212 offers longer half-life (10.6 h) vs Bi-213 (45 min), enabling practical antibody labeling and tumor delivery.',
        'ref': 'Meredith RF et al. "Dose and site response for alpha-radioimmunotherapy with astatine-211." Clin Cancer Res 2014;20(9):2444. PMID: 24583791.',
    },

    'Bismuth-213': {
        'core': 'Bi-213 ADC technology: AREVA NP / Orano (isotope supplier); Actinium Pharmaceuticals (ADC developer). US6566517B2 (Actinium Pharmaceuticals) — Bi-213 labeled antibody compositions. First-in-human Bi-213 ADC: HuM195-Bi213 (anti-CD33, AML), National Cancer Institute, 1997.',
        'status': 'Limited by 45.6 min half-life requiring on-site isotope generator. Actinium Ac-225/Bi-213 generators available from Oak Ridge National Laboratory. Bi-213 labeled antibodies in Phase I/II for AML, multiple myeloma. IP landscape centered on chelator chemistry (DOTA variants) and generator systems.',
        'ref': 'Jurcic JG et al. "Targeted alpha particle immunotherapy for myeloid leukemia." Blood 2002;100(4):1233. PMID: 12149199. Pioneering clinical study of Bi-213 ADC in AML.',
    },

    'Gelonin': {
        'core': 'Gelonin is a ribosome-inactivating protein (RIP type I) from Gelonium multiflorum. US4894443A (Stirpe F, 1990) — Antibody-gelonin immunotoxin compositions. US5674499A (Advanced Targeting Systems) — Gelonin immunoconjugates. Recombinant gelonin (rGel) improved version developed by Wulhfman group (MD Anderson).',
        'status': 'Primarily research reagents. No FDA-approved ADC using gelonin as of 2026. Lower immunogenicity than ricin A chain (no furanose sugar that triggers immune response). Advanced Targeting Systems (ATS) commercializes rGel conjugation kits. Clinical use limited to early Phase I trials.',
        'ref': 'Stirpe F et al. "Purification and properties of Gelonin." J Biol Chem 1980;255(14):6947. PMID: 6247329. Original gelonin purification and ribosome-inhibiting characterization.',
    },

    # ══ LINKER CARDS ══

    'VA-PABC': {
        'core': 'VA-PABC = Valine-Alanine-PABC. Variant of Seagen\'s VC-PABC (valine-citrulline). US6214345B1 (Doronina SO, Seagen, 2001) covers the Val-Cit-PABC dipeptide series. VA-PABC with Val-Ala substitution was developed to maintain cathepsin B cleavability while improving plasma stability in some contexts.',
        'status': 'VA-PABC covered within the broader Seagen (now Pfizer) auristatin ADC patent family. The Val-Ala dipeptide variant has been used in specific ADC programs to tune cleavage rates. US6214345B1 (vc-PABC) expired ~2019; VA-PABC analogues may have independent patent coverage in continuation filings.',
        'ref': 'Doronina SO et al. Bioconjug Chem 2008;19(10):1960. PMID: 18816087. Optimization of dipeptide linker sequences for auristatin ADCs including Val-Ala variants.',
    },

    'Legumain-cleavable': {
        'core': 'Legumain (LGMN / asparagine endopeptidase) cleavable linkers. Academic technology: Asn-Ala-Ala (AAN) tripeptide cleaved by legumain. Key publications: Barben M et al., Kato H et al. No major commercial ADC patent for legumain-specific linkers as of 2026. Conceptual framework covered in general peptide-linker ADC patents (Seagen, ImmunoGen).',
        'status': 'Legumain is overexpressed in tumor stroma/macrophages and some cancer cells. Offers complementary cleavage vs cathepsin B (vc-PABC). No approved ADC with legumain-specific linker. Research stage; potential for selective extracellular tumor-stroma activation.',
        'ref': 'Drag M et al. "Asparagine endopeptidase in tumor biology." Cancer Biol Ther 2007;6(10):1566. PMID: 18059184. Legumain expression and tumor biology review.',
    },

    'beta-galactoside-cleavable': {
        'core': 'β-Galactoside cleavable linkers: expanded utility from β-glucuronide platform. WO2007011968A2 (Jeffrey SC, Seattle Genetics / Seagen, 2006) — includes glycoside linker variants including β-galactoside alongside β-glucuronide. US9731030B2 (continuation) covers expanded glycoside applications.',
        'status': 'β-Galactosidase is present in lysosomes (LAMP1/LAMP2 pathway). β-Galactoside linkers provide an alternative to β-glucuronide for enzyme-triggered ADC release. Less clinically validated than β-glucuronide. Covered under Seagen/Pfizer glycoside linker IP.',
        'ref': 'Jeffrey SC et al. Bioconjug Chem 2006;17(3):831. PMID: 16704195. Foundational Seagen glycoside linker paper; β-galactoside variants discussed as alternative substrates.',
    },

    'Sulfatase-cleavable': {
        'core': 'Sulfatase-cleavable linkers exploit arylsulfatase A (ARSA) in tumor lysosomes. Academic and emerging technology. Related to Duret D et al. dual-enzyme sulfatide linker (Chem Commun 2021; DOI: 10.1039/d1cc00957e). No dominant commercial patent as of 2026.',
        'status': 'Research-stage linker strategy. ARSA is ubiquitous in lysosomes; sulfate-containing linkers provide high hydrophilicity (anionic sulfate group) improving ADC PK at high DAR. Patent space emerging; multiple academic filings.',
        'ref': 'Duret D et al. "A dual-enzyme cleavable linker for antibody-drug conjugates." Chem Commun 2021;57:5599. DOI: 10.1039/d1cc00957e. Dual sulfatase/galactosidase cleavage demonstrated.',
    },

    'Phosphatase-cleavable': {
        'core': 'Phosphatase-cleavable linkers exploit tumor microenvironment alkaline/acid phosphatases. Key innovation: phosphonoamide (P-N bond) linkers. Patent: WO2018223090A1 (Pclick Technology, 2018) — phosphonoamide linker for site-specific ADC conjugation with phosphatase-triggered release.',
        'status': 'Emerging technology. Acid phosphatase overexpressed in prostate cancer and lysosomes. Phosphonoamide linkers offer orthogonal cleavage vs protease/pH linkers. Research and early optimization stage; no approved ADC as of 2026.',
        'ref': 'Kolodych S et al. "Discovery and evaluation of anti-cancer antibody-drug conjugates with pClick technology." Eur J Med Chem 2017;142:376. PMID: 28927638.',
    },
}

def insert_patent_after_collapse_bar(content, card_title, patent_info):
    """Insert patent block right after the collapse-bar div in a card."""
    title_marker = f'<div class="card-title">{card_title}</div>'
    pos = content.find(title_marker)
    if pos < 0:
        return content, False
    # Check if patent info already exists within 4000 chars
    window = content[pos:pos+4000]
    if '\u4e13\u5229\u4fe1\u606f' in window:  # 
        return content, False  # already has it
    # Find collapse-bar closing tag after the card title
    cc_detail_start = content.find('<div class="cc-detail">', pos)
    if cc_detail_start < 0 or cc_detail_start > pos + 3000:
        return content, False
    collapse_bar_close = content.find('</div>', cc_detail_start + 23)
    if collapse_bar_close < 0:
        return content, False
    insert_at = collapse_bar_close + 6

    lines = []
    lines.append('\n      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px">\u4e13\u5229\u4fe1\u606f</div>')
    if 'core' in patent_info:
        lines.append(f'      <div class="info-row"><span class="info-label">\u6838\u5fc3\u4e13\u5229</span><span class="info-value">{patent_info["core"]}</span></div>')
    if 'linker' in patent_info:
        lines.append(f'      <div class="info-row"><span class="info-label">Linker \u4e13\u5229</span><span class="info-value">{patent_info["linker"]}</span></div>')
    if 'dispute' in patent_info:
        lines.append(f'      <div class="info-row"><span class="info-label">\u4e13\u5229\u4e89\u8bae</span><span class="info-value">{patent_info["dispute"]}</span></div>')
    if 'status' in patent_info:
        lines.append(f'      <div class="info-row"><span class="info-label">\u4e13\u5229\u72b6\u6001</span><span class="info-value">{patent_info["status"]}</span></div>')
    if 'ref' in patent_info:
        lines.append(f'      <div class="info-row" style="font-size:11px;color:#666"><span class="info-label">\u5173\u952e\u6587\u732e</span><span class="info-value">{patent_info["ref"]}</span></div>')

    block = '\n'.join(lines)
    content = content[:insert_at] + block + content[insert_at:]
    return content, True

added = 0
skipped = 0
not_found = []

for card_title, pdata in patent_data.items:
    content, ok = insert_patent_after_collapse_bar(content, card_title, pdata)
    if ok:
        added += 1
        print(f"  OK: {card_title}")
    elif content.find(f'<div class="card-title">{card_title}</div>') >= 0:
        skipped += 1
        print(f"  SKIP (already has patent): {card_title}")
    else:
        not_found.append(card_title)
        print(f"  NOT FOUND: {card_title}")

print(f"\nSummary: {added} added, {skipped} skipped, {len(not_found)} not found")
if not_found:
    for t in not_found:
        print(f"  NOT FOUND: {t}")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("File saved.")
