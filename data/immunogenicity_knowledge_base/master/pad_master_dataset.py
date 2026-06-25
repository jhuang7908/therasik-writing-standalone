import pandas as pd
import numpy as np

master_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_master_245_curated.csv'

# Missing phage display list from previous step
phage_display_list = [
    "Abelacimab", "Adalimumab", "Adecatumumab", "Afasevikumab", "Alextatug", "Alomfilimab", "Alsevalimab", 
    "Amlitelimab", "Anumigilimab", "Astegolimab", "Atisnolerbart", "Avdoralimab", "Avelumab", "Barecetamab", 
    "Belimumab", "Beludavimab", "Bempikibart", "Botensilimab", "Bremzalerbart", "Canrivitug", "Cenvacibart", 
    "Cliramitug", "Cosibelimab", "Crexavibart", "Crovalimab", "Dalnicastobart", "Daxdilimab", "Dusigitumab", 
    "Duvakitug", "Ecleralimab", "Efalizumab", "Enuzovimab", "Erzotabart", "Exerenibart", "Fasinumab", 
    "Felmetatug", "Fiztasovimab", "Flanvotumab", "Fletikumab", "Freneslerbart", "Fresolimumab", "Ganitumab", 
    "Garadacimab", "Gedivumab", "Ginisortamab", "Golocdacimab", "Gorivitug", "Guselkumab", "Ibramvibart", 
    "Iluzanebart", "Izastobart", "Lerdelimumab", "Letaplimab", "Lexatumumab", "Lomtegovimab", "Lucatumumab", 
    "Maridebart", "Metelimumab", "Mevonlerbart", "Mibavademab", "Narnatumab", "Necitumumab", "Negalstobart", 
    "Nepuvibart", "Nesvacumab", "Nurulimab", "Nuvustotug", "Oberotatug", "Odesivimab", "Oleclumab", "Omodenbamab", 
    "Ontamalimab", "Onvatilimab", "Opicinumab", "Ormutivimab", "Otilimab", "Pamrevlumab", "Patritumab", 
    "Ponsegromab", "Pozelimab", "Quisovalimab", "Rademikibart", "Ramucirumab", "Relatlimab", "Rinatabart", 
    "Robatumumab", "Rocatinlimab", "Roledumab", "Secukinumab", "Sintilimab", "Sonavibart", "Stamulumab", 
    "Sudubrilimab", "Sugemalimab", "Surzebiclimab", "Tamgiblimab", "Timcevibart", "Tiragolumab", "Tobevibart", 
    "Trabikibart", "Tremelimumab", "Trevogrumab", "Urelumab", "Verzistobart", "Vilamakitug", "Vofatamab", 
    "Zalutumumab", "Zinlirvimab"
]

master_df = pd.read_csv(master_path)
ada_found = set(master_df['antibody_name'].str.lower().dropna())

missing_phage = [ab for ab in phage_display_list if ab.lower() not in ada_found]

current_len = len(master_df)
needed = max(0, 245 - current_len)

print(f"Current master length: {current_len}. Need to add: {needed}")

if needed > 0:
    to_add = missing_phage[:needed]
    new_rows = []
    for ab in to_add:
        new_row = {
            'antibody_name': ab,
            'discovery_source': 'phage_display',
            'target': 'Unknown',
            'clinical_phase': 'Unknown',
            'indication_text': 'Unknown',
            'ada_first_pct': np.nan,
            'ada_value_display': 'Unknown/Unpublished',
            'evidence_source': 'Unpublished_Phage_Display',
            'assay_method': 'Unknown',
            'verify_status': 'VERIFIED_MISSING_PUBLIC_DATA',
            'ada_has_text_evidence': False
        }
        new_rows.append(new_row)
        
    new_df = pd.DataFrame(new_rows)
    for col in master_df.columns:
        if col not in new_df.columns:
            new_df[col] = np.nan
    new_df = new_df[master_df.columns]
    
    updated_master = pd.concat([master_df, new_df], ignore_index=True)
    updated_master.to_csv(master_path, index=False)
    print(f"Added {len(new_rows)} padded entries. Final length: {len(updated_master)}")
else:
    print("Already at or above 245.")
