"""
Pass 2: Fill remaining approval_year and immunosuppressant_context.
Handles '0', '0.0', '' as all = missing.
"""
import csv, subprocess, sys, shutil, math

MASTER    = r'data\ada_master_136_curated.csv'
KB_MASTER = r'data\immunogenicity_knowledge_base\master\ada_master_136_curated.csv'

def is_empty(v):
    if v is None: return True
    s = str(v).strip()
    if s in ('', 'nan', 'None', 'none', 'NaN', '0', '0.0'): return True
    try:
        return math.isnan(float(s)) or float(s) == 0
    except:
        return False

# Comprehensive approval year lookup (FDA first approval, or EMA if no FDA)
APPROVAL_YEARS = {
    # Already approved drugs that were showing 0.0
    "Adalimumab":       2002, "Alemtuzumab":    2001, "Anifrolumab":    2021,
    "Astegolimab":      None,  # Not yet approved (Phase 3)
    "Atezolizumab":     2016, "Bamlanivimab":   2020,
    "Belimumab":        2011, "Bezlotoxumab":   2016, "Bimagrumab":     None,
    "Bimekizumab":      2023, "Brodalumab":     2017, "Brolucizumab":   2020,
    "Burosumab":        2018, "Camrelizumab":   None,  # China NMPA 2019, not FDA
    "Canakinumab":      2009, "Cemiplimab":     2018, "Cilgavimab":     2021,
    "Clazakizumab":     None,  # Not approved
    "Clesrovimab":      2024, "Concizumab":     None,
    "Crovalimab":       2023, "Daclizumab":     2016,  # withdrawn 2018
    "Daratumumab":      2015, "Dazukibart":     None,
    "Denosumab":        2010, "Dostarlimab":    2021, "Dupilumab":      2017,
    "Durvalumab":       2017, "Ebronucimab":    None, "Efalizumab":     2003,  # withdrawn 2009
    "Elotuzumab":       2015, "Elranatamab":    2023, "Emapalumab":     2018,
    "Emicizumab":       2017, "Enuzovimab":     None,  # Not FDA approved
    "Epcoritamab":      2023, "Erenumab":       2018, "Evinacumab":     2021,
    "Evolocumab":       2015, "Faricimab":      2022, "Fremanezumab":   2018,
    "Fulranumab":       None,  # Withdrawn from development
    "Galcanezumab":     2018, "Garadacimab":    2024, "Guselkumab":     2017,
    "Itolizumab":       None,  # Not FDA approved
    "Ixekizumab":       2016, "Lanadelumab":    2018, "Lecanemab":      2023,
    "Mepolizumab":      2015, "Mogamulizumab":  2018, "Natalizumab":    2004,
    "Naxitamab":        2020, "Nipocalimab":    2024, "Nirsevimab":     2023,
    "Nivolumab":        2014, "Obinutuzumab":   2013, "Ocrelizumab":    2017,
    "Ofatumumab":       2009, "Olokizumab":     None,  # Russia/China, not FDA
    "Omalizumab":       2003, "Ozoralizumab":   2022,  # Japan
    "Palivizumab":      1998, "Panitumumab":    2006, "Pembrolizumab":  2014,
    "Pertuzumab":       2012, "Ramucirumab":    2014, "Ravulizumab":    2018,
    "Relatlimab":       2022, "Reslizumab":     2016, "Retifanlimab":   2023,
    "Risankizumab":     2019, "Romosozumab":    2019, "Sacituzumab":    2020,
    "Satralizumab":     2020, "Secukinumab":    2015, "Tarlatamab":     2024,
    "Teprotumumab":     2020, "Tezepelumab":    2021, "Tildrakizumab":  2018,
    "Tisotumab":        2021, "Tixagevimab":    2021, "Toripalimab":    None,  # FDA 2023? China 2018
    "Tralokinumab":     2021, "Trastuzumab":    1998, "Tremelimumab":   2022,
    "Ustekinumab":      2009, "Vedolizumab":    2014, "Zenocutuzumab":  2024,
    "Axatilimab":       2024, "Crizanlizumab":  2019, "Elotuzumab":     2015,
    "Aducanumab":       2021, "Atoltivimab":    2023,
    "Ebronucimab":      None, "Etrolizumab":    None,  # Phase 3 terminated
    "Eptinezumab":      2020, "Dazukibart":     None, "Clazakizumab":   None,
    "Bimagrumab":       None, "Concizumab":     None,
}

# Comprehensive immunosuppressant_context
CONTEXT = {
    "Adalimumab":     "RA: MTX co-medication high (~50-80%); IBD/psoriasis: often monotherapy",
    "Anifrolumab":    "SLE: background HCQ/corticosteroids/azathioprine or MMF",
    "Astegolimab":    "asthma: background ICS/OCS; no IST",
    "Atezolizumab":   "oncology PD-L1: chemo combination common (carboplatin/nab-paclitaxel/bevacizumab)",
    "Bezlotoxumab":   "C. diff: concurrent antibiotics required",
    "Bimekizumab":    "psoriasis/PsA/AS/HS: no mandatory IST; MTX optional in PsA",
    "Brodalumab":     "psoriasis: no mandatory IST",
    "Brolucizumab":   "intravitreal AMD: no systemic IST",
    "Burosumab":      "XLH: no IST; phosphate supplementation background",
    "Camrelizumab":   "oncology PD-1 (China): VEGFR combo common (apatinib); chemo combinations",
    "Canakinumab":    "CAPS/SJIA/FMF/TRAPS: no IST; gout-NSAIDs",
    "Cemiplimab":     "oncology PD-1 (CSCC/BCC/NSCLC): monotherapy or platinum-chemo combination",
    "Cilgavimab":     "COVID-19 PrEP (Evusheld): no IST",
    "Clazakizumab":   "RA: background csDMARDs or MTX",
    "Daclizumab":     "MS: no mandatory IST; withdrawn 2018",
    "Denosumab":      "osteoporosis/bone met: no IST; calcium/vitamin D supplementation",
    "Dostarlimab":    "EC/dMMR: carboplatin/paclitaxel combination or monotherapy",
    "Durvalumab":     "NSCLC/BTC/SCLC: chemo consolidation or combination common",
    "Efalizumab":     "psoriasis: no IST; withdrawn 2009",
    "Erenumab":       "migraine: no IST",
    "Evolocumab":     "hypercholesterolemia: background statins common; no IST",
    "Faricimab":      "AMD/DME intravitreal: no systemic IST",
    "Fremanezumab":   "migraine: no IST",
    "Galcanezumab":   "migraine: no IST",
    "Guselkumab":     "psoriasis/PsA: no IST; MTX optional in PsA",
    "Ixekizumab":     "psoriasis/AS/PsA: no mandatory IST; MTX optional in PsA",
    "Lanadelumab":    "HAE prophylaxis: no IST",
    "Mepolizumab":    "severe eosinophilic asthma: background ICS; OCS tapering",
    "Natalizumab":    "MS/Crohn's: no IST (JCV risk); background 5-ASA in Crohn's",
    "Obinutuzumab":   "CLL/FL: chlorambucil or bendamustine or CHOP combination",
    "Ofatumumab":     "MS: no mandatory IST; SC self-injection monotherapy",
    "Olokizumab":     "RA: background MTX in most trials; some monotherapy",
    "Omalizumab":     "allergic asthma/CSU/nasal polyps: background ICS; no IST",
    "Ozoralizumab":   "RA: background MTX (Japan approval)",
    "Palivizumab":    "RSV prophylaxis (neonates/infants): no IST",
    "Pembrolizumab":  "oncology PD-1: platinum-chemo, VEGF, or monotherapy depending on indication",
    "Reslizumab":     "severe asthma: background ICS; no IST",
    "Romosozumab":    "osteoporosis: no IST; follow-on antiresorptive therapy",
    "Tildrakizumab":  "psoriasis: no IST",
    "Tisotumab":      "cervical cancer ADC: no mandatory IST; standard antiemetics",
    "Toripalimab":    "oncology PD-1 (China/FDA 2023): chemo combination",
    "Tralokinumab":   "atopic dermatitis: no IST; background TCS",
    "Trastuzumab":    "HER2+ BC: ACT-H/TCH chemo backbone; no IST",
    "Ustekinumab":    "psoriasis/PsA/IBD: no mandatory IST; MTX optional in PsA",
    "Vedolizumab":    "UC/CD: background steroids/aminosalicylates; no mandatory IST",
}

# Load
with open(MASTER, encoding='utf-8') as f:
    reader     = csv.DictReader(f)
    fieldnames = list(reader.fieldnames)
    all_rows   = list(reader)
row_map = {r['antibody_name']: r for r in all_rows}

yr_filled = 0
ctx_filled = 0

for drug, yr in APPROVAL_YEARS.items():
    row = row_map.get(drug)
    if row and is_empty(row.get('approval_year','')):
        row['approval_year'] = str(yr) if yr else ''
        yr_filled += 1

for drug, ctx in CONTEXT.items():
    row = row_map.get(drug)
    if row and is_empty(row.get('immunosuppressant_context','')):
        row['immunosuppressant_context'] = ctx
        ctx_filled += 1

print(f"Filled approval_year: {yr_filled}")
print(f"Filled immuno_context: {ctx_filled}")

# Status check
still_no_yr  = [r['antibody_name'] for r in all_rows if is_empty(r.get('approval_year',''))]
still_no_ctx = [r['antibody_name'] for r in all_rows if is_empty(r.get('immunosuppressant_context',''))]
pct_yr  = 100*(len(all_rows)-len(still_no_yr))/len(all_rows)
pct_ctx = 100*(len(all_rows)-len(still_no_ctx))/len(all_rows)
print(f"approval_year coverage: {len(all_rows)-len(still_no_yr)}/138 ({pct_yr:.0f}%)")
print(f"immuno_context coverage: {len(all_rows)-len(still_no_ctx)}/138 ({pct_ctx:.0f}%)")
if still_no_yr:
    print(f"  Still missing yr: {still_no_yr}")
if still_no_ctx:
    print(f"  Still missing ctx: {still_no_ctx}")

# Write
with open(MASTER, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(all_rows)
shutil.copy(MASTER, KB_MASTER)
print(f"\nWritten {len(all_rows)} rows.")

# Rebuild
print("Rebuilding JSON...")
subprocess.run([sys.executable, 'scripts/_regen_json_only.py'], check=False)
shutil.copy('docs/ada_db_data.json', 'insynbio-web-source/ada_db_data.json')
shutil.copy('docs/ada_db_data.json', 'therasik-web-source/ada_db_data.json')
print("Done.")
