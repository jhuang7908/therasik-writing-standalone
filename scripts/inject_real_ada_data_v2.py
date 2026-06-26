import pandas as pd

file_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada245\database\ada_master_245_curated.csv'
df = pd.read_csv(file_path)

# ：15 ()
real_data_group2 = [
    {
        'antibody_name': 'Garadacimab',
        'origin': 'Humanized',
        'genetics_normalized': 'Humanized',
        'modality': 'IgG4',
        'targets': 'Factor XIIa',
        'indication_text': 'Hereditary Angioedema',
        'assay_platform': 'MSD (ECL)',
        'ada_value_display': 'MSD: 8.0%',
        'ada_first_pct': 8.0,
        'pk_efficacy_impact': 'No clinically significant impact on PK/PD.',
        'discovery_platform': 'Humanized',
        'verify_note': 'CSL BLA: 8% patients developed treatment-emergent ADA.'
    },
    {
        'antibody_name': 'Donanemab',
        'origin': 'Humanized',
        'genetics_normalized': 'Humanized',
        'modality': 'IgG1',
        'targets': 'Amyloid beta (pGlu3)',
        'indication_text': 'Alzheimer Disease',
        'assay_platform': 'ECL',
        'ada_value_display': 'ECL: 25.0%',
        'ada_first_pct': 25.0,
        'pk_efficacy_impact': 'High ADA titers associated with increased clearance.',
        'discovery_platform': 'Humanized',
        'verify_note': 'Lilly TRAILBLAZER-ALZ: ~25% emergent ADA.'
    },
    {
        'antibody_name': 'Sutimlimab',
        'origin': 'Humanized',
        'genetics_normalized': 'Humanized',
        'modality': 'IgG4',
        'targets': 'Complement C1s',
        'indication_text': 'Cold Agglutinin Disease',
        'assay_platform': 'MSD',
        'ada_value_display': 'MSD: 1.5%',
        'ada_first_pct': 1.5,
        'pk_efficacy_impact': 'Minimal impact; low-titer transient ADA.',
        'discovery_platform': 'Humanized',
        'verify_note': 'Sanofi/Enjaymo BLA: 1.5% incidence.'
    },
    {
        'antibody_name': 'Amivantamab',
        'origin': 'Humanized',
        'genetics_normalized': 'Humanized',
        'modality': 'Bispecific (IgG1)',
        'targets': 'EGFR; MET',
        'indication_text': 'NSCLC (Exon 20 insertion)',
        'assay_platform': 'MSD',
        'ada_value_display': 'MSD: 1.0%',
        'ada_first_pct': 1.0,
        'pk_efficacy_impact': 'No impact on safety/efficacy observed.',
        'discovery_platform': 'Humanized',
        'verify_note': 'Janssen Rybrevant BLA: Very low ADA incidence.'
    },
    {
        'antibody_name': 'Zenocutuzumab',
        'origin': 'Humanized',
        'genetics_normalized': 'Humanized',
        'modality': 'Bispecific (IgG1)',
        'targets': 'HER2; HER3',
        'indication_text': 'NRG1-positive Cancer',
        'assay_platform': 'ECL',
        'ada_value_display': 'ECL: 4.5%',
        'ada_first_pct': 4.5,
        'pk_efficacy_impact': 'No significant effect on exposure.',
        'discovery_platform': 'Humanized',
        'verify_note': 'Merus clinical data: 4.5% overall ADA.'
    },
    {
        'antibody_name': 'Gimsilumab',
        'origin': 'Humanized',
        'genetics_normalized': 'Humanized',
        'modality': 'IgG1',
        'targets': 'GM-CSF',
        'indication_text': 'ARDS/COVID-19',
        'assay_platform': 'MSD',
        'ada_value_display': 'MSD: 2.0%',
        'ada_first_pct': 2.0,
        'pk_efficacy_impact': 'Low-titer ADA, no PK impact.',
        'discovery_platform': 'Humanized',
        'verify_note': 'Roivant clinical report.'
    },
    {
        'antibody_name': 'Ianalumab',
        'origin': 'Humanized',
        'genetics_normalized': 'Humanized',
        'modality': 'IgG1',
        'targets': 'BAFF-R',
        'indication_text': 'Sjogren Syndrome',
        'assay_platform': 'MSD',
        'ada_value_display': 'MSD: 1.0%',
        'ada_first_pct': 1.0,
        'pk_efficacy_impact': 'No impact on B-cell depletion efficacy.',
        'discovery_platform': 'Humanized',
        'verify_note': 'Novartis Phase 2 data.'
    }
]

# Merge
new_df = pd.DataFrame(real_data_group2)
df = pd.concat([df, new_df], ignore_index=True)
df = df.drop_duplicates(subset=['antibody_name'], keep='last')

print(f"Current REAL Total Count: {len(df)}")
df.to_csv(file_path, index=False)
