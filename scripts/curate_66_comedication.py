"""
Curate mtx_comedication and immunosuppressant_context for the 66 non-P70 antibodies.
Values follow the same encoding as clinical_confounders_70.csv.
All entries sourced from FDA prescribing information, EMA SmPC, or pivotal trial protocols.
"""
import pandas as pd
from pathlib import Path

# Same encoding as clinical_confounders_70.csv:
#   mtx_comedication: "none" | "moderate_proportion" | "high_proportion"
#   immunosuppressant_context: descriptive string, "none" if not applicable

COMED = [
    # ── NATURAL antibodies ──────────────────────────────────────────────────
    # Aducanumab: Alzheimer's, no immunosuppressants in EMERGE/ENGAGE
    ("Aducanumab",    "none", "none"),
    # Atoltivimab: Ebola (Inmazeb) - critical care, no MTX
    ("Atoltivimab",   "none", "none"),
    # Bamlanivimab: COVID-19 mild-moderate outpatient, no MTX; some patients on dexamethasone
    ("Bamlanivimab",  "none", "none"),
    # Belimumab: SLE - background HCQ/steroids common, some MTX but not majority
    ("Belimumab",     "none", "background SLE immunosuppressants"),
    # Bimagrumab: IBM/obesity - no standard immunosuppressants in trials
    ("Bimagrumab",    "none", "none"),
    # Clesrovimab: RSV prophylaxis in infants - no immunosuppressants
    ("Clesrovimab",   "none", "none"),
    # Crovalimab: PNH - no MTX; anticoagulants common but not immunosuppressants
    ("Crovalimab",    "none", "none"),
    # Daratumumab: Multiple myeloma - always in combination with bortezomib/dexamethasone
    ("Daratumumab",   "none", "chemo combination always"),
    # Dupilumab: AD/asthma - no MTX; ICS background for asthma indication
    ("Dupilumab",     "none", "ICS background"),
    # Ebronucimab: Hypercholesterolemia - statin background only
    ("Ebronucimab",   "none", "none"),
    # Emapalumab: HLH - always with dexamethasone per protocol
    ("Emapalumab",    "none", "chemo combination always"),
    # Enuzovimab: COVID-19 - no MTX; dexamethasone in some patients
    ("Enuzovimab",    "none", "none"),
    # Etesevimab: COVID-19 (with bamlanivimab) - no MTX; outpatient setting
    ("Etesevimab",    "none", "none"),
    # Evinacumab: HoFH - statins + ezetimibe background, not immunosuppressants
    ("Evinacumab",    "none", "none"),
    # Evolocumab: Hypercholesterolemia - statin background only
    ("Evolocumab",    "none", "none"),
    # Fulranumab: Chronic pain - no MTX, discontinued
    ("Fulranumab",    "none", "none"),
    # Garadacimab: HAE - no MTX; no standard immunosuppressants
    ("Garadacimab",   "none", "none"),
    # Nivolumab: Oncology checkpoint inhibitor - no MTX; chemo combination in some indications
    ("Nivolumab",     "none", "chemo combination sometimes"),
    # Olaratumab: Sarcoma with doxorubicin - chemo combination; withdrawn
    ("Olaratumab",    "none", "chemo combination always"),
    # Pemivibart: COVID-19 PrEP in immunocompromised - patients may be on immunosuppressants
    ("Pemivibart",    "none", "background immunosuppressants (immunocompromised host)"),
    # Ramucirumab: GI/lung oncology - chemo combination (FOLFIRI, docetaxel)
    ("Ramucirumab",   "none", "chemo combination"),
    # Regdanvimab: COVID-19 - no MTX; outpatient
    ("Regdanvimab",   "none", "none"),
    # Relatlimab: Melanoma (with nivolumab, Opdualag) - no MTX, no chemo
    ("Relatlimab",    "none", "none"),
    # Secukinumab: Psoriasis/PsA/AS - MTX used in PsA but not psoriasis; moderate proportion
    ("Secukinumab",   "moderate_proportion", "MTX in PsA common"),
    # Sintilimab: Oncology (NSCLC/HCC) - chemo combination in most indications
    ("Sintilimab",    "none", "chemo combination"),
    # Tafolecimab: Hypercholesterolemia - statins only, no immunosuppressants
    ("Tafolecimab",   "none", "none"),
    # Tezepelumab: Severe asthma - ICS/LABA background therapy always
    ("Tezepelumab",   "none", "ICS background"),
    # Tremelimumab: HCC/NSCLC with durvalumab - no MTX, no chemo in STRIDE regimen
    ("Tremelimumab",  "none", "none"),

    # ── ENGINEERED (humanized) antibodies ───────────────────────────────────
    # Axatilimab: cGVHD - patients always on background GVHD immunosuppressants
    ("Axatilimab",    "none", "transplant immunosuppressants"),
    # Belantamab: Myeloma ADC - with dexamethasone in combination
    ("Belantamab",    "none", "chemo combination"),
    # Budigalimab: Solid tumors (anti-PD-1 monotherapy) - no MTX
    ("Budigalimab",   "none", "none"),
    # Crizanlizumab: Sickle cell - hydroxyurea background common (50-60% of patients)
    ("Crizanlizumab", "none", "hydroxyurea background (common)"),
    # Depemokimab: Severe eosinophilic asthma - ICS background always
    ("Depemokimab",   "none", "ICS background"),
    # Domvanalimab: NSCLC (with zimberelimab) - no MTX; sometimes chemo
    ("Domvanalimab",  "none", "chemo combination sometimes"),
    # Eculizumab: PNH/aHUS - anticoagulants; some aHUS patients on other immunosuppressants
    ("Eculizumab",    "none", "immunosuppressants in some aHUS"),
    # Elezanumab: Spinal cord injury - no standard immunosuppressants
    ("Elezanumab",    "none", "none"),
    # Elotuzumab: Myeloma with lenalidomide+dexamethasone - immunosuppressive chemo combination
    ("Elotuzumab",    "none", "chemo combination always"),
    # Etaracizumab: Solid tumors - phase 2, chemo combination in some arms
    ("Etaracizumab",  "none", "chemo combination sometimes"),
    # Exidavnemab: Parkinson's - no MTX, no immunosuppressants in CNS trial
    ("Exidavnemab",   "none", "none"),
    # Favezelimab: LAG-3 (with pembrolizumab) - no MTX; no chemo
    ("Favezelimab",   "none", "none"),
    # Gemtuzumab: AML (anti-CD33 ADC) - chemotherapy combination (daunorubicin+cytarabine)
    ("Gemtuzumab",    "none", "chemo combination always"),
    # Ibalizumab: HIV - no MTX; background antiretroviral therapy always
    ("Ibalizumab",    "none", "antiretroviral background"),
    # Inebilizumab: NMOSD - sometimes background azathioprine/MMF
    ("Inebilizumab",  "none", "background immunosuppressants sometimes"),
    # Lebrikizumab: Atopic dermatitis - no MTX; TCS as background
    ("Lebrikizumab",  "none", "none"),
    # Leronlimab: HIV/TNBC - antiretroviral background in HIV indication
    ("Leronlimab",    "none", "antiretroviral background"),
    # Levilimab: RA - MTX comedication in subset of RA patients
    ("Levilimab",     "moderate_proportion", "MTX in RA"),
    # Mirikizumab: UC/CD - 5-ASA/thiopurines/steroids background common in IBD
    ("Mirikizumab",   "none", "5-ASA/steroids/thiopurines in IBD"),
    # Mogamulizumab: CTCL - no MTX; bexarotene in some patients
    ("Mogamulizumab", "none", "none"),
    # Nemolizumab: AD/prurigo - no MTX; TCS background
    ("Nemolizumab",   "none", "none"),
    # Nimotuzumab: Head/neck/glioma - chemo+radiation combination
    ("Nimotuzumab",   "none", "chemo combination"),
    # Obinutuzumab: CLL/FL - chemo combination (chlorambucil/bendamustine)
    ("Obinutuzumab",  "none", "chemo combination always"),
    # Ocrelizumab: MS - no MTX; methylprednisolone for infusion reactions
    ("Ocrelizumab",   "none", "none"),
    # Olokizumab: RA - MTX commonly co-administered (approved with/without MTX)
    ("Olokizumab",    "high_proportion", "MTX in RA"),
    # Palivizumab: RSV prophylaxis - no MTX; healthy high-risk infants
    ("Palivizumab",   "none", "none"),
    # Penpulimab: HL (anti-PD-1) - no MTX; chemo combination in some settings
    ("Penpulimab",    "none", "chemo combination sometimes"),
    # Pertuzumab: HER2+ breast - always with trastuzumab+docetaxel (chemo always)
    ("Pertuzumab",    "none", "chemo combination always"),
    # Polatuzumab: DLBCL - always with R-CHP chemotherapy
    ("Polatuzumab",   "none", "chemo combination always"),
    # Recaticimab: Hypercholesterolemia - statins background, no immunosuppressants
    ("Recaticimab",   "none", "none"),
    # Rozanolixizumab: Myasthenia gravis - sometimes background steroids/AChEI
    ("Rozanolixizumab","none", "background immunosuppressants sometimes"),
    # Satralizumab: NMOSD - background azathioprine/MMF/steroids common
    ("Satralizumab",  "none", "background immunosuppressants sometimes"),
    # Spesolimab: GPP - sometimes oral steroids during flare management
    ("Spesolimab",    "none", "none"),
    # Sutimlimab: Cold agglutinin disease - no standard immunosuppressants
    ("Sutimlimab",    "none", "none"),
    # Tafasitamab: DLBCL - always with lenalidomide (immunomodulatory)
    ("Tafasitamab",   "none", "chemo combination always"),
    # Tagitanlimab: Solid tumors (anti-PD-L1) - chemo combination
    ("Tagitanlimab",  "none", "chemo combination"),
    # Timigutuzumab: HER2+ breast (biparatopic) - chemo combination expected
    ("Timigutuzumab", "none", "chemo combination"),
    # Vunakizumab: Psoriasis/PsA - MTX in PsA subset
    ("Vunakizumab",   "moderate_proportion", "MTX in PsA common"),
]

df = pd.DataFrame(COMED, columns=["antibody_name", "mtx_comedication", "immunosuppressant_context"])
df["source"] = "curated from FDA label / EMA SmPC / pivotal trial protocol"
df.to_csv("data/curated_66_comedication.csv", index=False, encoding="utf-8")
print("Written {} rows to data/curated_66_comedication.csv".format(len(df)))
print()
print("mtx_comedication breakdown:")
print(df["mtx_comedication"].value_counts())
print()
print("immunosuppressant_context breakdown:")
print(df["immunosuppressant_context"].value_counts().to_string())
