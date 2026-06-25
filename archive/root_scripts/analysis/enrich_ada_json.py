"""
Rebuild ada_db_data.json with additional quality fields from the master CSV.
New fields added: fc_mutation_notes, dose_mg, dose_freq, approval_year,
assay_generation, concomitant context, vh/vl CDRs, structural metrics,
evidence chain excerpt (truncated).
"""
import csv, json, os, re

MASTER = r'data\ada_master_136_curated.csv'
OUT_1  = r'therasik-web-source\ada_db_data.json'
OUT_2  = r'docs\ada_db_data.json'

def clean(v):
    if v is None: return ''
    v = str(v).strip
    if v.lower in ('nan','none','n/a',''): return ''
    return v

def to_float(v):
    try: return round(float(v), 3)
    except: return None

def to_int(v):
    try: return int(float(v))
    except: return None

def bool_flag(v):
    try: return bool(float(v))
    except: return None

def trunc_excerpt(v, max_chars=600):
    """Keep first 600 chars of evidence excerpt."""
    v = clean(v)
    if not v: return ''
    # Remove markdown ## headers repeated at start
    v = re.sub(r'^## \S.*?\n', '', v, flags=re.MULTILINE)
    v = v.strip
    if len(v) > max_chars:
        v = v[:max_chars].rstrip + '…'
    return v

def fc_effector_display(v):
    mapping = {
        'no_effector': '',
        'reduced_effector': '',
        'normal': '',
        'enhanced': '',
    }
    v = clean(v)
    for k, label in mapping.items:
        if k in v.lower:
            return label
    return v

rows = list(csv.DictReader(open(MASTER, encoding='utf-8')))
print(f"Master rows: {len(rows)}")

records = []
for r in rows:
    # --- Core fields (already in web) ---
    rec = {
        'name':          clean(r.get('antibody_name', r.get('name',''))),
        'origin':        clean(r.get('origin','')),
        'genetics':      clean(r.get('genetics_normalized', r.get('thera_genetics_class',''))),
        'targets':       clean(r.get('targets','')),
        'indication':    clean(r.get('indication_text','')),
        'disease_class': clean(r.get('disease_class_curated','')),
        'route':         clean(r.get('route_curated','')),
        'fc_isotype':    clean(r.get('fc_isotype','')),
        'fc_effector':   fc_effector_display(r.get('fc_effector_status','')),
        'phase':         clean(r.get('phase_bucket','')),
        'ada_pct':       clean(r.get('ada_value_display','')),
        'ada_first_pct': clean(r.get('ada_first_pct','')),
        'ada_display':   clean(r.get('ada_value_display','')),
        'v2_score':      to_float(r.get('ada_v2_score','')),
        'v2_risk':       clean(r.get('ada_v2_risk','')),
        'tier':          clean(r.get('evidence_tier','')),
        'pmids':         clean(r.get('ada_source_pmids','')),
        'citation_url':  clean(r.get('ada_source_url_primary', r.get('citation_urls',''))),
        'tcia_score':    to_float(r.get('immuno_tcia_score','')),
        'tcia_risk':     clean(r.get('immuno_risk_level','')),
        'mhcii_n_high':      to_int(r.get('immuno_n_high','')),
        'mhcii_n_medium':    to_int(r.get('immuno_n_medium','')),
        'mhcii_n_tolerated': to_int(r.get('immuno_n_tolerated','')),
        'mhcii_clusters_total': to_int(r.get('immuno_n_clusters','')),
        'mhcii_net_clusters': to_int(r.get('immuno_n_clusters','')),
        'assay_gen':     clean(r.get('assay_generation', r.get('assay_platform',''))),
        'vh_identity':   to_float(r.get('vh_identity_imgt','')),
        'vl_identity':   to_float(r.get('vl_identity_imgt','')),
        'pI':            to_float(r.get('pI','')),
        'gravy':         to_float(r.get('GRAVY','')),
        'instability':   to_float(r.get('instability_index','')),
        'net_charge':    to_float(r.get('net_charge_pH7','')),
        'hydro_patch':   to_float(r.get('hydro_patch_max9','')),
        'surf_patches':  to_int(r.get('surf_n_patches','')),
        'hydrophilic_vh':  to_float(r.get('surf_frac_exposed_vh','')),
        'hydrophilic_vl':  to_float(r.get('surf_frac_exposed_vl','')),
        'hydrophilic_frac': to_float(r.get('surf_hydrophilicity','')),
        'mtx':           clean(r.get('mtx_comedication', r.get('mtx_code',''))),
        'immuno_context': clean(r.get('immunosuppressant_context','')),
        'evidence_excerpt': trunc_excerpt(r.get('ada_evidence_chain_excerpt','')),
        'evidence_text':    trunc_excerpt(r.get('ada_evidence_chain_excerpt',''), 200),
        'surf_mode':     clean(r.get('surf_mode','')),
        'cdr_h3':        clean(r.get('vh_cdr3','')),
        # NEW enrichment fields
        'fc_mutation_notes': clean(r.get('fc_mutation_notes','')),
        'dose_mg':           clean(r.get('dose_mg','')),
        'dose_freq':         clean(r.get('dose_freq','')),
        'approval_year':     to_int(r.get('approval_year','')),
        'assay_platform':    clean(r.get('assay_platform','')),
        'concomitant_immuno': bool_flag(r.get('concomitant_immuno_likely','')),
        'checkpoint_inhibitor': bool_flag(r.get('checkpoint_inhibitor','')),
        'immune_depleting':  bool_flag(r.get('immune_depleting','')),
        'oncology':          bool_flag(r.get('oncology_indication','')),
        'vh_cdr1':           clean(r.get('vh_cdr1','')),
        'vh_cdr2':           clean(r.get('vh_cdr2','')),
        'vh_cdr3':           clean(r.get('vh_cdr3','')),
        'vl_cdr1':           clean(r.get('vl_cdr1','')),
        'vl_cdr2':           clean(r.get('vl_cdr2','')),
        'vl_cdr3':           clean(r.get('vl_cdr3','')),
        'vh_germline':       clean(r.get('vh_germline_imgt', r.get('vh_germline',''))),
        'vl_germline':       clean(r.get('vl_germline_imgt', r.get('vl_germline',''))),
        'vh_family':         clean(r.get('vh_family','')),
        'vl_family':         clean(r.get('vl_family','')),
        'vh_vl_angle':       to_float(r.get('vh_vl_angle_deg','')),
        'interface_pairs':   to_int(r.get('interface_n_pairs','')),
        'deamidation_sites': clean(r.get('deamidation_sites','')),
        'isomerization_sites': clean(r.get('isomerization_sites','')),
        'agg_motifs':        clean(r.get('agg_motifs','')),
        'cmc_flags':         clean(r.get('cmc_flags','')),
        'moa_class':         clean(r.get('moa_class','')),
    }
    records.append(rec)

out_json = json.dumps(records, ensure_ascii=False, indent=2)
with open(OUT_1, 'w', encoding='utf-8') as f:
    f.write(out_json)
with open(OUT_2, 'w', encoding='utf-8') as f:
    f.write(out_json)

print(f"Written {len(records)} records → {OUT_1}")
print(f"Fields per record: {len(records[0]) if records else 0}")
# Show sample of new fields
if records:
    r = records[0]
    print(f"\nSample record new fields:")
    print(f"  fc_mutation_notes: {r['fc_mutation_notes'][:80]}")
    print(f"  dose_mg: {r['dose_mg']}")
    print(f"  dose_freq: {r['dose_freq']}")
    print(f"  approval_year: {r['approval_year']}")
    print(f"  concomitant_immuno: {r['concomitant_immuno']}")
    print(f"  vh_cdr3: {r['vh_cdr3']}")
    print(f"  vh_vl_angle: {r['vh_vl_angle']}")
    print(f"  evidence_excerpt: {r['evidence_excerpt'][:120]}...")
