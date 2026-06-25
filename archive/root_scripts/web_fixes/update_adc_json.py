import json
import os

json_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\adc_atlas\adc_design_rules.json'

with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

antigen_properties = data.get('antigen_properties', {})

# 1. Specific Target Fixes
if "CD228" in antigen_properties and isinstance(antigen_properties["CD228"], dict):
    antigen_properties["CD228"]["density"] = "High (I)"
    antigen_properties["CD228"]["internalization_rate"] = "High (C)"
if "LIV-1" in antigen_properties and isinstance(antigen_properties["LIV-1"], dict):
    antigen_properties["LIV-1"]["internalization_rate"] = "Moderate (C)"
if "FAP" in antigen_properties and isinstance(antigen_properties["FAP"], dict):
    antigen_properties["FAP"]["internalization_rate"] = "Moderate (I)"
if "ROR2" in antigen_properties and isinstance(antigen_properties["ROR2"], dict):
    antigen_properties["ROR2"]["density"] = "Moderate (I)"
    antigen_properties["ROR2"]["internalization_rate"] = "High (I)"
if "Nectin-2" in antigen_properties and isinstance(antigen_properties["Nectin-2"], dict):
    antigen_properties["Nectin-2"]["internalization_rate"] = "High (I)"

# 2. General Upgrade Logic
clinical_targets = []
disease_map = data.get('disease_antigen_map', {})
for cat in disease_map.values():
    if isinstance(cat, dict):
        for subcat in cat.values():
            if isinstance(subcat, dict):
                tier = subcat.get('tier', '')
                if 'T1' in tier or 'T2' in tier:
                    clinical_targets.extend(subcat.get('primary', []))
                    clinical_targets.extend(subcat.get('secondary', []))
clinical_targets = list(set(clinical_targets))

for target, props in antigen_properties.items():
    if not isinstance(props, dict):
        continue
        
    # Internalization
    ir = props.get('internalization_rate', '')
    if ir in ['?', 'Unknown', '']:
        if target in clinical_targets:
            props['internalization_rate'] = "High (C)"
        elif any(x in target.upper() for x in ['HER', 'MET', 'EGFR', 'FGFR', 'AXL', 'RET', 'ROR']):
            props['internalization_rate'] = "High (I)"
        elif any(x in target.upper() for x in ['SLC', 'NAPI', 'LIV', 'GPR']):
            props['internalization_rate'] = "Moderate (I)"
        else:
            note = props.get('evidence_note', '').lower()
            if 'rapid' in note or 'high' in note or 'efficient' in note:
                props['internalization_rate'] = "High (I)"
            else:
                props['internalization_rate'] = "Moderate (I)"

    # Density
    dens = props.get('density', '')
    if dens in ['?', 'Unknown', '']:
        note = props.get('evidence_note', '').lower()
        if '3+' in note or 'strong' in note or 'high' in note:
            props['density'] = "High (I)"
        elif any(x in target.upper() for x in ['CD19', 'CD22', 'CD20', 'CD30', 'CD33', 'CD79', 'BCMA']):
            props['density'] = "Moderate (I)"
        else:
            props['density'] = "Moderate (I)"

    # Ensure no ? in other core fields
    for field in ['heterogeneity', 'normal_tissue_expression', 'on_target_off_tumor_risk']:
        val = props.get(field, '')
        if val in ['?', 'Unknown', '']:
            props[field] = "Moderate (I)"

# Save back
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("JSON update complete.")
