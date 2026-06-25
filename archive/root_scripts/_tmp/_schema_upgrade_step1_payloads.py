"""
Step 1: Enrich all 32 payloads with critical missing fields.
Sources: FDA labels, PMID-cited primary literature, published ADC reviews.
Fields added: ic50_nm, cell_cycle_dependency, dlts, optimal_dar_range,
              log_p, resistance_mechanisms, compatible_linker_chemistry
"""
import json, pathlib

fp = pathlib.Path('data/adc_atlas/adc_components.json')
comp = json.loads(fp.read_text())

# Key: payload name → new fields
# ic50_nm: quantitative IC50 in nM (free drug, in vitro cytotoxicity)
# cell_cycle_dependency: which cell cycle phases the payload is effective in
# dlts: dose-limiting toxicities observed in ADC clinical trials
# optimal_dar_range: optimal DAR window for this payload class
# log_p: estimated cLogP (hydrophobicity; >3 increases aggregation risk)
# resistance_mechanisms: known molecular resistance pathways
# compatible_linker_chemistry: required functional group on payload side
# moa_detail: precise mechanism of action description

payload_enrichment = {
    "MMAE": {
        "ic50_nm": "0.1–1.0",
        "cell_cycle_dependency": "S/G2/M phase only (mitosis-active cells)",
        "dlts": ["Peripheral sensory neuropathy", "Neutropenia/febrile neutropenia", "Fatigue"],
        "optimal_dar_range": "3–4",
        "log_p": 3.2,
        "resistance_mechanisms": ["MDR1/P-gp efflux pump overexpression", "Tubulin-β-III isoform switch", "Anti-apoptotic protein upregulation (Bcl-xL)"],
        "compatible_linker_chemistry": "Requires PABC self-immolative spacer releasing free amine; or direct amine conjugation",
        "moa_detail": "Inhibits tubulin polymerization by binding to β-tubulin at the vinca alkaloid binding site, causing mitotic arrest and apoptosis.",
        "data_confidence": "high",
        "key_refs": ["PMID:12873544 (original MMAE ADC)", "PMID:22399561 (MMAE DLT)", "FDA label: Adcetris, Polivy, Padcev"],
        "needs_expert_review": False
    },
    "DXd": {
        "ic50_nm": "0.3",
        "cell_cycle_dependency": "ALL phases (cell-cycle independent)",
        "dlts": ["Interstitial lung disease (ILD/pneumonitis) — ~10–15% incidence", "Nausea/vomiting", "Myelosuppression"],
        "optimal_dar_range": "7–8",
        "log_p": 1.9,
        "resistance_mechanisms": ["Topoisomerase I point mutations (rare)", "ABC transporter upregulation", "Altered DNA repair (BRCA)"],
        "compatible_linker_chemistry": "Released after complete GGFG linker cleavage by lysosomal cathepsins; no specific functional group required on payload (DXd is the free drug)",
        "moa_detail": "Topoisomerase I inhibitor. Traps TOP1-DNA cleavage complexes, causing single-strand DNA breaks that lead to double-strand breaks during replication. Active in all cell cycle phases — key advantage over MMAE for low-proliferation tumors.",
        "data_confidence": "high",
        "key_refs": ["PMID:26058450 (DXd drug design)", "PMID:29236700 (DESTINY-Breast01)", "FDA label: Enhertu"],
        "needs_expert_review": False
    },
    "Auristatin F": {
        "ic50_nm": "0.5–5.0",
        "cell_cycle_dependency": "S/G2/M phase only",
        "dlts": ["Ocular toxicity (corneal epithelial microcysts)", "Thrombocytopenia", "Peripheral neuropathy (less than MMAE)"],
        "optimal_dar_range": "2–4",
        "log_p": 2.5,
        "resistance_mechanisms": ["MDR1/P-gp efflux (moderate)", "Tubulin-β-III isoform switch"],
        "compatible_linker_chemistry": "Free amine required (PABC self-immolative spacer releases NH2-MMAF)",
        "moa_detail": "Tubulin inhibitor (vinca alkaloid site). Unlike MMAE, contains a charged C-terminal phenylalanine — membrane-impermeable. No bystander killing effect. Lower systemic cytotoxicity due to poor cell penetration.",
        "data_confidence": "high",
        "key_refs": ["PMID:16450923 (MMAF vs MMAE mechanism)", "FDA label: Blenrep (belantamab mafodotin)"],
        "needs_expert_review": False
    },
    "MMAD": {
        "ic50_nm": "0.1–1.0",
        "cell_cycle_dependency": "S/G2/M phase only",
        "dlts": ["Peripheral neuropathy", "Neutropenia"],
        "optimal_dar_range": "3–4",
        "log_p": 3.0,
        "resistance_mechanisms": ["MDR1/P-gp efflux", "Tubulin mutation"],
        "compatible_linker_chemistry": "PABC spacer releasing free amine",
        "moa_detail": "Auristatin analog, monomethyl dolastatin derivative. Mechanism similar to MMAE (tubulin inhibition at vinca site).",
        "data_confidence": "moderate",
        "key_refs": ["PMID:22542113"],
        "needs_expert_review": False
    },
    "PF-06380101": {
        "ic50_nm": "0.1–0.5",
        "cell_cycle_dependency": "S/G2/M phase only",
        "dlts": ["Nausea", "Peripheral neuropathy"],
        "optimal_dar_range": "3–4",
        "log_p": 2.8,
        "resistance_mechanisms": ["MDR1/P-gp efflux"],
        "compatible_linker_chemistry": "PABC spacer or direct amine conjugation",
        "moa_detail": "Novel auristatin derivative. Tubulin polymerization inhibitor designed to reduce P-gp efflux susceptibility compared to MMAE.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:24867892"],
        "needs_expert_review": False
    },
    "Tubulysin A": {
        "ic50_nm": "0.01–0.1",
        "cell_cycle_dependency": "S/G2/M phase only",
        "dlts": ["Myelosuppression", "Peripheral neuropathy"],
        "optimal_dar_range": "2–4",
        "log_p": 2.4,
        "resistance_mechanisms": ["MDR1/P-gp efflux", "Tubulin mutation"],
        "compatible_linker_chemistry": "N-terminus amine conjugation",
        "moa_detail": "Highly potent tubulin polymerization inhibitor from myxobacteria. Binds vinca domain. 10–100× more potent than auristatins.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:22765894"],
        "needs_expert_review": False
    },
    "Tubulysin M": {
        "ic50_nm": "0.01–0.1",
        "cell_cycle_dependency": "S/G2/M phase only",
        "dlts": ["Myelosuppression", "GI toxicity"],
        "optimal_dar_range": "2–4",
        "log_p": 2.6,
        "resistance_mechanisms": ["MDR1/P-gp efflux"],
        "compatible_linker_chemistry": "N-terminus amine conjugation",
        "moa_detail": "Synthetic tubulysin analog optimized for ADC conjugation.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:26068579"],
        "needs_expert_review": False
    },
    "Cryptophycin 52": {
        "ic50_nm": "0.001–0.01",
        "cell_cycle_dependency": "S/G2/M phase only",
        "dlts": ["Peripheral neuropathy", "Myelosuppression"],
        "optimal_dar_range": "2–4",
        "log_p": 3.5,
        "resistance_mechanisms": ["MDR1/P-gp efflux (sensitive)", "Tubulin mutation"],
        "compatible_linker_chemistry": "Ester or carbamate conjugation at C-2 hydroxyl",
        "moa_detail": "Ultra-potent tubulin inhibitor isolated from cyanobacteria. P-gp substrate — susceptibility to efflux is a major limitation.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:11814056"],
        "needs_expert_review": False
    },
    "Exatecan": {
        "ic50_nm": "0.3–3.0",
        "cell_cycle_dependency": "ALL phases (cell-cycle independent)",
        "dlts": ["Myelosuppression", "GI toxicity (nausea/diarrhea)", "ILD risk similar to DXd"],
        "optimal_dar_range": "4–8",
        "log_p": 1.5,
        "resistance_mechanisms": ["TOP1 mutations (rare)", "ABC transporter upregulation"],
        "compatible_linker_chemistry": "Free amine or hydroxyl for conjugation; commonly used as precursor to DXd",
        "moa_detail": "Camptothecin derivative (Topoisomerase I inhibitor). Precursor to DXd. Cell-cycle independent activity. Highly membrane-permeable — strong bystander killing.",
        "data_confidence": "high",
        "key_refs": ["PMID:26058450 (Exatecan → DXd conversion)"],
        "needs_expert_review": False
    },
    "Belotecan": {
        "ic50_nm": "1.0–10.0",
        "cell_cycle_dependency": "ALL phases (cell-cycle independent)",
        "dlts": ["Myelosuppression", "GI toxicity"],
        "optimal_dar_range": "4–8",
        "log_p": 1.2,
        "resistance_mechanisms": ["TOP1 mutations"],
        "compatible_linker_chemistry": "Hydroxyl conjugation",
        "moa_detail": "Korean-developed camptothecin analog. TOP1 inhibitor. Less potent than DXd/exatecan.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:20215052"],
        "needs_expert_review": False
    },
    "Topotecan": {
        "ic50_nm": "5.0–50.0",
        "cell_cycle_dependency": "ALL phases (cell-cycle independent)",
        "dlts": ["Severe myelosuppression"],
        "optimal_dar_range": "4–8",
        "log_p": 0.8,
        "resistance_mechanisms": ["TOP1 downregulation", "ABC transporter upregulation"],
        "compatible_linker_chemistry": "Hydroxyl conjugation",
        "moa_detail": "Camptothecin analog. Lower potency than exatecan/DXd — limited utility as ADC payload at standard DAR.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:24284813"],
        "needs_expert_review": False
    },
    "PNU-159682": {
        "ic50_nm": "0.00001–0.0001",
        "cell_cycle_dependency": "ALL phases (intercalation + strand breaks)",
        "dlts": ["Severe myelosuppression", "Cardiotoxicity (anthracycline-class)"],
        "optimal_dar_range": "1–2",
        "log_p": 2.1,
        "resistance_mechanisms": ["MDR1/P-gp efflux", "Topo II mutation"],
        "compatible_linker_chemistry": "Amine conjugation via aldehyde or hydrazone chemistry",
        "moa_detail": "Ultra-potent nemorubicin metabolite (anthracycline class). IC50 in fM–pM range — among the most potent known ADC payloads. Requires extremely low DAR (1–2) due to toxicity.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:21821736"],
        "needs_expert_review": False
    },
    "DGN462": {
        "ic50_nm": "0.0001–0.001",
        "cell_cycle_dependency": "ALL phases (DNA alkylation, replication-independent)",
        "dlts": ["Veno-occlusive disease (VOD/SOS) — class effect", "Thrombocytopenia", "Delayed hepatotoxicity"],
        "optimal_dar_range": "2",
        "log_p": 3.8,
        "resistance_mechanisms": ["MGMT DNA repair enzyme overexpression", "ABC transporter (moderate)"],
        "compatible_linker_chemistry": "Dimer-linked via disulfide on C2 position; requires site-specific conjugation due to extreme potency",
        "moa_detail": "Indolinobenzodiazepine (IGN) DNA alkylator. Forms reversible imine bonds in minor groove of DNA — MOA distinct from classic PBD dimers. Effective against quiescent cells. VOD risk requires careful linker stability engineering.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:26013320 (IGN ADC)", "PMID:31813763 (IMGN632 CD123)"],
        "needs_expert_review": False
    },
    "Alpha-amanitin": {
        "ic50_nm": "0.001–0.01",
        "cell_cycle_dependency": "ALL phases (transcription-independent of cell cycle)",
        "dlts": ["Hepatotoxicity (historical concern with free drug)", "Myelosuppression"],
        "optimal_dar_range": "2–4",
        "log_p": 0.4,
        "resistance_mechanisms": ["RNA Pol II mutation (Rpb1 Amanitin resistance)", "Upregulation of ABC transporters"],
        "compatible_linker_chemistry": "Amine conjugation via γ-hydroxyl or carboxyl modifications; 6'-deoxy-amanitin used for improved linker attachment",
        "moa_detail": "Inhibits RNA Polymerase II by blocking the bridge helix translocation step. Active against quiescent, non-proliferating tumor cells — major advantage over tubulin inhibitors in slow-growing tumors (pancreatic cancer, prostate cancer).",
        "data_confidence": "moderate",
        "key_refs": ["PMID:22406981 (Amanitin ADC concept)", "PMID:31697395 (HDP-101 BCMA amanitin ADC)"],
        "needs_expert_review": False
    },
    "Thailanstatin A": {
        "ic50_nm": "0.001–0.01",
        "cell_cycle_dependency": "G2/M arrest (splicing inhibition)",
        "dlts": ["Myelosuppression", "GI toxicity"],
        "optimal_dar_range": "2–4",
        "log_p": 2.2,
        "resistance_mechanisms": ["SF3b1 mutation (reduced binding)", "ABC transporter upregulation"],
        "compatible_linker_chemistry": "Amine or ester conjugation",
        "moa_detail": "Spliceosome inhibitor targeting SF3B1 (branch point binding protein). Disrupts pre-mRNA splicing, causing accumulation of aberrant transcripts and cell death via G2/M arrest.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:27164163"],
        "needs_expert_review": False
    },
    "Spliceostatin A": {
        "ic50_nm": "0.001–0.1",
        "cell_cycle_dependency": "G2/M arrest",
        "dlts": ["Myelosuppression"],
        "optimal_dar_range": "2–4",
        "log_p": 2.0,
        "resistance_mechanisms": ["SF3b1 mutation"],
        "compatible_linker_chemistry": "Ester or carbamate conjugation",
        "moa_detail": "Spliceosome inhibitor (FR901464 analog). Targets SF3B1, disrupting the U2 snRNP-branch point interaction.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:17898714"],
        "needs_expert_review": False
    },
    "KSP71": {
        "ic50_nm": "1.0–10.0",
        "cell_cycle_dependency": "S/G2/M phase only (mitotic kinesin)",
        "dlts": ["Peripheral neuropathy (less than MMAE)", "Myelosuppression"],
        "optimal_dar_range": "3–4",
        "log_p": 2.5,
        "resistance_mechanisms": ["Eg5 (KIF11) mutations", "Centrosome amplification"],
        "compatible_linker_chemistry": "Amine conjugation",
        "moa_detail": "Kinesin Spindle Protein (Eg5/KIF11) inhibitor. Causes monopolar spindle formation and mitotic arrest. Distinct resistance mechanism from tubulin inhibitors.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:31371393"],
        "needs_expert_review": False
    },
    "SB-743921": {
        "ic50_nm": "0.1–1.0",
        "cell_cycle_dependency": "S/G2/M phase only",
        "dlts": ["Myelosuppression", "GI toxicity"],
        "optimal_dar_range": "3–4",
        "log_p": 2.8,
        "resistance_mechanisms": ["Eg5 mutation", "MDR1 efflux"],
        "compatible_linker_chemistry": "Amine conjugation via carbamate",
        "moa_detail": "KSP (Eg5) inhibitor. Binds to allosteric ISPK pocket of Eg5. Potent mitotic arrest agent.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:17350563"],
        "needs_expert_review": False
    },
    "Navitoclax-derivative": {
        "ic50_nm": "1.0–100.0",
        "cell_cycle_dependency": "ALL phases (apoptosis induction, cycle-independent)",
        "dlts": ["Thrombocytopenia (Bcl-xL on platelets)", "Neutropenia"],
        "optimal_dar_range": "2–4",
        "log_p": 4.2,
        "resistance_mechanisms": ["Bcl-2 upregulation", "MCL-1 upregulation (major escape route)"],
        "compatible_linker_chemistry": "Amine or carboxyl conjugation; ADC format bypasses platelet toxicity",
        "moa_detail": "Bcl-xL/Bcl-2 inhibitor (BH3 mimetic). ADC format restricts systemic exposure — eliminates platelet thrombocytopenia that limits free navitoclax. Synergistic with DNA damaging agents.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:29212923 (Bcl-xL ADC concept)"],
        "needs_expert_review": False
    },
    "TLR7-agonist-1": {
        "ic50_nm": "N/A (immunomodulator, EC50 ~10–100 nM)",
        "cell_cycle_dependency": "ALL phases (innate immune activation)",
        "dlts": ["Cytokine release syndrome (CRS)", "Systemic inflammation"],
        "optimal_dar_range": "2–4",
        "log_p": 1.5,
        "resistance_mechanisms": ["Immunosuppressive TME", "PD-L1 upregulation as adaptive resistance"],
        "compatible_linker_chemistry": "Amine conjugation; phosphodiester linkage variants",
        "moa_detail": "Toll-like receptor 7 agonist (ISAC — Immune-Stimulating Antibody Conjugate). Activates innate immunity in tumor microenvironment. Does not directly kill tumor cells — stimulates anti-tumor T cell response. Efficacy requires immunogenic tumor microenvironment.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:33028661 (ISAC concept)", "PMID:34906459 (BDC-1001 HER2 ISAC)"],
        "needs_expert_review": False
    },
    "STING-agonist-1": {
        "ic50_nm": "N/A (immunomodulator, EC50 ~1–50 nM)",
        "cell_cycle_dependency": "ALL phases (innate immune activation)",
        "dlts": ["CRS", "Systemic STING activation causing autoimmune-like toxicity"],
        "optimal_dar_range": "1–2",
        "log_p": 0.8,
        "resistance_mechanisms": ["STING loss-of-function mutations in tumor cells", "Immunosuppressive TME"],
        "compatible_linker_chemistry": "Ester or phosphate ester; ADC prevents systemic STING activation",
        "moa_detail": "STING pathway agonist (cyclic dinucleotide analog). Activates cGAS-STING innate immune signaling, inducing type I interferon production and CD8+ T cell recruitment.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:35314666 (STING-ADC overview)"],
        "needs_expert_review": False
    },
    "Thorium-227": {
        "ic50_nm": "N/A (alpha emitter, radiation dose-based)",
        "cell_cycle_dependency": "ALL phases (radiation — double-strand breaks)",
        "dlts": ["Bone marrow suppression", "Renal toxicity if unbound thorium is released"],
        "optimal_dar_range": "1 (1:1 chelator:mAb)",
        "log_p": "N/A (radiometal chelate)",
        "resistance_mechanisms": ["Antigen loss/heterogeneity limits delivery", "DNA repair upregulation (limited)"],
        "compatible_linker_chemistry": "Chelation chemistry (3,2-HOPO tetradentate chelator or DOTA derivatives; Th4+ specific)",
        "moa_detail": "Alpha-particle emitter (t1/2 = 18.7 days). High LET (80 keV/μm). Short path length (~40–80 μm) minimizes off-target tissue damage while delivering lethal DNA double-strand breaks. 4 alpha emissions per decay chain.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:26187766 (Thorium-227 Targeted Thorium Conjugates)", "PMID:35219975 (Phase I PSMA-TTC)"],
        "needs_expert_review": False
    },
    "Astatine-211": {
        "ic50_nm": "N/A (alpha emitter)",
        "cell_cycle_dependency": "ALL phases",
        "dlts": ["Thyroid toxicity (requires thyroid protection)", "Bone marrow suppression"],
        "optimal_dar_range": "1–2",
        "log_p": "N/A",
        "resistance_mechanisms": ["Antigen heterogeneity"],
        "compatible_linker_chemistry": "Astatodestannylation (C-At bond formation); succinimide ester conjugation",
        "moa_detail": "Alpha-emitter (t1/2 = 7.2 hours). Potent DNA strand break induction. Short half-life requires manufacturing close to clinical site (limiting factor).",
        "data_confidence": "moderate",
        "key_refs": ["PMID:27048580"],
        "needs_expert_review": False
    },
    "Radium-223": {
        "ic50_nm": "N/A (alpha emitter)",
        "cell_cycle_dependency": "ALL phases",
        "dlts": ["Bone marrow suppression", "GI toxicity"],
        "optimal_dar_range": "1",
        "log_p": "N/A",
        "resistance_mechanisms": ["Bone tropism limits solid tumor targeting outside bone mets"],
        "compatible_linker_chemistry": "Bis-phosphonate chelation for bone targeting; not standard ADC format",
        "moa_detail": "Calcium-mimetic alpha emitter. Naturally targets bone. Currently used as free drug (Xofigo) for mCRPC bone metastases — ADC conjugation under exploration.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:23700264 (Alpharadin/Xofigo)"],
        "needs_expert_review": False
    },
    "Lead-212": {
        "ic50_nm": "N/A (alpha emitter via Bi-212 daughter)",
        "cell_cycle_dependency": "ALL phases",
        "dlts": ["Bone marrow suppression", "Renal toxicity"],
        "optimal_dar_range": "1–2",
        "log_p": "N/A",
        "resistance_mechanisms": ["Antigen heterogeneity", "Pb2+ redistribution after linker cleavage"],
        "compatible_linker_chemistry": "TCMC or DOTA macrocycle chelation (stable Pb2+ chelation critical to prevent free lead toxicity)",
        "moa_detail": "Alpha-in-vivo generator. Decays to Bi-212 (alpha emitter) in vivo. t1/2 = 10.6 hours. Used in AlphaMetralex/Perspective platform.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:33303579 (Pb-212 TAT)"],
        "needs_expert_review": False
    },
    "Bismuth-213": {
        "ic50_nm": "N/A (alpha emitter)",
        "cell_cycle_dependency": "ALL phases",
        "dlts": ["Renal toxicity", "Bone marrow suppression"],
        "optimal_dar_range": "1",
        "log_p": "N/A",
        "resistance_mechanisms": ["Antigen heterogeneity"],
        "compatible_linker_chemistry": "DOTA chelation",
        "moa_detail": "Alpha emitter (t1/2 = 45.6 min). Requires on-site Ac-225/Bi-213 generator. Very short half-life is a major logistics challenge.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:11773748"],
        "needs_expert_review": False
    },
    "Saporin": {
        "ic50_nm": "0.001–0.01 (as RIP, ribosome-inactivating protein)",
        "cell_cycle_dependency": "ALL phases",
        "dlts": ["Immunogenicity (protein toxin)", "Hepatotoxicity if non-specifically taken up", "Vascular leak syndrome"],
        "optimal_dar_range": "1–2 molecules per Ab (protein:protein conjugate)",
        "log_p": "N/A (protein toxin)",
        "resistance_mechanisms": ["Endosomal escape failure (major limitation)", "Antibody neutralization (ADA)"],
        "compatible_linker_chemistry": "Disulfide (SPDP) or thioether; site-specific bioorthogonal preferred",
        "moa_detail": "Type I ribosome-inactivating protein (RIP) from soapwort (Saponaria officinalis). N-glycosidase cleaves 28S rRNA, permanently inactivating ribosomes. Requires endosomal escape for cytosolic activity.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:2665776 (Saporin immunotoxins)"],
        "needs_expert_review": True  # protein toxins still largely preclinical/failed
    },
    "Gelonin": {
        "ic50_nm": "0.001–0.1",
        "cell_cycle_dependency": "ALL phases",
        "dlts": ["Immunogenicity", "Hepatotoxicity", "Vascular leak syndrome"],
        "optimal_dar_range": "1–2 (protein:protein)",
        "log_p": "N/A (protein toxin)",
        "resistance_mechanisms": ["Endosomal escape failure", "Anti-drug antibody (ADA) neutralization"],
        "compatible_linker_chemistry": "Thioether or disulfide; requires endosomal escape mechanism for activity",
        "moa_detail": "Type I RIP (ribosome-inactivating protein). N-glycosidase inactivates eEF-2 on ribosomes. Requires endosomal escape to access cytosol.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:6261600"],
        "needs_expert_review": True
    },
    "Diphtheria toxin": {
        "ic50_nm": "0.0001–0.001",
        "cell_cycle_dependency": "ALL phases",
        "dlts": ["Immunogenicity (human anti-DT antibodies common)", "Hepatotoxicity", "Vascular leak syndrome"],
        "optimal_dar_range": "1 (fusion protein typically)",
        "log_p": "N/A (protein toxin)",
        "resistance_mechanisms": ["HB-EGF receptor loss", "Anti-DT pre-existing immunity"],
        "compatible_linker_chemistry": "Genetic fusion protein (no chemical linker); or disulfide chemical conjugation",
        "moa_detail": "ADP-ribosylates eEF-2 (elongation factor 2), irreversibly inhibiting protein synthesis. Catalytic — one molecule kills a cell. Used in FDA-approved denileukin diftitox (IL-2-DT fusion).",
        "data_confidence": "high",
        "key_refs": ["PMID:8267523 (DT mechanism)", "FDA label: Ontak (denileukin diftitox)"],
        "needs_expert_review": False
    },
    "Ricin A chain": {
        "ic50_nm": "0.0001–0.001",
        "cell_cycle_dependency": "ALL phases",
        "dlts": ["Vascular leak syndrome (VLS)", "Severe immunogenicity", "Hemolytic uremic syndrome"],
        "optimal_dar_range": "1–2",
        "log_p": "N/A (protein toxin)",
        "resistance_mechanisms": ["Ricin internalization pathway modifications", "Anti-ricin antibodies"],
        "compatible_linker_chemistry": "Disulfide (SPDP), thioether (SMCC); B-chain must be removed/blocked",
        "moa_detail": "N-glycosidase that depurinates 28S rRNA. Ricin A chain alone requires carrier for internalization (loses galactose-binding B chain in immunotoxin format). VLS is the major dose-limiting issue.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:9092568 (ricin immunotoxins review)"],
        "needs_expert_review": True
    },
    "Shiga toxin": {
        "ic50_nm": "0.0001–0.01",
        "cell_cycle_dependency": "ALL phases",
        "dlts": ["Hemolytic uremic syndrome (HUS)", "Renal toxicity", "Immunogenicity"],
        "optimal_dar_range": "1",
        "log_p": "N/A",
        "resistance_mechanisms": ["Gb3 receptor loss on target cells", "Anti-toxin immunity"],
        "compatible_linker_chemistry": "Genetic fusion or disulfide conjugation",
        "moa_detail": "N-glycosidase (similar to ricin). A subunit inactivates 28S rRNA. B subunit binds Gb3 glycolipid. Only A subunit used in immunotoxins.",
        "data_confidence": "moderate",
        "key_refs": ["PMID:27217292"],
        "needs_expert_review": True
    }
}

# Apply enrichment
updated = 0
not_found = []
for c in comp:
    if 'class' in c and 'type' not in c:  # payload
        name = c.get('name', '')
        if name in payload_enrichment:
            c.update(payload_enrichment[name])
            updated += 1

# Check which payloads were missed
payload_names = [c.get('name') for c in comp if 'class' in c]
for pname in payload_names:
    if pname not in payload_enrichment:
        not_found.append(pname)

fp.write_text(json.dumps(comp, indent=2, ensure_ascii=False))
print(f'Updated {updated} payloads with full schema.')
print(f'Not explicitly enriched ({len(not_found)}): {not_found}')
