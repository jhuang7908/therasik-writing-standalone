import json
import os

def update_adc_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    antigens = data.get("antigen_properties", {})
    
    # Priority targets list
    priority_targets = [
        "CD228", "LIV-1", "NaPi2b", "HER3", "B7-H3", "MET", "GPC3", "CEACAM5", 
        "MSLN", "MUC1", "MUC16", "ROR1", "ROR2", "PSMA", "EGFR", "CD123", "FLT3"
    ]

    # Mapping of common qualitative terms to suffixes
    suffix_map = {
        "High": "High (I)",
        "Moderate": "Moderate (I)",
        "Low": "Low (I)",
        "Rapid": "Rapid (I)",
        "Slow": "Slow (I)",
        "Very High": "Very High (I)",
        "Very Low": "Very Low (I)",
        "None": "None (I)",
        "Minimal": "Minimal (I)",
        "Variable": "Variable (I)"
    }

    def apply_suffix(value, evidence_type="(I)"):
        if not value or not isinstance(value, str) or value == "NA":
            return "NA"
        if any(s in value for s in ["(D)", "(I)", "(C)"]):
            return value
        
        # Check if it's a known qualitative term
        for term, suffixed in suffix_map.items():
            if value.strip() == term:
                return suffixed
        
        return f"{value} {evidence_type}"

    for name, props in antigens.items():
        # Skip if props is not a dictionary (should not happen based on structure)
        if not isinstance(props, dict):
            continue

        # 1. Update fields with suffixes
        fields_to_update = [
            "density_quantitative",
            "internalization_t12",
            "internalization_mechanism",
            "recycling_after_internalization",
            "shedding_rate",
            "heterogeneity"
        ]
        
        # Determine default evidence type based on tier or existing notes
        tier_val = props.get("tier", "")
        evidence_type = "(I)"
        if "Approved" in tier_val or "Tier 1" in tier_val or "T1" in tier_val:
            evidence_type = "(C)" # Clinical proxy for approved/T1
        
        for field in fields_to_update:
            if field in props:
                props[field] = apply_suffix(props[field], evidence_type)
            else:
                # Initialize if missing for priority targets
                if name in priority_targets:
                    props[field] = "NA"

        # 2. Update design_logic
        tier = tier_val if tier_val else "Unknown Tier"
        logic = props.get("design_logic", "")
        
        # Extract key info for logic update
        density = props.get("density", "Unknown")
        internalization = props.get("internalization_rate", "Unknown")
        mechanism = props.get("internalization_mechanism", "Unknown")
        
        # Construct new logic if it doesn't already have the evidence basis
        if "Based on" not in logic:
            new_logic = f"[{tier}] Based on Inferred (I) {density} density and "
            if evidence_type == "(C)":
                new_logic += f"Clinical (C) validation of {internalization} internalization via "
                # Try to find a precedent from refs or common knowledge
                precedent = "clinical data"
                if "key_refs" in props and isinstance(props["key_refs"], list) and props["key_refs"]:
                    ref = props["key_refs"][0]
                    if "(" in ref and ")" in ref:
                        precedent = ref.split("(")[1].split(")")[0]
                new_logic += f"{precedent}. "
            else:
                new_logic += f"Inferred (I) {internalization} internalization. "
            
            if mechanism != "NA":
                new_logic += f"Internalized via {mechanism}."
            
            props["design_logic"] = new_logic

    # Save updated JSON
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\adc_atlas\adc_design_rules.json'
    update_adc_json(path)
    print("Update complete.")
