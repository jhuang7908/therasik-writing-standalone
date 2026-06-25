import json

def enrich_data_v4():
    rules_path = 'data/adc_atlas/adc_design_rules.json'
    master_path = 'data/adc_atlas/adc_master_internal.json'
    
    with open(rules_path, 'r') as f:
        rules = json.load(f)
    
    with open(master_path, 'r') as f:
        master = json.load(f)
    
    # Enrich Antigens
    ag = rules['antigen_properties']
    
    # AFP
    ag['AFP'] = {
        "internalization_mechanism": "Internalization-dependent delivery; AFP-targeted ADCs (e.g., ACT-903) are internalized into lysosomes for payload release.",
        "recycling_after_internalization": "Low; primarily degraded in lysosomes.",
        "shedding_rate": "High (secreted protein; high serum levels in HCC).",
        "biomarker_assay": "Serum AFP levels or IHC for AFP in HCC.",
        "proliferation_sensitivity": "High.",
        "data_confidence": "high",
        "evidence_note": "ACT-903 (AFP-maytansinoid) shows potent activity in HCC models despite high circulating AFP levels.",
        "key_refs": ["PMID:37196158"]
    }
    
    # PMEL
    ag['PMEL'] = {
        "internalization_mechanism": "Rapid internalization to lysosome-related organelles (melanosomes) upon antibody binding.",
        "recycling_after_internalization": "Low; efficient trafficking to LAMP1+ compartments.",
        "shedding_rate": "Low (membrane-bound melanosomal protein).",
        "biomarker_assay": "IHC for PMEL17 (gp100).",
        "proliferation_sensitivity": "Moderate.",
        "data_confidence": "high",
        "evidence_note": "PMEL17 is a highly selective target for melanoma; antibodies show robust internalization.",
        "key_refs": ["PMID:22699451"]
    }
    
    # PODO
    ag['PODO'] = {
        "internalization_mechanism": "Internalization confirmed in preclinical models; rate is moderate and can be enhanced by antibody cross-linking.",
        "recycling_after_internalization": "Moderate.",
        "shedding_rate": "Low to moderate (soluble PDPN can be detected in some cancers).",
        "biomarker_assay": "IHC for Podoplanin (PDPN).",
        "proliferation_sensitivity": "Moderate.",
        "data_confidence": "high",
        "evidence_note": "chLpMab-based ADCs show antitumor activity in PDPN-positive tumors.",
        "key_refs": ["PMID:28332312"]
    }

    # TNF_receptor
    ag['TNF_receptor'] = {
        "internalization_mechanism": "Efficient internalization of anti-TNF/TNFR1 complexes into lysosomes; used for delivery of immunomodulatory payloads.",
        "recycling_after_internalization": "Moderate.",
        "shedding_rate": "High (soluble TNFR1/2 are common).",
        "biomarker_assay": "IHC for TNFR1 or serum TNF levels.",
        "proliferation_sensitivity": "N/A (primarily used for autoimmune/inflammatory diseases).",
        "data_confidence": "high",
        "evidence_note": "ABBV-3373 (anti-TNF-GRM ADC) demonstrates efficacy in RA models via internalization and payload release.",
        "key_refs": ["PMID:38507467"]
    }

    # Enrich Clinical Programs
    for prog in master:
        name = prog.get('canonical_name')
        if name == "AbbVie ABBV-3373":
            prog['binder_name'] = "Adalimumab-based anti-TNF"
            prog['technical_audit'] = "Targets transmembrane TNF. Uses glucocorticoid receptor modulator (GRM) payload. Phase 2 for RA."
        elif name == "Mersana XMT-1660":
            prog['binder_name'] = "Anti-B7-H4 antibody"
            prog['technical_audit'] = "Targets B7-H4. Uses Dolasynthen platform with auristatin payload."

    with open(rules_path, 'w') as f:
        json.dump(rules, f, indent=2)
    
    with open(master_path, 'w') as f:
        json.dump(master, f, indent=2)
    
    print("Enrichment v4 complete.")

if __name__ == "__main__":
    enrich_data_v4()
