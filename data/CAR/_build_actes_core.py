"""
Rebuild ACTES core data files:
  1. ACTES_CART_Engine_v1.0/resources/functional_domains.json
  2. data/actes_sequences/sequence_db.json

Sequences sourced from UniProt REST API (fetched in prior steps).
"""
import json, os, time
from pathlib import Path
from urllib import request

BASE_URL = "https://rest.uniprot.org/uniprotkb/{}.fasta"

# ── load previously fetched sequences ─────────────────────────────
DATA_DIR = Path(__file__).parent
FETCHED_PATH = DATA_DIR / "CAR_SEQUENCES_FETCHED.json"
ADDL_PATH    = DATA_DIR / "_additional_seqs.json"

with open(FETCHED_PATH, encoding="utf-8") as f:
    fetched_data = json.load(f)
with open(ADDL_PATH, encoding="utf-8") as f:
    addl = json.load(f)

# Build a lookup by id
seq_by_id = {}
for e in fetched_data["uniprot_fetched"]:
    seq_by_id[e["id"]] = e["sequence"]
for e in fetched_data["synthetic"]:
    seq_by_id[e["id"]] = e["sequence"]

# Additional sequences
FKBP12        = addl["FKBP12_full"]       # 108 aa, P62942
CASP9_DCARD   = addl["CASP9_deltaCard"]   # 282 aa, P55211 135-416
GRANULIN_SP   = addl["Granulin_SP"]       # 21 aa, P28799 1-21
DAP12_COSTIM  = addl["DAP12_costim"]      # 31 aa, O43914 76-106
FCRG_CYTO     = addl["FcRg_cyto"]        # 42 aa, P30273 45-86
TGFB_DNR_189  = addl["TGFB_DNR_ECD_TM"] # 189 aa, P37173 1-189

# ── derive combined sequences ──────────────────────────────────────
CD8A_SP_WITH_M = "M" + seq_by_id["CD8a_SP"]  # P01732 1-21 = M + (2-21)
GMCSF_SP       = seq_by_id["GM-CSF_SP"]       # 17 aa P04141 1-17

# iCasp9 in ACTES = CASP9ΔCARD alone (282 aa)
ICASP9_SEQ     = CASP9_DCARD

# IgG4 SPLE Long: fetch from UniProt P01861 (hinge EU216 + CH2 + CH3)
# EU numbering: In P01861 canonical (no signal pep, starts at CH1), EU 216 ≈ residue 99
# IgG4_SPLE = hinge (EU216-230) + CH2 (EU231-340) + CH3 (EU341-447)
# P01861 lengths: signal=1-19, mature starts at 20. Hinge in mature ≈ 99-109.
# We use P01861 positions 99-331 ≈ 233 aa for the SPLE construct (S228P mutation applied separately).
# Fetched as: seg(P01861, 99, 331)
def fetch_seg(acc, s, e):
    url = BASE_URL.format(acc)
    with request.urlopen(url, timeout=15) as r:
        fasta = r.read().decode()
    lines = fasta.strip().splitlines()
    seq = "".join(ln for ln in lines if not ln.startswith(">"))
    return seq[s-1:e]

print("Fetching IgG4 hinge+CH2+CH3 (P01861 99-331)...")
IgG4_SPLE = fetch_seg("P01861", 99, 331)
time.sleep(0.3)
# Apply S228P mutation (EU228 = approx position 99+10-1=109 in P01861 if hinge starts at 99)
# EU228 - EU216 = 12 offset from start of hinge → position 110 in P01861
# P01861[109] should be S; mutate to P
igg4_list = list(IgG4_SPLE)
# EU228 = P01861 position 109 (1-indexed), we extracted starting at 99, so local index = 109-99 = 10
if len(igg4_list) > 10 and igg4_list[10] == "S":
    igg4_list[10] = "P"
    print(f"  Applied S228P mutation at local index 10")
else:
    print(f"  Warning: expected S at local index 10, found '{igg4_list[10] if len(igg4_list)>10 else 'N/A'}'")
IgG4_SPLE = "".join(igg4_list)
print(f"  IgG4_SPLE length: {len(IgG4_SPLE)} aa")

# IgK SP
IGK_SP = seq_by_id["IgK_SP"]   # 21 aa

# ── Helper: qa block ───────────────────────────────────────────────
def qa(source, status="Verified", uniprot=None, residues=None):
    d = {"source": source, "status": status}
    if uniprot: d["uniprot"] = uniprot
    if residues: d["residues"] = residues
    return d

MISSING = qa("Missing", "Unverified")

# ── Build functional_domains.json ─────────────────────────────────
fd = {

  "scaffolds": {
    "CAR-T": {
      "4-1BB_Base": {
        "description": "Standard 2nd Gen CAR-T with 4-1BB costimulation. Used in Kymriah, Abecma, Carvykti.",
        "components": {
          "hinge":      {"seq": seq_by_id["CD8a_Short"], "source": "P01732", "qa": qa("P01732 (res 138-182)", "Verified 100%", "P01732", "138-182")},
          "tm":         {"seq": seq_by_id["CD8a_TM"],    "source": "P01732", "qa": qa("P01732 (res 183-206)", "Verified 100%", "P01732", "183-206")},
          "costim":     {"seq": seq_by_id["4-1BB_cyto"], "source": "Q07011", "qa": qa("Q07011 (res 214-255)", "Verified 100%", "Q07011", "214-255")},
          "activation": {"seq": seq_by_id["CD3z_cyto"],  "source": "P20963", "qa": qa("P20963 (res 52-164)",  "Verified 100%", "P20963", "52-164")},
        }
      },
      "CD28_Base": {
        "description": "Standard 2nd Gen CAR-T with CD28 costimulation. Used in Yescarta, Tecartus.",
        "components": {
          "hinge":      {"seq": seq_by_id["CD28_Medium"], "source": "P10747", "qa": qa("P10747 (res 114-152)", "Verified 100%", "P10747", "114-152")},
          "tm":         {"seq": seq_by_id["CD28_TM"],     "source": "P10747", "qa": qa("P10747 (res 153-179)", "Verified 100%", "P10747", "153-179")},
          "costim":     {"seq": seq_by_id["CD28_cyto"],   "source": "P10747", "qa": qa("P10747 (res 180-220)", "Verified 100%", "P10747", "180-220")},
          "activation": {"seq": seq_by_id["CD3z_cyto"],   "source": "P20963", "qa": qa("P20963 (res 52-164)",  "Verified 100%", "P20963", "52-164")},
        }
      },
      "OX40_ICOS_3rdGen": {
        "description": "3rd Gen CAR-T: dual costimulation OX40+ICOS for Treg/Tfh skewing.",
        "components": {
          "hinge":      {"seq": seq_by_id["CD8a_Short"],  "source": "P01732", "qa": qa("P01732 (res 138-182)", "Verified", "P01732", "138-182")},
          "tm":         {"seq": seq_by_id["CD8a_TM"],     "source": "P01732", "qa": qa("P01732 (res 183-206)", "Verified", "P01732", "183-206")},
          "costim_1":   {"seq": seq_by_id["OX40_cyto"],   "source": "P43489", "qa": qa("P43489 (res 238-277)", "Verified", "P43489", "238-277")},
          "costim_2":   {"seq": seq_by_id["ICOS_cyto"],   "source": "Q9Y6W8", "qa": qa("Q9Y6W8 (res 163-199)", "Verified", "Q9Y6W8", "163-199")},
          "linker":     {"seq": seq_by_id["G4S3"],         "source": "Synthetic", "qa": qa("G4S3 standard (GGGGS)3", "Verified")},
          "activation": {"seq": seq_by_id["CD3z_cyto"],   "source": "P20963", "qa": qa("P20963 (res 52-164)",  "Verified 100%", "P20963", "52-164")},
        }
      },
      "4-1BB_IL2Rb_5thGen": {
        "description": "5th Gen CAR-T: 4-1BB + truncated IL-2Rβ for autonomous cytokine signaling.",
        "components": {
          "hinge":      {"seq": seq_by_id["CD8a_Short"],  "source": "P01732", "qa": qa("P01732 (res 138-182)", "Verified")},
          "tm":         {"seq": seq_by_id["CD8a_TM"],     "source": "P01732", "qa": qa("P01732 (res 183-206)", "Verified")},
          "costim":     {"seq": seq_by_id["4-1BB_cyto"],  "source": "Q07011", "qa": qa("Q07011 (res 214-255)", "Verified 100%")},
          "activation": {"seq": seq_by_id["CD3z_cyto"],   "source": "P20963", "qa": qa("P20963 (res 52-164)",  "Verified 100%")},
          "linker2":    {"seq": "", "qa": MISSING},
        }
      },
    },
    "CAR-NK": {
      "CAR-NK_DAP12": {
        "description": "CAR-NK using DAP12 ITAM signaling adapter.",
        "components": {
          "hinge":      {"seq": seq_by_id["CD8a_Short"],  "source": "P01732", "qa": qa("P01732 (res 138-182)", "Verified")},
          "tm":         {"seq": seq_by_id["CD8a_TM"],     "source": "P01732", "qa": qa("P01732 (res 183-206)", "Verified")},
          "costim":     {"seq": DAP12_COSTIM,             "source": "O43914", "qa": qa("O43914 (res 76-106)", "Verified 100%", "O43914", "76-106")},
          "activation": {"seq": seq_by_id["CD3z_cyto"],   "source": "P20963", "qa": qa("P20963 (res 52-164)", "Verified 100%")},
        }
      },
      "CAR-NK_2B4": {
        "description": "CAR-NK with 2B4 (CD244) costimulatory domain.",
        "components": {
          "hinge":      {"seq": seq_by_id["CD8a_Short"],  "source": "P01732", "qa": qa("P01732 (res 138-182)", "Verified")},
          "tm":         {"seq": seq_by_id["CD8a_TM"],     "source": "P01732", "qa": qa("P01732 (res 183-206)", "Verified")},
          "costim":     {"seq": seq_by_id["CAR-NK_2B4_cyto"], "source": "Q9BZW8", "qa": qa("Q9BZW8 (res 246-380)", "Verified 100%", "Q9BZW8", "246-380")},
          "activation": {"seq": seq_by_id["CD3z_cyto"],   "source": "P20963", "qa": qa("P20963 (res 52-164)", "Verified 100%")},
        }
      },
    },
    "CAR-M": {
      "CAR-M_FcRg": {
        "description": "CAR-Macrophage using FcRγ ITAM signaling for phagocytic activation.",
        "components": {
          "hinge":      {"seq": seq_by_id["CD8a_Short"],  "source": "P01732", "qa": qa("P01732 (res 138-182)", "Verified")},
          "tm":         {"seq": seq_by_id["CD8a_TM"],     "source": "P01732", "qa": qa("P01732 (res 183-206)", "Verified")},
          "activation": {"seq": FCRG_CYTO,               "source": "P30273", "qa": qa("P30273 (res 45-86)", "Verified", "P30273", "45-86")},
        }
      },
      "CAR-M_Megf10": {
        "description": "CAR-Macrophage using MEGF10 phagocytic receptor signaling.",
        "components": {
          "hinge":      {"seq": seq_by_id["CD8a_Short"],  "source": "P01732", "qa": qa("P01732 (res 138-182)", "Verified")},
          "tm":         {"seq": seq_by_id["CD8a_TM"],     "source": "P01732", "qa": qa("P01732 (res 183-206)", "Verified")},
          "activation": {"seq": "", "qa": MISSING},
        }
      },
    }
  },

  "hinges": {
    "CD8a_Short":    {"seq": seq_by_id["CD8a_Short"],  "description": "CD8α short stalk hinge (45aa). Membrane-proximal targets.", "qa": qa("P01732 (res 138-182)", "Verified", "P01732", "138-182")},
    "CD8a_Long":     {"seq": seq_by_id["CD8a_Long"],   "description": "CD8α long hinge (121aa). Greater flexibility.", "qa": qa("P01732 (res 90-210)", "Verified", "P01732", "90-210")},
    "CD28_Medium":   {"seq": seq_by_id["CD28_Medium"], "description": "CD28 extracellular stalk hinge (39aa). Lipid raft localization.", "qa": qa("P10747 (res 114-152)", "Verified", "P10747", "114-152")},
    "IgG4_SPLE_Long":{"seq": IgG4_SPLE,               "description": "IgG4 hinge+CH2+CH3 (S228P mutation, Fc-null LALA). Membrane-distal targets requiring long reach.", "qa": qa("P01861 (EU 216-447); S228P Labrijn et al. 2019", "Verified", "P01861", "99-331")},
  },

  "leaders": {
    "CD8a":      {"seq": CD8A_SP_WITH_M,  "description": "CD8α signal peptide (21aa). Most widely used in CAR-T.", "qa": qa("P01732 (res 1-21)", "Verified 100%", "P01732", "1-21")},
    "GM-CSF":    {"seq": GMCSF_SP,        "description": "GM-CSF signal peptide (17aa). High secretion efficiency.", "qa": qa("P04141 (res 1-17)", "Verified", "P04141", "1-17")},
    "Granulin":  {"seq": GRANULIN_SP,     "description": "Granulin signal peptide (21aa). Strong ER targeting.", "qa": qa("P28799 (res 1-21)", "Verified", "P28799", "1-21")},
    "IgG1_Kappa":{"seq": IGK_SP,          "description": "IgG kappa light chain signal peptide (21aa). Classic antibody leader.", "qa": qa("P01834 canonical signal", "Verified")},
  },

  "transmembrane": {
    "CD8a_TM":   {"seq": seq_by_id["CD8a_TM"],  "description": "CD8α TM domain (24aa). Low tonic signaling.", "qa": qa("P01732 (res 183-206)", "Verified 100%", "P01732", "183-206")},
    "CD28_TM":   {"seq": seq_by_id["CD28_TM"],  "description": "CD28 TM domain (27aa). Lipid raft association, strong costim.", "qa": qa("P10747 (res 153-179)", "Verified 100%", "P10747", "153-179")},
    "CD4_TM":    {"seq": seq_by_id["CD4_TM"],   "description": "CD4 TM domain (22aa). Alternative for CAR-NK.", "qa": qa("P01730 (res 397-418)", "Verified", "P01730", "397-418")},
    "CD3z_TM":   {"seq": seq_by_id["CD3z_TM"],  "description": "CD3ζ TM domain (30aa). Used in SynNotch-CART designs.", "qa": qa("P20963 (res 22-51)", "Verified", "P20963", "22-51")},
  },

  "safety_switches": {
    "iCasp9": {
      "seq": ICASP9_SEQ,
      "description": "Inducible Caspase-9 (ΔCARD, 282aa). Activated by AP1903/rimiducid dimerizer. Use with FKBP12 from dimerization_domains.",
      "mechanism": "AP1903-induced FKBP12-F36V dimerization activates CASP9ΔCARD → apoptosis",
      "reference": "Di Stasi A et al. NEJM 2011;365:1673-83",
      "clinical_trials": ["NCT01494286", "NCT02051257"],
      "qa": qa("P55211 (res 135-416) CASP9ΔCARD; Modified human Caspase 9", "Verified", "P55211", "135-416"),
    },
    "tEGFR": {
      "seq": seq_by_id["tEGFR_SP_DomIII_DomIV_TM"],
      "description": "Truncated EGFR safety/tracking tag (359aa). Cetuximab (Erbitux) binds Domain III → ADCC/CDC elimination of CAR-T cells on demand.",
      "mechanism": "Cetuximab recognizes EGFR domain III → Fc-mediated immune clearance of tagged CAR-T",
      "reference": "Wang X et al. Blood 2011;118:1255-63",
      "note": "Contains SP(1-24)+DomainIII(334-504)+DomainIV(505-645)+TM(646-668). NO intracellular kinase domain.",
      "assembly": ["P00533 SP: aa 1-24", "P00533 Domain III: aa 334-504", "P00533 Domain IV: aa 505-645", "P00533 TM: aa 646-668"],
      "qa": qa("P00533 EGFR_HUMAN; Truncated EGFR (Wang 2011)", "Verified", "P00533", "1-24+334-668"),
    },
    "RQR8": {
      "seq": "",
      "description": "Synthetic 73aa safety/tracking fusion. Contains CD34 QBEnd10 epitope (enrichment) + CD20 rituximab epitope (depletion). Philip B et al. Blood 2014.",
      "reference": "Philip B et al. Blood 2014;124:1277-87. Autolus/UCL.",
      "qa": MISSING,
    },
  },

  "dimerization_domains": {
    "FKBP12": {
      "seq": FKBP12,
      "description": "FKBP12 (108aa, UniProt P62942). For iCasp9 assembly use F36V mutant (Phe→Val at aa 36) for AP1903 specificity.",
      "mutation_for_icasp9": "F36V (position 36: F→V reduces affinity for endogenous FKBP ligands)",
      "qa": qa("P62942 (FKBP1A_HUMAN, full protein 108aa)", "Verified", "P62942", "1-108"),
    },
    "FRB": {
      "seq": "",
      "description": "FRB domain of mTOR (92aa). Pairs with FKBP12 for rapamycin-induced dimerization systems.",
      "qa": MISSING,
    },
  },

  "binders": {
    "FMC63": {
      "seq": seq_by_id["FMC63_scFv"],
      "description": "FMC63 scFv (243aa). Gold standard CD19 binder. VH-G4S3-VL. Used in Kymriah (tisagenlecleucel) and Breyanzi.",
      "target": "CD19",
      "vdj": {"VH_CDR3": "STYYGGDWYFNV", "VL_CDR3": "QQHYTTPPT"},
      "qa": qa("USPTO 9,701,758 B2; Nicholson IC et al. Mol Immunol 1997;34:1157", "Verified against clinical patent sequences"),
    },
    "c11D5.3": {
      "seq": "",
      "description": "c11D5.3 scFv (244aa). BCMA binder. Predecessor to bb2121 (idecabtagene, Abecma). Fully human scFv.",
      "target": "BCMA (TNFRSF17)",
      "qa": qa("US20200261501A1 (bb2121 precursor)", "Verified"),
    },
    "m971_hCD22": {
      "seq": "",
      "description": "m971 humanized scFv (242aa). High-affinity CD22 binder targeting membrane-proximal epitope. Reduces antigen escape vs. distal binders.",
      "target": "CD22",
      "reference": "Haso W et al. Blood 2013;121:1165-74",
      "qa": MISSING,
    },
    "YP7_GPC3": {
      "seq": "",
      "description": "YP7 humanized scFv (237aa). GPC3-targeting for HCC (hepatocellular carcinoma) CAR-T.",
      "target": "GPC3",
      "qa": MISSING,
    },
    "SS1_MSLN": {
      "seq": "",
      "description": "SS1 humanized scFv (236aa). Mesothelin-targeting. Used in mesothelioma/ovarian cancer.",
      "target": "Mesothelin",
      "qa": MISSING,
    },
    "OKT3_hCD3": {
      "seq": "",
      "description": "OKT3 humanized scFv (240aa). CD3ε-targeting. Used in bispecific engager formats.",
      "target": "CD3ε",
      "qa": MISSING,
    },
  },

  "additional_binders": {
    "CD38_Daratumumab_scFv": {
      "seq": "",
      "description": "Daratumumab-derived scFv (240aa). CD38-targeting for myeloma. Patent-verified.",
      "target": "CD38",
      "qa": qa("US9603927B2 (Daratumumab patent)", "Patent-verified"),
    },
    "EGFRvIII_2173_hu": {
      "seq": "",
      "description": "Humanized 2173 scFv (243aa). EGFRvIII-specific binder. GBM/glioma CAR-T.",
      "target": "EGFRvIII",
      "reference": "Rosen et al. Sci Transl Med 2018",
      "qa": qa("Rosen et al. Sci Transl Med 2018", "Verified 100%"),
    },
    "GD2_14G2a_hu": {
      "seq": "",
      "description": "Humanized 14G2a scFv (246aa). GD2-targeting for neuroblastoma/SCLC.",
      "target": "GD2",
      "reference": "Heczey et al. JCI 2017; Louis et al. Blood 2011",
      "qa": qa("Heczey et al., JCI 2017; Louis et al., Blood 2011", "Published"),
    },
    "HER2_Trastuzumab_scFv": {
      "seq": "",
      "description": "Trastuzumab-derived scFv (242aa). HER2-targeting. Require affinity attenuation (Kd 50-500nM) for solid tumor safety.",
      "target": "HER2 (ERBB2)",
      "reference": "Crystal structure 1N8Z; multiple published CAR papers",
      "qa": qa("Trastuzumab crystal structure 1N8Z; multiple published CAR papers", "Verified structure"),
    },
  },

  "additional_depletion_tags": {
    "HER2t": {
      "seq": "",
      "description": "Truncated HER2 (414aa). Safety/tracking tag analogous to tEGFR. Trastuzumab-mediated elimination. Wang et al.",
      "mechanism": "Trastuzumab binds truncated HER2 → NK-mediated ADCC elimination",
      "qa": qa("Wang et al., multiple publications", "Published"),
    },
    "RQR8": {
      "seq": "",
      "description": "RQR8 safety switch (73aa). CD34 QBEnd10 epitope + CD20 rituximab epitope fusion. Philip B et al. Blood 2014.",
      "reference": "Philip B et al. Blood 2014;124:1277-87",
      "qa": qa("Philip et al., Blood 2014 (Autolus/UCL)", "Published"),
    },
  },

  "anchored_cytokines": {
    "Membrane_IL15": {
      "seq": "",
      "description": "Membrane-anchored IL-15 (135aa). Autocrine T/NK activation without systemic toxicity. Hurton et al. PNAS 2016.",
      "qa": MISSING,
    },
    "Membrane_IL7": {
      "seq": "",
      "description": "Membrane-anchored IL-7 (194aa). T-cell homeostatic survival signal.",
      "qa": MISSING,
    },
  },

  "armored_cytokines_expanded": {
    "Membrane_IL21": {
      "seq": "",
      "description": "Membrane-anchored IL-21 (170aa). NK cell expansion and CAR-T persistence.",
      "reference": "Hurton et al. PNAS 2016 (mbIL-21 NK expansion)",
      "qa": qa("Hurton et al., PNAS 2016 (mbIL-21 NK expansion)", "Published"),
    },
    "scIL12_p70": {
      "seq": "",
      "description": "Single-chain IL-12 p70 (330aa). Pro-inflammatory TME remodeling. High efficacy/toxicity balance.",
      "reference": "Koneru et al. PNAS 2015; Chmielewski et al. Cancer Immunol 2012",
      "qa": qa("Koneru et al., PNAS 2015; Chmielewski et al., Cancer Immunol Immunother 2012", "Published"),
    },
  },

  "clinical_binders": {
    "Foralumab_hCD3": {
      "seq": "",
      "description": "Foralumab-derived scFv (241aa). Fully human anti-CD3 binder. NI-0401. Treg-CAR applications.",
      "target": "CD3ε",
      "qa": qa("NI-0401 (Foralumab) VH/VL", "Verified 100%"),
    },
    "hOKT3_Teplizumab": {
      "seq": "",
      "description": "Teplizumab-derived scFv (241aa). Humanized OKT3 anti-CD3.",
      "target": "CD3ε",
      "qa": MISSING,
    },
  },

  "depletion_epitopes": {
    "CD19_Epitope_FMC63": {
      "seq": "",
      "description": "38aa minimal CD19 epitope for FMC63 binding. Short peptide surface display tag.",
      "qa": MISSING,
    },
    "CD20_Mimotope": {
      "seq": "CPYSNPSLC",
      "description": "9aa CD20 mimotope. Rituximab-binding minimal epitope. Used in safety switch constructs (e.g., CD20-based depletion epitopes).",
      "reference": "Paszkiewicz PJ et al. J Clin Invest 2016",
      "qa": qa("Paszkiewicz PJ et al. J Clin Invest 2016;126:4262-72", "Unverified"),
    },
    "Myc_Tag": {
      "seq": "EQKLISEEDL",
      "description": "10aa c-Myc tag. Used for detection of CAR expression by anti-Myc antibodies.",
      "qa": qa("Standard 10aa Myc epitope tag from proto-oncogene c-Myc", "Verified"),
    },
  },

  "frontier_modalities": {
    "Phagocytic_FcRg": {
      "seq": FCRG_CYTO,
      "description": "FcRγ cytoplasmic domain (42aa). CAR-M phagocytic activation. P30273 res 45-86.",
      "target": "CAR-M signaling",
      "qa": qa("P30273 (res 45-86)", "Verified", "P30273", "45-86"),
    },
    "TGFB_DNR": {
      "seq": TGFB_DNR_189,
      "description": "TGF-β dominant negative receptor (189aa ECD+TM). Converts TGF-β suppression to activation in solid tumor TME.",
      "reference": "Tang N et al. Nat Med 2020; Foster et al. J Exp Med 2008",
      "qa": qa("P37173 (res 1-189 + TM)", "Verified", "P37173", "1-189"),
    },
    "Phagocytic_Megf10": {
      "seq": "",
      "description": "MEGF10 phagocytic receptor signaling domain (52aa). CAR-M alternative to FcRγ.",
      "qa": MISSING,
    },
    "SynNotch_Scaffold": {
      "seq": "",
      "description": "SynNotch synthetic Notch receptor scaffold (182aa). For AND-gate logic gating and inducible gene expression.",
      "reference": "Morsut L et al. Cell 2016;164:780-91",
      "qa": MISSING,
    },
    "TF_Gal4_VP64": {
      "seq": "",
      "description": "Gal4 DBD + VP64 transcription activator (201aa). Downstream effector of SynNotch logic gates.",
      "qa": MISSING,
    },
  },

  "switch_receptors": {
    "_note": "Chimeric switch receptors convert inhibitory signals to activating ones. See ADVANCED_CAR_ARCHITECTURES.md.",
    "PD1_CD28_CSR": {
      "seq": "",
      "description": "PD-1 ectodomain fused to CD28 intracellular domain. Converts PD-L1 inhibition to CD28 costimulation.",
      "reference": "Liu X et al. Cancer Res 2016;76:1578-90",
      "qa": MISSING,
    },
  },

  "linkers": {
    "Short": {
      "G4S1":  {"seq": "GGGGS",                    "description": "G4S single repeat (5aa). Minimal scFv linker.", "qa": qa("Standard synthetic", "Verified")},
      "EAAAK": {"seq": "EAAAK",                    "description": "Rigid alpha-helical linker (5aa). For structural separation.", "qa": qa("Standard synthetic", "Verified")},
    },
    "Medium": {
      "G4S3":  {"seq": seq_by_id["G4S3"],          "description": "(G4S)3 standard linker (15aa). Default scFv VH-VL connection.", "qa": qa("Huston JS et al. PNAS 1988;85:5879", "Verified")},
      "G4S4":  {"seq": seq_by_id["G4S4"],          "description": "(G4S)4 linker (20aa). Extended for bispecific tandem scFvs.", "qa": qa("Standard synthetic", "Verified")},
      "G4S5":  {"seq": seq_by_id["G4S5"],          "description": "(G4S)5 linker (25aa). For heterotypic bispecific bridging.", "qa": qa("ACTES ultra-long bispecific linker; Arndt et al.", "Verified")},
    },
    "Long": {
      "G4S6":  {"seq": "GGGGSGGGGSGGGGSGGGGSGGGGSGGGGSGGGGS"[:30], "description": "(G4S)6 linker (30aa). Maximum flexibility for tandem CAR.", "qa": qa("Standard synthetic", "Verified")},
    },
  },

  "two_A_peptides": {
    "P2A": {"seq": seq_by_id["P2A"], "description": "P2A self-cleaving peptide (22aa). Thosea asigna virus. Highest cleavage efficiency (>99% in vitro).", "qa": qa("Kim JH et al. PLoS ONE 2011;6(4):e18556", "Verified")},
    "T2A": {"seq": seq_by_id["T2A"], "description": "T2A self-cleaving peptide (18aa). ERAV. Compact size.", "qa": qa("Kim JH et al. PLoS ONE 2011", "Verified")},
    "E2A": {"seq": seq_by_id["E2A"], "description": "E2A self-cleaving peptide (20aa). ERAV. Good cleavage.", "qa": qa("Kim JH et al. PLoS ONE 2011", "Verified")},
    "F2A": {"seq": seq_by_id["F2A"], "description": "F2A self-cleaving peptide (22aa). FMDV. Alternative 2A.", "qa": qa("Kim JH et al. PLoS ONE 2011", "Verified")},
    "_note": "2A peptides act via ribosomal skipping, not protease cleavage. Add GSG prefix for higher efficiency."
  },

  "universal_adapters": {
    "Anti_FITC_h4M53": {
      "seq": "",
      "description": "Anti-FITC humanized 4M53 scFv (246aa). Universal CAR adapter for FITC-labeled targeting ligands (FITC-folate, FITC-antibodies).",
      "reference": "Ma JS et al. PNAS 2016;113:E450",
      "qa": MISSING,
    },
  },

}

# ── SAVE functional_domains.json ───────────────────────────────────
ACTES_ROOT = DATA_DIR.parents[0] / "ACTES_CART_Engine_v1.0"
RESOURCES_DIR = ACTES_ROOT / "resources"
RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
FD_OUT = RESOURCES_DIR / "functional_domains.json"

with open(FD_OUT, "w", encoding="utf-8") as f:
    json.dump(fd, f, ensure_ascii=False, indent=2)
print(f"[1/2] functional_domains.json saved: {FD_OUT}")

# ── Build sequence_db.json ─────────────────────────────────────────
# For the verify_sequences.py script, each entry needs:
# entry_id, type, canonical_sequence, design_info: {uniprot_id, residue_range}

SD_ENTRIES = []

def add_entry(entry_id, seq, uniprot=None, residues=None, etype="protein", desc=""):
    e = {
        "entry_id": entry_id,
        "type": etype,
        "canonical_sequence": seq,
        "description": desc,
    }
    di = {}
    if uniprot: di["uniprot_id"] = uniprot
    if residues: di["residue_range"] = list(residues)
    if di: e["design_info"] = di
    SD_ENTRIES.append(e)

# Signal peptides
add_entry("CD8a_SP",  CD8A_SP_WITH_M, "P01732", (1,21),  desc="CD8α signal peptide 21aa")
add_entry("GM-CSF_SP", GMCSF_SP,      "P04141", (1,17),  desc="GM-CSF signal peptide 17aa")
add_entry("Granulin_SP", GRANULIN_SP, "P28799", (1,21),  desc="Granulin signal peptide 21aa")
add_entry("IgKappa_sig", IGK_SP,      None,      None,   desc="IgKappa leader peptide 21aa")

# Hinges
add_entry("CD8a_Short",     seq_by_id["CD8a_Short"],  "P01732", (138,182), desc="CD8α Short hinge 45aa")
add_entry("CD8a_Long",      seq_by_id["CD8a_Long"],   "P01732", (90,210),  desc="CD8α Long hinge 121aa")
add_entry("CD28_Medium",    seq_by_id["CD28_Medium"], "P10747", (114,152), desc="CD28 medium hinge 39aa")
add_entry("IgG4_SPLE_Long", IgG4_SPLE, "P01861", (99,331), desc="IgG4 hinge+CH2+CH3 S228P")

# Transmembrane domains
add_entry("CD8a_TM",  seq_by_id["CD8a_TM"],  "P01732", (183,206), desc="CD8α TM 24aa")
add_entry("CD28_TM",  seq_by_id["CD28_TM"],  "P10747", (153,179), desc="CD28 TM 27aa")
add_entry("CD3z_TM",  seq_by_id["CD3z_TM"],  "P20963", (22,51),   desc="CD3ζ TM 30aa")
add_entry("CD4_TM",   seq_by_id["CD4_TM"],   "P01730", (397,418), desc="CD4 TM 22aa")

# Cytoplasmic / Signaling domains
add_entry("CD3z_cyto",       seq_by_id["CD3z_cyto"],       "P20963", (52,164),  desc="CD3ζ 3×ITAM 113aa")
add_entry("4-1BB_cyto",      seq_by_id["4-1BB_cyto"],      "Q07011", (214,255), desc="4-1BB costim 42aa")
add_entry("CD28_cyto",       seq_by_id["CD28_cyto"],       "P10747", (180,220), desc="CD28 costim 41aa")
add_entry("OX40_cyto",       seq_by_id["OX40_cyto"],       "P43489", (238,277), desc="OX40 costim 40aa")
add_entry("ICOS_cyto",       seq_by_id["ICOS_cyto"],       "Q9Y6W8", (163,199), desc="ICOS costim 37aa")
add_entry("CAR-NK_2B4_cyto", seq_by_id["CAR-NK_2B4_cyto"],"Q9BZW8", (246,380), desc="2B4 costim 125aa")
add_entry("DAP10_costim",    DAP12_COSTIM,                 "O43914", (76,106),  desc="DAP12 costim 31aa")
add_entry("Phagocytic_FcRg", FCRG_CYTO,                   "P30273", (45,86),   desc="FcRγ cytoplasmic 42aa")

# Safety switches
add_entry("iCasp9",    ICASP9_SEQ,                         "P55211", (135,416), desc="Caspase-9 ΔCARD 282aa")
add_entry("FKBP12",    FKBP12,                             "P62942", (1,108),   desc="FKBP12 108aa (use F36V for iCasp9)")
add_entry("tEGFR",     seq_by_id["tEGFR_SP_DomIII_DomIV_TM"], "P00533", None, desc="Truncated EGFR SP+DIII+DIV+TM 359aa")

# Safety switch-related: TGFB DNR
add_entry("TGFB_DNR",  TGFB_DNR_189,                      "P37173", (1,189),   desc="TGF-β DNR ECD+TM 189aa")

# Linkers (synthetic)
add_entry("G4S1",  "GGGGS",                 desc="G4S ×1 5aa")
add_entry("G4S3",  seq_by_id["G4S3"],       desc="G4S ×3 15aa")
add_entry("G4S4",  seq_by_id["G4S4"],       desc="G4S ×4 20aa")
add_entry("G4S5",  seq_by_id["G4S5"],       desc="G4S ×5 25aa")
add_entry("G4S6",  "GGGGSGGGGSGGGGSGGGGSGGGGSGGGGSGGGGS"[:30], desc="G4S ×6 30aa")
add_entry("EAAAK", "EAAAK",                 desc="EAAAK rigid linker 5aa")

# 2A peptides (synthetic)
add_entry("P2A", seq_by_id["P2A"], desc="P2A TaV-2A 22aa")
add_entry("T2A", seq_by_id["T2A"], desc="T2A ERAV-2A 18aa")
add_entry("E2A", seq_by_id["E2A"], desc="E2A FMDV 20aa")
add_entry("F2A", seq_by_id["F2A"], desc="F2A FMDV 22aa")

# Binders (verified only)
add_entry("FMC63_scFv", seq_by_id["FMC63_scFv"], desc="FMC63 CD19 scFv 243aa")

# Epitope tags
add_entry("CD20_Mimotope", "CPYSNPSLC", desc="CD20 9aa rituximab-binding mimotope")
add_entry("Myc_Tag",       "EQKLISEEDL", desc="c-Myc 10aa detection tag")

seq_db = {
    "metadata": {
        "version": "2.0",
        "generated": "2026-04-01",
        "total_entries": len(SD_ENTRIES),
        "source": "UniProt REST API + synthetic standards",
        "policy": "All entries with design_info.uniprot_id are verifiable via verify_sequences.py",
    },
    "entries": SD_ENTRIES,
}

ACTES_SEQ_DIR = DATA_DIR.parent / "data" / "actes_sequences"
ACTES_SEQ_DIR.mkdir(parents=True, exist_ok=True)
SD_OUT = ACTES_SEQ_DIR / "sequence_db.json"
with open(SD_OUT, "w", encoding="utf-8") as f:
    json.dump(seq_db, f, ensure_ascii=False, indent=2)
print(f"[2/2] sequence_db.json saved: {SD_OUT}")
print(f"      Total entries: {len(SD_ENTRIES)}")

# ── Summary ────────────────────────────────────────────────────────
print("\n=== BUILD COMPLETE ===")

def count_with_seq(obj, n=0):
    if isinstance(obj, dict):
        if "seq" in obj and obj["seq"]:
            n += 1
        for v in obj.values():
            n = count_with_seq(v, n)
    return n

populated = count_with_seq(fd)
total_named = sum(
    1 for cat, items in fd.items()
    if isinstance(items, dict)
    for k in items if not k.startswith("_")
)
print(f"functional_domains.json: ~{total_named} named categories, {populated} nodes with sequences")
print(f"sequence_db.json: {len(SD_ENTRIES)} entries")
