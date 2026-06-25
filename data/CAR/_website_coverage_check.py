"""
Systematic coverage check vs InSynBio website table
Website: https://insynbio.com/InSynBio_CART_Design_Page.html
"""
import json
from pathlib import Path
from collections import defaultdict

CAR_DIR = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\CAR")
with open(CAR_DIR / "CART_LIBRARY_V3.json", encoding="utf-8") as f:
    lib = json.load(f)
HAVE = {e["id"] for e in lib["elements"]}
v3 = {e["id"]: e for e in lib["elements"]}

# ── Website table items (literal from page) ──────────────────────
# Format: (website_name, library_id_or_None, status_note)
WEBSITE_TABLE = {
    "Binders": {
        "Clinical Standards": [
            ("scFv FMC63",          "FMC63_scFv",       "✅"),
            ("scFv Trastuzumab",    "Trastuzumab_scFv", "✅"),
            ("scFv 14G2a",          "14G2a_hu_scFv",    "✅"),
            ("scFv SS1",            "SS1_scFv",          "✅"),
            ("scFv m971",           "m971_scFv",         "✅"),
            ("scFv 4D5",            "Trastuzumab_scFv",  "✅ same as Trastuzumab"),
            ("scFv 225 (cetuximab)","Cetuximab_scFv",   "✅"),
            ("Humanized scFv",      "~multiple",         "✅ covered by 14G2a/MOv19/OKT3"),
            ("Fab Fragments",       None,               "⚠ Fab format not explicitly in library"),
        ],
        "Frontier Modalities": [
            ("VHH/Nanobody Solid Tumor","EGFRvIII_VHH/CLDN18_2_scFv","✅"),
            ("TCR-mimic WT1",       "ESK1_WT1_TCRmimic","✅"),
            ("TCR-mimic KRAS",      None,               "❌ not in library"),
            ("TCR-mimic NY-ESO-1",  None,               "❌ not in library"),
            ("TCR-mimic MAGE-A4",   "MAGE-A4_TCRmimic", "⚠ stub (MSKCC proprietary)"),
            ("Centyrins",           None,               "❌ not in library"),
            ("DARPins",             None,               "❌ not in library"),
            ("Ligand-based IL-13",  "IL13_Mutein_GBM",  "✅ IL-13 mutein"),
            ("Ligand-based APRIL",  "APRIL_Ligand_Binder","✅"),
            ("Computational Mask Design", None,         "❌ AI design concept, no sequence"),
            ("Peptide Binders",     None,               "❌ not in library"),
        ],
    },
    "Hinge": {
        "Clinical Standards": [
            ("CD8α Short (45aa)",   "CD8a_Short",        "✅"),
            ("IgG4 Long (228aa)",   "IgG4_SPLE_Long",    "✅"),
            ("CD28 Medium",         "CD28_Medium",        "✅"),
            ("IgG1 Hinge",          "IgG1_Hinge",        "✅"),
        ],
        "Frontier Modalities": [
            ("IgG4-SPLE (Fc-Null/S228P)", "IgG4_SPLE_Long", "✅"),
            ("Auto-Hinge AI-Matched",     None,           "❌ AI module concept, no sequence"),
            ("IgD Hinge protease-resistant","IgD_Hinge",  "✅"),
            ("CD8α-Long (119aa)",          "CD8a_Long",    "✅"),
            ("Synthetic Flexible Linkers", None,           "⚠ G4S variants partial coverage"),
            ("Rigid EAAAK Linkers",        "EAAAK3",       "✅ in Linker category"),
        ],
    },
    "Transmembrane": {
        "Clinical Standards": [
            ("CD8α TM (Low tonic)", "CD8a_TM",  "✅"),
            ("CD28 TM (Lipid raft)","CD28_TM",  "✅"),
            ("CD4 TM",              "CD4_TM",    "✅"),
        ],
        "Frontier Modalities": [
            ("NKG2D TM (NK Optimization)", "NKG2D_TM",  "✅"),
            ("DAP10 TM",           "DAP10_costim_full",  "⚠ DAP10 full (TM+cyto combined)"),
            ("DAP12 TM",           "DAP12_TM",           "✅"),
            ("ICOS TM",            "ICOS_TM",             "✅"),
            ("OX40 TM",            "OX40_TM",             "✅"),
            ("In Vivo Optimized TM (LNP)", None,         "❌ not in library"),
        ],
    },
    "Co-stimulatory": {
        "Clinical Standards": [
            ("4-1BB (Mitochondrial)", "4-1BB_cyto", "✅"),
            ("CD28 (Glycolytic)",     "CD28_cyto",  "✅"),
        ],
        "Frontier Modalities": [
            ("OX40 (CD134)",    "OX40_cyto",      "✅"),
            ("ICOS (Th17/Th1)", "ICOS_cyto",      "✅"),
            ("2B4 (CD244)",     "2B4_cyto",       "✅"),
            ("DAP10",           "DAP10_costim_full","✅"),
            ("CD27",            "CD27_cyto",      "✅"),
            ("GITR",            "GITR_cyto",      "✅"),
            ("HVEM",            "HVEM_cyto",      "✅"),
            ("CD40",            "CD40_cyto",      "✅"),
            ("MyD88",           "MyD88_TIR",      "✅"),
            ("TLR2",            "TLR2_TIR",       "✅"),
            ("4-1BBL Self-Driving","4-1BBL_Anchored","✅ in Armored Payload"),
        ],
    },
    "Activation": {
        "Clinical Standards": [
            ("CD3ζ (3x ITAM)", "CD3z_cyto", "✅"),
        ],
        "Frontier Modalities": [
            ("DAP12 (CAR-NK/Mac)",   "DAP12_costim",    "✅"),
            ("FcR-γ (Phagocytosis)", "FcRg_cyto",       "✅"),
            ("CD3ε (Recruitment)",   None,               "❌ CD3ε cyto not in library"),
            ("ZAP70 recruitment",    "ZAP70_tandem_SH2","✅"),
            ("1XX Calibrated ITAMs", "CD3z_1XX",        "✅"),
        ],
    },
    "Armored Payloads": {
        "Clinical Standards": [
            ("Secreted IL-12 (TRUCK)","Secreted_IL12",  "✅"),
            ("Constitutive IL-15",    "Membrane_IL15",   "✅"),
        ],
        "Frontier Modalities": [
            ("TGFB_DNR",               "TGFB_DNR",         "✅"),
            ("Membrane_IL15",          "Membrane_IL15",     "✅"),
            ("Membrane_IL21",          "Membrane_IL21",     "✅"),
            ("GPX4_Enhanced",          "GPX4_Enhanced",     "✅"),
            ("IL-7/CCL19 (7x19)",      "IL7_CCL19_Armor",  "✅"),
            ("c-JUN (exhaustion)",     "cJun_Overexpression","✅"),
            ("HPSE (Heparanase)",      "HPSE_Secreted",     "✅"),
            ("scFv-PD1 blocker",       "PD1_CD28_CSR",      "⚠ CSR not same as scFv PD-L1 blocker"),
            ("BiTE secretion",         None,                "❌ BiTE construct not in library"),
            ("IL-18 (new frontier)",   "Secreted_IL18",     "✅"),
        ],
    },
    "Safety Switches": {
        "Clinical Standards": [
            ("tEGFR (Cetuximab)",        "tEGFR",        "✅"),
            ("CD20 Mimotope (Rituximab)","CD20_Mimotope","✅"),
        ],
        "Frontier Modalities": [
            ("iCasp9 (Small Mol >95%)",  "iCasp9",          "✅"),
            ("RQR8 (Dual Tag)",          "RQR8",            "✅ reconstructed"),
            ("Rapamycin-ON",             "Rapamycin_FRB",   "✅ FRB domain"),
            ("Lenalidomide-ON",          None,              "❌ not in library"),
            ("HSV-TK",                   "HSV-TK",          "✅"),
            ("TMPD-inducible",           None,              "❌ not in library"),
        ],
    },
    "Logic Gates": {
        "Clinical Standards": [
            ("Tandem CAR (OR Gate)",  None,           "⚠ design construct not in library"),
        ],
        "Frontier Modalities": [
            ("SynNotch (AND Gate)",   "SynNotch_NRR", "✅"),
            ("iCAR (NOT Gate PD-1/CTLA-4)","iCAR_PSMA","✅"),
            ("Split CAR (Dimerization)","Rapamycin_FRB","✅ FRB; FKBP12 for split"),
            ("LOCKR (Protein Switch)", None,          "❌ not in library"),
            ("CLIP-CAR",              None,           "❌ not in library"),
            ("Universal CAR (BBIR)",  None,           "❌ not in library"),
        ],
    },
    "Regulatory": {
        "Clinical Standards": [
            ("EF1α Promoter", "EF1a_Promoter",  "✅"),
            ("PGK Promoter",  "PGK_Promoter",   "✅"),
            ("WPRE",          "WPRE",            "✅"),
        ],
        "Frontier Modalities": [
            ("NFAT_Response (Inducible)","NFAT_RE_Promoter","✅"),
            ("UCOE (Anti-Silencing)",    "UCOE_EF1a",       "✅ reference+sequence"),
            ("Tet-On",                   "Tet_On_System",   "✅"),
            ("Tet-Off",                  None,              "❌ not in library"),
            ("SFFV",                     "SFFV_Promoter",   "✅"),
            ("CMV",                      "CMV_Enhancer",    "⚠ enhancer only, not full CMV prom"),
            ("SV40",                     "SV40_polyA",      "⚠ polyA only, not promoter"),
            ("EFS (Compact)",            "EF1a_Short_EFS",  "✅"),
            ("JeT promoter",             "JeT_Promoter",    "✅"),
        ],
    },
    "Leaders & Linkers": {
        "Clinical Standards": [
            ("CD8α SP",     "CD8a_SP",     "✅"),
            ("GM-CSF SP",   "GM-CSF_SP",   "✅"),
            ("G4S (Flexible)","G4S3",      "✅"),
        ],
        "Frontier Modalities": [
            ("IL-2 SP",         "IL2_SP",        "✅"),
            ("Gaussia SP",      "Gaussia_SP",    "✅"),
            ("EAAAK3 Rigid",    "EAAAK3",        "✅"),
            ("Whitlow Linker",  "Whitlow",       "✅"),
            ("218 Linker",      "218",           "✅"),
            ("XTEN",            "XTEN_12",       "✅"),
            ("Furin-P2A",       "Furin_P2A",     "✅"),
            ("T2A/E2A/F2A",     "T2A/E2A/F2A",  "✅ all 4 2A peptides"),
        ],
    },
}

# ── Compute coverage ─────────────────────────────────────────────
total_items = 0
covered = 0
partial = 0
missing = 0
missing_list = []

print(f"\n{'='*68}")
print(f"{'Category':<18} {'Tier':<22} {'Status':<4} {'Website Item'}")
print(f"{'='*68}")

for cat, tiers in WEBSITE_TABLE.items():
    for tier_name, items in tiers.items():
        for website_name, lib_id, status in items:
            total_items += 1
            symbol = status[:1]
            if symbol == "✅": covered += 1
            elif symbol == "⚠": partial += 1
            else: missing += 1; missing_list.append((cat, website_name))
            if symbol == "❌":
                print(f"  {cat:<16} {tier_name[:22]:<22} {status[:2]}  {website_name}")

print(f"\n{'='*68}")
print(f"COVERAGE SUMMARY")
print(f"{'='*68}")
print(f"  Website items mapped:  {total_items}")
print(f"  ✅ Fully covered:      {covered} ({100*covered//total_items}%)")
print(f"  ⚠  Partial/overlap:   {partial}")
print(f"  ❌ Missing:            {missing}")
print(f"\n  Library size:          {len(lib['elements'])} elements")
print(f"  Website claims:        ~200 components")
print(f"  Gap to ~200:           ~{200 - len(lib['elements'])}")
print(f"\n  MISSING ITEMS ({missing}):")
for cat, item in missing_list:
    print(f"    [{cat}] {item}")
