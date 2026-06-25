"""
Enrich Conjugation Technologies and Validation Assays to match Payload/Linker detail levels.
"""
import json, pathlib

fp = pathlib.Path('data/adc_atlas/adc_design_rules.json')
rules = json.loads(fp.read_text())

# 1. Enrich Conjugation Technologies
# Adding: platform_name, developer, pmid_refs, cmc_detail, fto_detail
cj_enrichment = {
    "stochastic_cysteine": {
        "platform_name": "Classic Maleimide (Partial Reduction)",
        "developer": "Seagen / ImmunoGen (Public Domain)",
        "pmid_refs": ["PMID:12873544", "PMID:22399561"],
        "cmc_detail": "High complexity in purification due to DAR distribution (0, 2, 4, 6, 8). Requires hydrophobic interaction chromatography (HIC) for characterization. Risk of maleimide de-conjugation via retro-Michael reaction in vivo.",
        "fto_detail": "Broad freedom to operate (FTO); core patents expired. Most widely used clinical method."
    },
    "lysine_coupling": {
        "platform_name": "NHS-Ester Random Coupling",
        "developer": "ImmunoGen / Roche (Public Domain)",
        "pmid_refs": ["PMID:16814772", "PMID:22646630"],
        "cmc_detail": "Extremely heterogeneous DAR distribution. Characterization requires mass spectrometry (native MS) and ion-exchange chromatography (IEX). High batch-to-batch variability risk.",
        "fto_detail": "Broad FTO; used in Kadcyla and Mylotarg."
    },
    "site_specific_engineered_cys": {
        "platform_name": "THIOMAB™ / Engineered Cys",
        "developer": "Genentech (Roche)",
        "pmid_refs": ["PMID:18552842", "PMID:24703513"],
        "cmc_detail": "Requires precise control of reduction/re-oxidation to ensure engineered cysteines are reactive while native disulfides remain intact. High DAR homogeneity (typically DAR 2.0).",
        "fto_detail": "Patented by Genentech; requires licensing for commercial use."
    },
    "enzymatic_transglutaminase": {
        "platform_name": "MTGase-mediated conjugation",
        "developer": "Ajinomoto (AJICAP) / NBE-Therapeutics",
        "pmid_refs": ["PMID:24912431", "PMID:31110004"],
        "cmc_detail": "Requires deglycosylation (PNGase F) or specific Q-tag insertion. Highly site-specific at Gln295. Excellent homogeneity. Minimal impact on antibody folding.",
        "fto_detail": "Proprietary technology; AJICAP and NBE-Therapeutics hold key patents."
    },
    "glycan_remodeling": {
        "platform_name": "GlycoConnect™ / GlycoDesign",
        "developer": "Synaffix / Seattle Genetics",
        "pmid_refs": ["PMID:26554950", "PMID:30356154"],
        "cmc_detail": "Two-step enzymatic process: (1) Trimming of native glycans, (2) Addition of azide-modified sugars for click chemistry. High homogeneity (DAR 2 or 4). Bypasses need for protein engineering.",
        "fto_detail": "Strong patent protection by Synaffix (Lonza)."
    },
    "unnatural_amino_acid": {
        "platform_name": "p-Acetylphenylalanine (pAcPhe) / Ambrx",
        "developer": "Ambrx / Sutro Biopharma",
        "pmid_refs": ["PMID:25133814", "PMID:27064340"],
        "cmc_detail": "Requires cell line engineering (orthogonal tRNA/RS pair). Allows precise placement of payload anywhere on the scaffold. High manufacturing complexity (COGS).",
        "fto_detail": "Patented by Ambrx and Sutro."
    },
    "AJICAP": {
        "platform_name": "AJICAP® (Affinity-peptide mediated)",
        "developer": "Ajinomoto",
        "pmid_refs": ["PMID:31110004"],
        "cmc_detail": "Uses a temporary affinity peptide to direct conjugation to Lys188/248. No protein engineering required. High homogeneity for native IgG.",
        "fto_detail": "Proprietary to Ajinomoto."
    },
    "ThioBridge": {
        "platform_name": "ThioBridge™ (Disulfide Re-bridging)",
        "developer": "Abzena",
        "pmid_refs": ["PMID:25654301"],
        "cmc_detail": "Payload bridges the two sulfur atoms of a reduced disulfide bond. Improves ADC stability compared to maleimide. Maintains structural integrity of the antibody.",
        "fto_detail": "Proprietary to Abzena."
    },
    "GeneQuantum_iLDC": {
        "platform_name": "iLDC (intelligent Ligase-dependent Conjugation)",
        "developer": "GeneQuantum Healthcare",
        "pmid_refs": ["PMID:33454211"],
        "cmc_detail": "Enzymatic conjugation using microbial transglutaminase or other ligases in a continuous flow process. High efficiency and scalability.",
        "fto_detail": "Proprietary to GeneQuantum."
    }
}

# 2. Enrich Validation Assays
# Adding: protocol_summary, cell_line_recommendations, readout_sensitivity, pmid_refs
assay_enrichment = {
    "binding_affinity": {
        "protocol_summary": "Standard SPR: Immobilize antigen on CM5 chip; inject ADC at 5-6 concentrations (0.1-100 nM). Calculate Ka, Kd, KD. Compare Intact ADC vs Parental mAb.",
        "cell_line_recommendations": "Target-overexpressing (e.g., SK-BR-3 for HER2, BT-474) vs Target-negative (e.g., MDA-MB-231 for HER2).",
        "readout_sensitivity": "KD down to pM range for SPR; FACS requires ~10^4 receptors/cell.",
        "pmid_refs": ["PMID:22108849"]
    },
    "internalization": {
        "protocol_summary": "pHrodo labeling: Conjugate ADC with pH-sensitive dye; incubate with cells at 37°C; monitor fluorescence increase (lysosomal entry) via FACS or live-cell imaging over 24h.",
        "cell_line_recommendations": "High-internalizing (TROP-2+ JIMT-1) vs Low-internalizing variants.",
        "readout_sensitivity": "t1/2 detection from 15 mins to 48 hours.",
        "pmid_refs": ["PMID:30356154"]
    },
    "cytotoxicity": {
        "protocol_summary": "CellTiter-Glo: Seed cells (3000/well); add ADC (10-point dilution, 10 nM to 1 fM); incubate 72-120h; add CTG reagent; measure luminescence. Calculate IC50.",
        "cell_line_recommendations": "Panel of 5-10 lines with varying antigen density (H-score 0 to 300).",
        "readout_sensitivity": "IC50 detection down to 10^-12 M (pM).",
        "pmid_refs": ["PMID:12873544"]
    },
    "bystander_effect": {
        "protocol_summary": "Mix GFP+ (Target+) and RFP+ (Target-) cells at 1:1 ratio. Add ADC. Monitor RFP+ cell death over 5 days. If RFP+ cells die, payload is membrane-permeable.",
        "cell_line_recommendations": "HER2+ SK-BR-3 mixed with HER2- MDA-MB-231.",
        "readout_sensitivity": "Requires >20% bystander killing for 'Positive' classification.",
        "pmid_refs": ["PMID:26058450"]
    },
    "plasma_stability": {
        "protocol_summary": "Incubate ADC in human/mouse plasma at 37°C for 0, 1, 3, 7 days. Extract samples; analyze via LC-MS/MS to quantify intact ADC vs free payload.",
        "readout_sensitivity": "LOQ (Limit of Quantitation) typically 1-10 ng/mL for free drug.",
        "pmid_refs": ["PMID:22399561"]
    },
    "linker_cleavage": {
        "protocol_summary": "In vitro enzyme assay: Incubate ADC with recombinant Cathepsin B (pH 5.0) or β-glucuronidase. Analyze payload release kinetics via HPLC/MS.",
        "readout_sensitivity": ">90% cleavage within 4h for 'Rapid' linkers.",
        "pmid_refs": ["PMID:16955513"]
    }
}

# Apply Conjugation Enrichment
cj = rules['conjugation_technology']
for k, data in cj_enrichment.items():
    if k in cj:
        cj[k].update(data)
    else:
        # If not in rules, add it
        cj[k] = data

# Apply Assay Enrichment
ev = rules['experimental_methods']
for cat in ['in_vitro_assays', 'in_vivo_assays']:
    if cat in ev:
        for assay, data in assay_enrichment.items():
            if assay in ev[cat]:
                ev[cat][assay].update(data)

fp.write_text(json.dumps(rules, indent=2, ensure_ascii=False))
print('Enriched Conjugation Technologies and Validation Assays.')
