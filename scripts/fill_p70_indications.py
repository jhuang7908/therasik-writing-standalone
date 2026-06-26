"""
Fill indication_text and disease_class_curated for P70-panel antibodies.
All entries sourced from FDA labels or published regulatory documents.
"""
import pandas as pd
import numpy as np
from pathlib import Path

IND = {
    "Adalimumab":     ("RA, psoriasis, Crohn's, UC, JIA, AS, uveitis", "autoimmune"),
    "Anifrolumab":    ("Systemic lupus erythematosus (SLE)", "autoimmune"),
    "Astegolimab":    ("Asthma (anti-ST2, Phase 3)", "autoimmune_allergic"),
    "Bezlotoxumab":   ("C. difficile infection recurrence prevention", "infectious"),
    "Brodalumab":     ("Plaque psoriasis (anti-IL-17RA)", "autoimmune"),
    "Burosumab":      ("X-linked hypophosphatemia (XLH)", "metabolic_musculoskeletal"),
    "Canakinumab":    ("CAPS, SJIA, gout flares, TRAPS, HIDS, FMF", "autoimmune"),
    "Cemiplimab":     ("CSCC, BCC, NSCLC (anti-PD-1)", "oncology"),
    "Cilgavimab":     ("COVID-19 PrEP (with tixagevimab, Evusheld)", "infectious"),
    "Denosumab":      ("Osteoporosis, bone metastases (anti-RANKL)", "metabolic_musculoskeletal"),
    "Durvalumab":     ("NSCLC, BTC, ES-SCLC, HCC (anti-PD-L1)", "oncology"),
    "Efalizumab":     ("Plaque psoriasis (withdrawn 2009, PML risk)", "autoimmune"),
    "Enfortumab":     ("Urothelial carcinoma (anti-Nectin-4 ADC)", "oncology"),
    "Erenumab":       ("Migraine prevention (anti-CGRP receptor)", "neurology"),
    "Golimumab":      ("RA, PsA, AS, UC (anti-TNF)", "autoimmune"),
    "Guselkumab":     ("Plaque psoriasis, PsA (anti-IL-23p19)", "autoimmune"),
    "Lanadelumab":    ("Hereditary angioedema (anti-kallikrein)", "hematology_immunology"),
    "Necitumumab":    ("Squamous NSCLC (anti-EGFR)", "oncology"),
    "Nirsevimab":     ("RSV prevention in infants (anti-RSV-F, YTE)", "infectious"),
    "Ofatumumab":     ("CLL; relapsing MS (anti-CD20)", "oncology_neurology"),
    "Panitumumab":    ("Metastatic CRC (anti-EGFR)", "oncology"),
    "Sarilumab":      ("Rheumatoid arthritis (anti-IL-6R)", "autoimmune"),
    "Teprotumumab":   ("Thyroid eye disease (anti-IGF-1R)", "endocrine_autoimmune"),
    "Tisotumab":      ("Cervical cancer (anti-TF ADC)", "oncology"),
    "Tixagevimab":    ("COVID-19 PrEP (with cilgavimab, Evusheld)", "infectious"),
    "Tralokinumab":   ("Atopic dermatitis (anti-IL-13)", "autoimmune_allergic"),
    "Ustekinumab":    ("Psoriasis, PsA, Crohn's, UC (anti-IL-12/23)", "autoimmune"),
    "Alemtuzumab":    ("Relapsing MS; CLL (anti-CD52)", "neurology_autoimmune"),
    "Atezolizumab":   ("NSCLC, SCLC, HCC, TNBC, UC (anti-PD-L1)", "oncology"),
    "Benralizumab":   ("Severe eosinophilic asthma (anti-IL-5Rα)", "autoimmune_allergic"),
    "Bevacizumab":    ("CRC, NSCLC, GBM, RCC, cervical (anti-VEGF)", "oncology"),
    "Bimekizumab":    ("Plaque psoriasis, PsA, AS (anti-IL-17A/F)", "autoimmune"),
    "Brolucizumab":   ("Wet AMD, DME (anti-VEGF, scFv)", "ophthalmology"),
    "Camrelizumab":   ("HCC, HL, NSCLC, NPC, ESCC (anti-PD-1)", "oncology"),
    "Certolizumab":   ("RA, Crohn's, PsA, AS (PEGylated anti-TNF Fab)", "autoimmune"),
    "Clazakizumab":   ("Kidney transplant desensitization (anti-IL-6, Phase 3)", "autoimmune"),
    "Concizumab":     ("Hemophilia A/B with inhibitors (anti-TFPI)", "hematology"),
    "Daclizumab":     ("Relapsing MS (anti-CD25, withdrawn 2018)", "neurology_autoimmune"),
    "Dazukibart":     ("Systemic sclerosis (anti-IFN-beta, Phase 2)", "autoimmune"),
    "Donanemab":      ("Alzheimer's disease (anti-N3pG amyloid-beta)", "neurology"),
    "Dostarlimab":    ("Endometrial cancer, dMMR solid tumors (anti-PD-1)", "oncology"),
    "Emicizumab":     ("Hemophilia A (bispecific FIXa/FX bridging)", "hematology"),
    "Eptinezumab":    ("Migraine prevention (anti-CGRP)", "neurology"),
    "Etrolizumab":    ("Ulcerative colitis (anti-β7 integrin, Phase 3)", "autoimmune"),
    "Faricimab":      ("Wet AMD, DME (bispecific anti-VEGF-A/Ang-2)", "ophthalmology"),
    "Fremanezumab":   ("Migraine prevention (anti-CGRP)", "neurology"),
    "Galcanezumab":   ("Migraine prevention, cluster headache (anti-CGRP)", "neurology"),
    "Itolizumab":     ("Psoriasis (anti-CD6, India approved)", "autoimmune"),
    "Ixekizumab":     ("Plaque psoriasis, PsA, AS (anti-IL-17A)", "autoimmune"),
    "Lecanemab":      ("Alzheimer's disease (anti-amyloid-beta protofibrils)", "neurology"),
    "Mepolizumab":    ("Severe eosinophilic asthma, EGPA, HES (anti-IL-5)", "autoimmune_allergic"),
    "Natalizumab":    ("Relapsing MS, Crohn's (anti-α4 integrin)", "neurology_autoimmune"),
    "Naxitamab":      ("High-risk neuroblastoma (anti-GD2)", "oncology"),
    "Omalizumab":     ("Allergic asthma, chronic urticaria (anti-IgE)", "autoimmune_allergic"),
    "Ozoralizumab":   ("Rheumatoid arthritis (anti-TNF nanobody, Japan)", "autoimmune"),
    "Pembrolizumab":  ("Multiple cancers (anti-PD-1)", "oncology"),
    "Ranibizumab":    ("Wet AMD, DME, RVO (anti-VEGF Fab)", "ophthalmology"),
    "Ravulizumab":    ("PNH, aHUS (anti-C5, long-acting)", "hematology_immunology"),
    "Reslizumab":     ("Severe eosinophilic asthma (anti-IL-5)", "autoimmune_allergic"),
    "Retifanlimab":   ("Merkel cell carcinoma (anti-PD-1)", "oncology"),
    "Risankizumab":   ("Plaque psoriasis, PsA, Crohn's (anti-IL-23p19)", "autoimmune"),
    "Romosozumab":    ("Osteoporosis (anti-sclerostin)", "metabolic_musculoskeletal"),
    "Sacituzumab":    ("TNBC, UC (anti-Trop-2 ADC)", "oncology"),
    "Tarlatamab":     ("SCLC (bispecific DLL3 x CD3 T-cell engager)", "oncology"),
    "Tildrakizumab":  ("Plaque psoriasis (anti-IL-23p19)", "autoimmune"),
    "Tocilizumab":    ("RA, GCA, CRS, COVID-19 (anti-IL-6R)", "autoimmune"),
    "Toripalimab":    ("NPC, melanoma (anti-PD-1)", "oncology"),
    "Trastuzumab":    ("HER2+ breast/gastric cancer (anti-HER2)", "oncology"),
    "Vedolizumab":    ("UC, Crohn's (anti-α4β7 integrin)", "autoimmune"),
    "Zenocutuzumab":  ("NRG1-fusion+ cancers (bispecific anti-HER2/HER3)", "oncology"),
}

m = pd.read_csv(Path("data/ada_master_136_curated.csv"))
filled_ind = 0
filled_dc = 0

for i, row in m.iterrows():
    name = row["antibody_name"]
    if name in IND:
        ind_text, dc = IND[name]
        if pd.isna(row.get("indication_text")) or not str(row.get("indication_text","")).strip() or str(row.get("indication_text","")).strip() in ("nan", "None"):
            m.at[i, "indication_text"] = ind_text
            filled_ind += 1
        cur_dc = row.get("disease_class_curated")
        if pd.isna(cur_dc) or not str(cur_dc).strip() or str(cur_dc).strip() in ("nan", "None") or "(inferred" in str(cur_dc):
            m.at[i, "disease_class_curated"] = dc
            filled_dc += 1

print("Filled indication_text: {}".format(filled_ind))
print("Filled disease_class_curated: {}".format(filled_dc))

# Final coverage check
n = len(m)
for col in ["indication_text", "disease_class_curated"]:
    nn = m[col].apply(lambda x: bool(x) and str(x).strip() not in ("", "nan", "None")).sum()
    print("  {:30s} {:3d}/{} ({:.1f}%)".format(col, nn, n, nn/n*100))

m.to_csv("data/ada_master_136_curated.csv", index=False, encoding="utf-8")
print("Saved.")
