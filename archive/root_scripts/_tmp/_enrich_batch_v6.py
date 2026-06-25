import json

def enrich_data_v6():
    rules_path = 'data/adc_atlas/adc_design_rules.json'
    master_path = 'data/adc_atlas/adc_master_internal.json'
    
    with open(rules_path, 'r') as f:
        rules = json.load(f)
    
    with open(master_path, 'r') as f:
        master = json.load(f)
    
    # Enrich Clinical Programs with specific technical details
    for prog in master:
        name = prog.get('canonical_name')
        
        # Hengrui
        if name == "Hengrui SHR-A1904":
            prog['linker_name'] = "mc-Gly-Gly-Phe-Gly (GGFG)"
            prog['payload_name'] = "Rezetecan (SHR169106)"
            prog['dar_mean'] = 4.0
            prog['technical_audit'] = "Targets CLDN18.2. Uses Mc-GGFG linker with TOP1i payload. Evidence: Nature Medicine 2025."
            
        # Keymed / AstraZeneca
        elif name == "CMG901":
            prog['linker_name'] = "mc-val-cit-PABC"
            prog['payload_name'] = "MMAE"
            prog['dar_mean'] = 4.0
            prog['technical_audit'] = "Targets CLDN18.2. Protease-cleavable vc-PABC linker with MMAE. Licensed to AZ."
            
        # Lepu Biopharma
        elif name == "Lepu Biopharma MRG002":
            prog['linker_name'] = "vc-PABC"
            prog['payload_name'] = "MMAE"
            prog['dar_mean'] = 3.6
            prog['technical_audit'] = "Targets HER2. Cleavable vc-PABC linker with MMAE payload."
        elif name == "Lepu Biopharma MRG003":
            prog['linker_name'] = "vc-PABC"
            prog['payload_name'] = "MMAE"
            prog['dar_mean'] = 3.8
            prog['technical_audit'] = "Targets EGFR. Uses standard vc-PABC MMAE platform."
            
        # DualityBio / BioNTech
        elif name == "BNT323":
            prog['linker_name'] = "Cleavable peptide (DITAC platform)"
            prog['payload_name'] = "P1003 (TOP1i)"
            prog['dar_mean'] = 8.0
            prog['technical_audit'] = "Targets HER2. DITAC platform uses proprietary TOP1i payload with bystander effect."
        elif name == "BNT324":
            prog['linker_name'] = "Cleavable peptide (DITAC platform)"
            prog['payload_name'] = "Proprietary TOP1i"
            prog['dar_mean'] = 8.0
            prog['technical_audit'] = "Targets B7-H3. DITAC platform candidate."
        elif name == "BNT325":
            prog['linker_name'] = "Cleavable peptide (DITAC platform)"
            prog['payload_name'] = "Proprietary TOP1i"
            prog['dar_mean'] = 8.0
            prog['technical_audit'] = "Targets TROP-2. DITAC platform candidate."
            
        # Innovent
        elif name == "IBI343":
            prog['linker_name'] = "Cleavable peptide (DXd-like)"
            prog['payload_name'] = "Proprietary TOP1i"
            prog['dar_mean'] = 8.0
            prog['technical_audit'] = "Targets CLDN18.2. High DAR TOP1i ADC, fast follower to Enhertu."
            
        # SystImmune / BMS
        elif name == "BL-B01D1":
            prog['linker_name'] = "Cleavable peptide"
            prog['payload_name'] = "Ed-04 (TOP1i)"
            prog['dar_mean'] = 8.0
            prog['technical_audit'] = "Bispecific EGFRxHER3 ADC. Uses proprietary TOP1i payload Ed-04."

    with open(rules_path, 'w') as f:
        json.dump(rules, f, indent=2)
    
    with open(master_path, 'w') as f:
        json.dump(master, f, indent=2)
    
    print("Enrichment v6 complete.")

if __name__ == "__main__":
    enrich_data_v6()
