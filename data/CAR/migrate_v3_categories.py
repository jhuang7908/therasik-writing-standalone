import json

def update_library(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 1. Update Metadata
    data['metadata']['taxonomy_version'] = "v3.0 (In-Vivo & Clinical Sub-categorization)"
    data['metadata']['last_updated'] = "2026-04-26"

    # 2. Add New Category: In-Vivo CAR Module
    # We move some elements to this new category
    invivo_ids = ['OKT3_hu_scFv', 'OKT8_scFv', 'CD3ε_Targeting', 'CD8α_Targeting', 'HBA1_3UTR', 'HBB_3UTR']
    
    # 3. Antigen Binder Sub-categorization
    liquid_keywords = ['CD19', 'CD20', 'CD22', 'BCMA', 'CD123', 'CD33', 'CD38', 'CD138', 'B-cell', 'Hematologic', 'Leukemia', 'Lymphoma', 'Myeloma', 'B-ALL']
    solid_keywords = ['GPC3', 'HER2', 'MSLN', 'MESOTHELIN', 'EGFR', 'FOLR1', 'CLDN18.2', 'FAP', 'PSMA', 'MUC1', 'CEA', 'GD2', 'STEAP1', 'Solid Tumor', 'HCC', 'Gastric', 'Pancreatic', 'Prostate']
    autoimmune_keywords = ['AutoImmune', 'SLE', 'Lupus', 'DSG3', 'MuSK', 'Autoantigen', 'CAAR']
    neuro_keywords = ['GD2', 'ALK', 'B7H3', 'Glioma', 'Neuroblastoma', 'Brain', 'CNS']

    for element in data['elements']:
        eid = element['id']
        category = element['category']
        sub = element.get('subcategory', '')
        desc = element.get('description', '') + element.get('design_notes', '')

        # Check for In-Vivo move
        if eid in invivo_ids or 'In-Vivo' in sub or 'Targeting' in sub:
            element['category'] = 'In-Vivo CAR Module'
            if '3UTR' in eid:
                element['subcategory'] = 'mRNA Stability Element'
            else:
                element['subcategory'] = 'LNP/mRNA Targeting Ligand'

        # Refactor Antigen Binders
        if category == 'Antigen Binder' or element['category'] == 'Antigen Binder':
            if any(k.upper() in eid.upper() or k.upper() in desc.upper() for k in autoimmune_keywords):
                element['subcategory'] = 'Autoimmune (Self-Tolerance/CAAR)'
            elif any(k.upper() in eid.upper() or k.upper() in desc.upper() for k in neuro_keywords):
                element['subcategory'] = 'Neurological (CNS/Glioma)'
            elif any(k.upper() in eid.upper() or k.upper() in desc.upper() for k in liquid_keywords):
                element['subcategory'] = 'Hematologic (Liquid Tumor)'
            elif any(k.upper() in eid.upper() or k.upper() in desc.upper() for k in solid_keywords):
                element['subcategory'] = 'Solid Tumor'
            else:
                element['subcategory'] = 'General/Multi-Target'

    # 4. Add Sibrotuzumab if missing
    if not any(e['id'] == 'Sibrotuzumab_scFv' for e in data['elements']):
        sibro = {
            "id": "Sibrotuzumab_scFv",
            "name": "Sibrotuzumab (Anti-FAP) scFv",
            "category": "Antigen Binder",
            "subcategory": "Solid Tumor",
            "sequence": "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSVVRQAPGKGLEWVASTTNDGGTNYNEKFKGRFTMTRDTSISTAYMELSRLRSDDTAVYYCARGNWDDYWGQGTLVTVSSGGGGSGGGGSGGGGSDIQMTQSPSSLSASVGDRVTITCRASQGISSWLAWYQQKPEKAPKSLIYAASSLQSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQYFSYPWTFGGGTKVEIK",
            "length": 238,
            "target": "FAP (Fibroblast Activation Protein)",
            "regulatory_tier": "T2",
            "design_notes": "Sibrotuzumab humanized scFv. Targets FAP on tumor-associated fibroblasts (TAFs). Used in in-vivo CAR-T/LNP studies for solid tumor TME remodeling."
        }
        data['elements'].append(sibro)
        data['metadata']['total_elements'] += 1

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Library updated successfully. Total elements: {data['metadata']['total_elements']}")

update_library('CART_LIBRARY_V3.json')
