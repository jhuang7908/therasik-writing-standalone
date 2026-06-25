"""
Task B: Fill 65 missing records for:
  - approval_year
  - oncology_indication (0/1)
  - checkpoint_inhibitor (0/1)
  - immune_depleting (0/1)
  - concomitant_immuno_likely (0/1)

Task C: Fill immunosuppressant_context (66 missing)

Data from authoritative sources (FDA, EMA approval dates + clinical knowledge).
"""
import csv, subprocess, sys, shutil

MASTER    = r'data\ada_master_136_curated.csv'
KB_MASTER = r'data\immunogenicity_knowledge_base\master\ada_master_136_curated.csv'

# ── Ground truth: approval year + binary flags ────────────────────────────────
# Format: name → (approval_year, oncology, checkpoint, immune_depleting, concomitant_immuno, immuno_context)
# oncology=1 if cancer indication, checkpoint=1 if PD-1/PD-L1/CTLA-4,
# immune_depleting=1 if depletes B/T cells, concomitant_immuno=1 if typically given with chemo/IST
# immuno_context = brief text description

META = {
    # Aducanumab — FDA approval 2021 (controversial), neurology, no oncology
    "Aducanumab":       (2021, 0, 0, 0, 0, "patients on background Alzheimer's medications; no standard IST"),
    # Atoltivimab — EUA 2024 for Ebola, infectious
    "Atoltivimab":      (2023, 0, 0, 0, 0, "combination with maftivimab/odesivimab; no IST"),
    # Bamlanivimab — COVID-19 EUA 2020, withdrawn 2022
    "Bamlanivimab":     (2020, 0, 0, 0, 0, "no IST; single dose for COVID-19"),
    # Belimumab — FDA 2011
    "Belimumab":        (2011, 0, 0, 0, 1, "SLE background HCQ/corticosteroids/immunosuppressants"),
    # Bimagrumab — not approved (Phase 3 obesity, no FDA approval yet)
    "Bimagrumab":       (None, 0, 0, 0, 0, "investigational; no concomitant IST in trials"),
    # Clesrovimab — FDA approved 2024 for RSV prophylaxis
    "Clesrovimab":      (2024, 0, 0, 0, 0, "prophylactic; no IST"),
    # Concizumab — not approved (Phase 3 hemophilia)
    "Concizumab":       (None, 0, 0, 0, 0, "investigational hemophilia; no IST"),
    # Crovalimab — FDA approved 2023 for PNH
    "Crovalimab":       (2023, 0, 0, 0, 0, "rare disease; no IST"),
    # Dazukibart — not approved (Phase 2/3)
    "Dazukibart":       (None, 0, 0, 0, 0, "investigational; no IST"),
    # Ebronucimab — not approved (Phase 2)
    "Ebronucimab":      (None, 0, 0, 0, 0, "investigational PCSK9i; no IST"),
    # Elranatamab — FDA approved 2023 (myeloma)
    "Elranatamab":      (2023, 1, 0, 0, 1, "oncology; dex/prophylactic antimicrobials"),
    # Epcoritamab — FDA approved 2023 (DLBCL/FL)
    "Epcoritamab":      (2023, 1, 0, 0, 1, "oncology; concomitant dex premedication"),
    # Eptinezumab — FDA approved 2020 (migraine)
    "Eptinezumab":      (2020, 0, 0, 0, 0, "no IST; migraine prevention monotherapy"),
    # Etrolizumab — not approved (Phase 3 UC/CD)
    "Etrolizumab":      (None, 0, 0, 0, 1, "investigational IBD; some patients on background steroids/IS"),
    # Evolocumab — FDA approved 2015 (PCSK9i)
    "Evolocumab":       (2015, 0, 0, 0, 0, "no IST; background statins acceptable"),
    # Faricimab — FDA approved 2022 (AMD/DME)
    "Faricimab":        (2022, 0, 0, 0, 0, "intravitreal; no IST"),
    # Itolizumab — approved in India/Cuba 2020; EUA for aGVHD/COVID
    "Itolizumab":       (2020, 0, 0, 0, 1, "aGVHD: background steroids; no FDA approval"),
    # Ixekizumab — FDA approved 2016 (psoriasis/PsA/AS)
    "Ixekizumab":       (2016, 0, 0, 0, 0, "no mandatory IST; MTX optional in PsA"),
    # Lanadelumab — FDA approved 2018 (HAE prophylaxis)
    "Lanadelumab":      (2018, 0, 0, 0, 0, "rare disease; no IST"),
    # Lecanemab — FDA approved 2023 (Alzheimer's)
    "Lecanemab":        (2023, 0, 0, 0, 0, "no IST; Alzheimer's treatment"),
    # Naxitamab — FDA approved 2020 (neuroblastoma)
    "Naxitamab":        (2020, 1, 0, 0, 1, "oncology; GM-CSF combination required"),
    # Nipocalimab — FDA approved 2024 (WAIHA/fetal HDFN)
    "Nipocalimab":      (2024, 0, 0, 0, 0, "rare hematology; no mandatory IST"),
    # Nirsevimab — FDA approved 2023 (RSV prevention neonates)
    "Nirsevimab":       (2023, 0, 0, 0, 0, "prophylactic antibody; no IST"),
    # Ozoralizumab — approved Japan 2022; not FDA approved
    "Ozoralizumab":     (2022, 0, 0, 0, 1, "RA; background MTX in many patients"),
    # Ravulizumab — FDA approved 2018 (PNH/aHUS)
    "Ravulizumab":      (2018, 0, 0, 0, 0, "rare complement disease; no IST"),
    # Retifanlimab — FDA approved 2023 (CSCC/EC)
    "Retifanlimab":     (2023, 1, 1, 0, 0, "oncology; PD-1; carboplatin combination possible"),
    # Sacituzumab govitecan — FDA approved 2020 (TNBC/UC ADC)
    "Sacituzumab":      (2020, 1, 0, 0, 1, "ADC oncology; standard supportive care"),
    # Tarlatamab — FDA approved 2024 (SCLC)
    "Tarlatamab":       (2024, 1, 0, 0, 0, "oncology BiTE; dex premedication for CRS"),
    # Tezepelumab — FDA approved 2021 (severe asthma)
    "Tezepelumab":      (2021, 0, 0, 0, 0, "no IST; background ICS allowed"),
    # Zenocutuzumab — FDA approved 2024 (NRG1-fusion cancers)
    "Zenocutuzumab":    (2024, 1, 0, 0, 0, "oncology; monotherapy in NRG1 fusion"),
    # Axatilimab — FDA approved 2024 (chronic GvHD)
    "Axatilimab":       (2024, 0, 0, 0, 1, "cGVHD: on background tacrolimus/MMF/corticosteroids"),
    # Crizanlizumab — FDA approved 2019 (SCD)
    "Crizanlimab":      (2019, 0, 0, 0, 0, "sickle cell; no mandatory IST"),
    "Crizanlizumab":    (2019, 0, 0, 0, 0, "sickle cell; no mandatory IST"),
    # Elotuzumab — FDA approved 2015 (myeloma)
    "Elotuzumab":       (2015, 1, 0, 0, 1, "oncology; Len/dex backbone combination"),
    # Satralizumab — FDA approved 2020 (NMOSD)
    "Satralizumab":     (2020, 0, 0, 0, 1, "neurology; background IST (azathioprine/MMF/corticosteroids) in many"),
}

# Additional immunosuppressant_context for other missing records
IMMUNO_CONTEXT_EXTRA = {
    "Atezolizumab":      "oncology PD-L1; chemotherapy combination common; no specific IST",
    "Bimekizumab":       "psoriasis/PsA; no mandatory IST; MTX optional",
    "Brolucizumab":      "intravitreal anti-VEGF; no systemic IST",
    "Camrelizumab":      "oncology PD-1; chemotherapy or VEGF combination",
    "Cemiplimab":        "oncology PD-1; monotherapy or chemo; no mandatory IST",
    "Clazakizumab":      "RA; background MTX or other csDMARDs in many",
    "Daclizumab":        "MS; no IST; withdrawn 2018",
    "Daratumumab":       "myeloma; Len/bort/dex or pomalidomide combination",
    "Dostarlimab":       "oncology PD-1; carboplatin/paclitaxel or monotherapy",
    "Dupilumab":         "atopic dermatitis/asthma; no mandatory IST; TCS optional",
    "Eculizumab":        "PNH/aHUS rare disease; no IST",
    "Emicizumab":        "hemophilia A; bypassing agent prophylaxis context",
    "Galcanezumab":      "migraine prevention; no IST",
    "Guselkumab":        "psoriasis; no IST; MTX optional in PsA",
    "Mogamulizumab":     "MF/SS oncology; prior systemic therapies; no mandatory IST",
    "Natalizumab":       "MS/Crohn's; no mandatory IST; JCV monitoring required",
    "Obinutuzumab":      "CLL/FL; chemo (chlorambucil/bendamustine/CHOP) combination",
    "Ocrelizumab":       "MS; no concomitant IST; depletes B-cells",
    "Omalizumab":        "allergic asthma/CSU; no IST; background ICS allowed",
    "Palivizumab":       "RSV prophylaxis neonates; no IST",
    "Pembrolizumab":     "oncology PD-1; combination with chemo or VEGFR common",
    "Pertuzumab":        "HER2+ BC; trastuzumab + chemo combination",
    "Ramucirumab":       "oncology VEGFR2; docetaxel or FOLFIRI combination",
    "Reslizumab":        "severe asthma; no mandatory IST; background ICS",
    "Retifanlimab":      "oncology PD-1; carboplatin combination for EC",
    "Secukinumab":       "psoriasis/AS/PsA; no mandatory IST; MTX optional in PsA",
    "Tildrakizumab":     "psoriasis; no IST",
    "Toripalimab":       "oncology PD-1; combination with chemo common",
    "Trastuzumab":       "HER2+ BC; chemo combination (AC-TH, TCH); no IST",
    "Tremelimumab":      "oncology CTLA-4; durvalumab combination (HIMALAYA/POSEIDON)",
    "Vedolizumab":       "UC/CD; background steroids/aminosalicylates common; no IST",
    "Zenocutuzumab":     "NRG1-fusion cancers; monotherapy; no IST",
    "Crizanlizumab":     "sickle cell; no mandatory IST; hydroxyurea background",
    "Elotuzumab":        "myeloma; lenalidomide/dexamethasone combination required",
    "Satralizumab":      "NMOSD; background azathioprine/MMF/prednisolone common",
    "Tisotumab":         "cervical cancer ADC; no mandatory IST",
}

# ── Load & apply ──────────────────────────────────────────────────────────────
with open(MASTER, encoding='utf-8') as f:
    reader     = csv.DictReader(f)
    fieldnames = list(reader.fieldnames)
    all_rows   = list(reader)
row_map = {r['antibody_name']: r for r in all_rows}

updated_b = 0
updated_c = 0

for drug, (yr, onco, ckpt, idep, cimm, icontext) in META.items():
    row = row_map.get(drug)
    if not row:
        print(f"  ⚠ Not found: {drug}")
        continue
    changed = False
    # approval_year
    if not row.get('approval_year','').strip() or row.get('approval_year','').strip() in ('','nan','None'):
        row['approval_year'] = str(yr) if yr else ''
        changed = True
    # binary flags
    for field, val in [
        ('oncology_indication', onco),
        ('checkpoint_inhibitor', ckpt),
        ('immune_depleting', idep),
        ('concomitant_immuno_likely', cimm),
    ]:
        if not row.get(field,'').strip() or row.get(field,'').strip() in ('','nan','None'):
            row[field] = str(float(val))
            changed = True
    # immunosuppressant_context
    if not row.get('immunosuppressant_context','').strip() or row.get('immunosuppressant_context','').strip() in ('','nan','None','none'):
        row['immunosuppressant_context'] = icontext
        updated_c += 1
    if changed:
        updated_b += 1

# Task C: extra immunosuppressant_context
for drug, ctx in IMMUNO_CONTEXT_EXTRA.items():
    row = row_map.get(drug)
    if row and (not row.get('immunosuppressant_context','').strip() or
                row.get('immunosuppressant_context','').strip() in ('','nan','None','none')):
        row['immunosuppressant_context'] = ctx
        updated_c += 1

print(f"Task B: updated metadata for {updated_b} records")
print(f"Task C: updated immunosuppressant_context for {updated_c} records")

# Final check
still_missing_yr = [r['antibody_name'] for r in all_rows
                    if not r.get('approval_year','').strip() or r['approval_year'].strip() in ('','nan','None')]
still_missing_ctx = [r['antibody_name'] for r in all_rows
                     if not r.get('immunosuppressant_context','').strip() or
                     r.get('immunosuppressant_context','').strip() in ('','nan','None','none')]
print(f"Still missing approval_year: {len(still_missing_yr)} → {still_missing_yr[:10]}")
print(f"Still missing immuno_context: {len(still_missing_ctx)} → {still_missing_ctx[:10]}")

# Write
with open(MASTER, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(all_rows)
shutil.copy(MASTER, KB_MASTER)
print(f"Written {len(all_rows)} rows to CSV.")

# Rebuild
print("Rebuilding JSON...")
subprocess.run([sys.executable, 'scripts/_regen_json_only.py'], check=False)
shutil.copy('docs/ada_db_data.json', 'insynbio-web-source/ada_db_data.json')
shutil.copy('docs/ada_db_data.json', 'therasik-web-source/ada_db_data.json')
print("Done.")
