import json
import sys
from pathlib import Path

# Add suite root to path
suite_root = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
sys.path.append(str(suite_root))

from core.cmc.cmc_metrics import CMCMetricEngine
from core.cmc.mutation_advisor import MutationAdvisor

# V3 Sequences
vh_seq = "EVQLVESGGDLVKPGGSLRLSCVASGFSLIGYDLNWVRQAPGKGLQWLGIIWGDGTTDYNSAVKSRVTISKDSAKNTFYLQLQSLRAEETAVYYCARGGYWYATSYYFDYWGQGTSVTVSS"
vl_seq = "EIVLTQSPASLSLSQEEKVTITCRASQSISNNLNWYQQKPGQAPKLLIYYTSRFHSGVPSRFSGSGSGTDFSFTISSLEPEDVAVYYCQQEHTLPYTFGQGTKVELK"

# Compute raw metrics
print("Computing metrics...")
metrics = CMCMetricEngine.compute_metrics(vh_seq, vl_seq)

# Load rules and ref stats
ref_stats_path = suite_root / "data" / "reference" / "AbRef458_27m_stats_v1.json"
rules_path = suite_root / "data" / "rules" / "cmc_rules_v1.json"

with open(ref_stats_path) as f:
    ref_stats = json.load(f)
with open(rules_path) as f:
    rules = json.load(f)

# Run MutationAdvisor
print("Running MutationAdvisor...")
advisor = MutationAdvisor(
    vh_seq=vh_seq,
    vl_seq=vl_seq,
    metrics=metrics,
    reference_stats=ref_stats,
    rules=rules,
)

suggestions = advisor.advise()

print("\nCMC Optimization Suggestions for V3:")
for sug in suggestions:
    print(f"- {sug['metric']}: {sug['suggestion']}")
    print(f"  Rationale: {sug['rationale']}")
    for mut in sug.get('mutations', []):
        print(f"  * {mut['chain']} {mut['pos']}: {mut['old_aa']} -> {mut['new_aa']} ({mut['type']})")

with open("v3_smart_cmc_suggestions.json", "w") as f:
    json.dump(suggestions, f, indent=2)
