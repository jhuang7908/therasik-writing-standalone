import json
import os

INTERNAL_DB = "data/adc_atlas/adc_master_internal.json"
PUBLIC_DB = "data/adc_atlas/adc_master_public.json"

def filter_database():
    if not os.path.exists(INTERNAL_DB):
        print(f"Error: Internal database {INTERNAL_DB} not found.")
        return

    with open(INTERNAL_DB, 'r', encoding='utf-8') as f:
        data = json.load(f)

    public_data = []
    for entry in data:
        # 1. Check visibility tag
        if entry.get("visibility") != "public_ok":
            continue
        
        # 2. Strip sensitive fields even if public_ok
        # (Example: internal_insight, technical_audit details)
        filtered_entry = {
            "id": entry.get("id"),
            "canonical_name": entry.get("canonical_name"),
            "brand_name": entry.get("brand_name"),
            "company": entry.get("company"),
            "development_stage": entry.get("development_stage"),
            "regulatory_status_current": entry.get("regulatory_status_current"),
            "approval_regions": entry.get("approval_regions"),
            "target": entry.get("target"),
            "boundary_classification": entry.get("boundary_classification", "classical_ADC"),
            "traceability": {
                "source_summary": list(entry.get("traceability", {}).get("source_by_claim", {}).values())
            }
        }
        public_data.append(filtered_entry)

    with open(PUBLIC_DB, 'w', encoding='utf-8') as f:
        json.dump(public_data, f, indent=2, ensure_ascii=False)
    
    print(f"Public database generated at {PUBLIC_DB} ({len(public_data)} entries).")

if __name__ == "__main__":
    filter_database()
