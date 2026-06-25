
import json
import os

INTERNAL_JSON = "data/adc_atlas/adc_master_internal.json"

def list_priorities():
    with open(INTERNAL_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    def is_unknown(val):
        if val is None: return True
        if isinstance(val, str):
            v = val.lower().strip()
            return v in ["unknown", "none", "", "n/a", "tbd", "none (proprietary)"]
        return False

    priorities = []
    for item in data:
        if is_unknown(item.get("binder_name")) or is_unknown(item.get("patent_ids")):
            priorities.append({
                "id": item["id"],
                "name": item["canonical_name"],
                "target": item.get("target"),
                "company": item.get("company"),
                "stage": item.get("development_stage")
            })

    # Sort by stage (approved first, then phase 3)
    def stage_rank(s):
        s = s.lower()
        if "approved" in s: return 0
        if "phase_3" in s: return 1
        if "phase_2" in s: return 2
        return 3

    priorities.sort(key=lambda x: stage_rank(x["stage"]))
    
    print(f"Priority targets for enrichment (First 20):")
    for p in priorities[:20]:
        print(f"- {p['name']} ({p['target']}, {p['company']}, {p['stage']})")

if __name__ == "__main__":
    list_priorities()
