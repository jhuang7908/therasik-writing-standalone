"""Extract comprehensive ADA statistics from the master CSV for report generation."""
import csv, statistics, json
from collections import Counter

f = 'data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv'
rows = list(csv.DictReader(open(f, encoding='utf-8')))
out = {}

# --- Parse ADA values ---
def parse_ada(r):
    v = r.get('ada_first_pct','').strip().replace('%','').replace('<','').replace('>','').replace('~','')
    try: return float(v)
    except: return None

ada_all = [(r['antibody_name'], parse_ada(r)) for r in rows]
ada_all = [(n,v) for n,v in ada_all if v is not None]
vals = [v for _,v in ada_all]

out['total'] = len(rows)
out['ada_parsed'] = len(ada_all)
out['mean'] = round(statistics.mean(vals), 1)
out['median'] = round(statistics.median(vals), 1)
out['stdev'] = round(statistics.stdev(vals), 1)
out['min_val'] = round(min(vals), 1)
out['min_names'] = [n for n,v in ada_all if v == min(vals)]
out['max_val'] = round(max(vals), 1)
out['max_names'] = [n for n,v in ada_all if v == max(vals)]
vals_sorted = sorted(vals)
n = len(vals_sorted)
out['q1'] = round(vals_sorted[n//4], 1)
out['q3'] = round(vals_sorted[3*n//4], 1)
out['bucket_lt2'] = sum(1 for v in vals if v < 2)
out['bucket_2_5'] = sum(1 for v in vals if 2 <= v < 5)
out['bucket_5_10'] = sum(1 for v in vals if 5 <= v < 10)
out['bucket_10_20'] = sum(1 for v in vals if 10 <= v < 20)
out['bucket_ge20'] = sum(1 for v in vals if v >= 20)

# --- By genetics group ---
groups = {}
for r in rows:
    g = r.get('genetics_normalized','').strip()
    if g in ('humanised','humanised_engineered','humanized'):
        gkey = 'HU'
    elif g == 'genetically_human':
        gkey = 'FH'
    else:
        gkey = 'OTHER'
    v = parse_ada(r)
    if v is not None:
        groups.setdefault(gkey, []).append((r['antibody_name'], v))

for gk in ['HU','FH']:
    gvals = [v for _,v in groups[gk]]
    prefix = gk.lower()
    out[f'{prefix}_n'] = len(gvals)
    out[f'{prefix}_mean'] = round(statistics.mean(gvals), 1)
    out[f'{prefix}_median'] = round(statistics.median(gvals), 1)
    out[f'{prefix}_stdev'] = round(statistics.stdev(gvals), 1)
    out[f'{prefix}_min'] = round(min(gvals), 1)
    out[f'{prefix}_max'] = round(max(gvals), 1)
    top5 = sorted(groups[gk], key=lambda x: -x[1])[:5]
    out[f'{prefix}_top5'] = [(n, round(v,1)) for n,v in top5]
    bot5 = sorted(groups[gk], key=lambda x: x[1])[:5]
    out[f'{prefix}_bot5'] = [(n, round(v,1)) for n,v in bot5]

# --- Tiers ---
tiers = Counter(r.get('evidence_tier','').strip() for r in rows)
out['tier_a'] = tiers.get('A', 0)
out['tier_b'] = tiers.get('B', 0)

# --- Routes ---
route_ada = {}
for r in rows:
    rt = r.get('route_curated','').strip()
    if 'SC' in rt: rkey = 'SC'
    elif 'IV' in rt: rkey = 'IV'
    elif 'IM' in rt: rkey = 'IM'
    elif 'IVT' in rt: rkey = 'IVT'
    else: rkey = rt
    v = parse_ada(r)
    if v is not None:
        route_ada.setdefault(rkey, []).append(v)

out['route_stats'] = {}
for rkey in ['IV','SC','IM','IVT']:
    if rkey in route_ada:
        rv = route_ada[rkey]
        out['route_stats'][rkey] = {'n': len(rv), 'mean': round(statistics.mean(rv),1), 'median': round(statistics.median(rv),1)}

# --- Disease class ---
disease_ada = {}
for r in rows:
    d = r.get('disease_class_curated','').strip()
    v = parse_ada(r)
    if v is not None:
        disease_ada.setdefault(d, []).append(v)

out['disease_stats'] = {}
for d, dv in sorted(disease_ada.items(), key=lambda x: -len(x[1])):
    if len(dv) >= 3:
        out['disease_stats'][d] = {'n': len(dv), 'mean': round(statistics.mean(dv),1), 'median': round(statistics.median(dv),1)}

# --- Fc isotype ---
iso_ada = {}
for r in rows:
    iso = r.get('fc_isotype','').strip()
    v = parse_ada(r)
    if v is not None and iso:
        iso_ada.setdefault(iso, []).append(v)

out['isotype_stats'] = {}
for iso, iv in sorted(iso_ada.items(), key=lambda x: -len(x[1])):
    if len(iv) >= 3:
        out['isotype_stats'][iso] = {'n': len(iv), 'mean': round(statistics.mean(iv),1), 'median': round(statistics.median(iv),1)}

# --- Immunosuppressant ---
supp_ada = {'yes': [], 'no': [], 'unknown': []}
for r in rows:
    s = r.get('immunosuppressant_context','').strip().lower()
    v = parse_ada(r)
    if v is None: continue
    if s in ('mtx','yes','steroids','aza','pred','combo'):
        supp_ada['yes'].append(v)
    elif s in ('no','none',''):
        supp_ada['no'].append(v)
    else:
        supp_ada['unknown'].append(v)

out['supp_stats'] = {}
for sk, sv in supp_ada.items():
    if sv:
        out['supp_stats'][sk] = {'n': len(sv), 'mean': round(statistics.mean(sv),1), 'median': round(statistics.median(sv),1)}

# --- Half-life ---
hl_vals = []
for r in rows:
    try: hl_vals.append(float(r.get('half_life_days','').strip()))
    except: pass
out['hl_n'] = len(hl_vals)
if hl_vals:
    out['hl_mean'] = round(statistics.mean(hl_vals), 1)
    out['hl_median'] = round(statistics.median(hl_vals), 1)
    out['hl_range'] = [round(min(hl_vals),1), round(max(hl_vals),1)]

# --- VH/VL germline identity ---
for col, key in [('vh_germline_identity','vh_id'), ('vl_germline_identity','vl_id')]:
    id_vals = []
    for r in rows:
        try: id_vals.append(float(r.get(col,'').strip()))
        except: pass
    out[f'{key}_n'] = len(id_vals)
    if id_vals:
        out[f'{key}_mean'] = round(statistics.mean(id_vals), 3)
        out[f'{key}_range'] = [round(min(id_vals),3), round(max(id_vals),3)]

# --- Immunogenicity features ---
immuno_cols = ['immuno_tcia_score','immuno_n_high','immuno_n_medium','immuno_n_clusters']
for col in immuno_cols:
    iv = []
    for r in rows:
        try: iv.append(float(r.get(col,'').strip()))
        except: pass
    if iv:
        out[f'{col}_n'] = len(iv)
        out[f'{col}_mean'] = round(statistics.mean(iv), 2)
        out[f'{col}_range'] = [round(min(iv),2), round(max(iv),2)]

# --- Assay generation ---
assay_ada = {}
for r in rows:
    ag = r.get('assay_generation','').strip()
    v = parse_ada(r)
    if v is not None and ag:
        assay_ada.setdefault(ag, []).append(v)
out['assay_stats'] = {}
for ak, av in sorted(assay_ada.items()):
    if len(av) >= 3:
        out['assay_stats'][ak] = {'n': len(av), 'mean': round(statistics.mean(av),1)}

# --- Top 10 highest and lowest ADA ---
top10 = sorted(ada_all, key=lambda x: -x[1])[:10]
bot10 = sorted(ada_all, key=lambda x: x[1])[:10]
out['top10'] = []
out['bot10'] = []
for n,v in top10:
    r_ = next(r for r in rows if r['antibody_name']==n)
    out['top10'].append({'name':n, 'ada':round(v,1), 'origin':r_.get('genetics_normalized',''), 'target':r_.get('targets',''), 'route':r_.get('route_curated',''), 'tier':r_.get('evidence_tier','')})
for n,v in bot10:
    r_ = next(r for r in rows if r['antibody_name']==n)
    out['bot10'].append({'name':n, 'ada':round(v,1), 'origin':r_.get('genetics_normalized',''), 'target':r_.get('targets',''), 'route':r_.get('route_curated',''), 'tier':r_.get('evidence_tier','')})

# --- Spearman correlations (compute if scipy available) ---
try:
    from scipy.stats import spearmanr
    import numpy as np
    feature_cols = [
        'immuno_tcia_score','immuno_n_high','immuno_n_medium','immuno_n_clusters',
        'vh_germline_identity','vl_germline_identity','half_life_days',
        'pI','GRAVY','instability_index','net_charge_pH7',
        'hydro_patch_max9','charge_patch_max7',
        'surf_hydrophilicity','surf_frac_exposed_vh','surf_frac_exposed_vl'
    ]
    
    # All panel
    corrs_all = {}
    for col in feature_cols:
        pairs = []
        for r in rows:
            a = parse_ada(r)
            try: fv = float(r.get(col,'').strip())
            except: continue
            if a is not None:
                pairs.append((fv, a))
        if len(pairs) >= 20:
            x, y = zip(*pairs)
            rho, p = spearmanr(x, y)
            corrs_all[col] = {'rho': round(rho,3), 'p': round(p,4), 'n': len(pairs)}
    out['corrs_all'] = dict(sorted(corrs_all.items(), key=lambda x: -abs(x[1]['rho'])))
    
    # By group
    for gk in ['HU','FH']:
        g_names = set(n for n,_ in groups[gk])
        g_rows = [r for r in rows if r['antibody_name'] in g_names]
        corrs_g = {}
        for col in feature_cols:
            pairs = []
            for r in g_rows:
                a = parse_ada(r)
                try: fv = float(r.get(col,'').strip())
                except: continue
                if a is not None:
                    pairs.append((fv, a))
            if len(pairs) >= 15:
                x, y = zip(*pairs)
                rho, p = spearmanr(x, y)
                corrs_g[col] = {'rho': round(rho,3), 'p': round(p,4), 'n': len(pairs)}
        out[f'corrs_{gk.lower()}'] = dict(sorted(corrs_g.items(), key=lambda x: -abs(x[1]['rho'])))
    
    print('Scipy correlations computed.')
except ImportError:
    print('Scipy not available - skipping correlations.')

json.dump(out, open('data/immunogenicity_knowledge_base/reports/_138_stats.json','w'), indent=2, ensure_ascii=False)
print('Stats written to _138_stats.json')
print(json.dumps(out, indent=2, ensure_ascii=False)[:3000])
