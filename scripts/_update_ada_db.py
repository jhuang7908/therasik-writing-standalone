"""
Update ada_master_136_curated.csv:
  (Public website JSON: run scripts/_regen_json_only.py after CSV edits — it applies
   ada_web_publish_gate so docs/ada_db_data.json stays evidence-aligned.)

  1. Add moa_class field to all existing entries
  2. Append new entries (nipocalimab, epcoritamab, elranatamab) with confirmed FDA ADA data
  3. Regenerate gated ada_db_data.json via _regen_json_only.py
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

CSV_IN = "data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv"
REPO_ROOT = Path(__file__).resolve().parents[1]

df = pd.read_csv(CSV_IN)

# ── moa_class assignment ──────────────────────────────────────────────────────
def assign_moa(row):
    t = str(row.get('targets', '')).lower()
    cp = row.get('checkpoint_inhibitor', 0)
    if 'fcgrt' in t or 'fcrn' in t: return 'anti-FcRn'
    if 'cd3' in t:
        if 'cd20' in t or 'ms4a1' in t:    return 'CD20\u00d7CD3 bispecific'
        if 'bcma' in t or 'tnfrsf17' in t: return 'BCMA\u00d7CD3 bispecific'
        if 'gprc5d' in t:                   return 'GPRC5D\u00d7CD3 bispecific'
        if 'dll3' in t:                     return 'DLL3\u00d7CD3 bispecific'
        if 'her2' in t or 'erbb2' in t:     return 'HER2\u00d7CD3 bispecific'
        if 'egfr' in t:                     return 'EGFR\u00d7CD3 bispecific'
        return 'T-cell engager (other)'
    if 'vegf' in t and ('ang' in t or 'angpt' in t): return 'anti-VEGF/Ang-2'
    if 'vegf' in t or 'kdr' in t: return 'anti-VEGF'
    if cp == 1 or 'pdcd1' in t or ('cd279' in t and 'lag3' not in t):
        return 'anti-PD-1'
    if 'cd274' in t or 'pdl1' in t: return 'anti-PD-L1'
    if 'ctla4' in t: return 'anti-CTLA-4'
    if 'lag3' in t: return 'anti-LAG-3'
    if 'tnf' in t or 'tnfa' in t: return 'anti-TNF'
    if any(x in t for x in ['il4r','il13','il31','il17','il23','il5','il6',
                              'il1','il33','il36','il12','il2','tslp','ifn']):
        return 'anti-interleukin/cytokine'
    if any(x in t for x in ['calca','calcb','cgrp','ramp1']): return 'anti-CGRP'
    if 'pcsk9' in t: return 'anti-PCSK9'
    if 'cd20' in t or 'ms4a1' in t: return 'anti-CD20'
    if 'cd38' in t: return 'anti-CD38'
    if 'cd19' in t: return 'anti-CD19'
    if any(x in t for x in ['itg','integrin','itga']): return 'anti-integrin'
    if 'erbb2' in t or 'her2' in t: return 'anti-HER2'
    if 'egfr' in t: return 'anti-EGFR'
    if 'app' in t or 'abeta' in t or 'amyloid' in t: return 'anti-amyloid (CNS)'
    if 'comp5' in t or t.strip() == 'c5': return 'anti-complement'
    if 'tacstd' in t or 'trop2' in t: return 'anti-TROP2 (ADC)'
    if any(x in t for x in ['f3','cd142','tfpi','f11']): return 'anti-coagulation'
    if 'igf' in t: return 'anti-IGF-1R'
    if 'rankl' in t or 'tnfsf11' in t: return 'anti-RANKL'
    if any(x in t for x in ['rsv','syncytial','sars','spike','ebola','covid','viral']):
        return 'antiviral/infectious'
    if 'gd2' in t or 'ganglioside' in t: return 'anti-GD2'
    if 'csf1r' in t: return 'anti-CSF-1R'
    if 'sost' in t or 'dkk1' in t: return 'anti-bone'
    return 'other'

if 'moa_class' not in df.columns:
    df['moa_class'] = df.apply(assign_moa, axis=1)
else:
    # update only NaN cells
    mask = df['moa_class'].isna() | (df['moa_class'] == '')
    df.loc[mask, 'moa_class'] = df[mask].apply(assign_moa, axis=1)

base_cols = df.columns.tolist()
NAN = float('nan')

# ── New entries ───────────────────────────────────────────────────────────────
new_data = [
    # 1. Nipocalimab - anti-FcRn, gMG, FDA 2025
    {
        'antibody_name': 'Nipocalimab',
        'origin': 'engineered', 'genetics_normalized': 'humanized',
        'thera_genetics_class': 'humanized',
        'targets': 'FCGRT|FcRn',
        'indication_text': 'Generalized myasthenia gravis (gMG), AChR/MuSK antibody-positive',
        'disease_class_curated': 'neurology_autoimmune',
        'fc_isotype': 'G1',
        'fc_engineering': 'Aglycosylated IgG1 (Fc-null, effector-silenced)',
        'fc_effector_status': 'null',
        'fc_mutation_notes': 'Aglycosylated Fc: no FcgR/C1q binding; lambda light chain',
        'route_curated': 'IV', 'dose_mg': '15-30 mg/kg', 'dose_freq': 'q2w',
        'half_life_days': 1.2,
        'mtx_comedication': 'none',
        'immunosuppressant_context': 'Standard MG therapy (AChEI + steroids/NSISTs)',
        'approval_year': 2025.0,
        'oncology_indication': 0.0, 'checkpoint_inhibitor': 0.0,
        'immune_depleting': 0.0, 'concomitant_immuno_likely': 1.0,
        'ada_value_display': '48%', 'ada_first_pct': 48.0,
        'evidence_tier': 'A', 'evidence_source': 'FDA label (IMAAVY PI 2025)',
        'citation_urls': 'https://dailymed.nlm.nih.gov/dailymed/getFile.cfm?setid=8886274c-f2b2-48af-85c1-2f90bfe304b8&type=pdf',
        'ada_source_url_primary': 'FDA prescribing information',
        'ada_source_pmids': NAN, 'ada_source_type_curated': 'FDA label',
        'ada_has_text_evidence': True,
        'ada_evidence_chain_excerpt': '49/102 (48%) patients tested positive for ADAs in 24-week gMG study; 19/49 (38.8%) had neutralizing antibodies. No clinically meaningful effect on PK/PD/efficacy. (IMAAVY PI 2025 §12.6)',
        'format_type': 'monospecific_IgG_Fc-null', 'modality': 'standard',
        'phase_bucket': 'approved', 'panel_source': 'ada_136_expansion',
        'moa_class': 'anti-FcRn',
    },
    # 2. Epcoritamab - CD20xCD3, DLBCL/FL, FDA 2023
    {
        'antibody_name': 'Epcoritamab',
        'origin': 'engineered', 'genetics_normalized': 'humanized',
        'thera_genetics_class': 'humanized',
        'targets': 'MS4A1|CD20|CD3E|CD3',
        'indication_text': 'R/R DLBCL, NOS; R/R follicular lymphoma (≥2 prior lines)',
        'disease_class_curated': 'oncology',
        'fc_isotype': 'G1',
        'fc_engineering': 'IgG1 DuoBody bispecific (K409R/F405L Fc exchange)',
        'fc_effector_status': 'normal_IgG1',
        'fc_mutation_notes': 'Controlled Fab-arm exchange; normal IgG1 Fc effector function retained',
        'route_curated': 'SC', 'dose_mg': '48', 'dose_freq': 'QW then Q2W',
        'half_life_days': 28.0,
        'mtx_comedication': 'none',
        'immunosuppressant_context': 'Lymphodepleted oncology patients; B-cell depletion expected',
        'approval_year': 2023.0,
        'oncology_indication': 1.0, 'checkpoint_inhibitor': 0.0,
        'immune_depleting': 1.0, 'concomitant_immuno_likely': 0.0,
        'ada_value_display': '2.6%', 'ada_first_pct': 2.6,
        'evidence_tier': 'A', 'evidence_source': 'FDA label (EPKINLY PI 2025)',
        'citation_urls': 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761324s008lbl.pdf',
        'ada_source_url_primary': 'FDA prescribing information',
        'ada_source_pmids': NAN, 'ada_source_type_curated': 'FDA label',
        'ada_has_text_evidence': True,
        'ada_evidence_chain_excerpt': '4/156 (2.6%) evaluable patients developed ADA (approved 48 mg SC regimen). ADA status did not affect epcoritamab PK; immunogenicity risk deemed low. (EPKINLY PI 2025 §12.6)',
        'format_type': 'bispecific_TCE', 'modality': 'bispecific',
        'phase_bucket': 'approved', 'panel_source': 'ada_136_expansion',
        'moa_class': 'CD20\u00d7CD3 bispecific',
    },
    # 3. Elranatamab - BCMAxCD3, MM, FDA 2023
    {
        'antibody_name': 'Elranatamab',
        'origin': 'engineered', 'genetics_normalized': 'humanized',
        'thera_genetics_class': 'humanized',
        'targets': 'TNFRSF17|BCMA|CD3E|CD3',
        'indication_text': 'R/R multiple myeloma (≥4 prior lines, PI+IMiD+anti-CD38)',
        'disease_class_curated': 'oncology',
        'fc_isotype': 'G2',
        'fc_engineering': 'IgG2 Fc (inherently reduced FcgR binding)',
        'fc_effector_status': 'attenuated',
        'fc_mutation_notes': 'IgG2 hinge/Fc reduces ADCC/CDC; bispecific T-cell engager format (MagnetisMM)',
        'route_curated': 'SC', 'dose_mg': '76', 'dose_freq': 'QW then Q2W',
        'half_life_days': 22.0,
        'mtx_comedication': 'none',
        'immunosuppressant_context': 'Heavily pretreated MM with profound immunosuppression',
        'approval_year': 2023.0,
        'oncology_indication': 1.0, 'checkpoint_inhibitor': 0.0,
        'immune_depleting': 1.0, 'concomitant_immuno_likely': 0.0,
        'ada_value_display': '9.5%', 'ada_first_pct': 9.5,
        'evidence_tier': 'A', 'evidence_source': 'FDA label (ELREXFIO PI 2023)',
        'citation_urls': 'https://labeling.pfizer.com/ShowLabeling.aspx?id=19669',
        'ada_source_url_primary': 'FDA prescribing information (Pfizer)',
        'ada_source_pmids': NAN, 'ada_source_type_curated': 'FDA label',
        'ada_has_text_evidence': True,
        'ada_evidence_chain_excerpt': '9.5% (16/168) patients in MagnetisMM-3 tested ADA positive (up to 36 months). 56% (9/16) had neutralizing antibodies. Effect on PK/PD/safety/efficacy unknown. (ELREXFIO PI 2023 §12.6)',
        'format_type': 'bispecific_TCE', 'modality': 'bispecific',
        'phase_bucket': 'approved', 'panel_source': 'ada_136_expansion',
        'moa_class': 'BCMA\u00d7CD3 bispecific',
    },
]

new_rows = []
for nd in new_data:
    row = {c: NAN for c in base_cols}
    row.update(nd)
    new_rows.append(row)

df_combined = pd.concat([df, pd.DataFrame(new_rows, columns=base_cols)], ignore_index=True)
df_combined.to_csv(CSV_IN, index=False)
print(f'CSV saved: {len(df_combined)} rows')

# ── Regenerate gated ada_db_data.json (same as _regen_json_only.py) ──────────
regen = REPO_ROOT / "scripts" / "_regen_json_only.py"
subprocess.run([sys.executable, str(regen)], cwd=str(REPO_ROOT), check=True)

print('MOA class distribution:')
print(df_combined['moa_class'].value_counts().head(15).to_string())
