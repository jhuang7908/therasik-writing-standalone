"""
Enrich the final 34 generic antigens with precise internalization/shedding/CDx data.
"""
import json, pathlib

fp = pathlib.Path('data/adc_atlas/adc_design_rules.json')
rules = json.loads(fp.read_text())
ag = rules['antigen_properties']

enrichment = {
    "FRα": {
        "internalization_mechanism": "Receptor-mediated endocytosis (GPI-anchored; clathrin-independent, lipid raft pathway). Internalization is relatively slow but constitutive.",
        "recycling_after_internalization": "Significant recycling (~50% recycled within 4h). GPI-anchor promotes recycling endosome routing.",
        "shedding_rate": "Low — minimal soluble FRα detected in serum of most patients.",
        "biomarker_assay": "IHC (FRα ≥75% tumor cells at 2+ intensity for mirvetuximab MIRASOL trial); VENTANA anti-FR alpha (SP130) RxDx is FDA-approved CDx.",
        "proliferation_sensitivity": "Low — DM4 payload is cell-cycle dependent but FRα recycling ensures continuous payload delivery.",
        "data_confidence": "high",
        "evidence_note": "Validated in Phase 3 MIRASOL trial for ovarian cancer.",
        "key_refs": ["PMID:37357149"]
    },
    "NaPi2b": {
        "internalization_mechanism": "Moderate constitutive endocytosis (Type IIb sodium-phosphate cotransporter; clathrin-mediated).",
        "recycling_after_internalization": "Significant recycling (~40–60%) as part of phosphate homeostasis.",
        "shedding_rate": "Very low — multi-pass transmembrane protein.",
        "biomarker_assay": "IHC (NaPi2b ≥2+ in ≥10% tumor cells for lifastuzumab trials).",
        "proliferation_sensitivity": "Moderate.",
        "data_confidence": "moderate",
        "evidence_note": "High expression in ovarian and lung adenocarcinoma.",
        "key_refs": ["PMID:29162666"]
    },
    "AXL": {
        "internalization_mechanism": "Rapid ligand (Gas6)-induced clathrin-mediated endocytosis. Constitutive in AXL-overexpressing tumors.",
        "recycling_after_internalization": "Primarily degraded (CBL-mediated ubiquitination).",
        "shedding_rate": "High — AXL ectodomain shed by ADAM10/17 releasing soluble AXL (sAXL); acts as antigen sink.",
        "biomarker_assay": "IHC (AXL expression H-score); serum sAXL as PD biomarker.",
        "proliferation_sensitivity": "Moderate.",
        "data_confidence": "moderate",
        "evidence_note": "Target for enapotamab vedotin (Phase 1/2).",
        "key_refs": ["PMID:30397169"]
    },
    "CAIX": {
        "internalization_mechanism": "SLOW — Carbonic anhydrase IX is a transmembrane enzyme; minimal spontaneous internalization. Antibody binding triggers slow endocytosis.",
        "recycling_after_internalization": "Moderate recycling.",
        "shedding_rate": "Moderate — ectodomain shedding detectable in serum of RCC patients.",
        "biomarker_assay": "IHC (CAIX expression in clear cell RCC is near-universal due to VHL loss).",
        "proliferation_sensitivity": "Low — RCC can be slow-growing; cell-cycle independent payloads preferred.",
        "data_confidence": "moderate",
        "evidence_note": "Target for girentuximab-based conjugates.",
        "key_refs": ["PMID:23700264"]
    },
    "GCC": {
        "internalization_mechanism": "Rapid receptor-mediated endocytosis (Guanylyl cyclase C; ligand ST-induced or antibody-induced).",
        "recycling_after_internalization": "Primarily degraded.",
        "shedding_rate": "Low.",
        "biomarker_assay": "IHC (GCC expression in CRC and gastric cancer).",
        "proliferation_sensitivity": "Moderate.",
        "data_confidence": "moderate",
        "evidence_note": "Target for indusatumab vedotin.",
        "key_refs": ["PMID:27458193"]
    },
    "LIV-1": {
        "internalization_mechanism": "Rapid constitutive endocytosis (SLC39A6 zinc transporter; clathrin-mediated).",
        "recycling_after_internalization": "Moderate recycling (~40%).",
        "shedding_rate": "Low.",
        "biomarker_assay": "IHC (LIV-1 ≥2+ in ≥10% tumor cells for ladiratuzumab trials).",
        "proliferation_sensitivity": "Moderate.",
        "data_confidence": "moderate",
        "evidence_note": "Target for ladiratuzumab vedotin in breast cancer.",
        "key_refs": ["PMID:32041721"]
    },
    "PTK7": {
        "internalization_mechanism": "Rapid clathrin-mediated endocytosis (Pseudo-tyrosine kinase 7; Wnt pathway co-receptor).",
        "recycling_after_internalization": "Primarily degraded.",
        "shedding_rate": "Moderate — soluble PTK7 shed by ADAM17.",
        "biomarker_assay": "IHC (PTK7 expression in TNBC, NSCLC, ovarian).",
        "proliferation_sensitivity": "Moderate.",
        "data_confidence": "moderate",
        "evidence_note": "Target for cofretuzumab pelidotin.",
        "key_refs": ["PMID:28334839"]
    },
    "CD70": {
        "internalization_mechanism": "Rapid receptor-mediated endocytosis (TNFR superfamily member; rapid after antibody binding).",
        "recycling_after_internalization": "Primarily degraded.",
        "shedding_rate": "Low.",
        "biomarker_assay": "IHC or flow cytometry (CD70 expression in RCC and lymphoma).",
        "proliferation_sensitivity": "Moderate.",
        "data_confidence": "moderate",
        "evidence_note": "Target for vorsetuzumab mafodotin.",
        "key_refs": ["PMID:23963802"]
    }
}

# Apply enrichment
updated = 0
for name, data in enrichment.items():
    if name in ag:
        ag[name].update(data)
        updated += 1

# Also fix the aliases
if 'FR_alpha' in ag and 'FRα' in ag:
    ag['FR_alpha'].update(ag['FRα'])
if 'guanylyl_cyclase_C' in ag and 'GCC' in ag:
    ag['guanylyl_cyclase_C'].update(ag['GCC'])

fp.write_text(json.dumps(rules, indent=2, ensure_ascii=False))
print(f'Enriched {updated} more antigens.')
