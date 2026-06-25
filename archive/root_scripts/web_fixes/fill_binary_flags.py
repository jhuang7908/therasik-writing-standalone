"""
Infer binary clinical flags from existing disease_class and moa_class for the 51 records
that still have empty oncology_indication / checkpoint_inhibitor / immune_depleting /
concomitant_immuno_likely.
"""
import csv, subprocess, sys, shutil, math

MASTER    = r'data\ada_master_136_curated.csv'
KB_MASTER = r'data\immunogenicity_knowledge_base\master\ada_master_136_curated.csv'

def is_empty(v):
    s = str(v or '').strip()
    return s in ('', 'nan', 'None', 'none', 'NaN')

def contains(text, keywords):
    t = str(text or '').lower()
    return any(k.lower() in t for k in keywords)

ONCOLOGY_DISEASE = ['oncol', 'cancer', 'tumor', 'tumour', 'leukemia', 'lymphoma',
                    'myeloma', 'melanoma', 'carcinoma', 'sarcoma', 'glioblastoma',
                    'neuroblastoma', 'mesothelioma', 'adenocarcinoma', 'astrocytoma']

CHECKPOINT_MOA = ['PD-1', 'PD-L1', 'CTLA-4', 'LAG-3', 'TIM-3', 'TIGIT',
                  'programmed death', 'anti-PD', 'checkpoint']

DEPLETING_MOA  = ['CD20', 'CD52', 'CD19', 'BCMA', 'CD38', 'CD22',
                  'depleting', 'cytolytic', 'ADCC-enhanced', 'B cell depletion',
                  'T cell depletion', 'lymphodepleting']

CHEMO_COMBO_CONTEXT = ['chemo', 'chemotherapy', 'cytotoxic', 'carboplatin', 'paclitaxel',
                       'docetaxel', 'FOLFIRI', 'FOLFOX', 'bendamustine', 'doxorubicin']

IST_CONTEXT = ['methotrexate', 'MTX', 'azathioprine', 'mycophenolate', 'MMF', 'tacrolimus',
               'cyclosporine', 'corticosteroid', 'prednisolone', 'prednisone', 'OCS',
               'immunosuppressant', 'DMARDs', 'DMARD', 'lenalidomide', 'dexamethasone',
               'combination', 'ICS', 'background ster']

with open(MASTER, encoding='utf-8') as f:
    reader     = csv.DictReader(f)
    fieldnames = list(reader.fieldnames)
    all_rows   = list(reader)

updated = 0
for row in all_rows:
    if not all(is_empty(row.get(f, '')) for f in
               ['oncology_indication', 'checkpoint_inhibitor', 'immune_depleting', 'concomitant_immuno_likely']):
        # At least some flags are set — only fill the blanks
        pass
    
    dc   = row.get('disease_class_curated', '')
    moa  = row.get('moa_class', '')
    ctx  = row.get('immunosuppressant_context', '')
    ind  = row.get('indication_text', '')

    changed = False

    # oncology_indication
    if is_empty(row.get('oncology_indication', '')):
        val = 1 if (contains(dc, ONCOLOGY_DISEASE) or contains(ind, ONCOLOGY_DISEASE)) else 0
        row['oncology_indication'] = str(float(val))
        changed = True

    # checkpoint_inhibitor
    if is_empty(row.get('checkpoint_inhibitor', '')):
        val = 1 if contains(moa, CHECKPOINT_MOA) else 0
        row['checkpoint_inhibitor'] = str(float(val))
        changed = True

    # immune_depleting
    if is_empty(row.get('immune_depleting', '')):
        val = 1 if contains(moa, DEPLETING_MOA) else 0
        row['immune_depleting'] = str(float(val))
        changed = True

    # concomitant_immuno_likely
    if is_empty(row.get('concomitant_immuno_likely', '')):
        val = 1 if (contains(ctx, CHEMO_COMBO_CONTEXT) or contains(ctx, IST_CONTEXT)) else 0
        row['concomitant_immuno_likely'] = str(float(val))
        changed = True

    if changed:
        updated += 1

print(f"Updated binary flags for {updated} records")

# Summary
for flag in ['oncology_indication', 'checkpoint_inhibitor', 'immune_depleting', 'concomitant_immuno_likely']:
    filled = sum(1 for r in all_rows if not is_empty(r.get(flag, '')))
    print(f"  {flag:<28} {filled}/138 ({100*filled/138:.0f}%)")

with open(MASTER, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(all_rows)
shutil.copy(MASTER, KB_MASTER)

print("Rebuilding JSON...")
subprocess.run([sys.executable, 'scripts/_regen_json_only.py'], check=False)
shutil.copy('docs/ada_db_data.json', 'insynbio-web-source/ada_db_data.json')
shutil.copy('docs/ada_db_data.json', 'therasik-web-source/ada_db_data.json')
print("Done.")
