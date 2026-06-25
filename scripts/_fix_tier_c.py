import pandas as pd

df = pd.read_csv('data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv')

# ---- 1. NAXITAMAB: Tier C → Tier A, 8%, FDA PI DANYELZA ----
idx = df[df['antibody_name'] == 'Naxitamab'].index[0]
df.loc[idx, 'evidence_tier'] = 'A'
df.loc[idx, 'evidence_source'] = 'FDA PI (DANYELZA, BLA 761183)'
df.loc[idx, 'citation_urls'] = 'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=29a80c6b-8bad-4650-8c7f-f18490c868ec'
df.loc[idx, 'ada_source_url_primary'] = 'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=29a80c6b-8bad-4650-8c7f-f18490c868ec'
df.loc[idx, 'ada_source_type_curated'] = 'FDA_PI'
df.loc[idx, 'ada_has_text_evidence'] = 1
print(f'[1] Naxitamab → Tier A (row {idx})')

# ---- 2. ROZANOLIXIZUMAB: Tier C → Tier A, corrected 15%→37%, FDA PI RYSTIGGO ----
idx = df[df['antibody_name'] == 'Rozanolixizumab'].index[0]
df.loc[idx, 'evidence_tier'] = 'A'
df.loc[idx, 'ada_first_pct'] = 37.0
df.loc[idx, 'ada_value_display'] = '37%'
df.loc[idx, 'evidence_source'] = 'FDA PI (RYSTIGGO, BLA 761286); MycarinG §12.6, n=133'
df.loc[idx, 'citation_urls'] = 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10590285/'
df.loc[idx, 'ada_source_url_primary'] = 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10590285/'
df.loc[idx, 'ada_source_pmids'] = '37656420'
df.loc[idx, 'ada_source_type_curated'] = 'FDA_PI'
df.loc[idx, 'ada_has_text_evidence'] = 1
df.loc[idx, 'ada_evidence_chain_excerpt'] = 'ADAs detected in 37% and nAbs in 21% of 133 patients after one 6-week cycle (MycarinG, FDA PI §12.6)'
print(f'[2] Rozanolixizumab → Tier A, ADA 15%→37% (row {idx})')

# ---- 3. ETESEVIMAB: DELETE (EUA only, revoked, no standard FDA PI) ----
idx_ete = df[df['antibody_name'] == 'Etesevimab'].index[0]
df = df.drop(index=idx_ete).reset_index(drop=True)
print('[3] Etesevimab deleted')

# ---- 4. RETIFANLIMAB: Tier C → Tier B, FDA PI URL attached ----
idx = df[df['antibody_name'] == 'Retifanlimab'].index[0]
df.loc[idx, 'evidence_tier'] = 'B'
df.loc[idx, 'evidence_source'] = 'FDA PI (ZYNYZ, BLA 761334); §12.6 ADA % not disclosed; 2.8% modeled from anti-PD-1 class'
df.loc[idx, 'citation_urls'] = 'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=109648d0-d30a-42fc-8273-39cb1540a751'
df.loc[idx, 'ada_source_url_primary'] = 'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=109648d0-d30a-42fc-8273-39cb1540a751'
df.loc[idx, 'ada_source_type_curated'] = 'FDA_PI_partial'
df.loc[idx, 'ada_has_text_evidence'] = 0
print(f'[4] Retifanlimab → Tier B (row {idx})')

# ---- 5. RELATLIMAB: Tier C → Tier B, OPDUALAG PI URL attached ----
idx = df[df['antibody_name'] == 'Relatlimab'].index[0]
df.loc[idx, 'evidence_tier'] = 'B'
df.loc[idx, 'evidence_source'] = 'FDA PI (OPDUALAG, BLA 761234); ADA % not extracted from §12.6; <2% modeled'
df.loc[idx, 'citation_urls'] = 'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=b22c9d83-3256-4e17-85f7-f331a504adc6'
df.loc[idx, 'ada_source_url_primary'] = 'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=b22c9d83-3256-4e17-85f7-f331a504adc6'
df.loc[idx, 'ada_source_type_curated'] = 'FDA_PI_partial'
df.loc[idx, 'ada_has_text_evidence'] = 0
print(f'[5] Relatlimab → Tier B (row {idx})')

# ---- 6. OLOKIZUMAB: Tier C → Tier B, CREDO 3 ARD paper ----
idx = df[df['antibody_name'] == 'Olokizumab'].index[0]
df.loc[idx, 'evidence_tier'] = 'B'
df.loc[idx, 'evidence_source'] = 'Feist et al. ARD 2022 (CREDO 3, PMID 36109142); exact ADA % not in abstract; 10-15% estimated'
df.loc[idx, 'citation_urls'] = 'https://pmc.ncbi.nlm.nih.gov/articles/PMC9664111/'
df.loc[idx, 'ada_source_url_primary'] = 'https://pmc.ncbi.nlm.nih.gov/articles/PMC9664111/'
df.loc[idx, 'ada_source_pmids'] = '36109142'
df.loc[idx, 'ada_source_type_curated'] = 'journal_paper'
df.loc[idx, 'ada_has_text_evidence'] = 0
print(f'[6] Olokizumab → Tier B (row {idx})')

df.to_csv('data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv', index=False)
print(f'\nSaved. Total rows: {len(df)}')
print(f'Remaining Tier C rows: {len(df[df["evidence_tier"] == "C"])}')

verify_names = ['Naxitamab','Rozanolixizumab','Retifanlimab','Relatlimab','Olokizumab']
print(df[df['antibody_name'].isin(verify_names)][
    ['antibody_name','ada_first_pct','ada_value_display','evidence_tier']
].to_string())
