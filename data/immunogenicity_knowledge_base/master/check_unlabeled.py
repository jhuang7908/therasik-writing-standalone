import csv
import os

data_text = """
4. （unlabeled，27）— 
Anetumab, Aprutumab, Bezetabart, Camidanlumab, Danburstotug, Efungumab, Enapotamab, Enfortumab, Gancotamab, Glembatumumab, Indusatumab, Lenzilumab, Lupartumab, Moflerafusp, Ompekimig2, Opelkibart, Palverafusp, Pelgifatamab, Radretumab, Ramantamig2, Ruzaltatug, Sirtratumab, Solabafusp, Tabirafusp, Tilrekimig2, Torvutatug, Vislarafusp
"""

abs_list = []
for line in data_text.split('\n'):
    if line.strip and not line.startswith('4.'):
        abs_list.extend([x.strip for x in line.split(',') if x.strip])

print(f"Total unlabeled antibodies provided: {len(abs_list)}")

master_path1 = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\immunogenicity_panel_136_master.csv'
master_path2 = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_negative_library_by_phase.csv'

def load_master_names(path):
    names = set
    ada_found = set
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('antibody_name', '').lower
                if name:
                    names.add(name)
                    if 'ada_first_pct' in row and row['ada_first_pct'] and str(row['ada_first_pct']).strip != '' and str(row['ada_first_pct']).strip.lower != 'nan':
                        ada_found.add(name)
    return names, ada_found

names1, ada1 = load_master_names(master_path1)
names2, ada2 = load_master_names(master_path2)

all_db_names = names1.union(names2)
all_ada_names = ada1.union(ada2)

found_ada = []
no_ada = []
not_in_db = []

for ab in abs_list:
    ab_low = ab.lower
    if ab_low in all_ada_names:
        found_ada.append(ab)
    elif ab_low in all_db_names:
        no_ada.append(ab)
    else:
        not_in_db.append(ab)

print(f"\n--- Unlabeled ---")
print(f"Has ADA data: {len(found_ada)} {found_ada}")
print(f"In DB but NO ADA data: {len(no_ada)}")
print(f"Not in DB: {len(not_in_db)}")
