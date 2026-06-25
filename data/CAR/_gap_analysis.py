"""
Gap analysis: CART_LIBRARY_V3 vs InSynBio website "nearly 200 curated components"
Website: https://insynbio.com/InSynBio_CART_Design_Page.html
"""
import json
from pathlib import Path

CAR_DIR = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\CAR")
with open(CAR_DIR / "CART_LIBRARY_V3.json", encoding="utf-8") as f:
    lib = json.load(f)
v3 = {e["id"]: e for e in lib["elements"]}

HAVE = set(v3.keys())

# ── Website-declared components mapped to library IDs ─────────────
website_to_lib = {
    # BINDERS — Clinical
    "FMC63_scFv": "FMC63_scFv",
    "Trastuzumab_scFv (4D5)": "Trastuzumab_scFv",
    "Cetuximab_scFv (mAb225)": "Cetuximab_scFv",
    "14G2a_scFv": "14G2a_hu_scFv",
    "SS1_scFv": "SS1_scFv",
    "m971_scFv": "m971_scFv",
    # BINDERS — Frontier
    "ESK1_WT1_TCRmimic": "ESK1_WT1_TCRmimic",
    "MAGE-A4_TCRmimic": "MAGE-A4_TCRmimic",
    "APRIL_Ligand": "APRIL_Ligand_Binder",
    "NKG2D_Ligand": "NKG2D_Ligand_Binder",
    "EGFRvIII_VHH": "EGFRvIII_VHH",
    "CLDN18.2_VHH": "CLDN18_2_scFv",
    "JNJ_BCMA_VHH": "JNJ68284528_VHH",
    "OKT3_scFv": "OKT3_hu_scFv",
    "Rituximab_scFv": "Rituximab_scFv",
    "Daratumumab_scFv": "Daratumumab_scFv",
    "SJ25C1_scFv": "SJ25C1_scFv",
    "c11D5_BCMA_scFv": "c11D5_3_scFv",
    "Pertuzumab_scFv": "Pertuzumab_scFv",
    "ch14.18_GD2_scFv": "ch14_18_GD2_scFv",
    # HINGE
    "CD8a_Short_Hinge": "CD8a_Short",
    "CD8a_Long_Hinge": "CD8a_Long",
    "CD28_Medium_Hinge": "CD28_Medium",
    "IgG4_SPLE_Long": "IgG4_SPLE_Long",
    "IgD_Hinge": "IgD_Hinge",
    # TRANSMEMBRANE
    "CD8a_TM": "CD8a_TM",
    "CD28_TM": "CD28_TM",
    "CD4_TM": "CD4_TM",
    "NKG2D_TM": "NKG2D_TM",
    # COSTIMULATORY
    "4-1BB_cyto": "4-1BB_cyto",
    "CD28_cyto": "CD28_cyto",
    "OX40_cyto": "OX40_cyto",
    "ICOS_cyto": "ICOS_cyto",
    "2B4_cyto": "2B4_cyto",
    "CD27_cyto": "CD27_cyto",
    "DAP10_costim": "DAP10_costim_full",
    "DAP12_costim": "DAP12_costim",
    # ACTIVATION
    "CD3z_cyto": "CD3z_cyto",
    "CD3z_1XX": "CD3z_1XX",
    "FcRg_cyto": "FcRg_cyto",
    "IL2Rb_5thGen": "IL2Rb_cyto_5thGen",
    "ZAP70_SH2": "ZAP70_tandem_SH2",
    # ARMORED PAYLOADS
    "TGFB_DNR": "TGFB_DNR",
    "Membrane_IL15": "Membrane_IL15",
    "Membrane_IL21": "Membrane_IL21",
    "Secreted_IL12": "Secreted_IL12",
    "IL7_CCL19": "IL7_CCL19_Armor",
    "GPX4_Enhanced": "GPX4_Enhanced",
    "HPSE": "HPSE_Secreted",
    "4-1BBL_Armor": "4-1BBL_Anchored",
    "OX40L_Armor": "OX40L_Anchored",
    # SAFETY SWITCHES
    "tEGFR": "tEGFR",
    "iCasp9": "iCasp9",
    "RQR8": "RQR8",
    "HSV-TK": "HSV-TK",
    "CD20_Mimotope": "CD20_Mimotope",
    # LOGIC GATES
    "PD1_CD28_CSR": "PD1_CD28_CSR",
    "CTLA4_CD28_CSR": "CTLA4_CD28_CSR",
    "TIM3_CD28_CSR": "TIM3_CD28_CSR",
    "SynNotch": "SynNotch_NRR",
    "iCAR_PSMA": "iCAR_PSMA",
    # REGULATORY
    "EF1a_Promoter": "EF1a_Promoter",
    "EF1a_Short_EFS": "EF1a_Short_EFS",
    "PGK_Promoter": "PGK_Promoter",
    "MSCV_LTR": "MSCV_LTR",
    "SFFV_Promoter": "SFFV_Promoter",
    "NFAT_RE": "NFAT_RE_Promoter",
    "UCOE_EF1a": "UCOE_EF1a",
    "Tet_On": "Tet_On_System",
    "CMV_Enhancer": "CMV_Enhancer",
    "WPRE": "WPRE",
    "BGH_polyA": "BGH_polyA",
    # LEADERS
    "CD8a_SP": "CD8a_SP",
    "GM-CSF_SP": "GM-CSF_SP",
    "IL2_SP": "IL2_SP",
    "IgKappa_SP": "IgKappa_SP",
    # LINKERS
    "G4S3": "G4S3",
    "EAAAK3": "EAAAK3",
    "Whitlow": "Whitlow",
    "218_linker": "218",
    "XTEN": "XTEN_12",
    "P2A": "P2A",
    "T2A": "T2A",
    "E2A": "E2A",
    "F2A": "F2A",
    # CAAR / TREG
    "Dsg3_CAAR": "Dsg3_ECD_CAAR",
    "MuSK_CAAR": "MuSK_ECD_CAAR",
    "FoxP3_TF": "FoxP3_TF",
    # ALLOGENEIC
    "TRAC_KO": "TRAC_CRISPR_Target",
    "B2M_KO": "B2M_CRISPR_Target",
    "HLA_G": "HLA_G_Stealth",
    "CD47_Stealth": "CD47_Stealth",
}

# ── Website-mentioned items NOT yet in library ──────────────────
MISSING_FROM_WEBSITE = {
    "Binder": [
        ("KRAS_G12D_TCRmimic",       "Anti-KRAS G12D/HLA-A11 TCRmimic; KRAS muts in PDAC/CRC"),
        ("NYESO1_TCRmimic",           "Anti-NY-ESO-1/HLA-A2 TCRmimic; Clark CE 2019"),
        ("IL13_Mutein_GBM",           "IL-13 E13K/R66D mutein binder for IL-13Rα2 (GBM)"),
        ("DARPin_EGFR",               "EGFR-targeting DARPin scaffold; Stumpp MT Drug Disc Today 2008"),
        ("Centyrin_HER2",             "HER2-targeting Centyrin (Centauri Therapeutics); fibronectin III"),
        ("CXCR4_CAR_binder",          "Anti-CXCR4 based binder; AML/stem cell targeting"),
        ("My96_CD33_scFv_Corrected",  "Correct anti-CD33 My96 scFv; lintuzumab class; AML"),
        ("BiTE_CD19xCD3",             "Blinatumomab-class anti-CD19xCD3 BiTE for tandem secretion"),
    ],
    "Transmembrane": [
        ("DAP12_TM",      "DAP12 TM domain for CAR-NK/Macrophage optimization"),
        ("ICOS_TM",       "ICOS TM for Treg/Th17-skewing CAR"),
        ("OX40_TM",       "OX40 TM domain; improved persistence"),
        ("LNP_Optimized_TM", "In vivo LNP-compatible TM domain (hydrophilicity modified)"),
    ],
    "Costimulatory": [
        ("GITR_cyto",     "GITR (CD357) cytoplasmic; anti-tumor Treg depletion CAR"),
        ("HVEM_cyto",     "HVEM (CD270) cytoplasmic; BTLA/LIGHT pathway"),
        ("CD40_cyto",     "CD40 cytoplasmic; dendritic cell-like activation"),
        ("MyD88_cyto",    "MyD88 cytoplasmic; TLR-linked innate costimulation (GoD-CAR)"),
        ("TLR2_cyto",     "TLR2 cytoplasmic domain; innate pattern recognition costim"),
    ],
    "Safety Switch": [
        ("Rapamycin_ON",    "Rapamycin-inducible dimerization ON switch (FRB+FKBP)"),
        ("Lenalidomide_ON", "Lenalidomide-induced degron; targeted CAR degradation"),
        ("TMPD_Switch",     "TMPD-inducible safety switch"),
    ],
    "Logic Gate": [
        ("Split_CAR_FRB",   "Split CAR: FRB dimerization domain; rapamycin-dependent assembly"),
        ("Split_CAR_FKBP",  "Split CAR: FKBP domain for split-CAR reconstitution"),
        ("LOCKR_Switch",    "LOCKR (Latching Orthogonal Cage-Key pRotein) protein switch"),
        ("UniCAR_BBIR",     "Universal CAR backbone (BBIR); pairs with tumor-targeting module"),
        ("CLIP_CAR",        "CLIP-CAR: switchable synthetic CAR via snap-tag chemistry"),
    ],
    "Armored Payload": [
        ("cJun_DN",         "c-Jun dominant-negative; prevents AP-1 exhaustion in CAR-T"),
        ("BiTE_Secretion",  "Secreted CD19xCD3 or HER2xCD3 BiTE from CAR-T"),
        ("IL18_Armor",      "Secreted IL-18 payload; activates NK and DC in TME"),
    ],
    "Regulatory Element": [
        ("JeT_Promoter",    "JeT (Joint EF1α-T7) compact promoter; Blazeck J NAR 2013"),
        ("Tet_Off_System",  "Tet-Off: tTA + TRE promoter (Tet-Off, opposite polarity)"),
    ],
    "Leader (Signal Peptide)": [
        ("Gaussia_SP",      "Gaussia luciferase SP; strong secretion signal for armored CARs"),
        ("Furin_P2A",       "Furin cleavage + P2A for precise polyprotein cleavage"),
    ],
    "Hinge": [
        ("IgG1_Hinge",      "IgG1 hinge 15aa; alternative to IgG4 for non-Fc-binding design"),
        ("Synthetic_Flex",  "Synthetic flexible hinge (Gly-Ser rich, AI-tuned length)"),
    ],
}

# ── Compute coverage ────────────────────────────────────────────
covered = {k: v for k, v in website_to_lib.items() if v in HAVE}
partial_covered = {k: v for k, v in website_to_lib.items() if v not in HAVE}
total_website_items = sum(len(v) for v in MISSING_FROM_WEBSITE.values()) + len(website_to_lib)
total_missing = sum(len(v) for v in MISSING_FROM_WEBSITE.values())

print(f"=== GAP ANALYSIS vs InSynBio Website ===")
print(f"Website claims: ~200 curated components")
print(f"Current library: {len(lib['elements'])} elements")
print(f"Mapped to website categories: {len(covered)} covered")
print(f"Missing (explicit website mention): {total_missing}")
print(f"Remaining gap to ~200: {200 - len(lib['elements'])}")

print(f"\n{'='*60}")
print(f"MISSING ELEMENTS BY CATEGORY (website-mentioned, not in library)")
print(f"{'='*60}")
grand_total = 0
for cat, items in sorted(MISSING_FROM_WEBSITE.items()):
    print(f"\n  [{cat}] — {len(items)} missing:")
    for eid, note in items:
        print(f"    + {eid}")
        print(f"      {note}")
    grand_total += len(items)

print(f"\n  Subtotal explicitly missing: {grand_total}")
print(f"  Additional variants/subtypes to reach ~200: ~{200 - len(lib['elements']) - grand_total}")
