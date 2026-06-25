"""
ADA Negative Sample Library - Full Clinical Phase Collection
Builds records for ALL 312 discontinued antibodies, organized by clinical phase.
Follows exact schema of ada_master_136_curated.csv

Phase buckets:
  phase_I_discontinued       - 114 entries - potential high-ADA early failures
  phase_II_discontinued      - 134 entries - mixed failure reasons  
  phase_III_discontinued     - 47  entries - low-ADA controls (efficacy/safety failures)
  phase_I_II_discontinued    - 13  entries - early-stage
  other_discontinued         - 4   entries - preclinical/preregistration

Output:
  data/immunogenicity_knowledge_base/master/ada_negative_library_by_phase.csv
  data/immunogenicity_knowledge_base/reports/ADA_Negative_Library_Summary.md
"""
import pandas as pd
import os
from pathlib import Path

ROOT = Path(r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite')
DISC_CSV   = ROOT / 'data/immunogenicity_knowledge_base/reports/ADA_Negative_Candidates_Discontinued.csv'
MASTER_CSV = ROOT / 'data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv'
PH3_CSV    = ROOT / 'data/immunogenicity_knowledge_base/master/ada_ph3_disc_candidates.csv'
THERASABDAB = ROOT / 'data/thera_sabdab/TheraSAbDab_SeqStruc_OnlineDownload.xlsx'
OUT_CSV    = ROOT / 'data/immunogenicity_knowledge_base/master/ada_negative_library_by_phase.csv'
OUT_MD     = ROOT / 'data/immunogenicity_knowledge_base/reports/ADA_Negative_Library_Summary.md'

print("Loading data...")
disc_df    = pd.read_csv(DISC_CSV)
master_df  = pd.read_csv(MASTER_CSV)
thera_df   = pd.read_excel(THERASABDAB)

schema_cols = master_df.columns.tolist()

# ── Phase classification ──────────────────────────────────────────────────────
def classify_phase(trial_str):
    t = str(trial_str).strip()
    if 'Phase-III' in t or 'Preregistration' in t or 'Approved (withdrawn)' in t:
        return 'phase_III_discontinued'
    elif 'Phase-II/III' in t:
        return 'phase_III_discontinued'
    elif 'Phase-II' in t:
        return 'phase_II_discontinued'
    elif 'Phase-I/II' in t:
        return 'phase_I_II_discontinued'
    elif 'Phase-I' in t:
        return 'phase_I_discontinued'
    else:
        return 'other_discontinued'

disc_df['phase_bucket_disc'] = disc_df['highest_trial'].apply(classify_phase)
phase_counts = disc_df['phase_bucket_disc'].value_counts()
print("\nPhase distribution of all 312 discontinued antibodies:")
for phase, cnt in phase_counts.items():
    print(f"  {phase}: {cnt}")

# ── Helpers ───────────────────────────────────────────────────────────────────
GRAVY_SCALE = {'A':1.8,'R':-4.5,'N':-3.5,'D':-3.5,'C':2.5,'Q':-3.5,'E':-3.5,
               'G':-0.4,'H':-3.2,'I':4.5,'L':3.8,'K':-3.9,'M':1.9,'F':2.8,
               'P':-1.6,'S':-0.8,'T':-0.7,'W':-0.9,'Y':-1.3,'V':4.2}
INSTAB = {'II':1,'IV':45,'VV':3,'LL':4,'LV':4,'YY':1,'NQ':1,'QN':1,
          'FY':4,'YF':4,'IL':3,'LI':3,'IF':3,'LF':3,'SS':6,'GD':5}

def calc_gravy(seq):
    if not seq or len(seq) < 5: return None
    vals = [GRAVY_SCALE.get(aa, 0) for aa in str(seq).upper() if aa in GRAVY_SCALE]
    return round(sum(vals)/len(vals), 3) if vals else None

def calc_instability(seq):
    if not seq or len(seq) < 10: return None
    seq = str(seq).upper()
    score = sum(INSTAB.get(seq[i:i+2], 0) for i in range(len(seq)-1))
    return round(10/len(seq) * score, 1)

def calc_pi_simple(seq):
    if not seq or len(seq) < 5: return None
    seq = str(seq).upper()
    pKa = {'D':3.9,'E':4.1,'H':6.0,'C':8.3,'Y':10.1,'K':10.5,'R':12.5}
    counts = {aa: seq.count(aa) for aa in pKa}
    ph = 7.0
    for _ in range(200):
        charge = sum(
            -counts[aa]*(1/(1+10**(pKa[aa]-ph))) if aa in 'DECY'
            else counts[aa]*(1/(1+10**(ph-pKa[aa])))
            for aa in pKa
        )
        if abs(charge) < 0.01: break
        ph += 0.05 if charge < 0 else -0.05
    return round(ph, 2)

def normalize_genetics(gen_str):
    if not isinstance(gen_str, str): return 'unknown'
    g = gen_str.lower().strip()
    if 'genetically human' in g: return 'genetically_human'
    if 'humanis' in g or 'humaniz' in g: return 'humanised'
    if 'chimeric' in g and 'human' in g: return 'chimeric_humanised'
    if 'chimeric' in g: return 'chimeric'
    if 'murine' in g: return 'murine'
    return g

def get_disease_class(conditions):
    if not isinstance(conditions, str): return 'unknown'
    c = conditions.lower()
    if any(x in c for x in ['cancer','tumour','tumor','leukaemia','leukemia',
                              'lymphoma','melanoma','carcinoma','sarcoma','myeloma']):
        return 'oncology'
    if any(x in c for x in ['arthritis','lupus','crohn','colitis','sclerosis',
                              'psoriasis','autoimmune','ibd','spondylitis']):
        return 'autoimmune'
    if any(x in c for x in ['infection','virus','bacterial','fungal',
                              'pneumonia','covid','rsv','hiv']):
        return 'infectious'
    if any(x in c for x in ['alzheimer','neurolog','parkinson',
                              'neuropath','stroke','multiple sclerosis']):
        return 'neurology'
    if any(x in c for x in ['asthma','allerg','atopic','ige']):
        return 'autoimmune_allergic'
    return 'other'

# Load previously researched Ph3 data
ph3_researched = {}
try:
    ph3_df = pd.read_csv(PH3_CSV)
    for _, r in ph3_df.iterrows():
        if pd.notna(r.get('ada_first_pct')):
            ph3_researched[r['antibody_name']] = {
                'ada_first_pct': r['ada_first_pct'],
                'evidence_tier': r.get('evidence_tier'),
                'ada_evidence_chain_excerpt': r.get('ada_evidence_chain_excerpt'),
                'citation_urls': r.get('citation_urls'),
                'evidence_source': r.get('evidence_source'),
                'verify_status': r.get('verify_status'),
                'verify_note': r.get('verify_note'),
            }
    print(f"\nLoaded {len(ph3_researched)} previously researched Ph3 records")
except Exception as e:
    print(f"  [WARN] Could not load Ph3 CSV: {e}")

# ── ADA research annotations - organized by phase ────────────────────────────
# Phase-specific priors for evidence_chain when no data found
PHASE_PRIORS = {
    'phase_I_discontinued': {
        'ada_hypothesis': 'HIGH_ADA_LIKELY - Phase I termination may be due to immunogenicity, safety, or PK issues',
        'research_priority': 'HIGH - Phase I failures most likely to contain immunogenicity-driven terminations',
        'tier_default': 'PENDING',
    },
    'phase_II_discontinued': {
        'ada_hypothesis': 'MODERATE_ADA_POSSIBLE - Phase II failures span efficacy, safety, and immunogenicity',
        'research_priority': 'MEDIUM - Check CSR summaries and conference abstracts for ADA data',
        'tier_default': 'PENDING',
    },
    'phase_III_discontinued': {
        'ada_hypothesis': 'LOW_ADA_EXPECTED - Phase III drugs have cleared immunogenicity screening in Phase I/II',
        'research_priority': 'LOW - Use as low-ADA negative controls; failure reason likely efficacy/safety',
        'tier_default': 'PENDING',
    },
    'phase_I_II_discontinued': {
        'ada_hypothesis': 'UNKNOWN - Early phase combination trial, mixed failure risk',
        'research_priority': 'MEDIUM',
        'tier_default': 'PENDING',
    },
    'other_discontinued': {
        'ada_hypothesis': 'UNKNOWN',
        'research_priority': 'LOW',
        'tier_default': 'PENDING',
    },
}

# ── Build records ─────────────────────────────────────────────────────────────
records = []
for _, row in disc_df.iterrows():
    name = str(row['antibody_name'])
    heavy = str(row.get('heavy_seq', '') or '').strip()
    light = str(row.get('light_seq', '') or '').strip()
    genetics = str(row.get('genetics', '') or '')
    target = str(row.get('target', '') or '')
    disc_cond = str(row.get('disc_conditions', '') or '')
    highest_trial = str(row.get('highest_trial', '') or '')
    phase_bucket = row['phase_bucket_disc']

    gen_norm = normalize_genetics(genetics)
    dis_class = get_disease_class(disc_cond)
    is_onco = 1 if dis_class == 'oncology' else 0
    prior = PHASE_PRIORS.get(phase_bucket, PHASE_PRIORS['other_discontinued'])

    vh = heavy[:130] if len(heavy) > 30 else heavy
    vl = light[:115] if len(light) > 30 else light
    gravy_vh = calc_gravy(vh)
    gravy_vl = calc_gravy(vl)
    gravy_comb = round(((gravy_vh or 0) + (gravy_vl or 0)) / 2, 3) if gravy_vh and gravy_vl else None

    # Check if previously researched
    researched = ph3_researched.get(name, {})

    rec = {c: None for c in schema_cols}
    rec.update({
        'antibody_name': name,
        'origin': 'clinical_discontinued',
        'genetics_normalized': gen_norm,
        'thera_genetics_class': 'fully_human' if 'genetically_human' in gen_norm else gen_norm,
        'targets': target,
        'indication_text': disc_cond[:200] if disc_cond else None,
        'disease_class_curated': dis_class,
        'fc_isotype': 'G1',
        'fc_engineering': 'unknown',
        'fc_effector_status': 'unknown',
        'route_curated': 'IV',
        'approval_year': None,
        'oncology_indication': is_onco,
        'checkpoint_inhibitor': 1 if any(
            t in target.upper() for t in ['PD1','PDL1','CTLA4','LAG3','TIM3','TIGIT']
        ) else 0,
        'immune_depleting': 0,
        'concomitant_immuno_likely': 0,

        # ADA fields - use researched data or PENDING
        'ada_value_display': f"{researched['ada_first_pct']}%" if researched.get('ada_first_pct') else 'PENDING',
        'ada_first_pct': researched.get('ada_first_pct'),
        'evidence_tier': researched.get('evidence_tier', prior['tier_default']),
        'evidence_source': researched.get('evidence_source', 'PENDING_RESEARCH'),
        'citation_urls': researched.get('citation_urls', 'PENDING_RESEARCH'),
        'ada_source_url_primary': researched.get('citation_urls'),
        'ada_source_pmids': None,
        'ada_source_type_curated': 'discontinued_clinical',
        'ada_has_text_evidence': bool(researched),
        'ada_evidence_chain_excerpt': researched.get(
            'ada_evidence_chain_excerpt',
            f"[{phase_bucket.upper()}] {prior['ada_hypothesis']} | "
            f"Research priority: {prior['research_priority']} | "
            f"Indication: {disc_cond[:150]}"
        ),

        # Sequences
        'vh_seq': vh if len(vh) > 20 else None,
        'vl_seq': vl if len(vl) > 20 else None,
        'heavy_seq_len': len(vh) if len(vh) > 20 else None,
        'light_seq_len': len(vl) if len(vl) > 20 else None,

        # Biophysical
        'GRAVY': gravy_comb,
        'instability_index': calc_instability(vh),
        'pI': calc_pi_simple(vh),

        # Panel metadata
        'panel_source': f'therasabdab_2025_discontinued_{phase_bucket}',
        'format_type': str(row.get('format', 'na') or 'na'),
        'modality': 'standard',
        'phase_bucket': phase_bucket,
        'verify_status': researched.get('verify_status', 'PENDING_RESEARCH'),
        'verify_note': researched.get('verify_note',
            f"Discontinued at {highest_trial}. {prior['ada_hypothesis']}"),
        'ada_v2_track': 'FH' if 'genetically_human' in gen_norm else 'HU',
    })
    records.append(rec)

result_df = pd.DataFrame(records)[schema_cols]
result_df.to_csv(OUT_CSV, index=False, encoding='utf-8')
print(f"\nSaved {len(result_df)} total negative library records -> {OUT_CSV}")

# ── Stats ─────────────────────────────────────────────────────────────────────
print("\nBreakdown by phase:")
for phase in ['phase_I_discontinued','phase_II_discontinued','phase_III_discontinued',
              'phase_I_II_discontinued','other_discontinued']:
    sub = result_df[result_df['phase_bucket'] == phase]
    filled = sub['ada_first_pct'].notna().sum()
    print(f"  {phase}: {len(sub)} records, {filled} with ADA data")

# ── Generate markdown summary ─────────────────────────────────────────────────
with open(OUT_MD, 'w', encoding='utf-8') as f:
    f.write("# ADA （）\n\n")
    f.write(f"****: {len(result_df)}  \n")
    f.write(f"****: TheraSAbDab SeqStruc (Feb 2025) — Discontinued   \n")
    f.write(f"****:  ADA Panel (138 )   \n\n")
    f.write("---\n\n")

    f.write("## \n\n")
    f.write("|  |  | ADA |  |\n")
    f.write("|---------|------|------------|--------|\n")

    phase_labels = {
        'phase_I_discontinued':    ('Phase I', '⭐⭐⭐  — ADA'),
        'phase_II_discontinued':   ('Phase II', '⭐⭐  — '),
        'phase_III_discontinued':  ('Phase III', '⭐ ADA — PH1/2，ADA'),
        'phase_I_II_discontinued': ('Phase I/II', '⭐⭐ '),
        'other_discontinued':      ('Other', ''),
    }

    for phase, (label, note) in phase_labels.items():
        sub = result_df[result_df['phase_bucket'] == phase]
        filled = sub['ada_first_pct'].notna().sum()
        f.write(f"| **{label}** | {len(sub)} | {filled} | {note} |\n")

    f.write(f"\n\n> [!IMPORTANT]\n")
    f.write(f"> ****： Phase III  Phase I/II ，\n")
    f.write(f">  Phase III  ADA 。\n")
    f.write(f"> ** ADA  Phase I  {phase_counts.get('phase_I_discontinued', 0)} 。**\n\n")

    f.write("---\n\n")
    f.write("## Phase I （）\n\n")
    ph1 = result_df[result_df['phase_bucket'] == 'phase_I_discontinued']
    f.write(f"* {len(ph1)} ，，、*\n\n")
    ph1_show = ph1[['antibody_name','targets','genetics_normalized','disease_class_curated']].copy()
    ph1_show.index = range(1, len(ph1_show)+1)
    f.write(ph1_show.to_markdown())

    f.write("\n\n---\n\n")
    f.write("## Phase II \n\n")
    ph2 = result_df[result_df['phase_bucket'] == 'phase_II_discontinued']
    f.write(f"* {len(ph2)} ， 40 *\n\n")
    ph2_show = ph2[['antibody_name','targets','genetics_normalized','disease_class_curated']].head(40).copy()
    ph2_show.index = range(1, len(ph2_show)+1)
    f.write(ph2_show.to_markdown())

    f.write("\n\n---\n\n")
    f.write("## Phase III （ADA）\n\n")
    ph3 = result_df[result_df['phase_bucket'] == 'phase_III_discontinued']
    f.write(f"* {len(ph3)} ，*\n\n")
    ph3_show = ph3[['antibody_name','targets','genetics_normalized',
                     'disease_class_curated','ada_first_pct']].copy()
    ph3_show.index = range(1, len(ph3_show)+1)
    f.write(ph3_show.to_markdown())

    f.write("\n\n---\n\n")
    f.write("## \n\n")
    f.write("###  A（1-2）— Phase I \n")
    f.write("-  ClinicalTrials.gov  PubMed，\n")
    f.write("- ：\"immunogenicity\", \"anti-drug antibody\", \"ADA\", \"hypersensitivity\"\n")
    f.write("- ： ADA \n\n")
    f.write("###  B（2-4）— Phase II \n")
    f.write("- ， ADA > 10% \n\n")
    f.write("###  C（）— Phase III \n")
    f.write("-  ADA （ 3/47 ）\n")
    f.write("-  ADA ， Panel\n")

print(f"\nMarkdown summary -> {OUT_MD}")
print("\n=== PHASE COLLECTION COMPLETE ===")
print(f"\nTotal negative library: {len(result_df)} records")
print(f"Combined with existing 138 panel: {138 + len(result_df)} total antibodies in ecosystem")
