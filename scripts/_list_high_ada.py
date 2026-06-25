import os
import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
df = pd.read_csv(
    os.path.join(ROOT, "data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv")
)
df = df[df["ada_first_pct"].notna()].copy()
hi = df[df["ada_first_pct"] >= 30].sort_values("ada_first_pct", ascending=False)
for _, r in hi.iterrows():
    ex = str(r.get("ada_evidence_chain_excerpt") or "")[:140].replace("\n", " ")
    print(
        f"{r['ada_first_pct']:5.1f}% | {str(r['antibody_name']):22} | tier {r['evidence_tier']} | {ex}..."
    )
print("Count:", len(hi))
