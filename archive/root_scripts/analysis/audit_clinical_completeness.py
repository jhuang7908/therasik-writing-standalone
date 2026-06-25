"""
Audit completeness of all clinical/treatment fields across 138 ADA records.
Also check what fields are in the JSON output vs what clinical data exists.
"""
import csv, json
from collections import defaultdict

rows = list(csv.DictReader(open('data/ada_master_136_curated.csv', encoding='utf-8')))
print(f"Total records: {len(rows)}\n")

def pct_filled(field, empty_vals=('', 'nan', 'None', 'none', 'NaN')):
    filled = []
    empty  = []
    for r in rows:
        v = str(r.get(field, '') or '').strip()
        if v in empty_vals or v.lower() in empty_vals:
            empty.append(r['antibody_name'])
        else:
            filled.append(r['antibody_name'])
    return filled, empty

# ── Field groups ──────────────────────────────────────────────────────────────
GROUPS = {
    "CORE IDENTITY": [
        'targets', 'indication_text', 'disease_class_curated', 'moa_class',
        'approval_year', 'fc_isotype', 'route_curated',
    ],
    "DOSING/PK": [
        'dose_mg', 'dose_freq', 'half_life_days',
    ],
    "ASSAY": [
        'assay_platform', 'assay_generation',
    ],
    "CLINICAL CONFOUNDERS": [
        'mtx_comedication', 'immunosuppressant_context',
        'oncology_indication', 'checkpoint_inhibitor',
        'immune_depleting', 'concomitant_immuno_likely',
    ],
    "FC/ENGINEERING": [
        'fc_engineering', 'fc_effector_status', 'fc_mutation_notes',
    ],
    "ADA DATA": [
        'ada_value_display', 'ada_first_pct', 'evidence_tier',
        'ada_source_url_primary', 'ada_source_pmids',
        'verify_status', 'verify_note',
    ],
    "SEQUENCE/STRUCTURE": [
        'vh_cdr3', 'vh_germline', 'vl_germline', 'pdb_path',
    ],
}

for group, fields in GROUPS.items():
    print(f"{'─'*60}")
    print(f"{group}")
    print(f"{'─'*60}")
    print(f"  {'Field':<30} {'Filled':>6}  {'Missing':>3}  {'%':>4}  missing drugs")
    for field in fields:
        filled, empty = pct_filled(field)
        pct = 100 * len(filled) / len(rows)
        flag = ' ◄' if pct < 70 else (' ·' if pct < 90 else '')
        miss_str = ', '.join(empty[:5]) + (f' +{len(empty)-5}more' if len(empty)>5 else '')
        print(f"  {field:<30} {len(filled):>6}  {len(empty):>3}  {pct:>3.0f}%{flag}  {miss_str[:60]}")
    print()

# ── What clinical fields are NOT in the JSON output? ──────────────────────────
print("─"*60)
print("FIELDS IN CSV but NOT exported to ada_db_data.json:")
json_data = json.load(open('docs/ada_db_data.json', encoding='utf-8'))
json_keys  = set(json_data[0].keys()) if json_data else set()
csv_keys   = set(rows[0].keys()) if rows else set()

missing_in_json = [k for k in csv_keys if k not in json_keys and not k.startswith('_')]
# Filter to clinically interesting ones
clinical_missing = [k for k in missing_in_json if any(x in k for x in [
    'dose', 'freq', 'moa', 'indication', 'approval', 'assay',
    'immuno', 'checkpoint', 'concomitant', 'oncology', 'fc_mut',
    'disease_class', 'confounder', 'comedication'
])]
print(f"  Total CSV fields: {len(csv_keys)}")
print(f"  JSON fields: {len(json_keys)}")
print(f"  Clinically relevant missing from JSON: {len(clinical_missing)}")
for k in sorted(clinical_missing):
    filled, _ = pct_filled(k)
    print(f"    {k:<35} ({len(filled)}/138 filled)")

print("\nJSON fields currently exported:")
for k in sorted(json_keys):
    print(f"  {k}")
