import json
from pathlib import Path

# Load IgG-like IDs
with open("data/design_rules/bispecific_125_igg_like.json", "r") as f:
    igg_like_data = json.load(f)
igg_ids = set(igg_like_data["antibody_ids"])

# Load ESMFold IDs (from FASTA)
esm_ids = set()
with open("data/design_rules/multispecific_linker_pipeline/esmfold_input.fasta", "r") as f:
    for line in f:
        if line.startswith(">"):
            esm_ids.add(line[1:].strip())

overlap = igg_ids.intersection(esm_ids)
print(f"Overlap between IgG-like (75) and ESMFold input (84): {len(overlap)}")
print("Overlap IDs:", overlap)
