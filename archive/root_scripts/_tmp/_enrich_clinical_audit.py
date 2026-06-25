"""
Enrich Clinical Programs with detailed technical audits and failure analysis.
Focus on key programs: Enhertu, Kadcyla, Trodelvy, Padcev, Rova-T, etc.
"""
import json, pathlib

fp = pathlib.Path('data/adc_atlas/adc_master_internal.json')
master = json.loads(fp.read_text())

enrichment = {
    "Trastuzumab deruxtecan": {
        "technical_audit": "Gold standard for high-DAR (8.0) strategy. Hydrophilic GGFG linker prevents aggregation. DXd payload is cell-cycle independent and highly membrane-permeable, enabling potent bystander effect in HER2-low tumors.",
        "failure_analysis": {"is_failed": False}
    },
    "Trastuzumab emtansine": {
        "technical_audit": "First-generation non-cleavable linker ADC. Relies on complete lysosomal degradation of antibody. DM1-lysine metabolite is active but lacks bystander effect, limiting efficacy in heterogeneous tumors.",
        "failure_analysis": {"is_failed": False}
    },
    "Sacituzumab govitecan": {
        "technical_audit": "High-DAR (7.6) with pH-sensitive CL2A linker. Rapid release of SN-38 in acidic endosomes and tumor microenvironment. High bystander effect compensates for TROP-2 heterogeneity.",
        "failure_analysis": {"is_failed": False}
    },
    "Brentuximab vedotin": {
        "technical_audit": "Benchmark for vc-PABC-MMAE platform. DAR 4.0 stochastic conjugation. Highly effective in CD30+ hematological malignancies due to rapid internalization.",
        "failure_analysis": {"is_failed": False}
    },
    "Rovalpituzumab tesirine": {
        "technical_audit": "PBD-dimer payload at DAR 2.0. Failed due to excessive toxicity (VOD, pleural effusion) and lack of survival benefit. PBD class requires extremely low DAR or site-specific conjugation to improve therapeutic index.",
        "failure_analysis": {
            "is_failed": True,
            "reason_category": "safety/toxicity",
            "internal_insight": "PBD payload at DAR 2 was too toxic for solid tumor (SCLC) patients. Off-tumor neural tissue expression of DLL3 compounded safety issues."
        }
    },
    "Indatuximab ravtansine": {
        "technical_audit": "DM4 payload on CD138 target. Failed Phase 2 monotherapy. High shedding of CD138 (syndecan-1) acted as a massive antigen sink, reducing effective dose reaching tumor cells.",
        "failure_analysis": {
            "is_failed": True,
            "reason_category": "efficacy/antigen_sink",
            "internal_insight": "Massive ectodomain shedding of CD138 in myeloma patients neutralized the ADC in circulation."
        }
    },
    "Tusamitamab ravtansine": {
        "technical_audit": "DM4 payload on CEACAM5. Failed Phase 3 CARMEN-LC03 trial. Modest efficacy benefit compared to docetaxel. CEACAM5 shedding and partial recycling may have limited intracellular payload accumulation.",
        "failure_analysis": {
            "is_failed": True,
            "reason_category": "efficacy",
            "internal_insight": "Failed to meet PFS/OS endpoints in NSCLC Phase 3. Competition from Dato-DXd (higher DAR, bystander effect) likely reduced commercial viability."
        }
    },
    "Depatuxizumab mafodotin": {
        "technical_audit": "MMAF payload on EGFR (ABT-414). Failed Phase 3 INTELLANCE-1 in GBM. MMAF lacks bystander effect; GBM is highly heterogeneous, leaving antigen-negative cells untouched.",
        "failure_analysis": {
            "is_failed": True,
            "reason_category": "efficacy/heterogeneity",
            "internal_insight": "Lack of bystander effect in a highly heterogeneous tumor (GBM) was the primary driver of failure."
        }
    }
}

updated = 0
for prog in master:
    name = prog.get('canonical_name')
    if name in enrichment:
        prog.update(enrichment[name])
        updated += 1

fp.write_text(json.dumps(master, indent=2, ensure_ascii=False))
print(f'Enriched {updated} clinical programs with detailed audit/failure analysis.')
