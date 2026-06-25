"""
Full AI-contamination audit of all 138 ADA records.
Checks:
  1. Explicit AI phrases (claude, gpt, chatgpt, llm, language model, etc.)
  2. Generic/templated boilerplate evidence chains (AI-generated summaries)
  3. Evidence chain says "verified" but source URL is generic/landing page
  4. Stored value is round number (5%, 10%, 15%, 20%...) with NO PMID and weak URL
  5. Cross-check UNCERTAIN records from pass1 against source quality
"""
import csv, re, json

MASTER_CSV   = r'data\ada_master_136_curated.csv'
REPORT_CSV   = r'data\ada_evidence_verification_report.csv'

rows  = list(csv.DictReader(open(MASTER_CSV,  encoding='utf-8')))
rep1  = {r['antibody_name']: r for r in csv.DictReader(open(REPORT_CSV, encoding='utf-8'))}

# ── Pattern sets ──────────────────────────────────────────────────────────────

# 1. Explicit AI tool mentions
AI_EXPLICIT = re.compile(
    r'\bclaude\b|\bchatgpt\b|\bgpt[\-\s]?[3-9]\b|\bllm\b|\blarge\s+language\b|'
    r'\blanguage\s+model\b|\bai\s+response\b|\bai[\-\s]generated\b|'
    r'\bgenerated\s+by\s+ai\b|\bfrom\s+ai\b|\bper\s+ai\b|'
    r'\bsynthesized\s+from\b|\baccording\s+to\s+ai\b',
    re.IGNORECASE
)

# 2. Boilerplate template phrases unique to AI-generated chains
AI_TEMPLATE = re.compile(
    r'monoclonal antibody used in the treatment of various medical conditions|'
    r'the development of anti-drug antibodies.*is an important factor that can impact|'
    r'this data represents the proportion of patients treated with.*who develop detectable|'
    r'the assessment of ADA formation typically involves validated immunoassay|'
    r'in clinical trials.*the incidence of anti-drug antibodies was found to be|'
    r'these findings highlight the importance of monitoring',
    re.IGNORECASE
)

# 3. Vague/generic source URLs (not FDA, not PMC, not NEJM, not real journal)
WEAK_URL_PATTERNS = re.compile(
    r'drugs\.com|rxlist\.com|webmd\.com|healthline\.com|wikipedia|'
    r'generic\s+drug|prescribing\s+information$|no\s+url|none|^$',
    re.IGNORECASE
)

# 4. Round number values that are suspicious without strong evidence
ROUND_NUMBERS = {5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 50.0}

def to_float(v):
    try: return round(float(v), 1)
    except: return None

# ── Scan ──────────────────────────────────────────────────────────────────────
results = []

for row in rows:
    name    = row.get('antibody_name', '')
    chain   = row.get('ada_evidence_chain_excerpt', '')
    url     = row.get('ada_source_url_primary', '')
    pmids   = row.get('ada_source_pmids', '').strip()
    tier    = row.get('evidence_tier', '')
    val_str = row.get('ada_value_display', '')
    ada_pct = to_float(row.get('ada_first_pct', ''))
    
    flags = []
    
    # Check 1: explicit AI mention
    if AI_EXPLICIT.search(chain):
        flags.append(f"EXPLICIT_AI: {AI_EXPLICIT.search(chain).group()}")
    
    # Check 2: boilerplate template
    if AI_TEMPLATE.search(chain):
        flags.append("BOILERPLATE_TEMPLATE")
    
    # Check 3: weak source URL with no PMID
    has_pmid = bool(pmids and pmids not in ('', 'nan', 'None'))
    has_strong_url = bool(url and any(d in url.lower() for d in [
        'ncbi', 'pubmed', 'pmc.ncbi', 'fda.gov', 'accessdata', 'dailymed',
        'ema.europa', 'nejm.org', 'lancet.com', 'bmj.com', 'annrheumdis',
        'jci.org', 'nature.com', 'science.org', 'cell.com', 'jama',
        'onlinelibrary.wiley', 'springer', 'elsevier', 'jitc', 'jto',
        'annalsofoncology', 'acr', 'rheumatology', 'bloodjournal'
    ]))
    if not has_pmid and not has_strong_url and tier in ('B', 'C'):
        flags.append(f"NO_PMID_WEAK_URL: url={url[:60]}")
    
    # Check 4: suspicious round number + no PMID + boilerplate
    if ada_pct in ROUND_NUMBERS and not has_pmid and 'BOILERPLATE_TEMPLATE' in ' '.join(flags):
        flags.append(f"ROUND_NUMBER_NO_PMID: {ada_pct}%")
    
    # Check 5: Evidence chain is very short (< 200 chars) — likely placeholder
    chain_clean = chain.strip()
    if len(chain_clean) < 200 and chain_clean:
        flags.append(f"SHORT_CHAIN: {len(chain_clean)} chars")
    
    # Check 6: source URL is a generic drug page, not a study
    if url and WEAK_URL_PATTERNS.search(url):
        flags.append(f"GENERIC_URL: {url[:60]}")
    
    # Pass 1 status
    p1_status = rep1.get(name, {}).get('verify_status', 'N/A')
    
    if flags:
        results.append({
            'name': name, 'tier': tier, 'ada_pct': ada_pct,
            'val_str': val_str, 'has_pmid': has_pmid,
            'has_strong_url': has_strong_url, 'url': url[:70],
            'pmids': pmids[:30], 'p1_status': p1_status,
            'flags': flags,
            'chain_snippet': chain[:250],
        })

# ── Report ────────────────────────────────────────────────────────────────────
print(f"{'='*70}")
print(f"FULL CONTAMINATION AUDIT — {len(rows)} records")
print(f"{'='*70}")
print(f"Records with flags: {len(results)}\n")

# Group by severity
explicit_ai  = [r for r in results if any('EXPLICIT_AI' in f for f in r['flags'])]
boilerplate  = [r for r in results if any('BOILERPLATE' in f for f in r['flags'])]
no_pmid_weak = [r for r in results if any('NO_PMID_WEAK_URL' in f for f in r['flags'])]
round_nopmid = [r for r in results if any('ROUND_NUMBER' in f for f in r['flags'])]
generic_url  = [r for r in results if any('GENERIC_URL' in f for f in r['flags'])]

print(f"SEVERITY BREAKDOWN:")
print(f"  ⛔ Explicit AI mention:          {len(explicit_ai)}")
print(f"  🟠 Boilerplate template:         {len(boilerplate)}")
print(f"  🟡 No PMID + weak URL:           {len(no_pmid_weak)}")
print(f"  🟡 Round number + no PMID:       {len(round_nopmid)}")
print(f"  🔵 Generic URL:                  {len(generic_url)}")

if explicit_ai:
    print(f"\n{'─'*70}")
    print(f"⛔ EXPLICIT AI MENTIONS ({len(explicit_ai)}):")
    for r in explicit_ai:
        print(f"  {r['name']:30s} val={r['val_str'][:20]:20s} {r['flags']}")

print(f"\n{'─'*70}")
print(f"🟠 BOILERPLATE TEMPLATE — likely AI-drafted evidence chains ({len(boilerplate)}):")
print("  (These may still have correct data if the underlying source is real)")
for r in boilerplate:
    pmid_tag = f"PMID:{r['pmids'][:15]}" if r['has_pmid'] else "no-PMID"
    url_tag  = "strong-URL" if r['has_strong_url'] else "weak-URL"
    risk = "HIGH" if (not r['has_pmid'] and not r['has_strong_url']) else "LOW"
    p1   = r['p1_status']
    print(f"  [{risk}] {r['name']:30s} {r['val_str'][:15]:15s} {pmid_tag:20s} {url_tag:12s} P1={p1}")

print(f"\n{'─'*70}")
print(f"🟡 NO PMID + WEAK SOURCE URL ({len(no_pmid_weak)}):")
for r in no_pmid_weak:
    print(f"  {r['name']:30s} val={r['val_str'][:20]:20s} url={r['url']}")

# Summary: what truly needs action (HIGH risk boilerplate = AI + no strong source)
high_risk = [r for r in boilerplate 
             if not r['has_pmid'] and not r['has_strong_url'] 
             and r['p1_status'] not in ('VERIFIED',)]
print(f"\n{'='*70}")
print(f"ACTION REQUIRED — HIGH RISK (boilerplate + no PMID + no strong URL): {len(high_risk)}")
print(f"{'='*70}")
for r in high_risk:
    print(f"  {r['name']:30s} stored={r['val_str'][:20]:20s} Tier={r['tier']} URL={r['url']}")
    print(f"    flags: {r['flags']}")
    print(f"    chain: {r['chain_snippet'][:180]}")
    print()

# Low risk boilerplate (has PMID or strong URL — AI summary of real source)
low_risk_bp = [r for r in boilerplate if r not in high_risk]
print(f"LOW RISK (boilerplate text but has PMID/strong URL — data likely OK): {len(low_risk_bp)}")
print("  These just need the evidence chain text replaced with real excerpts,")
print("  but the stored ADA value is probably correct.")
