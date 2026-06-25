import json

def enrich_data_final_v2():
    rules_path = 'data/adc_atlas/adc_design_rules.json'
    master_path = 'data/adc_atlas/adc_master_internal.json'
    
    with open(rules_path, 'r') as f:
        rules = json.load(f)
    
    with open(master_path, 'r') as f:
        master = json.load(f)
    
    # Enrich Clinical Programs
    for prog in master:
        name = prog.get('canonical_name')
        
        if name == "Hengrui SHR-A1912":
            prog['binder_name'] = "Anti-CD79b antibody"
            prog['technical_audit'] = "Targets CD79b. Developed by Hengrui for B-NHL."
        elif name == "Hengrui SHR-A2009":
            prog['binder_name'] = "Anti-HER3 antibody"
            prog['technical_audit'] = "Targets HER3. Uses Top I inhibitor payload."
        elif name == "Seagen SGN-STNV":
            prog['binder_name'] = "Anti-STn antibody"
            prog['technical_audit'] = "Targets Sialyl-Tn (STn) antigen. Terminated in Phase 1 (2024)."

    with open(rules_path, 'w') as f:
        json.dump(rules, f, indent=2)
    
    with open(master_path, 'w') as f:
        json.dump(master, f, indent=2)
    
    print("Final enrichment v2 complete.")

if __name__ == "__main__":
    enrich_data_final_v2()
