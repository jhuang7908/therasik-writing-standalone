import json
import pandas as pd
import os

# Data from browser research
batch2_data = [
    {"name": "Relatlimab", "ada_pct": 7.0, "n_ada": 0.4, "assay": "ECLIA (MSD)", "indication": "Melanoma", "dose": "160mg", "freq": "q4w", "route": "IV", "targets": "LAG-3", "status": "CA"},
    {"name": "Bebtelovimab", "ada_pct": 3.5, "n_ada": 0.3, "assay": "ECLIA (MSD)", "indication": "COVID-19", "dose": "175mg", "freq": "Single", "route": "IV", "targets": "SARS-CoV-2", "status": "CA"},
    {"name": "Narsoplimab", "ada_pct": 0.0, "n_ada": 0.0, "assay": "ELISA", "indication": "HSCT-TMA", "dose": "4mg/kg", "freq": "twice weekly", "route": "IV", "targets": "MASP-2", "status": "CA"},
    {"name": "Maftivimab", "ada_pct": 2.0, "n_ada": 0.5, "assay": "ECLIA (MSD)", "indication": "Ebola Virus", "dose": "50mg/kg", "freq": "Single", "route": "IV", "targets": "Ebola GP", "status": "CA"},
    {"name": "Lenzilumab", "ada_pct": 3.8, "n_ada": 0.1, "assay": "ELISA", "indication": "COVID-19", "dose": "600mg", "freq": "q8h", "route": "IV", "targets": "GM-CSF", "status": "CA"},
    {"name": "Felzartamab", "ada_pct": 0.0, "n_ada": 0.0, "assay": "ELISA", "indication": "Multiple Myeloma", "dose": "16mg/kg", "freq": "weekly", "route": "IV", "targets": "CD38", "status": "CA"},
    {"name": "Camidanlumab", "ada_pct": 13.6, "n_ada": 0.9, "assay": "ECLIA (MSD)", "indication": "Hodgkin Lymphoma", "dose": "45ug/kg", "freq": "q3w", "route": "IV", "targets": "CD25", "status": "CA"},
    {"name": "Oportuzumab", "ada_pct": 100.0, "n_ada": 90.0, "assay": "ELISA", "indication": "Bladder Cancer", "dose": "30mg", "freq": "twice weekly", "route": "Intravesical", "targets": "EpCAM", "status": "HU"}, # High risk due to toxin
    {"name": "Iparomlimab", "ada_pct": 0.6, "n_ada": 0.0, "assay": "ELISA", "indication": "Hodgkin Lymphoma", "dose": "200mg", "freq": "q2w", "route": "IV", "targets": "PD-1", "status": "CA"},
    {"name": "Geptanolimab", "ada_pct": 14.3, "n_ada": 0.0, "assay": "ELISA", "indication": "PTCL", "dose": "3mg/kg", "freq": "q2w", "route": "IV", "targets": "PD-1", "status": "CA"}
]

atlas_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\clinical_kb\Antibody_Atlas_1142_Aggregated.json'
with open(atlas_path, 'r', encoding='utf-8') as f:
    atlas = json.load(f)

# Find sequences across all atlas files
base_dir = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data'
atlas_dirs = [d for d in os.listdir(base_dir) if d.endswith('_atlas') and os.path.isdir(os.path.join(base_dir, d))]

all_atlas_data = {}
for d in atlas_dirs:
    path = os.path.join(base_dir, d, 'master_table.csv')
    if os.path.exists(path):
        try:
            df_atlas = pd.read_csv(path)
            cols = df_atlas.columns.tolist()
            name_col = cols[0]
            for _, row in df_atlas.iterrows():
                name = str(row[name_col]).strip().lower()
                if name not in all_atlas_data:
                    all_atlas_data[name] = row.to_dict()
        except: pass

# Special case for clinical_kb
json_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\clinical_kb\Antibody_Atlas_1142_Aggregated.json'
if os.path.exists(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for entry in data:
            name = entry.get('name', '').strip().lower()
            if name not in all_atlas_data:
                all_atlas_data[name] = entry

# Combine with researched data
final_batch2 = []
for item in batch2_data:
    name_lower = item['name'].lower()
    atlas_entry = all_atlas_data.get(name_lower, {})
    
    entry = item.copy()
    # Sequences and structural fields
    entry['vh_seq'] = atlas_entry.get('vh_seq', atlas_entry.get('arm1_heavy', ''))
    entry['vl_seq'] = atlas_entry.get('vl_seq', atlas_entry.get('arm1_light', ''))
    entry['vh_germline'] = atlas_entry.get('vh_germline', '')
    entry['vl_germline'] = atlas_entry.get('vl_germline', '')
    
    # Structural/CDR fields (to match granularity)
    struct_cols = ['vh_fr1', 'vh_cdr1', 'vh_fr2', 'vh_cdr2', 'vh_fr3', 'vh_cdr3', 'vh_fr4', 
                   'vl_fr1', 'vl_cdr1', 'vl_fr2', 'vl_cdr2', 'vl_fr3', 'vl_cdr3', 'vl_fr4']
    for col in struct_cols:
        entry[col] = atlas_entry.get(col, '')
    
    # If sequences still missing, use those from browser research
    if not entry['vh_seq']:
        # Manual entry for some found by browser
        manual_seqs = {
            "relatlimab": ("QVQLQQWGAGLLKPSETLSLTCAVYGGSFSDYYWNWIRQPPGKGLEWIGEINHRGSTNSNPSLKSRVTLSLDTSKNQFSLKLRSVTAADTAVYYCAFGYS DYEYNWFDPWGQGTLVTVSS", "EIVLTQSPATLSLSPGERATLSCRASQSISSYLAWYQQKPGQAPRLLIYDASNRATGIPARFSGSGSGTDFTLTISSLEPEDFAVYYCQQRSNWPLTFGQ GTNLEIKR"),
            "bebtelovimab": ("QITLKESGPTLVKPTQTLTLTCTFSGFSLSISGVGVGWLRQPPGKALEWLALIYWDDDKRYSPSLKSRLTISKDTSKNQVVLKMTNIDPVDTATYYCAHHSISTIFDHWGQGTLVTVSS", "QSALTQPASVSGSPGQSITISCTATSSDVGDYNYVSWYQQHPGKAPKLMIFEVSDRPSGISNRFSGSKSGNTASLTISGLQAEDEADYYCSSYTTSSAVFGGGTKLTVL"),
            "narsoplimab": ("QVTLKESGPVLVKPTETLTLTCTVSGFSLSRGKMGVSWIRQPPGKALEWLAHIFSSDEKSYRTSLKSRLTISKDTSKNQVVLTMTNMDPVDTATYYCARIRRGGIDYWGQGTLVTVSS", "QPVLTQPPSLSVSPGQTASITCSGEKLGDKYAYWYQQKPGQSPVLVMYQDKQRPSGIPERFSGSNSGNTATLTISGTQAMDEADYYCQAWDSSTAVFGGGTKLTVL"),
            "maftivimab": ("EVQLVESGGGLVQPGGSLRLSCAASGFTSSSYAMNWVRQAPGKGLEWVSTISGMGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKRGYPHSFDIWGQGTMVTVSS", "DIQMTQSPSSLSASVGDRVTITCRASQSISSFLNWYQQKPGKAPKLLIYAASSLQSGVPSRFSGSGSGTDFTLTISSLQPEDFAYTTCQQSYSTLTFGQGTRLEIKR"),
            "lenzilumab": ("QVQLVQSGAEVKKPGASVKVSCKASGYSFTNYYIHWVRQAPGQRLEWMGWINAGNGNTKYSQKFQGRVTITRDTSASTAYMELSSLRSEDTAVYYCVRRQRFPYYFDYWGQGTLVTVSS", "EIVLTQSPATLSVSPGERATLSCRASQSVGTNVAWYQQKPGQAPRVLIYSTSSRATGITDRFSGSGSGTDFTLTISRLEPEDFAVYYCQQFNKSPLTFGGGTKVEIKR")
        }
        if name_lower in manual_seqs:
            entry['vh_seq'], entry['vl_seq'] = manual_seqs[name_lower]
        else:
            print(f"Warning: {item['name']} sequences still missing.")
    
    final_batch2.append(entry)

# Convert to DataFrame
df_batch2 = pd.DataFrame(final_batch2)

# Save to a staging file
staging_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_batch2_expanded.csv'
df_batch2.to_csv(staging_path, index=False)
print(f"Saved {len(df_batch2)} entries to {staging_path}")
