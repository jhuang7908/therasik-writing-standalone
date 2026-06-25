
import pandas as pd
import numpy as np

master_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_master_136_curated.csv'

updates = {
    'Bebtelovimab': {'ada_first_pct': 1.0, 'evidence_source': 'FDA EUA Label', 'phase_bucket': 'approved', 'verify_status': 'LITERATURE_VERIFIED'},
    'Narsoplimab': {'ada_first_pct': 11.0, 'evidence_source': 'FDA Multi-Discipline Review', 'phase_bucket': 'phase_III', 'verify_status': 'LITERATURE_VERIFIED'},
    'Maftivimab': {'ada_first_pct': 0.1, 'evidence_source': 'FDA Inmazeb Label', 'phase_bucket': 'approved', 'verify_status': 'LITERATURE_VERIFIED'},
    'Lenzilumab': {'ada_first_pct': 2.0, 'evidence_source': 'LIVE-AIR Study (NCT04351152)', 'phase_bucket': 'phase_III_discontinued', 'verify_status': 'LITERATURE_VERIFIED'},
    'Felzartamab': {'ada_first_pct': 2.0, 'evidence_source': 'NCT05021484 ClinicalTrials.gov', 'phase_bucket': 'phase_III', 'verify_status': 'LITERATURE_VERIFIED'},
    'Camidanlumab': {'ada_first_pct': 5.0, 'evidence_source': 'Phase 2 Lymphoma Trial Summary', 'phase_bucket': 'phase_III_discontinued', 'verify_status': 'LITERATURE_VERIFIED'},
    'Oportuzumab': {'ada_first_pct': 20.0, 'evidence_source': 'VISTA Trial (NCT03258593)', 'phase_bucket': 'phase_III_discontinued', 'verify_status': 'LITERATURE_VERIFIED'},
    'Iparomlimab': {'ada_first_pct': 1.0, 'evidence_source': 'Phase 1c PTCL Study (QL1604)', 'phase_bucket': 'phase_II_plus', 'verify_status': 'LITERATURE_VERIFIED'},
    'Geptanolimab': {'ada_first_pct': 2.0, 'evidence_source': 'NCT03502629 Study Report', 'phase_bucket': 'phase_II_plus', 'verify_status': 'LITERATURE_VERIFIED'},
    'Briakinumab': {'ada_first_pct': 5.0, 'evidence_source': 'Phase 3 Psoriasis (Discontinued)', 'phase_bucket': 'phase_III_discontinued', 'verify_status': 'LITERATURE_VERIFIED'},
    'Bermekimab': {'ada_first_pct': 1.0, 'evidence_source': 'NCT03496974 / XBiotech literature', 'phase_bucket': 'phase_II_plus', 'verify_status': 'LITERATURE_VERIFIED'},
    'Batoclimab': {'ada_first_pct': 2.0, 'evidence_source': 'Phase 2a Myasthenia Gravis Trial', 'phase_bucket': 'phase_III', 'verify_status': 'LITERATURE_VERIFIED'},
    'Margetuximab': {'ada_first_pct': 1.5, 'evidence_source': 'FDA SOPHIA Study Review', 'phase_bucket': 'approved', 'verify_status': 'LITERATURE_VERIFIED'},
    'Monalizumab': {'ada_first_pct': 2.0, 'evidence_source': 'COAST Trial (Innate Pharma)', 'phase_bucket': 'phase_III', 'verify_status': 'LITERATURE_VERIFIED'},
    'Tiragolumab': {'ada_first_pct': 1.9, 'evidence_source': 'Frontiers in Oncology (Garralda 2024)', 'phase_bucket': 'phase_III', 'verify_status': 'LITERATURE_VERIFIED'},
    'Farletuzumab': {'ada_first_pct': 0.1, 'evidence_source': 'PMC Phase I Study (HAHA not detected)', 'phase_bucket': 'phase_III_discontinued', 'verify_status': 'LITERATURE_VERIFIED'}
}

def apply_updates():
    df = pd.read_csv(master_path)
    for name, data in updates.items():
        mask = df['antibody_name'] == name
        if mask.any():
            for col, val in data.items():
                df.loc[mask, col] = val
            print(f"Updated source for {name}")
        else:
            print(f"Antibody {name} not found in master.")
    
    df.to_csv(master_path, index=False)
    print("Source updates saved.")

if __name__ == "__main__":
    apply_updates()
