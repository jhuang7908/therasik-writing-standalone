"""
Comprehensive authenticity audit for 131-panel clinical ADA data.
Checks evidence tier, citation URLs, evidence chain text, and source type.
"""
import pandas as pd
import json

master = pd.read_csv('data/immunogenicity_panel_136_master.csv')

# Focus on the 131 that have numeric ADA
panel = master[master['ada_first_pct'].notna].copy
n = len(panel)
print("=== CLINICAL ADA AUTHENTICITY AUDIT (n={}) ===\n".format(n))

# 1. Evidence tier breakdown
print("[1] Evidence Tier Distribution")
tier_counts = panel['evidence_tier'].value_counts
for tier, cnt in tier_counts.items:
    pct = cnt / n * 100
    if tier == 'A':
        desc = "PMID/FDA label/ClinicalTrials.gov — "
    elif tier == 'B':
        desc = "/ — "
    elif tier == 'C':
        desc = " — "
    else:
        desc = ""
    print("  Tier {} | {:3}  ({:.0f}%) | {}".format(tier, cnt, pct, desc))

# 2. Citation URL coverage
print("\n[2] Citation URL Coverage")
has_url = panel['citation_urls'].notna & (panel['citation_urls'].str.strip != '')
print("  Has citation URL: {}/{} ({:.0f}%)".format(has_url.sum, n, has_url.sum/n*100))

# 3. Load full evidence chain data
with open('data/ADA_reliable_package/clinical_db/clinical_ada_db_index.json', 'r', encoding='utf-8') as f:
    ada_index = json.load(f)['index']
with open('data/ADA_reliable_package/clinical_db/clinical_ada_db_data.json', 'r', encoding='utf-8') as f:
    ada_data = json.load(f)['records']

ada_idx_map  = {item['antibody_name'].lower: item for item in ada_index}
chain_present = 0
chain_lengths = []
for _, row in panel.iterrows:
    name = row['antibody_name'].lower
    if name in ada_idx_map:
        key = ada_idx_map[name].get('data_record_key', '')
        rec = ada_data.get(key, {}).get('primary_record', {})
        chain = rec.get('evidence_chain', '')
        if chain and len(chain) > 20:
            chain_present += 1
            chain_lengths.append(len(chain))

print("\n[3] Full Evidence Chain Coverage")
print("  Has evidence chain text: {}/{} ({:.0f}%)".format(chain_present, n, chain_present/n*100))
if chain_lengths:
    print("  Chain length: mean={:.0f} chars, min={}, max={} chars".format(
        sum(chain_lengths)/len(chain_lengths), min(chain_lengths), max(chain_lengths)))

# 4. Source type breakdown
print("\n[4] Source Type Breakdown")
src_counts = panel['evidence_source'].value_counts
for src, cnt in src_counts.items:
    print("  {:40} {:3} ".format(str(src), cnt))

# 5. By tier: list all Tier C (least reliable)
tier_c = panel[panel['evidence_tier'] == 'C']
if len(tier_c) > 0:
    print("\n[5] Tier C Antibodies ( — )")
    for _, r in tier_c.iterrows:
        print("  {} | ADA={} | src={}".format(
            r['antibody_name'], r['ada_value_display'], r['evidence_source']))

# 6. Detailed sample: Tier A examples with full citation
print("\n[6] Tier A Sample Evidence (3 examples)")
tier_a_sample = panel[panel['evidence_tier'] == 'A'].head(3)
for _, row in tier_a_sample.iterrows:
    name = row['antibody_name'].lower
    idx_rec = ada_idx_map.get(name, {})
    key = idx_rec.get('data_record_key', '')
    rec = ada_data.get(key, {}).get('primary_record', {})
    chain = rec.get('evidence_chain', '')[:300]
    print("\n  --- {} ---".format(row['antibody_name']))
    print("  ADA: {}".format(row['ada_value_display']))
    print("  URLs: {}".format(row['citation_urls']))
    print("  Evidence: {}...".format(chain.replace('\n', ' ')))

# 7. Detailed sample: Tier B examples
print("\n[7] Tier B Sample Evidence (3 examples)")
tier_b_sample = panel[panel['evidence_tier'] == 'B'].head(3)
for _, row in tier_b_sample.iterrows:
    name = row['antibody_name'].lower
    idx_rec = ada_idx_map.get(name, {})
    key = idx_rec.get('data_record_key', '')
    rec = ada_data.get(key, {}).get('primary_record', {})
    chain = rec.get('evidence_chain', '')[:300]
    print("\n  --- {} ---".format(row['antibody_name']))
    print("  ADA: {}".format(row['ada_value_display']))
    print("  URLs: {}".format(row['citation_urls']))
    print("  Evidence: {}...".format(chain.replace('\n', ' ')))

# 8. Full roster by tier
print("\n[8] Full Roster (sorted by Tier then ADA%)")
for tier in ['A', 'B', 'C']:
    sub = panel[panel['evidence_tier'] == tier].sort_values('ada_first_pct')
    print("\n  === Tier {} ({} ) ===".format(tier, len(sub)))
    for _, r in sub.iterrows:
        urls = str(r['citation_urls'])[:60] if pd.notna(r['citation_urls']) else 'no URL'
        print("  {:25} ADA={:5.1f}%  {}".format(
            r['antibody_name'], r['ada_first_pct'], urls))
