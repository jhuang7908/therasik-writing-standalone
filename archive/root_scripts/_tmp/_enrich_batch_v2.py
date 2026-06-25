import json

def enrich_data():
    rules_path = 'data/adc_atlas/adc_design_rules.json'
    master_path = 'data/adc_atlas/adc_master_internal.json'
    
    with open(rules_path, 'r') as f:
        rules = json.load(f)
    
    with open(master_path, 'r') as f:
        master = json.load(f)
    
    # Enrich Antigens
    ag = rules['antigen_properties']
    
    # ROR2
    ag['ROR2'] = {
        "internalization_mechanism": "Rapid internalization via clathrin-mediated endocytosis, confirmed by functional screening of human antibody libraries.",
        "recycling_after_internalization": "Primarily lysosomal trafficking.",
        "shedding_rate": "Low.",
        "biomarker_assay": "IHC for ROR2 expression in RCC and osteosarcoma.",
        "proliferation_sensitivity": "High.",
        "data_confidence": "high",
        "evidence_note": "Functional screening identified internalizing antibodies with potent ADC activity. Target for BA3021.",
        "key_refs": ["PMID:30546250"]
    }
    
    # CD46
    ag['CD46'] = {
        "internalization_mechanism": "Efficient internalization via macropinocytosis and clathrin-mediated pathways; identified as a top internalizing target in prostate cancer.",
        "recycling_after_internalization": "Moderate recycling; significant lysosomal delivery.",
        "shedding_rate": "Low to moderate.",
        "biomarker_assay": "IHC for CD46 (overexpressed in mCRPC and NEPC).",
        "proliferation_sensitivity": "Moderate.",
        "data_confidence": "high",
        "evidence_note": "CD46 targeted by FOR46 ADC shows robust internalization and efficacy in prostate cancer models.",
        "key_refs": ["PMID:30102631"]
    }
    
    # TA-MUC1
    ag['TA-MUC1'] = {
        "internalization_mechanism": "Internalization occurs via multiple pathways; rate is significantly influenced by linker hydrophilicity (PEG linkers enhance uptake).",
        "recycling_after_internalization": "High recycling rate for MUC1-C; TA-MUC1 (Gatipotuzumab) targets tumor-specific glycoform with better internalization.",
        "shedding_rate": "High (MUC1-N terminal shedding is common).",
        "biomarker_assay": "IHC using Gatipotuzumab or similar glyco-specific antibodies.",
        "proliferation_sensitivity": "Moderate.",
        "data_confidence": "high",
        "evidence_note": "Internalization kinetics studied extensively with site-specific conjugates.",
        "key_refs": ["PMID:30906522"]
    }

    # CD228
    ag['CD228'] = {
        "internalization_mechanism": "Rapid and efficient internalization in various solid tumor types (melanoma, lung, breast).",
        "recycling_after_internalization": "Minimal recycling; efficient lysosomal degradation.",
        "shedding_rate": "Very low (GPI-anchored protein).",
        "biomarker_assay": "IHC for CD228 (Melanotransferrin).",
        "proliferation_sensitivity": "High.",
        "data_confidence": "high",
        "evidence_note": "SGN-CD228A (hL49-MMAE) demonstrates that cytotoxic activity is strictly dependent on CD228 internalization.",
        "key_refs": ["PMID:36800443"]
    }

    # CD25
    ag['CD25'] = {
        "internalization_mechanism": "Rapid internalization via the IL-2 receptor complex (clathrin-independent, dynamin-dependent).",
        "recycling_after_internalization": "Low; primarily targeted to late endosomes/lysosomes.",
        "shedding_rate": "Moderate (soluble CD25 can be detected in serum).",
        "biomarker_assay": "Flow cytometry or IHC for CD25 (IL-2Ra).",
        "proliferation_sensitivity": "High (T-cell malignancies).",
        "data_confidence": "high",
        "evidence_note": "Target for Camidanlumab tesirine (ADCT-301). Rapid internalization is a hallmark of IL-2R signaling.",
        "key_refs": ["PMID:28935674"]
    }

    # CD37
    ag['CD37'] = {
        "internalization_mechanism": "Moderate to rapid internalization; tetraspanin family members often facilitate rapid endocytosis upon cross-linking.",
        "recycling_after_internalization": "Moderate.",
        "shedding_rate": "Low.",
        "biomarker_assay": "IHC or Flow for CD37 in B-cell lymphomas.",
        "proliferation_sensitivity": "High.",
        "data_confidence": "high",
        "evidence_note": "Naratuximab emtansine (IMGN529) relies on CD37 internalization for payload delivery.",
        "key_refs": ["PMID:24658681"]
    }

    # CD46
    ag['CD46'] = {
        "internalization_mechanism": "Efficient internalization via multiple pathways; identified as a top internalizing target in prostate cancer.",
        "recycling_after_internalization": "Moderate recycling; significant lysosomal delivery.",
        "shedding_rate": "Low to moderate.",
        "biomarker_assay": "IHC for CD46 (overexpressed in mCRPC and NEPC).",
        "proliferation_sensitivity": "Moderate.",
        "data_confidence": "high",
        "evidence_note": "CD46 targeted by FOR46 ADC shows robust internalization and efficacy in prostate cancer models.",
        "key_refs": ["PMID:30102631"]
    }

    # Enrich Clinical Programs
    for prog in master:
        name = prog.get('canonical_name')
        if name == "Seagen SGN-CD228A":
            prog['binder_name'] = "hL49 (Humanized anti-CD228 IgG1)"
            prog['technical_audit'] = "Humanized IgG1 antibody (clone hL49) targeting CD228. Evidence: PMID:36800443."
        elif name == "Kelun-Biotech A166":
            prog['binder_name'] = "Trastuzumab botidotin (Anti-HER2)"
            prog['technical_audit'] = "HER2-targeted ADC using trastuzumab as the binder. Approved in China for HER2+ BC."
        elif name == "BNT326":
            prog['binder_name'] = "Anti-HER3 antibody (YL202)"
            prog['technical_audit'] = "Targets HER3 (ERBB3). Developed by MediLink/BioNTech."
        elif name == "MediLink YL205":
            prog['binder_name'] = "Anti-NaPi-2b antibody"
            prog['technical_audit'] = "Targets NaPi-2b. Uses MediLink TMALIN platform."

    with open(rules_path, 'w') as f:
        json.dump(rules, f, indent=2)
    
    with open(master_path, 'w') as f:
        json.dump(master, f, indent=2)
    
    print("Enrichment complete.")

if __name__ == "__main__":
    enrich_data()
