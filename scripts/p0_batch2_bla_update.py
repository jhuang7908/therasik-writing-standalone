"""
P0 Batch 2: BLA Sourcing for 30 additional FDA-approved antibodies
All BLA numbers verified from FDA.gov search results
"""
import pandas as pd
import numpy as np

file_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada245\database\ada_master_245_curated.csv'
df = pd.read_csv(file_path)

for col in ['bla_number', 'trial_n_ada_evaluated', 'nab_pct', 'ada_source_section']:
    if col not in df.columns:
        df[col] = np.nan

# ============================================================
# BATCH 2: 30 FDA-APPROVED ANTIBODIES - VERIFIED BLA NUMBERS
# Source: FDA.gov Drugs@FDA / Purple Book (verified 2026-05-11)
# ============================================================
p0_batch2 = {
    'Brodalumab': {
        'bla_number': 'BLA 761032',
        'ada_source_section': 'SILIQ USPI Section 6.1',
        'verify_note': 'BLA 761032 (Siliq): Anti-IL-17RA. ADA incidence reported in psoriasis trials.'
    },
    'Burosumab': {
        'bla_number': 'BLA 761068',
        'ada_source_section': 'CRYSVITA USPI Section 6.1',
        'verify_note': 'BLA 761068 (Crysvita): Anti-FGF23. XLH indication.'
    },
    'Canakinumab': {
        'bla_number': 'BLA 125319',
        'ada_source_section': 'ILARIS USPI Section 6.1',
        'verify_note': 'BLA 125319 (Ilaris): Anti-IL-1b. Low immunogenicity in CAPS/SJIA.'
    },
    'Erenumab': {
        'bla_number': 'BLA 761077',
        'ada_source_section': 'AIMOVIG USPI Section 6.1',
        'verify_note': 'BLA 761077 (Aimovig): Anti-CGRP receptor. ~6.3% ADA in migraine trials.'
    },
    'Golimumab': {
        'bla_number': 'BLA 125289',
        'ada_source_section': 'SIMPONI USPI Section 6.1',
        'verify_note': 'BLA 125289 (Simponi): Anti-TNF. ~4% ADA in RA. Lower with MTX.'
    },
    'Lanadelumab': {
        'bla_number': 'BLA 761090',
        'ada_source_section': 'TAKHZYRO USPI Section 6.1',
        'verify_note': 'BLA 761090 (Takhzyro): Anti-kallikrein. ~3% ADA in HAE trials.'
    },
    'Ofatumumab': {
        'bla_number': 'BLA 125326',
        'ada_source_section': 'KESIMPTA USPI Section 6.1',
        'verify_note': 'BLA 125326 (Arzerra/Kesimpta): Anti-CD20. Very low ADA due to B-cell depletion.'
    },
    'Panitumumab': {
        'bla_number': 'BLA 125147',
        'ada_source_section': 'VECTIBIX USPI Section 6.1',
        'verify_note': 'BLA 125147 (Vectibix): Anti-EGFR. ~3.2% ADA. Fully human origin (XenoMouse).'
    },
    'Sarilumab': {
        'bla_number': 'BLA 761037',
        'ada_source_section': 'KEVZARA USPI Section 6.1',
        'verify_note': 'BLA 761037 (Kevzara): Anti-IL-6R. ~5.6% ADA in RA trials. NAb in ~1%.'
    },
    'Emicizumab': {
        'bla_number': 'BLA 761083',
        'ada_source_section': 'HEMLIBRA USPI Section 6.1',
        'verify_note': 'BLA 761083 (Hemlibra): Bispecific FIXa/FX. ~5% ADA. Some NAbs with clinical impact.'
    },
    'Ixekizumab': {
        'bla_number': 'BLA 125521',
        'ada_source_section': 'TALTZ USPI Section 6.1',
        'verify_note': 'BLA 125521 (Taltz): Anti-IL-17A. ~9-17% ADA in psoriasis. NAb in ~1%.'
    },
    'Ranibizumab': {
        'bla_number': 'BLA 125156',
        'ada_source_section': 'LUCENTIS USPI Section 6.1',
        'verify_note': 'BLA 125156 (Lucentis): Anti-VEGF Fab. ~1-6% ADA in nAMD trials.'
    },
    'Ravulizumab': {
        'bla_number': 'BLA 761108',
        'ada_source_section': 'ULTOMIRIS USPI Section 6.1',
        'verify_note': 'BLA 761108 (Ultomiris): Anti-C5. Very low ADA (<0.4%).'
    },
    'Reslizumab': {
        'bla_number': 'BLA 761033',
        'ada_source_section': 'CINQAIR USPI Section 6.1',
        'verify_note': 'BLA 761033 (Cinqair): Anti-IL-5. ~5% ADA in asthma. No NAb detected.'
    },
    'Romosozumab': {
        'bla_number': 'BLA 761062',
        'ada_source_section': 'EVENITY USPI Section 6.1',
        'verify_note': 'BLA 761062 (Evenity): Anti-sclerostin. ~18% binding ADA, ~3% NAb in osteoporosis.'
    },
    'Belimumab': {
        'bla_number': 'BLA 125370',
        'ada_source_section': 'BENLYSTA USPI Section 6.1',
        'verify_note': 'BLA 125370 (Benlysta IV): Anti-BAFF. ~0.7% ADA in SLE trials.'
    },
    'Daratumumab': {
        'bla_number': 'BLA 761036',
        'ada_source_section': 'DARZALEX USPI Section 6.1',
        'verify_note': 'BLA 761036 (Darzalex): Anti-CD38. <0.1% ADA in myeloma trials. Fully human.'
    },
    'Evolocumab': {
        'bla_number': 'BLA 125522',
        'ada_source_section': 'REPATHA USPI Section 6.1',
        'verify_note': 'BLA 125522 (Repatha): Anti-PCSK9. 0.3% binding ADA, 0% NAb. Fully human.'
    },
    'Ramucirumab': {
        'bla_number': 'BLA 125477',
        'ada_source_section': 'CYRAMZA USPI Section 6.1',
        'verify_note': 'BLA 125477 (Cyramza): Anti-VEGFR2. ~3% ADA in gastric/NSCLC trials.'
    },
    'Fremanezumab': {
        'bla_number': 'BLA 761089',
        'ada_source_section': 'AJOVY USPI Section 6.1',
        'verify_note': 'BLA 761089 (Ajovy): Anti-CGRP. ~1% ADA in migraine. Very low immunogenicity.'
    },
    'Galcanezumab': {
        'bla_number': 'BLA 761063',
        'ada_source_section': 'EMGALITY USPI Section 6.1',
        'verify_note': 'BLA 761063 (Emgality): Anti-CGRP. ~4.8% ADA. ~3% NAb. Minimal PK impact.'
    },
    'Certolizumab': {
        'bla_number': 'BLA 125160',
        'ada_source_section': 'CIMZIA USPI Section 6.1',
        'verify_note': 'BLA 125160 (Cimzia): Anti-TNF PEG-Fab. ~8% ADA in RA. PEG moiety may contribute.'
    },
    'Faricimab': {
        'bla_number': 'BLA 761235',
        'ada_source_section': 'VABYSMO USPI Section 6.1',
        'verify_note': 'BLA 761235 (Vabysmo): Bispecific VEGF-A/Ang-2. ~10% ADA in nAMD/DME.'
    },
    'Lecanemab': {
        'bla_number': 'BLA 761269',
        'ada_source_section': 'LEQEMBI USPI Section 6.1',
        'verify_note': 'BLA 761269 (Leqembi): Anti-Abeta. ~15% ADA in Clarity AD study.'
    },
    'Donanemab': {
        'bla_number': 'BLA 761248',
        'ada_source_section': 'KISUNLA USPI Section 6.1',
        'verify_note': 'BLA 761248 (Kisunla): Anti-Abeta pGlu3. ~25% ADA. High-titer subset with faster clearance.'
    },
    'Spesolimab': {
        'bla_number': 'BLA 761244',
        'ada_source_section': 'SPEVIGO USPI Section 6.1',
        'verify_note': 'BLA 761244 (Spevigo): Anti-IL-36R. ~24% ADA. NAb in subset.'
    },
    'Teplizumab': {
        'bla_number': 'BLA 761183',
        'ada_source_section': 'TZIELD USPI Section 6.1',
        'verify_note': 'BLA 761183 (Tzield): Anti-CD3. ~5% ADA. First-in-class T1D delay.'
    },
    'Mirikizumab': {
        'bla_number': 'BLA 761279',
        'ada_source_section': 'OMVOH USPI Section 6.1',
        'verify_note': 'BLA 761279 (Omvoh): Anti-IL-23p19. ~18% ADA. Reduced trough in high-titer patients.'
    },
    'Retifanlimab': {
        'bla_number': 'BLA 761334',
        'ada_source_section': 'ZYNYZ USPI Section 6.1',
        'verify_note': 'BLA 761334 (Zynyz): Anti-PD-1. ~4.1% ADA. Low immunogenicity.'
    },
    'Dostarlimab': {
        'bla_number': 'BLA 761174',
        'ada_source_section': 'JEMPERLI USPI Section 6.1',
        'verify_note': 'BLA 761174 (Jemperli): Anti-PD-1. ~2.1% ADA. No PK impact.'
    },
}

# Apply updates
updated = 0
for name, fields in p0_batch2.items():
    mask = df['antibody_name'] == name
    if mask.any():
        for col, val in fields.items():
            if val is not None:
                df.loc[mask, col] = val
        updated += 1
    else:
        print(f"  [WARN] {name} not found in database.")

# Final stats
total = len(df)
bla_filled = df['bla_number'].notna().sum()
nab_filled = df['nab_pct'].notna().sum()

print(f"\n=== P0 Batch 2 Summary ===")
print(f"Entries updated this batch: {updated}")
print(f"Total BLA Numbers filled: {bla_filled} / {total} ({bla_filled/total:.1%})")
print(f"Total NAb% filled: {nab_filled} / {total} ({nab_filled/total:.1%})")

df.to_csv(file_path, index=False)
print("P0 Batch 2 Complete.")
