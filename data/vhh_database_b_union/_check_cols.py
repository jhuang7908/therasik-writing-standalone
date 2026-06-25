import csv

with open('data/vhh_clinical_39_union/vhh_39_cdr_fr_segments.csv') as f:
    rows = list(csv.DictReader(f))
print('VHH39 cols:', list(rows[0].keys()) if rows else 'empty', flush=True)
print('VHH39 first:', rows[0] if rows else 'none', flush=True)

with open('data/vhh_database_b_union/vhh29_cdr_segments.csv') as f:
    rows29 = list(csv.DictReader(f))
print('VHH29 cols:', list(rows29[0].keys()) if rows29 else 'empty', flush=True)
print('VHH29 first:', rows29[0] if rows29 else 'none', flush=True)
