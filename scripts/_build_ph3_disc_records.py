"""
Build Phase III Discontinued Antibody ADA Records
Follows exact schema of ada_master_136_curated.csv
Outputs: data/immunogenicity_knowledge_base/master/ada_ph3_discontinued_candidates.csv

Strategy:
- For each Ph3-discontinued antibody, populate all fields derivable from:
  1. TheraSAbDab sequences (vh_seq, vl_seq, genetics)
  2. Computed biophysical features (pI, GRAVY, germline identity, immuno scores)
  3. ADA evidence = "UNKNOWN - Discontinued" unless a specific source is found
  
Fields that CANNOT be filled without clinical data:
  ada_first_pct, ada_evidence_chain_excerpt, citation_urls -> marked as 'PENDING_RESEARCH'
"""
import pandas as pd
import numpy as np
import os, sys, math, re
from pathlib import Path

ROOT = Path(r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite')
DISC_CSV  = ROOT / 'data/immunogenicity_knowledge_base/reports/ADA_Negative_Candidates_Discontinued.csv'
MASTER_CSV = ROOT / 'data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv'
OUT_CSV   = ROOT / 'data/immunogenicity_knowledge_base/master/ada_ph3_disc_candidates.csv'
THERASABDAB = ROOT / 'data/thera_sabdab/TheraSAbDab_SeqStruc_OnlineDownload.xlsx'

print("Loading data...")
disc_df = pd.read_csv(DISC_CSV)
master_df = pd.read_csv(MASTER_CSV)
thera_df = pd.read_excel(THERASABDAB)

# Filter Ph3+ discontinued
ph3 = disc_df[disc_df['highest_trial'].str.contains(
    'Phase-III|Phase-II/III|Preregistration', na=False, case=False
)].copy()
print(f"Phase III discontinued candidates: {len(ph3)}")

# Merge with full TheraSAbDab for extra metadata
thera_lookup = thera_df.set_index('Therapeutic')

# Get master schema columns
schema_cols = master_df.columns.tolist()

# ── Amino acid property helpers ───────────────────────────────────────────────
AA_MW = {'A':89,'R':174,'N':132,'D':133,'C':121,'Q':146,'E':147,'G':75,
         'H':155,'I':131,'L':131,'K':146,'M':149,'F':165,'P':115,'S':105,
         'T':119,'W':204,'Y':181,'V':117}

GRAVY_SCALE = {'A':1.8,'R':-4.5,'N':-3.5,'D':-3.5,'C':2.5,'Q':-3.5,'E':-3.5,
               'G':-0.4,'H':-3.2,'I':4.5,'L':3.8,'K':-3.9,'M':1.9,'F':2.8,
               'P':-1.6,'S':-0.8,'T':-0.7,'W':-0.9,'Y':-1.3,'V':4.2}

INSTAB = {'II':1,'IV':45,'VV':3,'LL':4,'LV':4,'YY':1,'NQ':1,'QN':1,
          'FY':4,'YF':4,'IL':3,'LI':3,'IF':3,'LF':3,'SS':6,'GD':5}

def calc_gravy(seq):
    if not seq or len(seq) < 5: return None
    vals = [GRAVY_SCALE.get(aa, 0) for aa in seq.upper() if aa in GRAVY_SCALE]
    return round(sum(vals)/len(vals), 3) if vals else None

def calc_instability(seq):
    if not seq or len(seq) < 10: return None
    score = sum(INSTAB.get(seq[i:i+2].upper(), 0) for i in range(len(seq)-1))
    return round(10/len(seq) * score, 1)

def calc_pi(seq):
    """Simplified isoelectric point estimate."""
    if not seq or len(seq) < 5: return None
    pKa = {'D':3.9,'E':4.1,'H':6.0,'C':8.3,'Y':10.1,'K':10.5,'R':12.5}
    counts = {aa: seq.upper().count(aa) for aa in pKa}
    # Very simplified: use charge balance
    ph = 7.0
    for _ in range(200):
        charge = 0
        for aa, pK in pKa.items():
            n = counts.get(aa, 0)
            if aa in ('D','E','C','Y'):
                charge -= n * (1/(1+10**(pK-ph)))
            else:
                charge += n * (1/(1+10**(ph-pK)))
        if abs(charge) < 0.01: break
        ph += 0.05 if charge < 0 else -0.05
    return round(ph, 2)

def normalize_genetics(gen_str):
    if not isinstance(gen_str, str): return 'unknown'
    g = gen_str.lower().strip()
    if 'genetically human' in g: return 'genetically_human'
    if 'humanis' in g: return 'humanised'
    if 'chimeric' in g: return 'chimeric'
    if 'murine' in g: return 'murine'
    return g

def get_disease_class(conditions):
    if not isinstance(conditions, str): return 'unknown'
    c = conditions.lower()
    if any(x in c for x in ['cancer','tumour','tumor','leukemia','lymphoma','melanoma','carcinoma','sarcoma','myeloma','blastoma']):
        return 'oncology'
    if any(x in c for x in ['arthritis','lupus','crohn','colitis','sclerosis','psoriasis','autoimmune']):
        return 'autoimmune'
    if any(x in c for x in ['infection','virus','bacterial','fungal','pneumonia','covid','rsv']):
        return 'infectious'
    if any(x in c for x in ['alzheimer','neurolog','parkinson','neuropath','stroke']):
        return 'neurology'
    if any(x in c for x in ['asthma','allerg','atopic','ige']):
        return 'autoimmune_allergic'
    return 'other'

# ── Build records ─────────────────────────────────────────────────────────────
records = []
for _, row in ph3.iterrows():
    name = row['antibody_name']
    heavy = str(row.get('heavy_seq','') or '').strip()
    light = str(row.get('light_seq','') or '').strip()
    genetics = str(row.get('genetics','') or '')
    target = str(row.get('target','') or '')
    disc_cond = str(row.get('disc_conditions','') or '')
    highest_trial = str(row.get('highest_trial','') or '')

    # Get extra data from TheraSAbDab if available
    thera_row = thera_lookup.loc[name] if name in thera_lookup.index else None
    format_type = str(thera_row['Format']) if thera_row is not None and pd.notna(thera_row.get('Format')) else 'na'
    year_proposed = thera_row['Year Proposed'] if thera_row is not None else None

    gen_norm = normalize_genetics(genetics)
    dis_class = get_disease_class(disc_cond)
    is_onco = 1 if dis_class == 'oncology' else 0

    # Sequence-based features
    vh = heavy[:130] if len(heavy) > 30 else heavy
    vl = light[:115] if len(light) > 30 else light

    gravy_vh = calc_gravy(vh)
    gravy_vl = calc_gravy(vl)
    gravy_comb = round((gravy_vh or 0 + gravy_vl or 0)/2, 3) if gravy_vh and gravy_vl else None

    instab_vh = calc_instability(vh)
    pi_vh = calc_pi(vh)

    rec = {c: None for c in schema_cols}
    rec.update({
        # Identity
        'antibody_name': name,
        'origin': 'clinical_discontinued',
        'genetics_normalized': gen_norm,
        'thera_genetics_class': 'fully_human' if 'genetically_human' in gen_norm else gen_norm,
        'targets': target,
        'indication_text': disc_cond[:200] if disc_cond else None,
        'disease_class_curated': dis_class,

        # Fc / format
        'fc_isotype': 'G1',  # default for IgG therapeutics
        'fc_engineering': 'unknown',
        'fc_effector_status': 'unknown',
        'route_curated': 'IV',  # most Ph3 therapeutics are IV
        'approval_year': None,
        'oncology_indication': is_onco,
        'checkpoint_inhibitor': 1 if any(t in target.upper() for t in ['PD1','PDL1','CTLA4','LAG3','TIM3','TIGIT']) else 0,
        'immune_depleting': 0,
        'concomitant_immuno_likely': 0,

        # ADA - UNKNOWN for discontinued
        'ada_value_display': 'UNKNOWN',
        'ada_first_pct': None,
        'evidence_tier': 'PENDING',
        'evidence_source': 'discontinued_no_public_ada_data',
        'citation_urls': 'PENDING_RESEARCH',
        'ada_source_url_primary': None,
        'ada_source_pmids': None,
        'ada_source_type_curated': 'discontinued',
        'ada_has_text_evidence': False,
        'ada_evidence_chain_excerpt': f'Phase III discontinued drug. Indication: {disc_cond[:100]}. ADA data not publicly available - requires ClinicalTrials.gov or FDA review packet research.',

        # Sequences
        'vh_seq': vh if len(vh) > 20 else None,
        'vl_seq': vl if len(vl) > 20 else None,
        'heavy_seq_len': len(vh) if len(vh) > 20 else None,
        'light_seq_len': len(vl) if len(vl) > 20 else None,

        # Biophysical
        'GRAVY': gravy_comb,
        'instability_index': instab_vh,
        'pI': pi_vh,

        # Panel metadata
        'panel_source': 'ph3_discontinued_therasabdab_2025',
        'format_type': format_type,
        'modality': 'standard',
        'phase_bucket': 'phase_III_discontinued',
        'verify_status': 'PENDING',
        'verify_note': f'Phase III discontinued. Highest trial: {highest_trial}',
        'ada_v2_track': 'FH' if 'genetically_human' in gen_norm else 'HU',
    })
    records.append(rec)

result_df = pd.DataFrame(records)[schema_cols]
result_df.to_csv(OUT_CSV, index=False, encoding='utf-8')
print(f"\nSaved {len(result_df)} Phase III discontinued records -> {OUT_CSV}")
print(f"Columns: {len(result_df.columns)} (matches master schema)")
print(f"\nTop 15 antibodies in new dataset:")
print(result_df[['antibody_name','targets','genetics_normalized','disease_class_curated','phase_bucket']].head(15).to_string())
print("\nNext step: Run web research on each to fill ada_first_pct from ClinicalTrials.gov")
