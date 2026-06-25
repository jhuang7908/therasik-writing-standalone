"""Pass 3: fill remaining known drugs."""
import csv, subprocess, sys, shutil, math

MASTER    = r'data\ada_master_136_curated.csv'
KB_MASTER = r'data\immunogenicity_knowledge_base\master\ada_master_136_curated.csv'

def is_empty(v):
    if v is None: return True
    s = str(v).strip()
    if s in ('', 'nan', 'None', 'none', 'NaN', '0', '0.0'): return True
    try: return math.isnan(float(s)) or float(s) == 0
    except: return False

YEARS = {
    "Eculizumab":      2007, "Gemtuzumab":     2017,  # re-approved
    "Inebilizumab":    2020, "Lebrikizumab":   2023, "Mirikizumab":    2023,
    "Nemolizumab":     2024, "Polatuzumab":    2019, "Rozanolixizumab":2024,
    "Spesolimab":      2022, "Sutimlimab":     2022, "Tafasitamab":    2020,
    "Ibalizumab":      2018, "Leronlimab":     None,  # Not approved (HIV, failed)
    "Donanemab":       2024, "Depemokimab":    2024,
    "Olaratumab":      2016,  # withdrawn 2019
    "Pemivibart":      2024,  # COVID-19 mAb
    "Regdanvimab":     2021,  # South Korea; not FDA
    "Sintilimab":      None,  # China NMPA 2018; not FDA
    "Tafolecimab":     None,  # China approval 2022
    "Belantamab":      2020,  # conditionally approved; withdrawn 2022
    "Budigalimab":     None,  # Phase 3
    "Domvanalimab":    None,  # Phase 3
    "Elezanumab":      None,  # Phase 3
    "Etaracizumab":    None,  # Discontinued
    "Exidavnemab":     None,  # Phase 2
    "Favezelimab":     None,  # Phase 3
    "Levilimab":       None,  # Russia 2020 (Ilsira); not FDA
    "Nimotuzumab":     None,  # Cuba/other markets
    "Penpulimab":      None,  # China NMPA 2021
    "Recaticimab":     None,  # China NMPA 2023
    "Tagitanlimab":    None,  # Phase 3
    "Timigutuzumab":   None,  # Phase 3
    "Vunakizumab":     None,  # Phase 2
}

CONTEXT = {
    "Teprotumumab":    "thyroid eye disease (TED): no IST; IV infusion q3w monotherapy",
    "Tixagevimab":     "COVID-19 PrEP (Evusheld with cilgavimab): no IST",
    "Alemtuzumab":     "MS: strong B/T cell depletion; no concomitant IST; lymphopenia monitoring",
    "Donanemab":       "Alzheimer's: no IST; ARIA monitoring required",
    "Ranibizumab":     "AMD/DME intravitreal: no systemic IST",
    "Risankizumab":    "psoriasis/PsA/Crohn's: no mandatory IST; some csDMARD in PsA",
    "Enuzovimab":      "COVID-19 treatment: no IST; single infusion",
    "Evinacumab":      "HoFH: no IST; background lipid-lowering therapy",
    "Fulranumab":      "pain: no IST; withdrew from development",
    "Garadacimab":     "HAE prophylaxis: no IST",
    "Regdanvimab":     "COVID-19 (Korea): no IST",
    "Relatlimab":      "NSCLC/MEL: nivolumab combination; no IST; standard supportive care",
    "Tafolecimab":     "hyperlipidemia (China PCSK9i): no IST; background statins",
    "Budigalimab":     "oncology PD-1 (investigational): chemo or anti-TGF combination",
    "Elezanumab":      "spinal cord injury (investigational): no IST",
    "Exidavnemab":     "Parkinson's (investigational): no IST",
    "Favezelimab":     "oncology LAG-3/PD-1 (investigational): pembrolizumab combination",
    "Lebrikizumb":     "atopic dermatitis: no IST; background TCS allowed",
    "Lebrikizumab":    "atopic dermatitis: no IST; background TCS allowed",
    "Nemolizumab":     "prurigo nodularis/AD: no IST; background TCS allowed",
    "Recaticimab":     "HFpEF/hyperlipidemia (China): no IST; statin background",
    "Spesolimab":      "generalized pustular psoriasis (GPP): no IST; acute flare treatment",
    "Sutimlimab":      "cold agglutinin disease: no IST; rare hematology",
    "Gemtuzumab":      "AML (ADC): standard cytarabine/daunorubicin induction combination",
    "Polatuzumab":     "DLBCL: BR (bendamustine/rituximab) or R-CHOP-like combination",
    "Inebilizumab":    "NMOSD: B-cell depleting; no concomitant IST typically",
    "Lebrikizumab":    "atopic dermatitis: no IST; background TCS allowed",
    "Mirikizumab":     "UC/psoriasis: no mandatory IST; background 5-ASA in UC",
    "Rozanolixizumab": "gMG/primary ITP: no IST; background prednisone taper",
    "Tafasitamab":     "DLBCL: lenalidomide combination",
    "Donanemab":       "Alzheimer's: no IST; ARIA monitoring",
}

with open(MASTER, encoding='utf-8') as f:
    reader     = csv.DictReader(f)
    fieldnames = list(reader.fieldnames)
    all_rows   = list(reader)
row_map = {r['antibody_name']: r for r in all_rows}

yr_filled = ctx_filled = 0
for drug, yr in YEARS.items():
    row = row_map.get(drug)
    if row and is_empty(row.get('approval_year','')):
        row['approval_year'] = str(yr) if yr else ''
        yr_filled += 1
for drug, ctx in CONTEXT.items():
    row = row_map.get(drug)
    if row and is_empty(row.get('immunosuppressant_context','')):
        row['immunosuppressant_context'] = ctx
        ctx_filled += 1

still_no_yr  = [r['antibody_name'] for r in all_rows if is_empty(r.get('approval_year',''))]
still_no_ctx = [r['antibody_name'] for r in all_rows if is_empty(r.get('immunosuppressant_context',''))]
pct_yr  = 100*(len(all_rows)-len(still_no_yr))/len(all_rows)
pct_ctx = 100*(len(all_rows)-len(still_no_ctx))/len(all_rows)
print(f"approval_year  {len(all_rows)-len(still_no_yr)}/138 ({pct_yr:.0f}%)  +{yr_filled}")
print(f"immuno_context {len(all_rows)-len(still_no_ctx)}/138 ({pct_ctx:.0f}%)  +{ctx_filled}")
if still_no_yr:
    print(f"Still missing yr:  {still_no_yr}")
if still_no_ctx:
    print(f"Still missing ctx: {still_no_ctx}")

with open(MASTER, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(all_rows)
shutil.copy(MASTER, KB_MASTER)

print("Rebuilding JSON...")
subprocess.run([sys.executable, 'scripts/_regen_json_only.py'], check=False)
shutil.copy('docs/ada_db_data.json', 'insynbio-web-source/ada_db_data.json')
shutil.copy('docs/ada_db_data.json', 'therasik-web-source/ada_db_data.json')
print("Done.")
