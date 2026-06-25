"""
Step 3: Add internalization mechanism, recycling, shedding, and biomarker assay
to all antigen entries in adc_design_rules.json.
"""
import json, pathlib

fp = pathlib.Path('data/adc_atlas/adc_design_rules.json')
rules = json.loads(fp.read_text())
ag = rules['antigen_properties']

antigen_enrichment = {
    "HER2": {
        "internalization_mechanism": "Clathrin-mediated endocytosis (CME); macropinocytosis at high antibody occupancy",
        "recycling_after_internalization": "Partial recycling to surface (25–40%); remainder targeted for lysosomal degradation",
        "shedding_rate": "Low (p95-HER2 shed ECD fragment; not major sink)",
        "biomarker_assay": "IHC + FISH (HER2+: IHC 3+ or IHC 2+/FISH+); HER2-low: IHC 1+ or 2+/FISH-; FDA CDx: PATHWAY HER2 (Ventana)",
        "proliferation_sensitivity": "Moderate — bystander-capable payloads (DXd) preferred for HER2-low/heterogeneous tumors"
    },
    "TROP-2": {
        "internalization_mechanism": "Rapid constitutive clathrin-mediated endocytosis (CME) + lipid raft-mediated",
        "recycling_after_internalization": "Primarily lysosomal degradation (>80% degraded, minimal recycling)",
        "shedding_rate": "Low — minimal soluble TROP-2 ectodomain shedding",
        "biomarker_assay": "IHC (TROP-2 H-score ≥100 for patient selection in some trials); no FDA CDx approved for sacituzumab govitecan",
        "proliferation_sensitivity": "Moderate — TOP1i (DXd/SN-38) active in all phases"
    },
    "Nectin-4": {
        "internalization_mechanism": "Rapid clathrin-mediated endocytosis",
        "recycling_after_internalization": "Primarily degraded in lysosomes",
        "shedding_rate": "Low",
        "biomarker_assay": "IHC (>25% tumor cells positive); no FDA CDx currently required for Padcev",
        "proliferation_sensitivity": "Moderate — tubulin inhibitor (MMAE); requires proliferating cells"
    },
    "CD30": {
        "internalization_mechanism": "Rapid receptor-mediated endocytosis (TNFR superfamily pathway)",
        "recycling_after_internalization": "Primarily degraded; minimal recycling",
        "shedding_rate": "Moderate — soluble CD30 (sCD30) shed by metalloprotease ADAM10/17; elevated sCD30 in serum is prognostic but does not significantly affect BV efficacy",
        "biomarker_assay": "IHC (≥10% CD30+ tumor cells required for HL/ALCL; FDA CDx: CD30 (Dako/Agilent))",
        "proliferation_sensitivity": "Moderate"
    },
    "CD33": {
        "internalization_mechanism": "Rapid receptor-mediated endocytosis (Siglec family; lectin-like internalization)",
        "recycling_after_internalization": "Rapid internalization AND rapid recycling to surface — requires pulse dosing strategy (Mylotarg fractionated dosing rationale)",
        "shedding_rate": "Low (some shedding but not a major pharmacological sink)",
        "biomarker_assay": "IHC or flow cytometry (>30% AML blasts CD33+; no strict cutoff required for GO)",
        "proliferation_sensitivity": "Low — calicheamicin (Mylotarg payload) is cell-cycle independent"
    },
    "CD22": {
        "internalization_mechanism": "Constitutive receptor-mediated endocytosis (lectin-type; internalizes B-cell receptor complex)",
        "recycling_after_internalization": "Primarily degraded in lysosomes; some recycling",
        "shedding_rate": "Very low",
        "biomarker_assay": "Flow cytometry (>20% CD22+ blasts in B-ALL); IHC for lymphoma",
        "proliferation_sensitivity": "Moderate"
    },
    "CD79b": {
        "internalization_mechanism": "Rapid internalization via B-cell receptor (BCR) complex co-endocytosis; clathrin-mediated",
        "recycling_after_internalization": "Primarily lysosomal degradation",
        "shedding_rate": "Very low",
        "biomarker_assay": "IHC (VENTANA anti-CD79b; >25% tumor cells); flow cytometry for B-cell lymphomas",
        "proliferation_sensitivity": "Moderate — requires tubulin-active cells"
    },
    "BCMA": {
        "internalization_mechanism": "Clathrin-mediated endocytosis; APRIL/BAFF ligand-induced internalization increases rate",
        "recycling_after_internalization": "Primarily degraded",
        "shedding_rate": "High — BCMA is actively shed by ADAM10/17; soluble BCMA (sBCMA) is a resistance biomarker. Elevated sBCMA associates with belantamab mafodotin resistance.",
        "biomarker_assay": "IHC or flow cytometry (>50% plasma cells BCMA+); sBCMA serum level is emerging biomarker. FDA CDx: BCMA IHC (pending for several agents)",
        "proliferation_sensitivity": "Low — auristatin F (belantamab) is mitosis-dependent; bystander effect absent (MMAF)"
    },
    "CD19": {
        "internalization_mechanism": "Co-internalization with BCR complex (clathrin-mediated); also trogocytosis",
        "recycling_after_internalization": "Partial recycling",
        "shedding_rate": "Very low",
        "biomarker_assay": "Flow cytometry or IHC (>20% CD19+ for B-ALL/DLBCL)",
        "proliferation_sensitivity": "Moderate"
    },
    "FRalpha": {
        "internalization_mechanism": "Receptor-mediated endocytosis (folate-driven GPI-anchored receptor; clathrin-independent, lipid raft pathway)",
        "recycling_after_internalization": "Significant recycling to surface (GPI-anchored; ~50% recycled within 4h)",
        "shedding_rate": "Low",
        "biomarker_assay": "IHC (FR-alpha IHC ≥75% tumor cells at 2+ intensity for mirvetuximab MIRASOL trial; FDA CDx: VENTANA anti-FR alpha)",
        "proliferation_sensitivity": "Low — DM4 payload is cell-cycle dependent but FRα recycling ensures continuous payload delivery"
    },
    "EGFR": {
        "internalization_mechanism": "CME (CBL-mediated ubiquitination → lysosomal degradation after EGF stimulation); at high antibody occupancy also macropinocytosis",
        "recycling_after_internalization": "Major recycling (Rab11-mediated recycling endosome) without ligand; degradation with EGF/ligand co-stimulation",
        "shedding_rate": "Low for full ECD; some EGFR domain shedding by ADAM10",
        "biomarker_assay": "IHC (EGFR expression by IHC, H-score; EGFR mutation by NGS/PCR for subtype selection); EGFRvIII by specific IHC",
        "proliferation_sensitivity": "High — most EGFR ADCs use MMAE/auristatin (mitosis-dependent); limits activity against slow-growing tumors"
    },
    "EGFRvIII": {
        "internalization_mechanism": "Rapid constitutive internalization (unlike WT EGFR, EGFRvIII internalizes without ligand due to constitutive activation)",
        "recycling_after_internalization": "Primarily degraded",
        "shedding_rate": "Very low (tumor-cell-specific splicing; no detectable soluble form)",
        "biomarker_assay": "EGFRvIII-specific IHC or RT-PCR (tumor-specific; not detectable in blood); high intratumoral heterogeneity is a major challenge",
        "proliferation_sensitivity": "High"
    },
    "Mesothelin": {
        "internalization_mechanism": "POOR — GPI-anchored protein primarily on apical/luminal surface; macropinocytosis is limited; SLOW internalization is a major ADC design challenge",
        "recycling_after_internalization": "Primarily membrane-retained; minimal degradation after internalization",
        "shedding_rate": "High — soluble megakaryocyte potentiating factor (MPF) shed by ADAM proteases; soluble mesothelin in plasma acts as antigen sink (reduces effective dose reaching tumor)",
        "biomarker_assay": "IHC (mesothelin expression by H-score >50); serum soluble mesothelin (SMRP) as pharmacodynamic biomarker",
        "proliferation_sensitivity": "High — most Mesothelin ADCs use MMAE; poor internalization limits payload delivery efficiency"
    },
    "GD2": {
        "internalization_mechanism": "VERY SLOW — ganglioside (glycolipid); lipid raft-mediated macropinocytosis only; classical receptor endocytosis absent",
        "recycling_after_internalization": "Minimal — lipid components recycled via lipid recycling pathways, not lysosomal delivery",
        "shedding_rate": "Moderate (shed ganglioside in circulation; GD2 shedding rate correlates with tumor burden)",
        "biomarker_assay": "IHC or immunofluorescence (≥20% cells GD2+); serum GD2 ganglioside as pharmacodynamic biomarker in neuroblastoma",
        "proliferation_sensitivity": "High — poor internalization means most therapeutic effect may rely on ADCC/CDC rather than payload delivery in GD2 ADCs"
    },
    "CD123": {
        "internalization_mechanism": "Rapid receptor-mediated endocytosis (IL-3Rα; clathrin-mediated)",
        "recycling_after_internalization": "Primarily degraded",
        "shedding_rate": "Low",
        "biomarker_assay": "Flow cytometry (>20% AML blasts CD123+; MFI-based quantification)",
        "proliferation_sensitivity": "Low — DGN462/IGN payloads (IMGN632) are cell-cycle independent"
    },
    "FLT3": {
        "internalization_mechanism": "Ligand-induced rapid internalization (RTK pathway; clathrin-mediated)",
        "recycling_after_internalization": "Primarily degraded via ubiquitin-proteasome and lysosomal pathways",
        "shedding_rate": "Low (some sFLT3 shed, not clinically significant)",
        "biomarker_assay": "Flow cytometry (AML blasts); FLT3 mutation status (ITD/D835) by PCR/NGS for treatment selection",
        "proliferation_sensitivity": "Low — most FLT3 ADC payloads are DNA-damaging (cell-cycle independent)"
    },
    "Claudin18.2": {
        "internalization_mechanism": "SLOW — tight junction protein; internalization requires cell-cell junction disruption. Accessible CLDN18.2 is only on 'free surfaces' of gastric cancer cells (not at tight junctions)",
        "recycling_after_internalization": "Primarily recycled back to membrane (tight junction protein turnover)",
        "shedding_rate": "Very low (transmembrane protein; no known ectodomain shedding)",
        "biomarker_assay": "IHC (CLDN18.2 ≥2+ in ≥75% tumor cells for CMG901 trial; Claudin18 CLDN18/CPS for zolbetuximab); VENTANA CLDN18 RxDx Assay",
        "proliferation_sensitivity": "High — slow internalization requires membrane-permeable bystander-effect payloads (DXd preferred over MMAE)"
    },
    "Tissue Factor": {
        "internalization_mechanism": "Rapid constitutive and ligand-induced endocytosis (coagulation cascade activation triggers internalization)",
        "recycling_after_internalization": "Primarily degraded",
        "shedding_rate": "Low",
        "biomarker_assay": "IHC (≥25% TF+ tumor cells for Tivdak; FDA CDx: VENTANA SP295 anti-TF RxDx)",
        "proliferation_sensitivity": "Moderate"
    },
    "ROR1": {
        "internalization_mechanism": "Rapid clathrin-mediated endocytosis (caveolae-mediated reported in some cell lines; mechanism varies)",
        "recycling_after_internalization": "Primarily degraded",
        "shedding_rate": "Very low",
        "biomarker_assay": "Flow cytometry (>20% ROR1+) or IHC; ROR1 protein expression correlates with gene expression",
        "proliferation_sensitivity": "Moderate"
    },
    "HER3": {
        "internalization_mechanism": "Rapid internalization via HER2/HER3 heterodimer (requires HER2 co-expression for efficient endocytosis)",
        "recycling_after_internalization": "Significant recycling (HER3 has very low intrinsic kinase activity; recycling > degradation)",
        "shedding_rate": "Low",
        "biomarker_assay": "IHC (HER3 expression by H-score; no standardized CDx); HER3 is ubiquitously expressed making patient selection challenging",
        "proliferation_sensitivity": "Moderate"
    },
    "B7-H3": {
        "internalization_mechanism": "Moderate — clathrin-mediated endocytosis",
        "recycling_after_internalization": "Moderate recycling to membrane",
        "shedding_rate": "Low",
        "biomarker_assay": "IHC (H-score ≥100 typically used); no FDA CDx currently",
        "proliferation_sensitivity": "Moderate"
    },
    "MUC16": {
        "internalization_mechanism": "Moderate — transmembrane domain anchors it; EGF-domain binding triggers endocytosis",
        "recycling_after_internalization": "Moderate recycling",
        "shedding_rate": "VERY HIGH — massive ectodomain shedding (CA125) is the primary challenge. Shed CA125 acts as a massive antigen sink in ovarian cancer (serum CA125 >10,000 U/mL common). ADCs must target the proximal STALK domain (retained after shedding).",
        "biomarker_assay": "Serum CA125 (CA125/MUC16 EIA; used as PD biomarker); IHC for tumor expression. Target: membrane-proximal repeat domain (e.g., DMUC5754A targets retained stalk)",
        "proliferation_sensitivity": "Moderate"
    },
    "PSMA": {
        "internalization_mechanism": "Ligand-induced rapid internalization (clathrin-mediated; PSMA is a Type II membrane protein folate hydrolase)",
        "recycling_after_internalization": "Primarily degraded",
        "shedding_rate": "Very low (transmembrane; no known shedding)",
        "biomarker_assay": "IHC (PSMA expression by IHC); PSMA PET-CT (68Ga-PSMA-11 or 18F-DCFPyL) for in vivo imaging; serum PSA for disease monitoring",
        "proliferation_sensitivity": "Low — PSMA ADCs often use DNA-damaging payloads (cell-cycle independent)"
    },
}

# Generic template for antigens without specific data
generic_fields = {
    "internalization_mechanism": "Not specifically characterized for ADC context; estimated from receptor biology",
    "recycling_after_internalization": "Unknown — expert review required",
    "shedding_rate": "Unknown — expert review required",
    "biomarker_assay": "Standard IHC or flow cytometry; no FDA-approved CDx available unless noted",
    "proliferation_sensitivity": "Unknown — depends on payload class selected"
}

enriched = 0
generic_applied = 0
for name, props in ag.items():
    if name.startswith('_') or not isinstance(props, dict):
        continue
    if name in antigen_enrichment:
        props.update(antigen_enrichment[name])
        enriched += 1
    elif 'internalization_mechanism' not in props:
        props.update(generic_fields)
        generic_applied += 1

fp.write_text(json.dumps(rules, indent=2, ensure_ascii=False))
print(f'Enriched {enriched} antigens with full detail.')
print(f'Applied generic template to {generic_applied} antigens (marked for expert review).')
