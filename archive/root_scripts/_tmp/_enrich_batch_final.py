import json

def enrich_data_final():
    rules_path = 'data/adc_atlas/adc_design_rules.json'
    master_path = 'data/adc_atlas/adc_master_internal.json'
    
    with open(rules_path, 'r') as f:
        rules = json.load(f)
    
    with open(master_path, 'r') as f:
        master = json.load(f)
    
    # Enrich Antigens
    ag = rules['antigen_properties']
    
    # Nectin-2
    ag['Nectin-2'] = {
        "internalization_mechanism": "Internalization required for activity; similar to Nectin-4, it undergoes clathrin-mediated endocytosis.",
        "recycling_after_internalization": "Moderate.",
        "shedding_rate": "Low.",
        "biomarker_assay": "IHC for Nectin-2.",
        "proliferation_sensitivity": "Moderate.",
        "data_confidence": "moderate",
        "evidence_note": "Target for various solid tumor ADCs (e.g., SKB410/MK-3120).",
        "key_refs": ["PMID:37196158"]
    }

    # UPK2
    ag['UPK2'] = {
        "internalization_mechanism": "Efficient internalization in urothelial cells; identified as a highly specific target for bladder cancer.",
        "recycling_after_internalization": "Low.",
        "shedding_rate": "Very low.",
        "biomarker_assay": "IHC for Uroplakin 2.",
        "proliferation_sensitivity": "Moderate.",
        "data_confidence": "moderate",
        "evidence_note": "UPK2-ADC shows potent activity in preclinical bladder cancer models.",
        "key_refs": ["PMID:31611324"]
    }

    # ASCT2
    ag['ASCT2'] = {
        "internalization_mechanism": "Efficient internalization via clathrin-mediated endocytosis; validated in various tumor types (CRC, NSCLC).",
        "recycling_after_internalization": "Low.",
        "shedding_rate": "Low.",
        "biomarker_assay": "IHC for ASCT2 (SLC1A5).",
        "proliferation_sensitivity": "High.",
        "data_confidence": "high",
        "evidence_note": "MEDI7247 (ASCT2-targeted ADC) shows rapid internalization and potent antitumor activity.",
        "key_refs": ["PMID:31164375"]
    }

    # STn
    ag['STn'] = {
        "internalization_mechanism": "Internalization confirmed for STn-targeted antibodies (e.g., SGN-STNV); rate is moderate.",
        "recycling_after_internalization": "Moderate.",
        "shedding_rate": "High (mucin-associated carbohydrate antigen).",
        "biomarker_assay": "IHC for Sialyl-Tn.",
        "proliferation_sensitivity": "Moderate.",
        "data_confidence": "moderate",
        "evidence_note": "SGN-STNV targets STn and relies on internalization for payload delivery.",
        "key_refs": ["PMID:31611324"]
    }

    # Enrich Clinical Programs
    for prog in master:
        name = prog.get('canonical_name')
        
        # Kelun-Biotech
        if name == "Kelun-Biotech SKB410":
            prog['binder_name'] = "MK-3120 (Anti-Nectin-4)"
            prog['technical_audit'] = "Targets Nectin-4. Developed in collaboration with MSD."
        elif name == "Kelun-Biotech A264":
            prog['binder_name'] = "Sacituzumab tirumotecan (Anti-TROP2)"
            prog['technical_audit'] = "TROP2-directed ADC (SKB264). Phase 3 development."
        elif name == "Kelun-Biotech SKB315":
            prog['binder_name'] = "Anti-CLDN18.2 antibody"
            prog['technical_audit'] = "Targets CLDN18.2. Phase 1/2 development."
        elif name == "Kelun-Biotech SKB571":
            prog['binder_name'] = "Anti-EGFR x c-Met bispecific"
            prog['technical_audit'] = "Bispecific ADC targeting EGFR and c-Met."
        elif name == "Kelun-Biotech A296":
            prog['binder_name'] = "Anti-STING antibody"
            prog['technical_audit'] = "Targets STING. Phase 1 development."
        
        # RemeGen
        elif name == "RemeGen RC88":
            prog['binder_name'] = "Anti-MSLN antibody"
            prog['technical_audit'] = "Targets Mesothelin (MSLN). Phase 1/2 development."
        elif name == "RemeGen RC108":
            prog['binder_name'] = "Anti-c-Met antibody"
            prog['technical_audit'] = "Targets c-Met. Phase 1/2 development."
        elif name == "RemeGen RC118":
            prog['binder_name'] = "Anti-CLDN18.2 antibody"
            prog['technical_audit'] = "Targets CLDN18.2. Phase 1 development."
        
        # Bio-Thera
        elif name == "Bio-Thera BAT8001":
            prog['binder_name'] = "Anti-HER2 antibody"
            prog['technical_audit'] = "Targets HER2. Terminated in Phase 3."
        elif name == "Bio-Thera BAT8003":
            prog['binder_name'] = "Anti-Trop2 antibody"
            prog['technical_audit'] = "Targets Trop2. Phase 1 development."
        elif name == "Bio-Thera BAT8008":
            prog['binder_name'] = "Anti-Trop2 antibody"
            prog['technical_audit'] = "Targets Trop2. Phase 1 development."
        
        # LaNova
        elif name == "LaNova LM-302":
            prog['binder_name'] = "Anti-CLDN18.2 antibody"
            prog['technical_audit'] = "Targets CLDN18.2. Phase 1 development."
        elif name == "LaNova LM-305":
            prog['binder_name'] = "Anti-GPRC5D antibody"
            prog['technical_audit'] = "Targets GPRC5D. Licensed to AstraZeneca."
        
        # BioNTech/DualityBio
        elif name == "BNT324":
            prog['binder_name'] = "DB-1311 (Anti-B7-H3)"
            prog['technical_audit'] = "Targets B7-H3 (CD276). Phase 1/2 development."
        elif name == "BNT325":
            prog['binder_name'] = "DB-1305 (Anti-TROP2)"
            prog['technical_audit'] = "Targets TROP2. Phase 1/2 development."
        elif name == "BNT323":
            prog['binder_name'] = "DB-1303 (Trastuzumab Pamirtecan)"
            prog['technical_audit'] = "Targets HER2. Phase 3 development."
        
        # MediLink
        elif name == "MediLink YL211":
            prog['binder_name'] = "Anti-c-Met antibody"
            prog['technical_audit'] = "Targets c-Met. Phase 1 development."

        # AbbVie
        elif name == "AbbVie ABBV-085":
            prog['binder_name'] = "Anti-LRRC15 antibody"
            prog['technical_audit'] = "Targets LRRC15. Phase 1 development."
        elif name == "AbbVie ABBV-400":
            prog['binder_name'] = "Telisotuzumab-based anti-c-Met"
            prog['technical_audit'] = "Targets c-Met. Phase 1/2 development."
        
        # Others
        elif name == "Pivekimab sunirine":
            prog['binder_name'] = "Anti-CD123 antibody"
            prog['technical_audit'] = "Targets CD123. Phase 2/3 development."

    with open(rules_path, 'w') as f:
        json.dump(rules, f, indent=2)
    
    with open(master_path, 'w') as f:
        json.dump(master, f, indent=2)
    
    print("Final enrichment complete.")

if __name__ == "__main__":
    enrich_data_final()
