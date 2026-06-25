"""
ADA Database Expansion Audit - Corrected v2
Uses Est. Status column correctly.
"""
import pandas as pd
import os

EXCEL = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\thera_sabdab\TheraSAbDab_SeqStruc_OnlineDownload.xlsx'
MASTER_CSV = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_master_136_curated.csv'
OUT_DIR = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\reports'
os.makedirs(OUT_DIR, exist_ok=True)

print("Loading TheraSAbDab Excel...")
df = pd.read_excel(EXCEL)
print(f"  Total records: {len(df)}")
print(f"  Est. Status counts:\n{df['Est. Status'].value_counts().to_string()}")

master_df = pd.read_csv(MASTER_CSV)
existing = set(master_df['antibody_name'].str.lower().str.strip())
print(f"\n  Existing ADA panel: {len(existing)} antibodies")

# Fix: use Est. Status column properly
disc = df[
    (df['Est. Status'] == 'Discontinued') &
    df['HeavySequence'].notna() &
    (~df['Therapeutic'].str.lower().str.strip().isin(existing))
].copy()

approved_new = df[
    (df['Est. Status'] == 'Approved') &
    df['HeavySequence'].notna() &
    (~df['Therapeutic'].str.lower().str.strip().isin(existing))
].copy()

print(f"\n[RESULT] Discontinued (with seq, not in 138): {len(disc)}")
print(f"[RESULT] Approved but not in 138 (expansion candidates): {len(approved_new)}")

# Stage breakdown of discontinued
stage_col = "Highest_Clin_Trial (Feb '25)"
stage_counts = disc[stage_col].value_counts()
print(f"\nDiscontinued stage breakdown:")
print(stage_counts.to_string())

# High-value: Ph2/Ph3 discontinued
disc_ph23 = disc[disc[stage_col].str.contains('Phase-II|Phase-III', na=False, case=False)]
print(f"\nPhase II/III discontinued (highest value for AI negative samples): {len(disc_ph23)}")

# Save discontinuted candidates
disc_cols = ['Therapeutic', 'Target', 'Format', stage_col,
             'Conditions Discontinued', 'HeavySequence', 'LightSequence',
             'Genetics (Bispecifics delimited with semicolon)']
disc_save = disc[disc_cols].rename(columns={
    'Therapeutic': 'antibody_name',
    'Target': 'target',
    'Format': 'format',
    stage_col: 'highest_trial',
    'Conditions Discontinued': 'disc_conditions',
    'HeavySequence': 'heavy_seq',
    'LightSequence': 'light_seq',
    'Genetics (Bispecifics delimited with semicolon)': 'genetics'
})
disc_path = os.path.join(OUT_DIR, 'ADA_Negative_Candidates_Discontinued.csv')
disc_save.to_csv(disc_path, index=False, encoding='utf-8')
print(f"\nSaved {len(disc_save)} negative candidates -> {disc_path}")

# Save expansion candidates
exp_cols = ['Therapeutic', 'Target', 'Format', stage_col,
            'Conditions Approved', 'HeavySequence', 'LightSequence',
            'Genetics (Bispecifics delimited with semicolon)']
exp_save = approved_new[exp_cols].rename(columns={
    'Therapeutic': 'antibody_name',
    'Target': 'target',
    'Format': 'format',
    stage_col: 'highest_trial',
    'Conditions Approved': 'approved_conditions',
    'HeavySequence': 'heavy_seq',
    'LightSequence': 'light_seq',
    'Genetics (Bispecifics delimited with semicolon)': 'genetics'
})
exp_path = os.path.join(OUT_DIR, 'ADA_Positive_Expansion_Candidates.csv')
exp_save.to_csv(exp_path, index=False, encoding='utf-8')
print(f"Saved {len(exp_save)} expansion candidates -> {exp_path}")

# ===== TARGET-LEVEL ADA BASELINE =====
if 'target_curated' in master_df.columns:
    master_df['ada_first_pct'] = pd.to_numeric(master_df['ada_first_pct'], errors='coerce')
    target_stats = master_df.groupby('target_curated')['ada_first_pct'].agg(
        mean_ada='mean', n='count', max_ada='max'
    ).sort_values('mean_ada', ascending=False)
    print(f"\nTop 15 highest-ADA targets in current 138 panel:")
    print(target_stats.head(15).round(1).to_string())

# ===== GENERATE MARKDOWN REPORT =====
md_path = os.path.join(OUT_DIR, 'ADA_Expansion_Audit_2026.md')
with open(md_path, 'w', encoding='utf-8') as f:
    f.write("# ADA  v2\n\n")
    f.write("****: TheraSAbDab SeqStruc (Feb 2025)  \n")
    f.write("** ADA Panel**: 138  (Tier A/B )  \n")
    f.write("****: 2026-04  \n\n")
    f.write("---\n\n")

    f.write("## 1. \n\n")
    f.write("|  |  |\n|------|------|\n")
    f.write(f"| TheraSAbDab  | {len(df)} |\n")
    f.write(f"|  Heavy+Light  | {len(df[df['HeavySequence'].notna() & df['LightSequence'].notna()])} |\n")
    f.write(f"| ** (Discontinued) +  + ** | **{len(disc)}** |\n")
    f.write(f"|  Phase II/III （） | {len(disc_ph23)} |\n")
    f.write(f"| ** (Approved) +  + ** | **{len(approved_new)}** |\n\n")

    f.write("> [!IMPORTANT]\n")
    f.write(f">  **{len(approved_new)}**  FDA PI §12.6， ADA Panel  138  **{138 + len(approved_new)}+**。\n")
    avoid_str = ""
    f.write(f">  **{len(disc_ph23)}**  Phase II/III ， AI {avoid_str}。\n\n")

    f.write("---\n\n")
    f.write("## 2. （）\n\n")
    f.write("|  |  |\n|------|------|\n")
    for stage, cnt in stage_counts.items():
        f.write(f"| {stage} | {cnt} |\n")

    f.write("\n\n## 3. （30）\n\n")
    f.write("*、、138 Panel*\n\n")
    preview = exp_save[['antibody_name', 'target', 'genetics', 'approved_conditions']].head(30)
    f.write(preview.to_markdown(index=False))
    f.write(f"\n\n*... {len(exp_save)} ， ADA_Positive_Expansion_Candidates.csv*\n\n")

    f.write("---\n\n")
    f.write("## 4. ——（30）\n\n")
    f.write("* Phase II/III 、， AI \"\" *\n\n")
    prev_disc = disc_save[['antibody_name', 'target', 'genetics', 'highest_trial', 'disc_conditions']].head(30)
    f.write(prev_disc.to_markdown(index=False))
    f.write(f"\n\n*... {len(disc_save)} ， ADA_Negative_Candidates_Discontinued.csv*\n\n")

    f.write("---\n\n")
    f.write("## 5. \n\n")
    f.write("1. ** A（2）**： Approved  FDA PI §12.6， +50  Tier A \n")
    f.write("2. ** B（1）**： Phase III （），\n")
    f.write("3. ** C（）**： + HLA （ hla_freq_population.json）\n")

print(f"\nMarkdown report -> {md_path}")
print("=== AUDIT v2 COMPLETE ===")
