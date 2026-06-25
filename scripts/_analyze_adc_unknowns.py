
import json
import os

INTERNAL_JSON = "data/adc_atlas/adc_master_internal.json"

def analyze_unknowns():
    if not os.path.exists(INTERNAL_JSON):
        print(f"Error: {INTERNAL_JSON} not found")
        return

    with open(INTERNAL_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total = len(data)
    stats = {
        "brand_name": 0,
        "binder_name": 0,
        "linker_name": 0,
        "payload_name": 0,
        "dar_mean": 0,
        "indication": 0,
        "technical_audit": 0,
        "vh_seq": 0,
        "vl_seq": 0,
        "patent_ids": 0
    }

    def is_unknown(val):
        if val is None: return True
        if isinstance(val, str):
            v = val.lower().strip()
            return v in ["unknown", "none", "", "n/a", "tbd", "none (proprietary)"]
        if isinstance(val, (list, dict)) and len(val) == 0: return True
        return False

    for item in data:
        if is_unknown(item.get("brand_name")): stats["brand_name"] += 1
        if is_unknown(item.get("binder_name")): stats["binder_name"] += 1
        if is_unknown(item.get("linker_name")): stats["linker_name"] += 1
        if is_unknown(item.get("payload_name")): stats["payload_name"] += 1
        if is_unknown(item.get("dar_mean")): stats["dar_mean"] += 1
        if is_unknown(item.get("indication")): stats["indication"] += 1
        
        # Technical audit - check if it's just a generic "pass" or empty
        audit = item.get("technical_audit")
        if isinstance(audit, dict):
            if is_unknown(audit.get("physical_consistency")) and is_unknown(audit.get("logic_check")):
                stats["technical_audit"] += 1
        elif is_unknown(audit):
            stats["technical_audit"] += 1
            
        # Sequences
        seq_data = item.get("sequence_data", {})
        binder_seqs = seq_data.get("binder_sequences", {})
        if is_unknown(binder_seqs.get("vh_seq")): stats["vh_seq"] += 1
        if is_unknown(binder_seqs.get("vl_seq")): stats["vl_seq"] += 1
        
        if is_unknown(item.get("patent_ids")): stats["patent_ids"] += 1

    print(f"Analysis of {total} ADC Clinical Records:")
    print("-" * 40)
    for field, count in stats.items():
        pct = (count / total) * 100
        print(f"{field:15}: {count:3} unknowns ({pct:4.1f}%)")

if __name__ == "__main__":
    analyze_unknowns()
