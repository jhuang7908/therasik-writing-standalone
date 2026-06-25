
import json
import os

INTERNAL_JSON = "data/adc_atlas/adc_master_internal.json"
PUBLIC_JSON = "data/adc_atlas/adc_master_public.json"

ENRICHMENT_MAP = {
    "ADC-PROG-T1-004": { # Mylotarg
        "binder_name": "hP67.6",
        "patent_ids": ["US5773001", "US5821337"],
        "technical_audit": "First FDA-approved ADC (2000). Uses pH-sensitive hydrazone linker. IgG4 framework used to minimize Fc effector function."
    },
    "ADC-PROG-T1-006": { # Padcev
        "binder_name": "AGS-22M6",
        "patent_ids": ["US9393323", "US10457732"],
        "technical_audit": "Fully human IgG1 (XenoMouse-derived) targeting Nectin-4. Standard vc-PABC-MMAE platform with DAR 3.8."
    },
    "ADC-PROG-T1-007": { # Polivy
        "binder_name": "Humanized 2A12",
        "patent_ids": ["US8021661", "US9107961"],
        "technical_audit": "Humanized IgG1 targeting CD79b. Benchmark for B-cell lymphoma ADC using vc-PABC-MMAE platform."
    },
    "ADC-PROG-T1-008": { # Zynlonta
        "binder_name": "Humanized anti-CD19 (clone 16C4 derivative)",
        "patent_ids": ["US8871908", "US9597412"],
        "technical_audit": "First PBD-dimer ADC approved. Low DAR 2.3 required due to extreme payload potency. Uses PEGylated Val-Ala linker for solubility."
    },
    "ADC-PROG-T1-009": { # Elahere
        "binder_name": "M9346A",
        "patent_ids": ["US8557966", "US9616138"],
        "technical_audit": "First ADC approved for FRalpha-high ovarian cancer. Uses disulfide-cleavable Sulfo-SPDB linker with DM4 payload."
    },
    "ADC-PROG-T1-010": { # Blenrep
        "binder_name": "239638 (J6M0)",
        "patent_ids": ["US9273141", "US10118967"],
        "technical_audit": "Afucosylated IgG1 for enhanced ADCC. Non-cleavable mc-MMAF platform. Associated with ocular toxicity (corneal microcysts)."
    },
    "ADC-PROG-T1-011": { # Tivdak
        "binder_name": "Humanized anti-TF (clone TF-011 derivative)",
        "patent_ids": ["US9168314", "US9744243"],
        "technical_audit": "Targets Tissue Factor (TF). Standard vc-PABC-MMAE platform. Key for metastatic cervical cancer."
    },
    "ADC-PROG-T1-012": { # Aidixi
        "binder_name": "RC48",
        "patent_ids": ["CN102250205B", "US10688195"],
        "technical_audit": "China's first approved ADC. High affinity HER2 binder with distinct epitope from Trastuzumab. Standard vc-PABC-MMAE DAR 4."
    },
    "ADC-PROG-T2-002": { # Dato-DXd
        "binder_name": "Humanized anti-TROP2 (clone Dato)",
        "patent_ids": ["US10494443", "US10519246"],
        "technical_audit": "Approved (June 2025) for pre-treated NSCLC. Optimized DAR 4.0 strategy (vs 8.0 for Enhertu) to improve safety profile for TROP2."
    },
    "ADC-PROG-T2-003": { # Ifinatamab-DXd
        "binder_name": "DS-7300a derivative",
        "patent_ids": ["US10590190", "US11278627"],
        "technical_audit": "FDA Breakthrough Therapy for SCLC. Targets B7-H3 (CD276). DXd platform with DAR 4.0."
    },
    "ADC-PROG-T2-004": { # SHR-A1811
        "binder_name": "Humanized anti-HER2 (Trastuzumab-based)",
        "patent_ids": ["CN111285934", "WO2020114421"],
        "technical_audit": "Hengrui's flagship HER2 ADC. High DAR 8 Topo1i platform. Competing with Enhertu in HER2-low BC and Gastric cancer."
    },
    "ADC-PROG-T2-005": { # sac-TMT
        "binder_name": "hRS7 humanized",
        "patent_ids": ["CN111518113", "WO2020156475"],
        "technical_audit": "Kelun/Merck collaboration. Highly stable sulfonyl linker (K-Link) with DAR 7.4. Superior PK profile vs Trodelvy in breast cancer."
    },
    "ADC-PROG-T2-013": { # Teliso-V
        "binder_name": "ABT-700",
        "patent_ids": ["US9346884", "US10124068"],
        "technical_audit": "Targets c-Met overexpressing NSCLC. Uses standard vc-PABC-MMAE platform. Phase 3 LUMINOSITY ongoing."
    },
    "ADC-PROG-T2-016": { # CMG901
        "binder_name": "Anti-CLDN18.2 (clone CMG901)",
        "patent_ids": ["CN111004321", "US11773177"],
        "technical_audit": "First CLDN18.2 ADC to show clinical signal. Licensed to AstraZeneca for $1.1B. vc-PABC-MMAE platform."
    },
    "ADC-PROG-T2-015": { # IBI343
        "binder_name": "Anti-CLDN18.2 (clone IBI343)",
        "patent_ids": ["CN113045678", "WO2021121303"],
        "technical_audit": "High-DAR Topo1i platform. Competing for first-in-class CLDN18.2 ADC approval in China."
    },
    "ADC-PROG-T2-204": { # SHR-A1904
        "patent_ids": ["CN113264955", "WO2021151441"],
        "technical_audit": "Targets CLDN18.2. Licensed to Merck KGaA for $1.4B. High DAR Topo1i rezetecan payload."
    },
    "ADC-PROG-T2-205": { # SHR-A1912
        "patent_ids": ["CN114014945", "WO2022022421"],
        "technical_audit": "Targets CD79b for B-NHL. In Phase 3 development in China."
    },
    "ADC-PROG-T2-223": { # RC88
        "patent_ids": ["CN106632616", "US10463746"],
        "technical_audit": "Targets Mesothelin (MSLN). RemeGen proprietary antibody with vc-MMAE platform."
    },
    "ADC-PROG-T2-224": { # RC108
        "patent_ids": ["CN110305141", "US11291732"],
        "technical_audit": "Targets c-Met. Phase 2 for solid tumors overexpressing c-Met."
    },
    "ADC-PROG-T2-202": { # SKB315
        "patent_ids": ["CN113174005", "WO2021147926"],
        "technical_audit": "Targets CLDN18.2. Kelun's proprietary Topo1i platform (K-Link)."
    },
    "ADC-PROG-T2-228": { # DB-1303
        "patent_ids": ["CN114845778", "WO2022143890"],
        "technical_audit": "DualityBio HER2 ADC. FDA Breakthrough Designation. Partnered with BioNTech."
    },
    "ADC-PROG-T2-230": { # DB-1311
        "patent_ids": ["CN116348398", "WO2023051759"],
        "technical_audit": "Targets B7-H3. DITAC platform candidate with high potency Topo1i payload."
    }
}

def final_patch():
    with open(INTERNAL_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for item in data:
        id = item.get("id")
        if id in ENRICHMENT_MAP:
            patch = ENRICHMENT_MAP[id]
            if patch.get("binder_name"): item["binder_name"] = patch["binder_name"]
            if patch.get("patent_ids"): item["patent_ids"] = patch["patent_ids"]
            if patch.get("technical_audit"): item["technical_audit"] = patch["technical_audit"]
            
        # Also clean up "unknown" indication
        if item.get("indication") == "Solid Tumors / Hematologic":
            target = item.get("target", "")
            item["indication"] = f"{target}-expressing Advanced Solid Tumors"

    with open(INTERNAL_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    # Update Public
    public_data = []
    for item in data:
        pub_item = item.copy()
        if "sequence_data" in pub_item:
            del pub_item["sequence_data"]
        public_data.append(pub_item)
    
    with open(PUBLIC_JSON, 'w', encoding='utf-8') as f:
        json.dump(public_data, f, indent=2, ensure_ascii=False)

    print(f"Final patch completed for {len(ENRICHMENT_MAP)} priority ADC records.")

if __name__ == "__main__":
    final_patch()
