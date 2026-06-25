import pandas as pd, sys
df = pd.read_csv('data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv', low_memory=False)
fields = ['disease_class_curated','dose_mg','dose_freq','half_life_days',
          'assay_platform','assay_generation','mtx_comedication',
          'immunosuppressant_context','route_curated','checkpoint_inhibitor',
          'concomitant_immuno_likely']
lines = []
for c in fields:
    if c in df.columns:
        nn = int(df[c].notna().sum())
        top = df[c].value_counts(dropna=False).head(4).to_dict()
        lines.append(f"{c}: non_null={nn}  top={top}")
    else:
        lines.append(f"{c}: MISSING")
out = '\n'.join(lines)
print(out)
with open('scripts/_clinical_audit.txt','w',encoding='utf-8') as f:
    f.write(out)
