import json

def enrich_data_v5():
    rules_path = 'data/adc_atlas/adc_design_rules.json'
    master_path = 'data/adc_atlas/adc_master_internal.json'
    
    with open(rules_path, 'r') as f:
        rules = json.load(f)
    
    with open(master_path, 'r') as f:
        master = json.load(f)
    
    # Enrich Clinical Programs
    for prog in master:
        name = prog.get('canonical_name')
        
        # Hengrui
        if name == "Hengrui SHR-A1912":
            prog['binder_name'] = "Anti-CD79b antibody"
            prog['linker_name'] = "Cleavable peptide linker"
            prog['payload_name'] = "Topoisomerase I inhibitor"
            prog['technical_audit'] = "Targets CD79b. Phase 3 for B-NHL (NCT06104553)."
        elif name == "Hengrui SHR-A2009":
            prog['binder_name'] = "Ruzaltatug rezetecan (Anti-HER3)"
            prog['linker_name'] = "Maleimidocaproyl tetrapeptide (GGFG)"
            prog['payload_name'] = "SHR169106 (TOP1i)"
            prog['dar_mean'] = 4
            prog['technical_audit'] = "Targets HER3. Fast Track for NSCLC. Evidence: PMID:36045843."
        elif name == "Hengrui SHR-A1811":
            prog['binder_name'] = "Trastuzumab-based anti-HER2"
            prog['linker_name'] = "mc-Gly-Gly-Phe-Gly"
            prog['payload_name'] = "SHR9265 (TOP1i)"
            prog['dar_mean'] = 5.7
            prog['technical_audit'] = "Next-gen HER2 ADC. Phase 3. Evidence: PMID:40569929."
            
        # Kelun-Biotech
        elif name == "Kelun-Biotech A166":
            prog['binder_name'] = "Trastuzumab botidotin (Anti-HER2)"
            prog['linker_name'] = "Valine-Citrulline (vc)"
            prog['payload_name'] = "Duostatin-5 (MMAF derivative)"
            prog['dar_mean'] = 2
            prog['technical_audit'] = "Site-specific HER2 ADC. NDA accepted in China (2025)."
        elif name == "Kelun-Biotech SKB410":
            prog['binder_name'] = "MK-3120 (Anti-Nectin-4)"
            prog['technical_audit'] = "Targets Nectin-4. Collaboration with MSD (MK-3120)."
            
        # Bio-Thera
        elif name == "Bio-Thera BAT8001":
            prog['binder_name'] = "Anti-HER2 antibody"
            prog['linker_name'] = "6-maleimidocaproic acid (non-cleavable)"
            prog['payload_name'] = "Maytansinoid (DM1)"
            prog['dar_mean'] = 3.5
            prog['technical_audit'] = "Targets HER2. Terminated in Phase 3."
        elif name == "Bio-Thera BAT8003":
            prog['binder_name'] = "Anti-Trop2 antibody"
            prog['linker_name'] = "Non-cleavable (Batansine platform)"
            prog['payload_name'] = "Batansine (Maytansinoid)"
            prog['technical_audit'] = "Targets Trop2. Discontinued at Phase 1."
            
        # MediLink
        elif name == "MediLink YL211":
            prog['binder_name'] = "Anti-c-Met antibody"
            prog['technical_audit'] = "Targets c-Met. Uses TMALIN platform. Licensed to Roche (2024)."
            
        # CSPC
        elif name == "CSPC CPO102":
            prog['binder_name'] = "SYSA-1801 (Anti-CLDN18.2)"
            prog['linker_name'] = "PEG3-Val-Cit-PABC"
            prog['payload_name'] = "MMAE"
            prog['technical_audit'] = "Targets CLDN18.2. Developed by Conjupro/CSPC. Phase 1 (NCT05043987)."
            
        # AbbVie
        elif name == "AbbVie ABBV-400":
            prog['binder_name'] = "Telisotuzumab adizutecan (Temab-A)"
            prog['payload_name'] = "Adizutecan (TOP1i)"
            prog['technical_audit'] = "Targets c-Met. Phase 3 for CRC. Evidence: NCT05029882."
            
        # Seagen
        elif name == "Seagen SGN-B6A":
            prog['binder_name'] = "Anti-Integrin beta-6 antibody"
            prog['payload_name'] = "MMAE"
            prog['technical_audit'] = "Targets Integrin beta-6. Vedotin ADC. Evidence: PMID:37619980."

    with open(rules_path, 'w') as f:
        json.dump(rules, f, indent=2)
    
    with open(master_path, 'w') as f:
        json.dump(master, f, indent=2)
    
    print("Enrichment v5 complete.")

if __name__ == "__main__":
    enrich_data_v5()
