
import json
import os

INTERNAL_JSON = "data/adc_atlas/adc_master_internal.json"
PUBLIC_JSON = "data/adc_atlas/adc_master_public.json"

def enrich_adc_data():
    if not os.path.exists(INTERNAL_JSON):
        print(f"Error: {INTERNAL_JSON} not found")
        return

    with open(INTERNAL_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for item in data:
        # 1. Ifinatamab deruxtecan (ADC-PROG-T2-003)
        if item.get("id") == "ADC-PROG-T2-003":
            item["development_stage"] = "clinical_phase_3"
            item["indication"] = "Extensive-stage SCLC (ES-SCLC), Esophageal cancer"
            item["brand_name"] = "I-DXd"
            item["technical_audit"] = (
                "FDA Breakthrough Therapy Designation (Aug 2025). Phase II IDeate-Lung01: 48.2% confirmed ORR in ES-SCLC at 12 mg/kg. "
                "Intracranial response 46.2% observed. Manageable ILD risk (12.4%)."
            )
            item["source_primary"] = "PMID: 39186361, NCT05280470"

        # 2. Sacituzumab tirumotecan (ADC-PROG-T2-005)
        if item.get("id") == "ADC-PROG-T2-005":
            item["brand_name"] = "sac-TMT (SKB264 / MK-2870)"
            item["indication"] = "mTNBC, HR+/HER2– Metastatic Breast Cancer, NSCLC"
            item["technical_audit"] = (
                "Phase 3 OptiTROP-Breast02: Median PFS 8.3 mo vs 4.1 mo (chemo) in HR+/HER2- mBC. "
                "65% reduction in progression risk. Collaboration between Kelun and Merck (MSD)."
            )
            item["source_primary"] = "NCT05347135, ESMO 2025"

        # 3. Raludotatug deruxtecan (ADC-PROG-T2-200)
        if item.get("id") == "ADC-PROG-T2-200":
            item["development_stage"] = "clinical_phase_3"
            item["indication"] = "Platinum-resistant Ovarian Cancer, Peritoneal/Fallopian Tube Cancer"
            item["technical_audit"] = (
                "Phase 2 REJOICE-Ovarian01: 50.0% ORR at 5.6 mg/kg dose. Moving to Phase 3 vs chemotherapy. "
                "CDH6-directed ADC with DXd platform."
            )
            item["source_primary"] = "PMID: 34711587, REJOICE-Ovarian01"

        # 4. SHR-A1904 (ADC-PROG-T2-204)
        if item.get("id") == "ADC-PROG-T2-204":
            item["indication"] = "Advanced Gastric or Gastroesophageal Junction (GEJ) Cancer"
            item["technical_audit"] = (
                "Phase 1 trial (n=95): 25.0% confirmed ORR at 8.0 mg/kg. Median PFS ~5.8 months. "
                "Targeting CLDN18.2 with Rezetecan (SHR169106) payload."
            )
            item["source_primary"] = "Nature Medicine 2025, NCT05043987"

        # 5. Telisotuzumab vedotin (ADC-PROG-T2-013)
        if item.get("id") == "ADC-PROG-T2-013":
            item["brand_name"] = "Teliso-V"
            item["indication"] = "NSCLC (c-Met overexpressed), EGFR-wild type"
            item["technical_audit"] = (
                "FDA Breakthrough Therapy Designation for c-Met-high NSCLC. LUMINOSITY trial data support Phase 3 development."
            )

        # 6. Bulumtatug fuvedotin (ADC-PROG-T2-004)
        if item.get("id") == "ADC-PROG-T2-004":
            item["brand_name"] = "SHR-A1811"
            item["indication"] = "HER2+ Breast Cancer, Gastric Cancer, HER2-low BC"
            item["technical_audit"] = (
                "Phase 3 candidate for HER2-positive breast cancer. Hengrui's proprietary Topo1i platform. "
                "Showed competitive ORR vs DS-8201 in Chinese clinical cohorts."
            )

        # 7. Disitamab vedotin (ADC-PROG-T1-012)
        if item.get("id") == "ADC-PROG-T1-012":
            item["brand_name"] = "Aidixi (RC48)"
            item["indication"] = "HER2+ Gastric, Urothelial, and Breast Cancer"
            item["technical_audit"] = (
                "First China-developed ADC approved (2021). High affinity for HER2. "
                "Licensed globally (ex-Asia/non-Japan) to Seagen (Pfizer) for $2.6B."
            )

        # 8. Patritumab deruxtecan (ADC-PROG-T2-001)
        if item.get("id") == "ADC-PROG-T2-001":
            item["development_stage"] = "clinical_phase_3 (withdrawn)"
            item["technical_audit"] = (
                "BLA voluntarily withdrawn (May 2025) after HERTHENA-Lung02 failed to meet OS significance in NSCLC. "
                "Remains in development for other HER3+ indications (15+ cancer types). High DAR 8.0 DXd platform."
            )
            item["source_primary"] = "HERTHENA-Lung02, May 2025 BLA Withdrawal"

        # 9. Datopotamab deruxtecan (ADC-PROG-T2-002)
        if item.get("id") == "ADC-PROG-T2-002":
            item["development_stage"] = "approved"
            item["brand_name"] = "Dato-DXd"
            item["indication"] = "EGFR-mutated Locally Advanced or Metastatic NSCLC"
            item["technical_audit"] = (
                "FDA Accelerated Approval (June 2025). TROP2-directed ADC using DXd platform. "
                "Phase 3 TROPION-Lung01/05 demonstrated 45% ORR in pre-treated NSCLC. DAR 4.0 optimized for safety."
            )
            item["source_primary"] = "FDA Approval June 23, 2025"

        # Update generic indications to "Advanced Solid Tumors" where specific target is unclear
        if item.get("indication") == "Solid Tumors / Hematologic":
             target = item.get("target", "")
             if target:
                 item["indication"] = f"{target}-expressing Advanced Solid Tumors"
             else:
                 item["indication"] = "Advanced Solid Tumors"

    with open(INTERNAL_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Update Public JSON (firewalled - no sequences)
    public_data = []
    for item in data:
        pub_item = item.copy()
        if "sequence_data" in pub_item:
            del pub_item["sequence_data"]
        public_data.append(pub_item)
    
    with open(PUBLIC_JSON, 'w', encoding='utf-8') as f:
        json.dump(public_data, f, indent=2, ensure_ascii=False)

    print(f"Successfully enriched {len(data)} ADC records.")

if __name__ == "__main__":
    enrich_adc_data()
