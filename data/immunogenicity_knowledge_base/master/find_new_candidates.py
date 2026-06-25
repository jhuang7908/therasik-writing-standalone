
import csv

master_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_master_136_curated.csv'
candidates_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_ph3_disc_candidates.csv'

with open(master_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    master_names = {row['antibody_name'].lower() for row in reader}

with open(candidates_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    candidates = []
    for row in reader:
        name = row['antibody_name']
        if name.lower() not in master_names:
            candidates.append(name)

print("\n".join(candidates))
