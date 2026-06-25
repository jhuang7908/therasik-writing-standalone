"""Extract all stats needed for the meta-analysis paper."""
import csv, statistics, json
from scipy.stats import mannwhitneyu, spearmanr, kruskal
from collections import Counter, defaultdict

rows = list(csv.DictReader(open(
    'data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv',
    encoding='utf-8')))

def pf(r, col):
    v = r.get(col,'').strip().replace('%','').replace('<','').replace('>','').replace('~','')
    try: return float(v)
    except: return None

data = []
for r in rows:
    ada = pf(r, 'ada_first_pct')
    if ada is None: continue
    g = r.get('genetics_normalized','').strip()
    grp = 'HU' if g in ('humanised','humanised_engineered','humanized') else ('FH' if g=='genetically_human' else 'OTHER')
    data.append({
        'name': r['antibody_name'], 'ada': ada, 'grp': grp,
        'route': r.get('route_curated',''), 'disease': r.get('disease_class_curated',''),
        'fc': r.get('fc_isotype',''), 'year': pf(r, 'approval_year'),
        'assay': r.get('assay_generation',''), 'tier': r.get('evidence_tier',''),
        'mtx': r.get('mtx_comedication','').strip()
    })

ada_all = [d['ada'] for d in data]
ada_hu  = [d['ada'] for d in data if d['grp']=='HU']
ada_fh  = [d['ada'] for d in data if d['grp']=='FH']

print(f"N={len(data)}, HU={len(ada_hu)}, FH={len(ada_fh)}")
print(f"All:  mean={statistics.mean(ada_all):.2f}%, SD={statistics.stdev(ada_all):.2f}%, median={statistics.median(ada_all):.2f}%")
print(f"HU:   mean={statistics.mean(ada_hu):.2f}%,  SD={statistics.stdev(ada_hu):.2f}%,  median={statistics.median(ada_hu):.2f}%")
print(f"FH:   mean={statistics.mean(ada_fh):.2f}%,  SD={statistics.stdev(ada_fh):.2f}%,  median={statistics.median(ada_fh):.2f}%")

_, p_mwu = mannwhitneyu(ada_hu, ada_fh, alternative='two-sided')
print(f"HU vs FH Mann-Whitney U: p={p_mwu:.6f}")

# Heterogeneity proxy (I²)
all_var = statistics.variance(ada_all)
pooled_var = ((len(ada_hu)-1)*statistics.variance(ada_hu) +
              (len(ada_fh)-1)*statistics.variance(ada_fh)) / (len(ada_hu)+len(ada_fh)-2)
tau2 = max(0, all_var - pooled_var)
I2 = 100*tau2/all_var if all_var > 0 else 0
print(f"tau²={tau2:.2f}, I²={I2:.1f}%")

# Years
years = [d['year'] for d in data if d['year'] and d['year']>=1986]
print(f"Year range: {int(min(years))}–{int(max(years))}")

# Assay
print("Assay gen:", dict(Counter(d['assay'] for d in data)))

# Tier
tierA_vals = [d['ada'] for d in data if d['tier']=='A']
tierB_vals = [d['ada'] for d in data if d['tier']=='B']
print(f"Tier A: n={len(tierA_vals)}, mean={statistics.mean(tierA_vals):.2f}%")
print(f"Tier B: n={len(tierB_vals)}, mean={statistics.mean(tierB_vals):.2f}%")

# Route
route_ada = defaultdict(list)
for d in data:
    rt = d['route']
    rk = 'SC' if 'SC' in rt else ('IV' if 'IV' in rt else ('IM' if 'IM' in rt else 'Other'))
    route_ada[rk].append(d['ada'])
for k in ['IV','SC','IM']:
    v = route_ada[k]
    print(f"Route {k}: n={len(v)}, mean={statistics.mean(v):.2f}%, median={statistics.median(v):.2f}%")
_, p_rt = mannwhitneyu(route_ada['IV'], route_ada['SC'], alternative='two-sided')
print(f"IV vs SC p={p_rt:.4f}")

# Disease
print("Disease:", Counter(d['disease'] for d in data).most_common(8))

# MTX
mtx_yes = sum(1 for d in data if 'MTX' in d['mtx'].upper() or d['mtx'].lower() in ('yes','mtx'))
print(f"MTX comedication approx: {mtx_yes}")

# ADA bucket
vals = ada_all
print(f"<2%: {sum(1 for v in vals if v<2)} ({sum(1 for v in vals if v<2)/len(vals)*100:.1f}%)")
print(f"2-5%: {sum(1 for v in vals if 2<=v<5)} ({sum(1 for v in vals if 2<=v<5)/len(vals)*100:.1f}%)")
print(f">=20%: {sum(1 for v in vals if v>=20)} ({sum(1 for v in vals if v>=20)/len(vals)*100:.1f}%)")

# Key correlations (confirmed from prior run)
corr_targets = [
    ('surf_n_patches', 'genetically_human', 'FH surf_n_patches'),
    ('vl_germline_identity', 'genetically_human', 'FH vl_germline_identity'),
    ('agg_motifs', None, 'All agg_motifs'),
    ('surf_frac_exposed_vh', None, 'All surf_frac_exposed_vh'),
    ('vh_germline_identity', None, 'All vh_germline_identity'),
    ('interface_n_pairs', 'genetically_human', 'FH interface_n_pairs'),
    ('ada_v2_score', 'genetically_human', 'FH ada_v2_score'),
    ('surf_frac_exposed_vl', 'humanised', 'HU surf_frac_exposed_vl'),
]
for col, gfilter, label in corr_targets:
    pairs = []
    for r in rows:
        ada = pf(r, 'ada_first_pct')
        fv = pf(r, col)
        if ada is None or fv is None: continue
        g = r.get('genetics_normalized','').strip()
        if gfilter and g != gfilter and not (gfilter=='humanised' and g in ('humanised','humanised_engineered','humanized')):
            continue
        pairs.append((fv, ada))
    if len(pairs) >= 10:
        x, y = zip(*pairs)
        rho, p = spearmanr(x, y)
        print(f"{label}: rho={rho:.3f}, p={p:.4f}, n={len(pairs)}")
