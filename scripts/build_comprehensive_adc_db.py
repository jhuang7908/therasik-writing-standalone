import json
import os
from pathlib import Path

DATA_DIR = Path("data/adc_atlas")

def load_json(filename):
    path = DATA_DIR / filename
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return [] if "master" in filename or "components" in filename or "platforms" in filename or "patents" in filename else {}

def save_json(data, filename):
    with open(DATA_DIR / filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def expand_targets(rules):
    antigens = rules.get("antigen_properties", {})
    
    # Massive target expansion
    new_targets = {
        "MSLN": {"expression": "solid_tumor", "density": "high", "heterogeneity": "moderate", "internalization_rate": "moderate", "normal_tissue_expression": "low (pleura, peritoneum)", "on_target_off_tumor_risk": "low"},
        "MUC1": {"expression": "solid_tumor", "density": "high", "heterogeneity": "high", "internalization_rate": "moderate", "normal_tissue_expression": "moderate (epithelia)", "on_target_off_tumor_risk": "moderate"},
        "MUC16": {"expression": "solid_tumor", "density": "high", "heterogeneity": "high", "internalization_rate": "low", "normal_tissue_expression": "low", "on_target_off_tumor_risk": "low"},
        "ROR1": {"expression": "liquid_solid", "density": "moderate", "heterogeneity": "low", "internalization_rate": "high", "normal_tissue_expression": "very_low", "on_target_off_tumor_risk": "low"},
        "ROR2": {"expression": "solid_tumor", "density": "moderate", "heterogeneity": "moderate", "internalization_rate": "moderate", "normal_tissue_expression": "very_low", "on_target_off_tumor_risk": "low"},
        "ENPP3": {"expression": "solid_tumor", "density": "high", "heterogeneity": "low", "internalization_rate": "high", "normal_tissue_expression": "low (kidney)", "on_target_off_tumor_risk": "low"},
        "CD70": {"expression": "liquid_solid", "density": "moderate", "heterogeneity": "high", "internalization_rate": "high", "normal_tissue_expression": "very_low (activated T/B cells)", "on_target_off_tumor_risk": "low"},
        "CD228": {"expression": "solid_tumor", "density": "high", "heterogeneity": "moderate", "internalization_rate": "high", "normal_tissue_expression": "low", "on_target_off_tumor_risk": "low"},
        "FAP": {"expression": "solid_tumor", "density": "high (stroma)", "heterogeneity": "low", "internalization_rate": "low", "normal_tissue_expression": "low (healing wounds)", "on_target_off_tumor_risk": "low"},
        "LGR5": {"expression": "solid_tumor", "density": "moderate", "heterogeneity": "high", "internalization_rate": "high", "normal_tissue_expression": "moderate (GI stem cells)", "on_target_off_tumor_risk": "high"},
        "LRRC15": {"expression": "solid_tumor", "density": "high (stroma)", "heterogeneity": "low", "internalization_rate": "moderate", "normal_tissue_expression": "very_low", "on_target_off_tumor_risk": "low"},
        "SLITRK6": {"expression": "solid_tumor", "density": "moderate", "heterogeneity": "moderate", "internalization_rate": "high", "normal_tissue_expression": "low (neural)", "on_target_off_tumor_risk": "moderate"},
        "UPK2": {"expression": "solid_tumor", "density": "high", "heterogeneity": "low", "internalization_rate": "moderate", "normal_tissue_expression": "moderate (urothelium)", "on_target_off_tumor_risk": "moderate"},
        "NaPi2b": {"expression": "solid_tumor", "density": "high", "heterogeneity": "moderate", "internalization_rate": "moderate", "normal_tissue_expression": "moderate (lung, GI)", "on_target_off_tumor_risk": "moderate"},
        "LIV-1": {"expression": "solid_tumor", "density": "moderate_to_high", "heterogeneity": "moderate", "internalization_rate": "high", "normal_tissue_expression": "low", "on_target_off_tumor_risk": "low"},
        "GCC": {"expression": "solid_tumor", "density": "high", "heterogeneity": "low", "internalization_rate": "high", "normal_tissue_expression": "moderate (GI)", "on_target_off_tumor_risk": "moderate"},
        "ASCT2": {"expression": "solid_tumor", "density": "high", "heterogeneity": "low", "internalization_rate": "high", "normal_tissue_expression": "moderate", "on_target_off_tumor_risk": "moderate"},
        "B7-H4": {"expression": "solid_tumor", "density": "high", "heterogeneity": "low", "internalization_rate": "moderate", "normal_tissue_expression": "very_low", "on_target_off_tumor_risk": "low"},
        "CD25": {"expression": "liquid_tumor", "density": "high", "heterogeneity": "low", "internalization_rate": "high", "normal_tissue_expression": "moderate (Tregs)", "on_target_off_tumor_risk": "moderate"},
        "CD46": {"expression": "liquid_solid", "density": "high", "heterogeneity": "low", "internalization_rate": "high", "normal_tissue_expression": "high (ubiquitous)", "on_target_off_tumor_risk": "high"},
        "CD37": {"expression": "liquid_tumor", "density": "high", "heterogeneity": "low", "internalization_rate": "high", "normal_tissue_expression": "moderate (B cells)", "on_target_off_tumor_risk": "low"},
        "CD138": {"expression": "liquid_tumor", "density": "high", "heterogeneity": "low", "internalization_rate": "high", "normal_tissue_expression": "low (epithelia)", "on_target_off_tumor_risk": "low"},
        "FcRH5": {"expression": "liquid_tumor", "density": "moderate", "heterogeneity": "low", "internalization_rate": "high", "normal_tissue_expression": "low (B cells)", "on_target_off_tumor_risk": "low"},
        "GPRC5D": {"expression": "liquid_tumor", "density": "high", "heterogeneity": "low", "internalization_rate": "high", "normal_tissue_expression": "low (hair follicles)", "on_target_off_tumor_risk": "moderate"},
        "CLL-1": {"expression": "liquid_tumor", "density": "moderate", "heterogeneity": "low", "internalization_rate": "high", "normal_tissue_expression": "low (myeloid cells)", "on_target_off_tumor_risk": "low"}
    }
    
    for k, v in new_targets.items():
        if k not in antigens:
            antigens[k] = v
            
    rules["antigen_properties"] = antigens
    return rules

def expand_payloads(rules):
    pcls = rules.get("payload_classification", {})
    
    # Add new payload classes
    new_classes = {
        "rna_polymerase_ii_inhibitors": {
            "members": ["Amanitin", "Amatoxin"],
            "potency_range_pM": [10, 100],
            "mechanism": "Inhibition of RNA Pol II → transcription arrest",
            "best_for": "Slow-growing or dormant tumors, p53-mutant tumors",
            "limitation": "Hepatotoxicity, narrow therapeutic index",
            "typical_dar": [2.0]
        },
        "spliceosome_inhibitors": {
            "members": ["Thailanstatin", "Spliceostatin"],
            "potency_range_pM": [100, 1000],
            "mechanism": "Inhibition of SF3B1 → splicing disruption",
            "best_for": "Splicing-factor mutant tumors (e.g., SF3B1 mutant AML/MDS)",
            "limitation": "Systemic toxicity",
            "typical_dar": [2.0, 4.0]
        },
        "immune_stimulatory_agonists": {
            "members": ["TLR7/8 agonist", "STING agonist", "ISAC"],
            "potency_range_pM": "N/A (immune activation)",
            "mechanism": "Innate immune activation (myeloid cells) in TME",
            "best_for": "Cold tumors, combination with PD-1/PD-L1",
            "limitation": "Cytokine release syndrome if systemically released",
            "typical_dar": [2.0, 4.0]
        }
    }
    
    for k, v in new_classes.items():
        if k not in pcls:
            pcls[k] = v
            
    # Update existing classes with more members
    if "dna_damaging_agents" in pcls:
        pcls["dna_damaging_agents"]["members"].extend(["Duocarmycin", "SYD985 payload", "IGN", "PNU-159682"])
        pcls["dna_damaging_agents"]["members"] = list(set(pcls["dna_damaging_agents"]["members"]))
        
    rules["payload_classification"] = pcls
    return rules

def expand_conjugation(rules):
    conj = rules.get("conjugation_technology", {})
    
    new_conj = {
        "enzyme_fge_smartag": {
            "description": "Formylglycine-generating enzyme (FGE) converts Cys to aldehyde for HIPS ligation",
            "dar_homogeneity": "very_high",
            "typical_dar": 2.0,
            "cmc_complexity": "high (cell line engineering)",
            "patent_freedom": "Catalent patents (check FTO)"
        },
        "sortase_a_mediated": {
            "description": "Enzymatic ligation using Sortase A at LPETG motif",
            "dar_homogeneity": "very_high",
            "typical_dar": 2.0,
            "cmc_complexity": "moderate",
            "patent_freedom": "NBE-Therapeutics / Boehringer Ingelheim"
        },
        "tub_tag_tubulin_ligase": {
            "description": "Tubulin tyrosine ligase (TTL) adds unnatural tyrosine derivatives",
            "dar_homogeneity": "high",
            "typical_dar": 2.0,
            "cmc_complexity": "moderate",
            "patent_freedom": "Tubulis patents"
        }
    }
    
    for k, v in new_conj.items():
        if k not in conj:
            conj[k] = v
            
    rules["conjugation_technology"] = conj
    return rules

def expand_programs(master):
    existing_names = {p["canonical_name"].lower() for p in master}
    
    new_programs = [
        {
            "id": "ADC-PROG-T2-008",
            "canonical_name": "Trastuzumab duocarmazine",
            "brand_name": "SYD985",
            "company": "Byondis",
            "visibility": "public_ok",
            "development_stage": "clinical_phase_3 (rejected/resubmitting)",
            "target": "HER2",
            "binder_name": "Trastuzumab",
            "linker_name": "vc-seco-DUBA",
            "payload_name": "Duocarmycin",
            "payload_class": "dna_damaging_agents",
            "dar_mean": 2.8,
            "indication": "HER2+ Breast Cancer",
            "technical_audit": { "physical_consistency": "pass", "logic_check": "DNA alkylator requires low DAR. Ocular toxicity is a known class effect." }
        },
        {
            "id": "ADC-PROG-T2-009",
            "canonical_name": "Camidanlumab tesirine",
            "brand_name": "Cami",
            "company": "ADC Therapeutics",
            "visibility": "public_ok",
            "development_stage": "clinical_phase_2",
            "target": "CD25",
            "binder_name": "HuMax-TAC",
            "linker_name": "Val-Ala-PABC",
            "payload_name": "SG3199 (PBD)",
            "payload_class": "dna_damaging_agents",
            "dar_mean": 2.3,
            "indication": "Hodgkin Lymphoma",
            "technical_audit": { "physical_consistency": "pass", "logic_check": "Targeting Tregs in TME; Guillain-Barre syndrome risk observed." }
        },
        {
            "id": "ADC-PROG-T2-010",
            "canonical_name": "Zilovertamab vedotin",
            "brand_name": "VLS-101",
            "company": "Merck (MSD) / VelosBio",
            "visibility": "public_ok",
            "development_stage": "clinical_phase_2/3",
            "target": "ROR1",
            "binder_name": "Zilovertamab",
            "linker_name": "mc-val-cit-PABC",
            "payload_name": "MMAE",
            "payload_class": "tubulin_inhibitors",
            "dar_mean": 4.0,
            "indication": "MCL, DLBCL",
            "technical_audit": { "physical_consistency": "pass", "logic_check": "Standard Seagen platform applied to ROR1." }
        },
        {
            "id": "ADC-PROG-T2-011",
            "canonical_name": "Farletuzumab ecteribulin",
            "brand_name": "MORAb-202",
            "company": "Eisai / BMS",
            "visibility": "public_ok",
            "development_stage": "clinical_phase_2",
            "target": "FRα",
            "binder_name": "Farletuzumab",
            "linker_name": "Cathepsin B cleavable",
            "payload_name": "Eribulin",
            "payload_class": "tubulin_inhibitors",
            "dar_mean": 4.0,
            "indication": "Ovarian Cancer",
            "technical_audit": { "physical_consistency": "pass", "logic_check": "Eribulin payload provides bystander effect; differentiated from DM4." }
        },
        {
            "id": "ADC-PROG-T2-012",
            "canonical_name": "Upifitamab rilsodotin",
            "brand_name": "UpRi",
            "company": "Mersana",
            "visibility": "public_ok",
            "development_stage": "clinical_phase_3 (paused/terminated)",
            "target": "NaPi2b",
            "binder_name": "Upifitamab",
            "linker_name": "Dolaflexin",
            "payload_name": "Auristatin F-HPA",
            "payload_class": "tubulin_inhibitors",
            "dar_mean": 10.0,
            "indication": "Ovarian Cancer",
            "technical_audit": { "physical_consistency": "pass", "logic_check": "High DAR 10 polymer scaffold; bleeding events led to clinical hold." }
        },
        {
            "id": "ADC-PROG-T2-013",
            "canonical_name": "Telisotuzumab vedotin",
            "brand_name": "Teliso-V",
            "company": "AbbVie",
            "visibility": "public_ok",
            "development_stage": "clinical_phase_3",
            "target": "MET",
            "binder_name": "ABT-700",
            "linker_name": "mc-val-cit-PABC",
            "payload_name": "MMAE",
            "payload_class": "tubulin_inhibitors",
            "dar_mean": 3.1,
            "indication": "NSCLC (c-Met overexpressed)",
            "technical_audit": { "physical_consistency": "pass", "logic_check": "MET is highly heterogeneous; MMAE bystander effect is crucial." }
        },
        {
            "id": "ADC-PROG-T2-014",
            "canonical_name": "BL-B01D1",
            "company": "SystImmune / BMS",
            "visibility": "public_ok",
            "development_stage": "clinical_phase_3",
            "target": "EGFR x HER3",
            "binder_format": "Bispecific",
            "linker_name": "Cleavable (cathepsin)",
            "payload_name": "Ed-04 (TOP1i)",
            "payload_class": "topoisomerase_I_inhibitors",
            "dar_mean": 8.0,
            "indication": "NSCLC, Breast Cancer",
            "technical_audit": { "physical_consistency": "pass", "logic_check": "First-in-class bispecific ADC in Phase 3; targets dual RTK signaling." }
        },
        {
            "id": "ADC-PROG-T2-015",
            "canonical_name": "IBI343",
            "company": "Innovent Biologics",
            "visibility": "public_ok",
            "development_stage": "clinical_phase_3",
            "target": "Claudin18.2",
            "binder_name": "Anti-CLDN18.2",
            "linker_name": "Cleavable",
            "payload_name": "TOP1i",
            "payload_class": "topoisomerase_I_inhibitors",
            "dar_mean": 8.0,
            "indication": "Gastric Cancer, Pancreatic Cancer",
            "technical_audit": { "physical_consistency": "pass", "logic_check": "Fast follower in CLDN18.2 space; DXd-like profile." }
        },
        {
            "id": "ADC-PROG-T2-016",
            "canonical_name": "CMG901",
            "brand_name": "AZD0901",
            "company": "Keymed / AstraZeneca",
            "visibility": "public_ok",
            "development_stage": "clinical_phase_3",
            "target": "Claudin18.2",
            "binder_name": "CMG901",
            "linker_name": "Cleavable",
            "payload_name": "MMAE",
            "payload_class": "tubulin_inhibitors",
            "dar_mean": 4.0,
            "indication": "Gastric Cancer",
            "technical_audit": { "physical_consistency": "pass", "logic_check": "MMAE payload for CLDN18.2; differentiated from TOP1i competitors." }
        },
        {
            "id": "ADC-PROG-T2-017",
            "canonical_name": "ARX788",
            "company": "Ambrx / NovoCodex",
            "visibility": "public_ok",
            "development_stage": "clinical_phase_3",
            "target": "HER2",
            "binder_name": "Trastuzumab-like",
            "linker_name": "Non-cleavable (PEG-AS)",
            "payload_name": "AS269 (Tubulin inhibitor)",
            "payload_class": "tubulin_inhibitors",
            "conjugation_technology": "unnatural_amino_acid",
            "dar_mean": 2.0,
            "indication": "HER2+ Breast Cancer, Gastric Cancer",
            "technical_audit": { "physical_consistency": "pass", "logic_check": "Site-specific DAR 2 using pAF; highly stable non-cleavable linker." }
        }
    ]
    
    for prog in new_programs:
        if prog["canonical_name"].lower() not in existing_names:
            master.append(prog)
            
    return master

def main():
    print("Starting Comprehensive ADC Database Expansion...")
    
    # Load
    rules = load_json("adc_design_rules.json")
    master = load_json("adc_master_internal.json")
    
    # Expand
    rules = expand_targets(rules)
    rules = expand_payloads(rules)
    rules = expand_conjugation(rules)
    master = expand_programs(master)
    
    # Save
    save_json(rules, "adc_design_rules.json")
    save_json(master, "adc_master_internal.json")
    
    print(f"Expansion complete. Master table now has {len(master)} programs.")
    print(f"Target Antigens count: {len(rules.get('antigen_properties', {}))}")
    print(f"Payload Classes count: {len(rules.get('payload_classification', {}))}")
    print(f"Conjugation Techs count: {len(rules.get('conjugation_technology', {}))}")

if __name__ == "__main__":
    main()
