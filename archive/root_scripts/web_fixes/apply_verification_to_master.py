"""
Apply verification results to the master CSV and rebuild ada_db_data.json.

Findings from 2-pass verification:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERIFIED (41): PMID-confirmed match within ±3%
FALSE POSITIVE (19): algorithm extracted efficacy % not ADA %
  → These are verified (stored value was correct)
URL_LIVE (34): source URL accessible, not deep-parsed
  → Keep as TIER B / TIER A per existing tier assignment

REQUIRE CORRECTION:
1. Adalimumab    stored=30% → CORRECT but needs context note
   (DailyMed shows 6.8-9.4% WITH MTX; 30% is overall rate)
2. Fulranumab    stored=6%  → CORRECT
   (PMID 24590506 shows 60% was ARTIFACT due to NGF interference;
    corrected rate after validated assay = ~6%)
3. Enuzovimab   stored=1.5% → PMID WRONG (39793935 is for HFB30132A,
   a different COVID-19 mAb; 50% = PD neutralization EC50, not ADA)
   → Mark as UNCERTAIN, needs new source
4. Olokizumab   stored=10-15% → POSSIBLE DISCREPANCY
   (PMID 36109142 shows 3.2-7%; may be different arm/timepoint)
   → Mark as UNCERTAIN

UNREACHABLE / PAYWALL (42):
  → Keep existing evidence_tier; mark as source_status=PAYWALL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
import csv, json, os

MASTER_CSV = r'data\ada_master_136_curated.csv'
REPORT_CSV = r'data\ada_evidence_verification_report.csv'
REPORT2_CSV= r'data\ada_evidence_verify_pass2.csv'

OUT_MASTER = r'data\ada_master_136_curated.csv'   # overwrite in place
OUT_JSON_1 = r'therasik-web-source\ada_db_data.json'
OUT_JSON_2 = r'docs\ada_db_data.json'
OUT_JSON_3 = r'insynbio-web-source\ada_db_data.json'

rows  = list(csv.DictReader(open(MASTER_CSV,  encoding='utf-8')))
rep1  = {r['antibody_name']: r for r in csv.DictReader(open(REPORT_CSV,  encoding='utf-8'))}
rep2  = {r['antibody_name']: r for r in csv.DictReader(open(REPORT2_CSV, encoding='utf-8'))}

# ── Corrections ───────────────────────────────────────────────────────────────
CORRECTIONS = {
    'Relatlimab': {
        'verify_status':    'CORRECTED',
        'verify_note':      ('CORRECTED from <2% (AI-generated) to 5.6% (16/286) per FDA PI '
                             'Opdualag §12.6, RELATIVITY-047 24-month data. '
                             'Neutralizing antibodies: 0.3% (1/286). '
                             'DailyMed setid b22c9d83-3256-4e17-85f7-f331a504adc6.'),
    },
    'Olokizumab': {
        'verify_status':    'CORRECTED',
        'verify_note':      ('CORRECTED from 10-15% (AI-generated) to 3.2% (Q4W) / 7.0% (Q2W) '
                             'per PMID 36109142 (Feist et al., Ann Rheum Dis 2022;81:1661-1668, '
                             'Phase III TNFi-IR trial, n=197). No impact on clinical outcomes '
                             'in ADA+ vs ADA- patients.'),
    },
    'Adalimumab': {
        'verify_status':    'VERIFIED_WITH_CONTEXT',
        'verify_note':      ('FDA PI confirmed ~30% overall ADA rate. '
                             'DailyMed shows 6.8–9.4% WITH MTX co-administration; '
                             '30% reflects mixed/no-MTX population. Value is correct '
                             'for the stated concomitant context.'),
    },
    'Fulranumab': {
        'verify_status':    'VERIFIED',
        'verify_note':      ('PMID 24590506 confirms >60% apparent ADA in early assay '
                             'was a methodological artifact caused by NGF interference '
                             'during acid-dissociation pre-treatment. After corrected '
                             'validated assay, true rate ~6%. Stored value is correct.'),
    },
    'Enuzovimab': {
        'verify_status':    'UNCERTAIN',
        'verify_note':      ('PMID 39793935 is assigned to HFB30132A (SARS-CoV-2 nAb), '
                             'a different molecule. The 50% in abstract = PD neutralization '
                             'EC50 dilution, not ADA incidence. Stored 1.5% needs a '
                             'valid primary source. Flagged for re-sourcing.'),
    },
    'Olokizumab': {
        'verify_status':    'UNCERTAIN',
        'verify_note':      ('PMID 36109142 (24-week RA trial) reports ADA 3.2–7.0%. '
                             'Stored value 10–15% may reflect different study arms, '
                             'time points, or populations. Needs clarification against '
                             'primary Artlegia registration trial data.'),
    },
}

# ── Determine verify_status for all records ────────────────────────────────────
def get_verify_status(name, r1, r2):
    # Explicit corrections first
    if name in CORRECTIONS:
        return CORRECTIONS[name]['verify_status'], CORRECTIONS[name]['verify_note']
    # Pass 2 takes priority
    if name in r2:
        s2 = r2[name]['pass2_status']
        if s2 == 'FALSE_POSITIVE':
            return 'VERIFIED', 'Pass-2 confirmed: original discrepancy was efficacy data, not ADA'
        if s2 == 'VERIFIED':
            return 'VERIFIED', r2[name]['pass2_note']
        if s2 in ('PAYWALL', 'URL_LIVE'):
            pass  # fall through to pass 1
    if name in r1:
        s1 = r1[name]['verify_status']
        if s1 == 'VERIFIED':
            return 'VERIFIED', 'PMID-confirmed ±3%'
        if s1 == 'URL_LIVE':
            return 'SOURCE_LIVE', 'URL verified live; ADA % not auto-extracted'
        if s1 == 'UNREACHABLE':
            return 'SOURCE_UNREACHABLE', r1[name].get('note', '')
        if s1 == 'NO_SOURCE':
            return 'NO_SOURCE', 'No verifiable PMID or URL'
        if s1 == 'UNCERTAIN':
            return 'UNCERTAIN', r1[name].get('note', '')
    return 'NOT_VERIFIED', ''

def to_float(v):
    try: return round(float(v), 3)
    except: return None

def clean(v):
    v = str(v).strip()
    return '' if v.lower() in ('nan','none','n/a','') else v

def bool_flag(v):
    try: return bool(float(v))
    except: return None

def to_int(v):
    try: return int(float(v))
    except: return None

def trunc(v, n=600):
    v = clean(v)
    if not v: return ''
    import re
    v = re.sub(r'^## \S.*?\n', '', v, flags=re.MULTILINE).strip()
    return v[:n].rstrip() + '…' if len(v) > n else v

def fc_eff(v):
    v = clean(v)
    m = {'no_effector':'No effector function','reduced_effector':'Reduced effector',
         'normal':'Normal (ADCC/CDC active)','enhanced':'Enhanced effector'}
    for k,l in m.items():
        if k in v.lower(): return l
    return v

# ── Rebuild JSON ──────────────────────────────────────────────────────────────
records = []
stats = {'VERIFIED':0,'VERIFIED_WITH_CONTEXT':0,'SOURCE_LIVE':0,
         'UNCERTAIN':0,'SOURCE_UNREACHABLE':0,'NO_SOURCE':0,'NOT_VERIFIED':0}

for row in rows:
    name = clean(row.get('antibody_name',''))
    vstatus, vnote = get_verify_status(name, rep1, rep2)
    stats[vstatus] = stats.get(vstatus, 0) + 1

    rec = {
        'name':          name,
        'origin':        clean(row.get('origin','')),
        'genetics':      clean(row.get('genetics_normalized', row.get('thera_genetics_class',''))),
        'targets':       clean(row.get('targets','')),
        'indication':    clean(row.get('indication_text','')),
        'disease_class': clean(row.get('disease_class_curated','')),
        'route':         clean(row.get('route_curated','')),
        'fc_isotype':    clean(row.get('fc_isotype','')),
        'fc_effector':   fc_eff(row.get('fc_effector_status','')),
        'fc_mutation_notes': clean(row.get('fc_mutation_notes','')),
        'phase':         clean(row.get('phase_bucket','')),
        'ada_pct':       to_float(row.get('ada_first_pct','')),
        'ada_display':   clean(row.get('ada_value_display','')),
        'v2_score':      to_float(row.get('ada_v2_score','')),
        'v2_risk':       clean(row.get('ada_v2_risk','')),
        'tier':          clean(row.get('evidence_tier','')),
        'pmids':         clean(row.get('ada_source_pmids','')),
        'citation_url':  clean(row.get('ada_source_url_primary', row.get('citation_urls',''))),
        'tcia_score':    to_float(row.get('immuno_tcia_score','')),
        'tcia_risk':     clean(row.get('immuno_risk_level','')),
        'mhcii_n_high':       to_int(row.get('immuno_n_high','')),
        'mhcii_n_medium':     to_int(row.get('immuno_n_medium','')),
        'mhcii_n_tolerated':  to_int(row.get('immuno_n_tolerated','')),
        'mhcii_clusters_total': to_int(row.get('immuno_n_clusters','')),
        'mhcii_net_clusters': to_int(row.get('immuno_n_clusters','')),
        'assay_gen':     clean(row.get('assay_generation', row.get('assay_platform',''))),
        'assay_platform': clean(row.get('assay_platform','')),
        'vh_identity':   to_float(row.get('vh_identity_imgt','')),
        'vl_identity':   to_float(row.get('vl_identity_imgt','')),
        'pI':            to_float(row.get('pI','')),
        'gravy':         to_float(row.get('GRAVY','')),
        'instability':   to_float(row.get('instability_index','')),
        'net_charge':    to_float(row.get('net_charge_pH7','')),
        'hydro_patch':   to_float(row.get('hydro_patch_max9','')),
        'surf_patches':  to_int(row.get('surf_n_patches','')),
        'hydrophilic_vh':  to_float(row.get('surf_frac_exposed_vh','')),
        'hydrophilic_vl':  to_float(row.get('surf_frac_exposed_vl','')),
        'hydrophilic_frac': to_float(row.get('surf_hydrophilicity','')),
        'mtx':           clean(row.get('mtx_comedication', row.get('mtx_code',''))),
        'immuno_context': clean(row.get('immunosuppressant_context','')),
        'evidence_excerpt': trunc(row.get('ada_evidence_chain_excerpt','')),
        'evidence_text':    trunc(row.get('ada_evidence_chain_excerpt',''), 200),
        'surf_mode':     clean(row.get('surf_mode','')),
        'cdr_h3':        clean(row.get('vh_cdr3','')),
        'dose_mg':       clean(row.get('dose_mg','')),
        'dose_freq':     clean(row.get('dose_freq','')),
        'approval_year': to_int(row.get('approval_year','')),
        'concomitant_immuno': bool_flag(row.get('concomitant_immuno_likely','')),
        'checkpoint_inhibitor': bool_flag(row.get('checkpoint_inhibitor','')),
        'immune_depleting':  bool_flag(row.get('immune_depleting','')),
        'oncology':          bool_flag(row.get('oncology_indication','')),
        'vh_cdr1':   clean(row.get('vh_cdr1','')),
        'vh_cdr2':   clean(row.get('vh_cdr2','')),
        'vh_cdr3':   clean(row.get('vh_cdr3','')),
        'vl_cdr1':   clean(row.get('vl_cdr1','')),
        'vl_cdr2':   clean(row.get('vl_cdr2','')),
        'vl_cdr3':   clean(row.get('vl_cdr3','')),
        'vh_germline':   clean(row.get('vh_germline_imgt', row.get('vh_germline',''))),
        'vl_germline':   clean(row.get('vl_germline_imgt', row.get('vl_germline',''))),
        'vh_family':     clean(row.get('vh_family','')),
        'vl_family':     clean(row.get('vl_family','')),
        'vh_vl_angle':   to_float(row.get('vh_vl_angle_deg','')),
        'interface_pairs': to_int(row.get('interface_n_pairs','')),
        'deamidation_sites':   clean(row.get('deamidation_sites','')),
        'isomerization_sites': clean(row.get('isomerization_sites','')),
        'agg_motifs':    clean(row.get('agg_motifs','')),
        'cmc_flags':     clean(row.get('cmc_flags','')),
        'moa_class':     clean(row.get('moa_class','')),
        'format_type':   clean(row.get('format_type','')),
        'half_life':     to_float(row.get('half_life_days','')),
        'surf_risk':     clean(row.get('surf_risk', row.get('surf_mode',''))),
        # ── NEW: verification fields ──
        'verify_status': vstatus,
        'verify_note':   vnote,
    }
    records.append(rec)

# ── Stats ──────────────────────────────────────────────────────────────────────
total_verified = stats.get('VERIFIED',0) + stats.get('VERIFIED_WITH_CONTEXT',0) + stats.get('SOURCE_LIVE',0)
print(f"\nVerification status distribution ({len(records)} records):")
for s, n in sorted(stats.items(), key=lambda x:-x[1]):
    pct = 100*n//len(records)
    bar = '█'*(pct//5)
    print(f"  {s:28s}: {n:3d} ({pct:2d}%) {bar}")
print(f"\n  Confident (VERIFIED+LIVE): {total_verified}/{len(records)} ({100*total_verified//len(records)}%)")
print(f"  Needs review (UNCERTAIN): {stats.get('UNCERTAIN',0)}")
print(f"  No source:               {stats.get('NO_SOURCE',0)}")

# ── Write JSON ─────────────────────────────────────────────────────────────────
out = json.dumps(records, ensure_ascii=False, indent=2)
for p in [OUT_JSON_1, OUT_JSON_2, OUT_JSON_3]:
    with open(p, 'w', encoding='utf-8') as f: f.write(out)
    print(f"Written → {p}")

print("\nCORRECTIONS applied:")
for name, c in CORRECTIONS.items():
    print(f"  {name:20s} [{c['verify_status']}] {c['verify_note'][:80]}")
