import pandas as pd
import numpy as np
from pathlib import Path
import re

# Paths
PROJECT_ROOT = Path('.').resolve()
PRED_PARQUET = PROJECT_ROOT / "reports" / "slice3_vhh_mhcii_predictions.parquet"
STRATEGY_CSV = PROJECT_ROOT / "reports" / "slice3_vhh_comprehensive_functional_library.csv"
OUT_MD = PROJECT_ROOT / "reports" / "slice3_vhh_epitope_clustering_report.md"

# 1. Load Data
print("Loading data...")
df_pred = pd.read_parquet(PRED_PARQUET)
df_strat = pd.read_csv(STRATEGY_CSV)

# Map Strategy
strat_map = df_strat.set_index('Drug Name')['Humanization Strategy'].to_dict()

# Filter: Only Native variant (clinical molecule) and Strong/Weak Binders
# Rank <= 2.0 is the standard threshold for IEDB MHC-II
df_binders = df_pred[
    (df_pred['variant'] == 'native') & 
    (df_pred['rank'] <= 2.0)
].copy()

df_binders['record_id'] = df_binders['antibody_id']
df_binders['Strategy'] = df_binders['record_id'].map(strat_map)

# 2. Region Mapping Logic (Approximate based on position)
# VHH structural regions (approx 120aa):
# FR1: 1-25, CDR1: 26-32, FR2: 33-50, CDR2: 51-58, FR3: 59-95, CDR3: 96-110+, FR4: End
# We use a simplified mapping for 15-mer peptides based on their Start Position.
# A 15-mer starting at 30 covers 30-44 (CDR1-FR2 junction).
def map_region(start_pos):
    p = int(start_pos)
    if p < 25: return "FR1"
    if p < 35: return "CDR1_Zone"
    if p < 50: return "FR2_Hallmark_Zone"
    if p < 60: return "CDR2_Zone"
    if p < 90: return "FR3"
    if p < 115: return "CDR3_Zone"
    return "FR4"

df_binders['Region'] = df_binders['start'].apply(map_region)

# 3. Clustering Analysis

# A. Regional Hotspots
region_counts = df_binders.groupby(['Strategy', 'Region']).size().unstack(fill_value=0)
# Normalize by number of antibodies in each strategy to get "Epitopes per Antibody"
n_per_strat = df_strat['Humanization Strategy'].value_counts()
region_norm = region_counts.div(n_per_strat, axis=0)

# B. Shared Epitope Discovery (Sequence Clustering)
# We cluster peptides by sequence similarity (e.g. sharing a 9-mer core)
# Simple approach: Find identical 9-mer cores in the binders
def extract_cores(peptide):
    # A 15-mer has 15-9+1 = 7 possible 9-mer cores.
    # We take the middle one or iterate.
    # MHC binding is usually determined by a 9-mer core.
    cores = set()
    for i in range(len(peptide)-9+1):
        cores.add(peptide[i:i+9])
    return cores

# Build a registry of cores
core_registry = {} # core -> list of (antibody, region)
for _, row in df_binders.iterrows():
    pep = row['peptide']
    ab = row['record_id']
    reg = row['Region']
    strat = row['Strategy']
    
    cores = extract_cores(pep)
    for c in cores:
        if c not in core_registry:
            core_registry[c] = set()
        core_registry[c].add((ab, strat, reg))

# Find cores shared by multiple antibodies
shared_cores = []
for core, occ in core_registry.items():
    abs_involved = set(x[0] for x in occ)
    if len(abs_involved) >= 2: # Shared by at least 2 antibodies
        strats = set(x[1] for x in occ)
        regions = set(x[2] for x in occ)
        shared_cores.append({
            "Core": core,
            "Count": len(abs_involved),
            "Antibodies": ", ".join(list(abs_involved)[:5]), # Limit display
            "Strategies": ", ".join(strats),
            "Regions": ", ".join(regions)
        })

df_shared = pd.DataFrame(shared_cores).sort_values('Count', ascending=False)

# 4. Generate Report
with open(OUT_MD, 'w', encoding='utf-8') as f:
    f.write("# VHH MHC-II Epitope Clustering Report\n\n")
    f.write("Analysis of predicted T-cell epitopes (Rank < 2.0) across 19 VHH clinical molecules.\n\n")
    
    f.write("## 1. Epitope Density by Region (Hotspot Map)\n")
    f.write("Average number of strong binder peptides per antibody in each region:\n\n")
    f.write(region_norm.round(1).to_markdown())
    
    f.write("\n\n### Interpretation\n")
    f.write("- **CDR3_Zone**: Expected to be the main source of immunogenicity (Neo-epitopes).\n")
    f.write("- **FR2_Hallmark_Zone**: Critical for VHH. Does retaining hallmarks (SR) cause more epitopes here than Grafting (BM)?\n")
    
    f.write("\n## 2. Shared Epitope Clusters (Public Epitopes)\n")
    f.write("9-mer cores found in high-affinity binders across multiple different antibodies.\n\n")
    if not df_shared.empty:
        f.write(df_shared.head(15).to_markdown(index=False))
    else:
        f.write("No shared epitopes found across antibodies (High Specificity).\n")

    f.write("\n\n## 3. High-Risk Antibodies\n")
    f.write("Top 5 antibodies with the most predicted epitopes:\n\n")
    top_risk = df_binders['record_id'].value_counts().head(5).to_frame("Epitope Count")
    f.write(top_risk.to_markdown())

print(f"Report generated: {OUT_MD}")
