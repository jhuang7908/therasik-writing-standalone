
import json
import os

INTERNAL_JSON = "data/adc_atlas/adc_master_internal.json"
PUBLIC_JSON = "data/adc_atlas/adc_master_public.json"

CLINICAL_ENRICHMENT = {
    "ADC-PROG-T2-003": { # Ifinatamab-DXd
        "clinical_data": {
            "efficacy": {"orr": "48.2% (12mg/kg)", "pfs": "4.9 mo", "os": "10.3 mo (9-mo estimate 59.1%)", "notes": "ES-SCLC data from IDeate-Lung01."},
            "safety": {"grade3_plus_ae_rate": "36.5%", "common_ae": ["Nausea", "Anemia", "Neutropenia", "ILD (12.4%)"], "notes": "ILD grade 3+ was 4.4%."},
            "immunogenicity": {"ada_incidence": "Not Reported", "notes": "Typically low for DXd platform based on Enhertu profile."},
            "dose": {"recommended_dose": "12 mg/kg", "schedule": "Q3W"}
        }
    },
    "ADC-PROG-T2-005": { # sac-TMT
        "clinical_data": {
            "efficacy": {"orr": "45.4% (TNBC)", "pfs": "6.7 mo", "notes": "OptiTROP-Breast01 Phase 3. ORR up to 77.6% in combo with PD-L1 in NSCLC."},
            "safety": {"grade3_plus_ae_rate": "High (Hematologic)", "common_ae": ["Neutropenia", "Stomatitis", "Anemia", "Rash"], "notes": "Stomatitis is a frequent Grade 3 AE."},
            "immunogenicity": {"ada_incidence": "Not Reported", "notes": "K-Link stability may minimize immunogenicity."},
            "dose": {"recommended_dose": "5 mg/kg", "schedule": "Q2W or Q3W"}
        }
    },
    "ADC-PROG-T2-004": { # SHR-A1811
        "clinical_data": {
            "efficacy": {"orr": "66.7% (TNBC combo)", "pfs": "86.2% (6-mo rate)", "notes": "Data in combo with Adebrelimab."},
            "safety": {"grade3_plus_ae_rate": "61.9%", "common_ae": ["Neutropenia", "WBC decrease", "Lymphocyte decrease"], "notes": "Primarily hematologic toxicity."},
            "immunogenicity": {"ada_incidence": "Not Reported"},
            "dose": {"recommended_dose": "4.8 mg/kg", "schedule": "Q3W"}
        }
    },
    "ADC-PROG-T2-015": { # IBI343
        "clinical_data": {
            "efficacy": {"orr": "29.0% (CLDN18.2 high)", "pfs": "5.5 mo", "notes": "Phase 1 trial in Gastric/GEJ cancer."},
            "safety": {"grade3_plus_ae_rate": "Moderate", "common_ae": ["Myelosuppression", "Neutropenia", "Febrile neutropenia"], "notes": "DLT observed at 10 mg/kg."},
            "immunogenicity": {"ada_incidence": "Not Reported"},
            "dose": {"recommended_dose": "6 mg/kg", "schedule": "Q3W"}
        }
    },
    "ADC-PROG-T2-016": { # CMG901
        "clinical_data": {
            "efficacy": {"orr": "35% overall, 48% (2.2mg/kg)", "pfs": "4.8 mo", "os": "11.8 mo", "notes": "CLDN18.2 high Gastric/GEJ patients."},
            "safety": {"grade3_plus_ae_rate": "55%", "common_ae": ["Nausea", "Anemia", "Neutropenia"], "notes": "Serious AEs reported in 32%."},
            "immunogenicity": {"ada_incidence": "Not Reported"},
            "dose": {"recommended_dose": "2.2 - 3.0 mg/kg", "schedule": "Q3W"}
        }
    },
    "ADC-PROG-T2-014": { # BL-B01D1
        "clinical_data": {
            "efficacy": {"orr": "29.3% (ESCC), 54.6% (NPC)", "pfs": "8.38 mo (NPC)", "notes": "Breakthrough data in Nasopharyngeal Carcinoma."},
            "safety": {"grade3_plus_ae_rate": "63.3% (2.5mg/kg)", "common_ae": ["Anemia", "Leukopenia", "Thrombocytopenia", "ILD"], "notes": "Highly hematologic toxicity profile."},
            "immunogenicity": {"ada_incidence": "Not Reported"},
            "dose": {"recommended_dose": "2.5 mg/kg", "schedule": "D1, D8 Q3W"}
        }
    },
    "ADC-PROG-T2-223": { # RC88
        "clinical_data": {
            "efficacy": {"orr": "45.2% (Ovarian)", "pfs": "6.87 mo (NSCLC high MSLN)", "notes": "Strong signal in MSLN-high ovarian cancer."},
            "safety": {"grade3_plus_ae_rate": "Manageable", "common_ae": ["Neutropenia", "AST/ALT elevation"], "notes": "Safety profile consistent with vc-MMAE platform."},
            "immunogenicity": {"ada_incidence": "Not Reported"},
            "dose": {"recommended_dose": "2.0 mg/kg", "schedule": "Q3W"}
        }
    },
    "ADC-PROG-T2-200": { # Raludotatug deruxtecan
        "clinical_data": {
            "efficacy": {"orr": "50.0%", "notes": "REJOICE-Ovarian01 Phase 2 data presented at ESMO 2025."},
            "safety": {"grade3_plus_ae_rate": "Moderate", "common_ae": ["Nausea", "Anemia", "Asthenia"], "notes": "4 cases of ILD reported in all-dose cohort."},
            "immunogenicity": {"ada_incidence": "Low", "notes": "Estimated <5% based on DXd platform."},
            "dose": {"recommended_dose": "5.6 mg/kg", "schedule": "Q3W"}
        }
    },
    "ADC-PROG-T1-001": { # Enhertu
        "clinical_data": {
            "efficacy": {"orr": "60.9% (DESTINY-Breast03)", "pfs": "28.8 mo", "notes": "Gold standard for HER2 ADCs."},
            "safety": {"grade3_plus_ae_rate": "40-50%", "common_ae": ["Nausea", "Neutropenia", "ILD (10-15%)"], "notes": "ILD is the critical DLT; requires proactive monitoring."},
            "immunogenicity": {"ada_incidence": "2.1%", "notes": "Very low immunogenicity due to highly stable design."},
            "dose": {"recommended_dose": "5.4 mg/kg", "schedule": "Q3W"}
        }
    },
    "ADC-PROG-T1-002": { # Adcetris
        "clinical_data": {
            "efficacy": {"orr": "75% (HL)", "pfs": "42.9 mo (ECHELON-1)", "notes": "Standard of care for CD30+ Hodgkin Lymphoma."},
            "safety": {"grade3_plus_ae_rate": "Moderate", "common_ae": ["Peripheral Neuropathy", "Neutropenia", "Anemia"], "notes": "Neuropathy is dose-limiting and cumulative."},
            "immunogenicity": {"ada_incidence": "37% (transient)", "notes": "Persistent ADA in ~7%; impacts PK but rarely efficacy."},
            "dose": {"recommended_dose": "1.8 mg/kg", "schedule": "Q3W"}
        }
    },
    "ADC-PROG-T2-002": { # Dato-DXd
        "clinical_data": {
            "efficacy": {"orr": "30.0% (pooled)", "pfs": "5.56 mo", "notes": "Approved for EGFR-mutated NSCLC. HR 0.63 in HR+/HER2- BC."},
            "safety": {"grade3_plus_ae_rate": "20.8%", "common_ae": ["Stomatitis (55%)", "Nausea (49%)", "Alopecia (38%)"], "notes": "Stomatitis is the hallmark toxicity for Dato-DXd."},
            "immunogenicity": {"ada_incidence": "Not Reported", "notes": "Likely low based on DXd platform."},
            "dose": {"recommended_dose": "6 mg/kg", "schedule": "Q3W"}
        }
    },
    "ADC-PROG-T2-001": { # Patritumab-DXd
        "clinical_data": {
            "efficacy": {"orr": "53.5% (HER3+ BC)", "notes": "ICARUS-BREAST01 trial data."},
            "safety": {"grade3_plus_ae_rate": "Moderate", "common_ae": ["Fatigue", "Nausea", "Diarrhea", "Alopecia"], "notes": "Profile similar to other DXd ADCs."},
            "immunogenicity": {"ada_incidence": "Not Reported"},
            "dose": {"recommended_dose": "5.6 mg/kg", "schedule": "Q3W"}
        }
    }
}

def enrich_clinical_deep():
    if not os.path.exists(INTERNAL_JSON):
        print(f"Error: {INTERNAL_JSON} not found")
        return

    with open(INTERNAL_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for item in data:
        id = item.get("id")
        
        # Initialize default clinical data structure if not exists
        if "clinical_data" not in item:
            item["clinical_data"] = {
                "efficacy": {"orr": "TBD", "pfs": "TBD", "os": "TBD", "notes": ""},
                "safety": {"grade3_plus_ae_rate": "TBD", "dlt": "TBD", "common_ae": [], "notes": ""},
                "immunogenicity": {"ada_incidence": "TBD", "notes": ""},
                "dose": {"recommended_dose": "TBD", "schedule": "TBD"}
            }

        if id in CLINICAL_ENRICHMENT:
            enrichment = CLINICAL_ENRICHMENT[id]
            # Deep update clinical_data
            for key, val in enrichment["clinical_data"].items():
                if isinstance(val, dict):
                    item["clinical_data"][key].update(val)
                else:
                    item["clinical_data"][key] = val

    with open(INTERNAL_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Sync to public (stripping sequences)
    public_data = []
    for item in data:
        pub_item = item.copy()
        if "sequence_data" in pub_item:
            del pub_item["sequence_data"]
        public_data.append(pub_item)
    
    with open(PUBLIC_JSON, 'w', encoding='utf-8') as f:
        json.dump(public_data, f, indent=2, ensure_ascii=False)

    print(f"Successfully enriched clinical depth for {len(CLINICAL_ENRICHMENT)} ADCs.")

if __name__ == "__main__":
    enrich_clinical_deep()
