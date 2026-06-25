import pandas as pd
df = pd.read_csv('data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv', low_memory=False)

fields2 = ['ada_profile_disease','ada_profile_route','indication_unified',
           'phase_unified','moa_class','target_unified','discovery_platform',
           'fc_effector_status','fc_engineering','approval_year']
lines = []
for c in fields2:
    if c in df.columns:
        nn = int(df[c].notna().sum())
        top = df[c].value_counts(dropna=False).head(5).to_dict()
        lines.append(f"{c}: non_null={nn}\n  top={top}")
    else:
        lines.append(f"{c}: MISSING")

# Also check route cleaning
if 'route_curated' in df.columns:
    lines.append("\nroute_curated full dist:")
    lines.append(str(df['route_curated'].value_counts(dropna=False).to_dict()))

# assay platform categories
if 'assay_platform' in df.columns:
    lines.append("\nassay_platform full dist:")
    lines.append(str(df['assay_platform'].value_counts(dropna=False).to_dict()))

out = '\n'.join(lines)
print(out)
with open('scripts/_clinical_audit2.txt','w',encoding='utf-8') as f:
    f.write(out)
