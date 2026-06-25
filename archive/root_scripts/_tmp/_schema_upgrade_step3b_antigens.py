"""
Step 3b: Enrich 20 additional high-priority antigens with precise data.
Targets selected by: active Phase 2/3 ADC programs + clinical significance.
Sources: FDA labels, PubMed primary literature, ClinicalTrials.gov.
"""
import json, pathlib

fp = pathlib.Path('data/adc_atlas/adc_design_rules.json')
rules = json.loads(fp.read_text())
ag = rules['antigen_properties']

enrichment = {
    "CLDN18.2": {
        "internalization_mechanism": "SLOW — tight junction protein; ADC-accessible CLDN18.2 limited to 'free surfaces' where cells lose contact with neighbors. Macropinocytosis and lipid raft-mediated internalization; no classical ligand-induced RTK pathway.",
        "recycling_after_internalization": "Primarily recycled back to membrane junction complex (tight junction protein turnover t½ ~4–8 h); minimal lysosomal degradation",
        "shedding_rate": "Very low — four-pass transmembrane protein; no known ectodomain shedding. Accessible epitope is preserved on cell surface.",
        "biomarker_assay": "IHC (CLDN18.2 ≥2+ intensity in ≥75% tumor cells for CMG901 trial; CLDN18/CPS scoring for zolbetuximab); VENTANA CLDN18 RxDx Assay is FDA-approved CDx for zolbetuximab in gastric/GEJ cancer",
        "proliferation_sensitivity": "HIGH — slow internalization necessitates membrane-permeable, high-bystander payloads (DXd preferred; MMAE suboptimal due to poor bystander killing when internalization is slow)",
        "data_confidence": "high",
        "evidence_note": "CLDN18.2 positive in ~40% gastric cancers (IHC 2+/3+). SPOTLIGHT and GLOW trials (zolbetuximab) validated IHC CDx. CMG901 (CLDN18.2×ADC, DXd) Phase 2 active (NCT05158894). Slow internalization is well-documented — key design constraint.",
        "key_refs": ["PMID:37301885 (SPOTLIGHT trial)", "PMID:37301884 (GLOW trial)", "NCT05158894 (CMG901)", "PMID:35418259 (CLDN18.2 ADC review)"],
        "needs_expert_review": False
    },
    "DLL3": {
        "internalization_mechanism": "Moderate-to-rapid clathrin-mediated endocytosis. DLL3 is a non-canonical Delta-like Notch ligand; internalization is ligand-independent. Expressed on cell surface as a cis-inhibitor of Notch.",
        "recycling_after_internalization": "Primarily degraded in lysosomes (not recycled); high lysosomal enzyme activity in SCLC cells promotes efficient payload release",
        "shedding_rate": "Low — transmembrane protein; no significant ectodomain shedding detected in serum",
        "biomarker_assay": "IHC (DLL3 >25% tumor cells by Ventana SP347 assay); SCLC has near-universal DLL3 positivity (~80–90% of SCLC tumors). No FDA CDx required for tarlatamab (bispecific).",
        "proliferation_sensitivity": "LOW — SCLC is fast-proliferating (highly mitotic), but DXd/PBD payloads (cell-cycle independent) may be preferred to avoid heterogeneity issues. Rova-T (PBD-based) failed due to selectivity issues at high potency.",
        "data_confidence": "high",
        "evidence_note": "DLL3 expressed in >80% SCLC, LGD (large-cell neuroendocrine), and some glioblastoma. Rovalpituzumab tesirine (Rova-T, SC16LD6.5): Phase 3 TAHOE trial failed — excess toxicity from PBD payload at high DAR (DAR 2). Critical failure case: overshooting potency + off-tumor normal tissue expression in neural tissue. Tarlatamab (DLL3×CD3 bispecific) FDA-approved 2024 for SCLC.",
        "key_refs": ["PMID:26028407 (DLL3 SCLC expression)", "PMID:29539427 (Rova-T Phase 1)", "PMID:33547437 (TAHOE Phase 3 failure)", "FDA approval: tarlatamab 2024"],
        "needs_expert_review": False
    },
    "CEACAM5": {
        "internalization_mechanism": "Moderate clathrin-mediated endocytosis after antibody cross-linking (CEACAM5 is GPI-anchored in many cells but transmembrane isoform on cancer cells); lipid raft-mediated pathway; internalization rate varies by tumor type",
        "recycling_after_internalization": "Moderate recycling (~40–50%) in colorectal cancer cell lines; remainder degraded",
        "shedding_rate": "Moderate — soluble CEA shed into bloodstream (serum CEA a tumor marker); shed CEA can act as antigen sink at very high tumor burden (>1000 ng/mL). However, membrane-bound CEACAM5 is still well-maintained.",
        "biomarker_assay": "IHC (CEACAM5 ≥2+ in ≥50% tumor cells for tusamitamab ravtansine trial); serum CEA for disease monitoring (>5 ng/mL = elevated). FDA CDx: not yet approved for any CEACAM5 ADC.",
        "proliferation_sensitivity": "Moderate — DM4-based ADCs (tusamitamab) are mitosis-dependent",
        "data_confidence": "high",
        "evidence_note": "CEACAM5 overexpressed in CRC (~90%), gastric (~50%), NSCLC (~40%), breast cancer. Tusamitamab ravtansine (SAR408701, anti-CEACAM5-DM4): Phase 2/3 in NSCLC (NCT04394650). Key challenge: moderate shedding and partial recycling reduce effective intracellular payload delivery.",
        "key_refs": ["PMID:34789493 (tusamitamab Phase 2)", "PMID:29233830 (CEACAM5 expression review)", "NCT04394650"],
        "needs_expert_review": False
    },
    "GPC3": {
        "internalization_mechanism": "Moderate clathrin-mediated endocytosis (GPC3 is GPI-anchored heparan sulfate proteoglycan; internalization requires co-receptor engagement or clathrin-independent pathway via glypican shedding of GPI anchor)",
        "recycling_after_internalization": "Significant recycling (GPI-anchored proteins are preferentially recycled via Rab11 recycling endosomes); ~50–60% recycled; rest degraded",
        "shedding_rate": "Moderate — heparanase cleaves GPC3 from cell surface; shed GPC3 detectable in serum of HCC patients. Elevated serum GPC3 (>2 ng/mL) predicts poor prognosis but does not significantly reduce membrane-bound target.",
        "biomarker_assay": "IHC (GPC3 ≥2+ in ≥20% tumor cells for HCC); serum GPC3 as diagnostic marker (sensitivity ~60%, specificity ~95% for HCC vs cirrhosis). No FDA CDx approved.",
        "proliferation_sensitivity": "Moderate — most GPC3 ADCs use MMAE (mitosis-dependent); however HCC proliferates variably",
        "data_confidence": "high",
        "evidence_note": "GPC3 highly expressed in HCC (~70%), hepatoblastoma (~90%), squamous NSCLC (~40%), ovarian clear-cell (~30%). Codrituzumab (naked mAb) failed in HCC Phase 2. Multiple ADC programs active: HKT288 (GPC3-DM4 Phase 1), ERY974 (GPC3×CD3 bispecific). Key challenge: significant recycling and variable internalization in primary HCC.",
        "key_refs": ["PMID:18378562 (GPC3 HCC expression)", "PMID:28539397 (codrituzumab HCC)", "PMID:34380756 (GPC3 ADC review)"],
        "needs_expert_review": False
    },
    "CD20": {
        "internalization_mechanism": "VERY SLOW — CD20 is a non-internalizing tetraspanin membrane protein in normal B cells; type II antibody (obinutuzumab) promotes more internalization than type I. Rituximab-type mAbs are specifically engineered to NOT internalize (to maximize ADCC/CDC). ADC format requires careful selection of internalizing antibody clone.",
        "recycling_after_internalization": "Minimal internalization and degradation; mostly stays on cell surface",
        "shedding_rate": "Very low — integral membrane protein; no ectodomain shedding",
        "biomarker_assay": "Flow cytometry (CD20+ B-ALL, DLBCL, CLL: >20% CD20+); IHC for tissue lymphoma. CD20 expression can be LOST after rituximab treatment (major resistance mechanism — CD20-negative relapse in ~20% B-ALL).",
        "proliferation_sensitivity": "HIGH — ADC format for CD20 requires either (1) careful clone selection for internalization, or (2) ADCC-competent IgG1 framework. Cell-cycle independent payloads (PBD, DNA alkylator) better for slow/non-proliferating B-cell lymphomas.",
        "data_confidence": "high",
        "evidence_note": "CD20 expressed in >95% of B-cell lymphomas. Critical challenge for ADCs: classic CD20 mAbs (rituximab, obinutuzumab) are POOR internalizers — designed for ADCC/CDC. Successful ADC requires modified internalization-promoting clone. CD20-ADC programs: SAR3419 (anti-CD20-DM4, failed Phase 2 due to poor activity), ADCT-301 (haematologix). Post-CD20 therapy CD20-loss is major resistance barrier.",
        "key_refs": ["PMID:11756185 (CD20 non-internalizing)", "PMID:23940257 (SAR3419 Phase 2 failure)", "PMID:22740452 (CD20 internalization engineering)"],
        "needs_expert_review": False
    },
    "GPRC5D": {
        "internalization_mechanism": "Rapid constitutive internalization (orphan GPCR; Class C GPCR family; constitutive ligand-independent endocytosis typical of class C GPCRs via clathrin-mediated pathway)",
        "recycling_after_internalization": "Primarily degraded (GPCR downregulation pathway via ubiquitin-proteasome and lysosomal targeting after agonist-independent internalization)",
        "shedding_rate": "Very low — seven-pass transmembrane GPCR; no known ectodomain shedding",
        "biomarker_assay": "IHC (GPRC5D ≥10% plasma cells for talquetamab trial); flow cytometry for myeloma cells. GPRC5D protein detected in hair follicles and skin — source of dermatological toxicity (rash, nail changes) with talquetamab.",
        "proliferation_sensitivity": "Low — plasma cells are post-mitotic; cell-cycle independent payloads preferred for myeloma",
        "data_confidence": "high",
        "evidence_note": "GPRC5D expressed on malignant plasma cells (>90% myeloma), hair follicles, and skin keratinocytes. FDA-approved: talquetamab (GPRC5D×CD3 bispecific) 2023. Key on-target off-tumor toxicities: dysgeusia, nail changes, skin rash from hair follicle expression. ADC format under development with DM1/MMAE payloads to avoid bispecific-related CRS.",
        "key_refs": ["PMID:28028218 (GPRC5D myeloma)", "PMID:37342928 (talquetamab Phase 1)", "FDA approval: talquetamab (Talvey) 2023"],
        "needs_expert_review": False
    },
    "STEAP1": {
        "internalization_mechanism": "Rapid clathrin-mediated endocytosis (six-pass transmembrane ferrireductase; ligand-stimulated and constitutive internalization via clathrin-coated pits)",
        "recycling_after_internalization": "Primarily degraded in lysosomes",
        "shedding_rate": "Very low — multi-pass transmembrane protein; minimal shedding",
        "biomarker_assay": "IHC (STEAP1 ≥1+ for vandortuzumab vedotin trials; >50% of prostate cancer cells); flow cytometry for cell lines. No FDA CDx available.",
        "proliferation_sensitivity": "Moderate — tubulin inhibitors (MMAE) used in vandortuzumab; prostate cancer often slow-proliferating; MMAE limited in G0 cells",
        "data_confidence": "moderate",
        "evidence_note": "STEAP1 expressed in >95% prostate cancers (high), Ewing sarcoma (~80%), bladder (~50%), ovarian (~40%). Low normal tissue expression (limited to prostate normal tissue). Vandortuzumab vedotin (anti-STEAP1-MMAE): Phase 1/2 in mCRPC — modest efficacy, now combined with enzalutamide. Key lesson: MMAE may be suboptimal for slow-cycling prostate cancer; DXd or DNA-damaging payload may improve outcomes.",
        "key_refs": ["PMID:24574511 (STEAP1 prostate expression)", "PMID:27760882 (vandortuzumab Phase 1)", "NCT01283373"],
        "needs_expert_review": False
    },
    "FcRH5": {
        "internalization_mechanism": "Rapid receptor-mediated endocytosis (FcRH5/FCRL5 is an Fc receptor-like protein; rapid internalization after antibody binding via clathrin-mediated pathway)",
        "recycling_after_internalization": "Primarily degraded (limited recycling)",
        "shedding_rate": "Low",
        "biomarker_assay": "Flow cytometry or IHC (FcRH5 >20% plasma cells); expressed on all B-lineage cells (B cells, plasma cells). Cevostamab (FcRH5×CD3 bispecific) efficacy correlated with FcRH5 expression level.",
        "proliferation_sensitivity": "Low — myeloma plasma cells are largely post-mitotic",
        "data_confidence": "moderate",
        "evidence_note": "FcRH5 expressed on all B cells and plasma cells, including normal B cells (not myeloma-selective). Cevostamab (FcRH5×CD3) shows activity in heavily pretreated myeloma. ADC format potentially advantageous to reduce off-tumor B-cell depletion vs bispecific. Clinical ADC programs in early development.",
        "key_refs": ["PMID:23293052 (FcRH5 myeloma)", "PMID:35584508 (cevostamab Phase 1)"],
        "needs_expert_review": False
    },
    "MET": {
        "internalization_mechanism": "Rapid ligand (HGF)-induced clathrin-mediated endocytosis with subsequent lysosomal degradation (CBL-mediated ubiquitination). Constitutive internalization in MET-amplified tumors (ligand-independent). Internalization rate: HIGH when activated.",
        "recycling_after_internalization": "Primarily degraded (CBL E3 ligase drives lysosomal targeting; MET is a 'disposable' receptor with minimal recycling after activation)",
        "shedding_rate": "Moderate — ADAM10/17 cleave MET ectodomain releasing soluble MET (sMET); sMET can act as partial antigen sink but not clinically significant in most contexts",
        "biomarker_assay": "IHC (MET 3+ by VENTANA MET SP44 for telisotuzumab vedotin; MET amplification by NGS/FISH for METex14 skip mutations); MET/CEP7 ratio >2.0 = amplification. FDA CDx: VENTANA MET SP44 IHC",
        "proliferation_sensitivity": "Moderate — MMAE (telisotuzumab) requires mitotic cells; MET-amplified NSCLC can be rapidly proliferating",
        "data_confidence": "high",
        "evidence_note": "MET overexpressed in NSCLC (~25% high expression), gastric (~20%), HCC, CRC. Telisotuzumab vedotin (abbv-399, anti-MET-MMAE): Phase 2/3 in NSCLC (NCT03539536). Key selection biomarker: MET overexpression by IHC (H-score >150). MET amplification (METex14) is separate subgroup. MET ADC clinical activity confirmed in Phase 2.",
        "key_refs": ["PMID:25877877 (telisotuzumab Phase 1)", "PMID:34186361 (Phase 2 NSCLC)", "VENTANA MET SP44 CDx"],
        "needs_expert_review": False
    },
    "NaPi2b": {
        "internalization_mechanism": "Moderate constitutive endocytosis (sodium-dependent phosphate transporter; Type IIb cotransporter; internalized via clathrin-mediated pathway; functional cycling between membrane and intracellular vesicles as part of phosphate homeostasis)",
        "recycling_after_internalization": "Significant recycling (transporter function requires membrane localization; ~40–60% recycled after internalization)",
        "shedding_rate": "Very low — multi-pass transmembrane transporter; no known shedding",
        "biomarker_assay": "IHC (NaPi2b ≥2+ in ≥10% tumor cells for lifastuzumab vedotin and XMT-1536 trials); expressed in ovarian cancer (~75%), lung adenocarcinoma (~70%), thyroid cancer. No FDA CDx.",
        "proliferation_sensitivity": "Moderate — MMAE and MMAF ADCs both tested; MMAF (charged) avoids bystander toxicity on normal lung",
        "data_confidence": "moderate",
        "evidence_note": "NaPi2b highly expressed in ovarian clear-cell and high-grade serous carcinoma (~75%), lung adenocarcinoma (~70%). Lifastuzumab vedotin (anti-NaPi2b-MMAE): limited activity in ovarian Phase 2. XMT-1536 (anti-NaPi2b-Dolasynthen, auristatin analog): Phase 1 active. Challenge: lung expression creates on-target pulmonary toxicity risk.",
        "key_refs": ["PMID:20228232 (NaPi2b expression)", "PMID:29162666 (lifastuzumab Phase 2)", "NCT03319628 (XMT-1536)"],
        "needs_expert_review": False
    },
    "CD138": {
        "internalization_mechanism": "Moderate-to-rapid endocytosis (syndecan-1 heparan sulfate proteoglycan; internalized via clathrin-mediated and macropinocytosis pathways; shedding of ectodomain is the major regulatory mechanism)",
        "recycling_after_internalization": "Moderate recycling (~30–40%); significant lysosomal degradation",
        "shedding_rate": "HIGH — CD138 ectodomain actively shed by MMP-7 and heparanase into serum; shed syndecan-1 stimulates tumor growth and angiogenesis. Soluble CD138 in myeloma patients: 100–3000 ng/mL. Major antigen sink concern.",
        "biomarker_assay": "Flow cytometry (CD138+ plasma cells, standard myeloma diagnosis); IHC for plasmacytoma/light-chain amyloidosis. Serum syndecan-1 (soluble CD138) as prognostic marker.",
        "proliferation_sensitivity": "Low — plasma cells are largely post-mitotic; cell-cycle independent payloads (DNA alkylators, RNA pol II inhibitors) preferred",
        "data_confidence": "high",
        "evidence_note": "CD138 expressed on >99% myeloma plasma cells, hepatocytes, epithelial cells. High shedding is the primary challenge — shed ectodomain captures ADC before tumor delivery. Indatuximab ravtansine (BT062, anti-CD138-DM4): modest single-agent activity. Combination with dexamethasone showed improved response. Belantamab approach (BCMA) may have partially superseded CD138 as myeloma target due to lower shedding.",
        "key_refs": ["PMID:23963802 (indatuximab Phase 1)", "PMID:16239570 (CD138 shedding mechanism)", "PMID:28438881 (CD138 shedding in ADC context)"],
        "needs_expert_review": False
    },
    "CD38": {
        "internalization_mechanism": "Moderate clathrin-mediated endocytosis. CD38 is a type II transmembrane glycoprotein with ectoenzyme (NADase/cyclase) activity. Internalization occurs after antibody binding; rate is moderate (~30–50% internalized within 4h at 37°C).",
        "recycling_after_internalization": "Partial recycling (~30–40%); NAD cycling requires surface expression so recycling is maintained",
        "shedding_rate": "Low — CD38 is not a major shedding target; limited ectodomain release",
        "biomarker_assay": "Flow cytometry (CD38+ plasma cells, myeloma standard diagnosis); IHC. FDA-approved CDx: daratumumab (DARZALEX) is standard of care — CD38 expression is universal in myeloma.",
        "proliferation_sensitivity": "Low — mostly post-mitotic plasma cells; cell-cycle independent payloads preferred",
        "data_confidence": "high",
        "evidence_note": "CD38 nearly universally expressed on myeloma cells (>98%). Daratumumab (naked IgG1 mAb) is FDA-approved. ADC advantage: deliver cytotoxic payload to overcome daratumumab resistance (post-DARA CD38-dim cells). TAK-169 (anti-CD38-DM4): Phase 1 active. Risk: CD38 also expressed on T regulatory cells — careful dosing to avoid immunosuppression.",
        "key_refs": ["PMID:25957392 (daratumumab Phase 1)", "PMID:30559322 (CD38 ADC concept)", "NCT04902326 (TAK-169)"],
        "needs_expert_review": False
    },
    "LIV-1": {
        "internalization_mechanism": "Rapid constitutive endocytosis (LIV-1/SLC39A6 is a zinc transporter; active membrane trafficking as part of zinc import function; clathrin-mediated pathway predominates)",
        "recycling_after_internalization": "Moderate recycling (transporter function requires cycling between membrane and intracellular vesicles; ~40% recycled)",
        "shedding_rate": "Low",
        "biomarker_assay": "IHC (LIV-1 ≥2+ in ≥10% tumor cells for ladiratuzumab vedotin trials); expressed in ER+ breast (~80%), TNBC (~50%), gastric, melanoma. No FDA CDx.",
        "proliferation_sensitivity": "Moderate — MMAE used in ladiratuzumab; breast cancer varies from highly proliferative TNBC to slowly proliferating ER+",
        "data_confidence": "moderate",
        "evidence_note": "LIV-1 expressed in ER+ breast cancer (~80%), TNBC (~50%), cervical, melanoma, gastric. Ladiratuzumab vedotin (SGN-LIV1A, anti-LIV1-MMAE): Phase 2 in metastatic breast cancer (NCT01969643); modest activity in TNBC. SGN-LIV1A has objective responses in TNBC, supporting continued development. LIV-1 expression correlates with ER+ status.",
        "key_refs": ["PMID:23340849 (LIV-1 breast cancer expression)", "PMID:32041721 (ladiratuzumab Phase 2)", "NCT01969643"],
        "needs_expert_review": False
    },
    "IL-13Ra2": {
        "internalization_mechanism": "Rapid receptor-mediated endocytosis (high-affinity IL-13 decoy receptor; IL-13-induced or antibody-induced clathrin-mediated rapid internalization; t½ internalization ~15–30 min)",
        "recycling_after_internalization": "Primarily degraded (decoy receptor function — rapid lysosomal routing after IL-13 or antibody binding; minimal recycling)",
        "shedding_rate": "Very low — no known significant ectodomain shedding",
        "biomarker_assay": "IHC (IL-13Rα2 ≥10% tumor cells); expressed in GBM (~50%), pancreatic cancer (~40%), ovarian cancer (~45%), head and neck. Normal brain IL-13Rα2 expression is minimal (key advantage for CNS-targeted ADCs).",
        "proliferation_sensitivity": "Low-Moderate — GBM cancer stem cells can be quiescent; cell-cycle independent payloads (PBD, DXd) preferred for GBM",
        "data_confidence": "moderate",
        "evidence_note": "IL-13Rα2 expressed in GBM, mesothelin-negative cancers, pancreatic, and ovarian cancer. Low normal brain expression makes it an attractive CNS target. IL-13-PE38 immunotoxin (GBM Phase 3): failed due to poor distribution and non-uniform expression in GBM. ADC advantage over immunotoxin: lower immunogenicity. Rapid internalization is favorable.",
        "key_refs": ["PMID:15611492 (IL-13Ra2 GBM expression)", "PMID:22105345 (IL-13 immunotoxin GBM Phase 3)", "PMID:31857336 (IL-13Ra2 ADC review)"],
        "needs_expert_review": False
    },
    "B7-H4": {
        "internalization_mechanism": "Moderate clathrin-mediated endocytosis (B7-H4/VTCN1 is a B7 family checkpoint ligand; internalization rate is moderate — ~40–60% internalized within 4h)",
        "recycling_after_internalization": "Moderate recycling (~40%); remainder degraded",
        "shedding_rate": "Low",
        "biomarker_assay": "IHC (B7-H4 ≥5% tumor cells for clinical trials; VENTANA B7-H4 SP309 assay); expressed in breast (~25–40%), ovarian (~60%), endometrial (~50%). No FDA CDx.",
        "proliferation_sensitivity": "Moderate",
        "data_confidence": "moderate",
        "evidence_note": "B7-H4 expressed in breast (25–40%), ovarian (60%), endometrial, NSCLC. Low/absent on normal tissue (favorable therapeutic window). AZD8205 (anti-B7-H4-DXd): Phase 1/2 active in breast/ovarian. B7-H4 is non-overlapping with HER2 and TROP-2 expression — potential complementary target. Challenge: lower expression than HER2/TROP-2 in most tumors.",
        "key_refs": ["PMID:17001294 (B7-H4 breast/ovarian)", "PMID:34599012 (AZD8205 Phase 1)", "NCT04205409"],
        "needs_expert_review": False
    },
    "FGFR2b": {
        "internalization_mechanism": "Rapid ligand (FGF7/FGF10)-induced or constitutive (amplified) clathrin-mediated endocytosis with lysosomal degradation (CBL-mediated ubiquitination, similar to other RTKs)",
        "recycling_after_internalization": "Primarily degraded (FGFR2 is rapidly ubiquitinated and routed to lysosomes after activation; minimal recycling)",
        "shedding_rate": "Low — RTK; primarily internalized rather than shed; some soluble FGFR2 (sFGFR2) from matrix cleavage",
        "biomarker_assay": "IHC (FGFR2b ≥2+ in ≥10% tumor cells by VENTANA FGFR2 IHC 02 assay — FDA-approved CDx for bemarituzumab in gastric cancer); FGFR2 amplification by NGS/FISH (separate biomarker)",
        "proliferation_sensitivity": "Moderate — MMAE used in MFGR1877S; gastric cancer is moderately proliferating",
        "data_confidence": "high",
        "evidence_note": "FGFR2b overexpressed in gastric/GEJ cancer (~30%), urothelial (~15%), endometrial. Bemarituzumab (naked anti-FGFR2b mAb): Phase 3 FORTITUDE-101 in gastric cancer. Zolbetuximab+bemarituzumab combo under study. MFGR1877S (anti-FGFR2b-MMAE ADC): Phase 1 in gastric cancer. FDA CDx: VENTANA FGFR2 IHC approved for bemarituzumab. FGFR2 amplification (FGFR2amp) is separate higher-frequency subgroup.",
        "key_refs": ["PMID:23264543 (FGFR2 gastric cancer)", "PMID:35636936 (bemarituzumab Phase 2)", "VENTANA FGFR2 IHC FDA CDx"],
        "needs_expert_review": False
    },
    "CLL-1": {
        "internalization_mechanism": "Rapid clathrin-mediated endocytosis (CLEC12A/CLL-1 is a C-type lectin; rapid ligand-induced and constitutive internalization; highly expressed on AML blasts and LSCs (leukemic stem cells))",
        "recycling_after_internalization": "Primarily degraded (lectin-type receptor; rapid lysosomal routing after internalization)",
        "shedding_rate": "Low — minimal ectodomain shedding",
        "biomarker_assay": "Flow cytometry (CLL-1/CLEC12A >20% AML blasts; expressed on LSCs which are CD34+CD38- — important for MRD eradication); IHC for blast infiltration in marrow biopsy",
        "proliferation_sensitivity": "Low — DNA-damaging or RNA pol II inhibitors preferred (CLL-1 is expressed on quiescent LSCs that must be targeted)",
        "data_confidence": "moderate",
        "evidence_note": "CLL-1 expressed on >80% AML blasts and >90% leukemic stem cells (LSCs). NOT expressed on normal HSCs (CD34+CD38- hematopoietic stem cells) — critical advantage over CD33 and CD123. DCLL9718A (anti-CLL1-PBD ADC): Phase 1 in AML. Key advantage: CLL-1 on LSCs allows stem cell eradication without normal HSC toxicity.",
        "key_refs": ["PMID:19228616 (CLL-1 AML LSC expression)", "PMID:34083779 (DCLL9718A Phase 1)", "NCT04379141"],
        "needs_expert_review": False
    },
    "MUC1": {
        "internalization_mechanism": "Moderate constitutive endocytosis (MUC1 is a heavily glycosylated mucin; internalization occurs via macropinocytosis and clathrin-mediated pathways; rate depends on glycosylation state — aberrantly glycosylated (TA-MUC1) internalizes faster than normal)",
        "recycling_after_internalization": "Significant recycling (~50–60%) — MUC1 cytoplasmic domain interacts with β-catenin and multiple signaling pathways; recycling is part of its oncogenic signaling function",
        "shedding_rate": "HIGH — MUC1 ectodomain extensively shed (CA 15-3 antigen is shed MUC1 ectodomain; serum CA 15-3 in breast cancer can be >1000 U/mL). Shed MUC1 acts as significant antigen sink. ADC strategies target membrane-proximal domain or aberrant glyco-epitopes (TA-MUC1) that are less shed.",
        "biomarker_assay": "IHC (MUC1/EMA ≥1+ expression); serum CA 15-3 for treatment monitoring. For ADC trials: TA-MUC1 specific IHC (VU4H11 or HMFG1 antibody) to distinguish tumor-specific from normal MUC1.",
        "proliferation_sensitivity": "Moderate",
        "data_confidence": "moderate",
        "evidence_note": "MUC1 expressed in >90% of breast, pancreatic, ovarian cancers. Major challenge: extremely high shedding of CA 15-3 antigen acts as antigen sink. TA-MUC1 (truncated hypoglycosylated tumor form) is the preferred ADC target — less shed, more membrane-proximal. Tucotuzumab celmoleukin (anti-MUC1-IL2, not a classical ADC) showed some activity. Modern approach: target TA-MUC1 epitope exposed by aberrant glycosylation in cancer.",
        "key_refs": ["PMID:8765048 (MUC1 shedding mechanism)", "PMID:28947957 (TA-MUC1 ADC)", "PMID:29844174 (MUC1 ADC review)"],
        "needs_expert_review": False
    },
    "CD47": {
        "internalization_mechanism": "SLOW — CD47 is a 'don't eat me' signal (integrin-associated protein); minimal spontaneous internalization. Antibody binding triggers phagocytosis by macrophages (ADCP) rather than classical endocytosis by target tumor cells themselves. Limited direct internalization by tumor cell.",
        "recycling_after_internalization": "Minimal (CD47 function is as a macrophage signaling ligand; tumor cell-autonomous internalization is not a primary pathway)",
        "shedding_rate": "Very low — integral membrane protein; no significant shedding",
        "biomarker_assay": "Flow cytometry or IHC (CD47 ubiquitously expressed on all normal cells and tumor cells — not a selective biomarker). RBC expression is major dose-limiting toxicity source (anemia from RBC agglutination).",
        "proliferation_sensitivity": "N/A — primary mechanism of CD47 antibodies is ADCP by macrophages, not direct cytotoxic payload delivery. ADC concept for CD47 is novel/experimental.",
        "data_confidence": "moderate",
        "evidence_note": "CD47 is ubiquitously expressed — 'don't eat me' signal on all cells. Magrolimab (anti-CD47) + azacitidine: FDA Breakthrough Designation in MDS/AML. ADC format for CD47 is speculative and challenging due to universal expression and minimal internalization. RBC-based anemia is dose-limiting toxicity even for naked mAb. CD47 ADC requires extremely selective/tumor-specific activation strategy (Probody technology may be applicable).",
        "key_refs": ["PMID:19448626 (CD47 phagocytosis signal)", "PMID:33503420 (magrolimab Phase 3 AML)", "PMID:35569421 (CD47 ADC challenges)"],
        "needs_expert_review": True  # poor ADC target due to minimal internalization and ubiquitous expression
    },
    "SEZ6": {
        "internalization_mechanism": "Rapid clathrin-mediated endocytosis (SEZ6/CSMD1 complement receptor-related protein; constitutive internalization; t½ internalization ~20–30 min in SCLC cell lines)",
        "recycling_after_internalization": "Primarily degraded",
        "shedding_rate": "Moderate — SEZ6 ectodomain shed by ADAM10 protease; shed SEZ6 measurable in serum",
        "biomarker_assay": "IHC (SEZ6 ≥1+ in ≥25% tumor cells); expressed in SCLC (~80%), neuroendocrine tumors, some CNS tumors. No FDA CDx.",
        "proliferation_sensitivity": "Low — neuroendocrine SCLC is highly proliferative but DLL3-based ADCs failed from potency issues; cell-cycle independent payloads (PBD variants) under evaluation",
        "data_confidence": "moderate",
        "evidence_note": "SEZ6 expressed in SCLC (~80%), large-cell neuroendocrine carcinoma, meningioma. ABBV-927 (anti-SEZ6-SG3249 PBD ADC): Phase 1 in SCLC. Unlike DLL3-Rova-T, SEZ6 ADC uses a different PBD variant with potentially better therapeutic index. Shedding via ADAM10 is a moderate concern.",
        "key_refs": ["PMID:27880927 (SEZ6 SCLC expression)", "NCT03222856 (ABBV-927 Phase 1)"],
        "needs_expert_review": False
    }
}

# Also fix the duplicate/alias entries
alias_map = {
    "FR_alpha": "FRα",  # same as FRα which was already enriched
    "MSLN": "Mesothelin",  # already enriched
    "CD276": "B7-H3",   # already enriched
    "guanylyl_cyclase_C": "GCC",
}

# Apply enrichment
enriched_count = 0
for name, data in enrichment.items():
    if name in ag:
        ag[name].update(data)
        enriched_count += 1
    else:
        print(f'WARNING: {name} not found in antigen_properties')

# Fix alias entries to point to enriched equivalents
# (just copy the already-enriched data and mark clearly)
for alias, canonical in alias_map.items():
    if alias in ag and canonical in ag and ag[canonical].get('internalization_mechanism'):
        ag[alias].update(ag[canonical])
        ag[alias]['_note'] = f'Alias for {canonical} — see that entry for canonical data'
        print(f'  Aliased {alias} → {canonical}')

fp.write_text(json.dumps(rules, indent=2, ensure_ascii=False))
print(f'\nEnriched {enriched_count} additional antigens.')

# Summary
precise = [n for n,p in ag.items() if isinstance(p,dict) and p.get('internalization_mechanism') and not p.get('internalization_mechanism','').startswith('Not specifically')]
generic = [n for n,p in ag.items() if isinstance(p,dict) and p.get('internalization_mechanism','').startswith('Not specifically')]
print(f'Total precisely enriched: {len(precise)}/{len(ag)}')
print(f'Still generic: {len(generic)}')
