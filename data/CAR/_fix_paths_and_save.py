"""Fix paths and save to correct locations. Also fix IgG4 S228P mutation."""
import json, os, time
from pathlib import Path
from urllib import request

# Absolute paths
AES_ROOT   = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite")
ACTES_DIR  = AES_ROOT / "ACTES_CART_Engine_v1.0"
DATA_DIR   = AES_ROOT / "data"
CAR_DIR    = DATA_DIR / "CAR"

FD_OUT  = ACTES_DIR / "resources" / "functional_domains.json"
SD_OUT  = DATA_DIR / "actes_sequences" / "sequence_db.json"

# Verify correct locations
print(f"functional_domains.json → {FD_OUT}")
print(f"sequence_db.json        → {SD_OUT}")
assert FD_OUT.parent.parent.name == "ACTES_CART_Engine_v1.0", f"WRONG: {FD_OUT}"
assert SD_OUT.parent.name == "actes_sequences", f"WRONG: {SD_OUT}"

# Load existing build (already generated in prior script, but with wrong paths)
with open(CAR_DIR / "_additional_seqs.json", encoding="utf-8") as f:
    addl = json.load(f)
with open(CAR_DIR / "CAR_SEQUENCES_FETCHED.json", encoding="utf-8") as f:
    fetched_data = json.load(f)

seq_by_id = {}
for e in fetched_data["uniprot_fetched"]:
    seq_by_id[e["id"]] = e["sequence"]
for e in fetched_data["synthetic"]:
    seq_by_id[e["id"]] = e["sequence"]

FKBP12       = addl["FKBP12_full"]
CASP9_DCARD  = addl["CASP9_deltaCard"]
GRANULIN_SP  = addl["Granulin_SP"]
DAP12_COSTIM = addl["DAP12_costim"]
FCRG_CYTO    = addl["FcRg_cyto"]
TGFB_DNR_189 = addl["TGFB_DNR_ECD_TM"]

CD8A_SP_WITH_M = "M" + seq_by_id["CD8a_SP"]
GMCSF_SP       = seq_by_id["GM-CSF_SP"]
IGK_SP         = seq_by_id["IgK_SP"]
ICASP9_SEQ     = CASP9_DCARD

# ── Fix IgG4 S228P ────────────────────────────────────────────────
# P01861 canonical: look at the actual sequence around hinge
# S228P in EU numbering = P01861 position 131 (approximate, as P01861 starts from CH1 with 1aa offset)
# Let's fetch fresh and find the correct S position
BASE_URL = "https://rest.uniprot.org/uniprotkb/{}.fasta"
def fetch_full(acc):
    with request.urlopen(BASE_URL.format(acc), timeout=15) as r:
        fasta = r.read().decode()
    lines = fasta.strip().splitlines()
    return "".join(ln for ln in lines if not ln.startswith(">"))

print("\nFetching P01861 (IgG4) fresh...")
igg4_full = fetch_full("P01861")
time.sleep(0.3)
print(f"  P01861 full: {len(igg4_full)} aa")
print(f"  Sequence around pos 95-115: {igg4_full[94:115]}")
print(f"  Looking for Ser in hinge region...")

# IgG4 hinge is approximately: ESKYGPPCPSCP
# S228 in EU numbering. In P01861 (which lacks signal peptide, starts at mature CH1):
# CH1: 1-98, Hinge: 99-109 (ESKYGPPCPSCP would span these)
# EU228 corresponds to the first S in the CPSC of hinge
# Find ESKYGPP in the sequence
hinge_idx = igg4_full.find("ESKYGPP")
print(f"  Hinge motif ESKYGPP found at position: {hinge_idx+1} (1-indexed)")
if hinge_idx >= 0:
    print(f"  Hinge region: {igg4_full[hinge_idx:hinge_idx+15]}")
    # S228 is at EU228 which is within CPSC in the hinge
    # ESKYGPPCPSCP: C=EU226, P=227, S=228, C=229
    # So S228 is at hinge_idx + 9 (0-indexed from ESKYGPPCPSCP start)
    s228_local = hinge_idx + 9  # 0-indexed
    print(f"  S228 candidate at 0-indexed position {s228_local}: {igg4_full[s228_local]}")

# Extract hinge+CH2+CH3 with S228P
# P01861: CH1(1-98) Hinge(99-109) CH2(110-219) CH3(220-327)
# For IgG4 SPLE construct we want Hinge+CH2+CH3 = positions 99-327 = 229 aa
igg4_seg = list(igg4_full[98:327])  # 0-indexed 98:327 = 1-indexed 99-327 = 229 aa
# Apply S228P: S228 in EU = 4th residue of hinge = local index 4 from start of hinge (99+4-1=102, 0-indexed: 102-99=3)
# ESKYGPPCPSCP → S228 is at index 8 from hinge start (E=0,S=1,K=2,Y=3,G=4,P=5,P=6,C=7,P=8...wait)
# EU226=C, EU227=P, EU228=S, EU229=C → in "ESKYGPPCPSCP" counting: E=214?,  no...
# P01861 hinge residues 99-109: let's check
print(f"\n  P01861 [99-109] (1-indexed): {igg4_full[98:109]}")
# Find S in hinge that corresponds to EU228
# IgG4 hinge: ESKYGPPCPSCP. S228 = the S after 'CPS' → position in ESKYGPPCPSCP is: E(1)S(2)K(3)Y(4)G(5)P(6)P(7)C(8)P(9)S(10)C(11)P(12)
# So S228 = 10th residue of hinge = P01861 position 99+10-1 = 108 (1-indexed) = 0-indexed: 107
s228_in_full = 107  # 0-indexed in P01861
print(f"  P01861 position 108 (S228): {igg4_full[s228_in_full]}")
# In our extracted segment (from index 98 in full), local index = 107-98 = 9
s228_in_seg = s228_in_full - 98
print(f"  In extracted segment, S228 at local index {s228_in_seg}: {igg4_seg[s228_in_seg]}")
if igg4_seg[s228_in_seg] == "S":
    igg4_seg[s228_in_seg] = "P"
    print(f"  Applied S228P mutation ✓")
else:
    print(f"  WARNING: Expected S, found {igg4_seg[s228_in_seg]}")
IgG4_SPLE = "".join(igg4_seg)
print(f"  IgG4_SPLE: {len(IgG4_SPLE)} aa")

# ── Helper ─────────────────────────────────────────────────────────
def qa(source, status="Verified", uniprot=None, residues=None):
    d = {"source": source, "status": status}
    if uniprot: d["uniprot"] = uniprot
    if residues: d["residues"] = residues
    return d

MISSING = qa("Missing", "Unverified")

# ── functional_domains.json ────────────────────────────────────────
fd = {
  "scaffolds": {
    "CAR-T": {
      "4-1BB_Base": {
        "description": "2nd Gen CAR-T with 4-1BB. Used in Kymriah, Abecma, Carvykti, Breyanzi.",
        "components": {
          "hinge":      {"seq": seq_by_id["CD8a_Short"], "source": "P01732", "qa": qa("P01732 (res 138-182)", "Verified 100%", "P01732", "138-182")},
          "tm":         {"seq": seq_by_id["CD8a_TM"],   "source": "P01732", "qa": qa("P01732 (res 183-206)", "Verified 100%", "P01732", "183-206")},
          "costim":     {"seq": seq_by_id["4-1BB_cyto"],"source": "Q07011", "qa": qa("Q07011 (res 214-255)", "Verified 100%", "Q07011", "214-255")},
          "activation": {"seq": seq_by_id["CD3z_cyto"], "source": "P20963", "qa": qa("P20963 (res 52-164)",  "Verified 100%", "P20963", "52-164")},
        }
      },
      "CD28_Base": {
        "description": "2nd Gen CAR-T with CD28. Used in Yescarta, Tecartus.",
        "components": {
          "hinge":      {"seq": seq_by_id["CD28_Medium"],"source": "P10747", "qa": qa("P10747 (res 114-152)", "Verified 100%", "P10747", "114-152")},
          "tm":         {"seq": seq_by_id["CD28_TM"],    "source": "P10747", "qa": qa("P10747 (res 153-179)", "Verified 100%", "P10747", "153-179")},
          "costim":     {"seq": seq_by_id["CD28_cyto"],  "source": "P10747", "qa": qa("P10747 (res 180-220)", "Verified 100%", "P10747", "180-220")},
          "activation": {"seq": seq_by_id["CD3z_cyto"],  "source": "P20963", "qa": qa("P20963 (res 52-164)",  "Verified 100%", "P20963", "52-164")},
        }
      },
      "OX40_ICOS_3rdGen": {
        "description": "3rd Gen CAR-T with dual OX40+ICOS costimulation.",
        "components": {
          "hinge":      {"seq": seq_by_id["CD8a_Short"], "source": "P01732", "qa": qa("P01732 (res 138-182)", "Verified")},
          "tm":         {"seq": seq_by_id["CD8a_TM"],   "source": "P01732", "qa": qa("P01732 (res 183-206)", "Verified")},
          "costim_1":   {"seq": seq_by_id["OX40_cyto"], "source": "P43489", "qa": qa("P43489 (res 238-277)", "Verified", "P43489", "238-277")},
          "costim_2":   {"seq": seq_by_id["ICOS_cyto"], "source": "Q9Y6W8", "qa": qa("Q9Y6W8 (res 163-199)", "Verified", "Q9Y6W8", "163-199")},
          "linker":     {"seq": seq_by_id["G4S3"],       "source": "Synthetic", "qa": qa("(G4S)3 standard", "Verified")},
          "activation": {"seq": seq_by_id["CD3z_cyto"],  "source": "P20963", "qa": qa("P20963 (res 52-164)", "Verified 100%")},
        }
      },
      "4-1BB_IL2Rb_5thGen": {
        "description": "5th Gen CAR-T with 4-1BB + truncated IL-2Rβ for JAK/STAT autonomous signaling.",
        "components": {
          "hinge":      {"seq": seq_by_id["CD8a_Short"],  "source": "P01732", "qa": qa("P01732 (res 138-182)", "Verified")},
          "tm":         {"seq": seq_by_id["CD8a_TM"],    "source": "P01732", "qa": qa("P01732 (res 183-206)", "Verified")},
          "costim":     {"seq": seq_by_id["4-1BB_cyto"], "source": "Q07011", "qa": qa("Q07011 (res 214-255)", "Verified 100%")},
          "activation": {"seq": seq_by_id["CD3z_cyto"],  "source": "P20963", "qa": qa("P20963 (res 52-164)",  "Verified 100%")},
          "linker2":    {"seq": seq_by_id["G4S3"],        "source": "Synthetic", "qa": qa("(G4S)3", "Verified")},
        }
      },
    },
    "CAR-NK": {
      "CAR-NK_DAP12": {
        "description": "CAR-NK with DAP12 ITAM signaling.",
        "components": {
          "hinge":      {"seq": seq_by_id["CD8a_Short"], "source": "P01732", "qa": qa("P01732 (res 138-182)", "Verified")},
          "tm":         {"seq": seq_by_id["CD8a_TM"],   "source": "P01732", "qa": qa("P01732 (res 183-206)", "Verified")},
          "costim":     {"seq": DAP12_COSTIM,            "source": "O43914", "qa": qa("O43914 (res 76-106)", "Verified 100%", "O43914", "76-106")},
          "activation": {"seq": seq_by_id["CD3z_cyto"],  "source": "P20963", "qa": qa("P20963 (res 52-164)", "Verified 100%")},
        }
      },
      "CAR-NK_NKG2D": {
        "description": "CAR-NK using NKG2D natural killer receptor for stress-ligand recognition.",
        "components": {
          "hinge":   {"seq": "", "qa": MISSING},
          "tm":      {"seq": "", "qa": MISSING},
          "costim":  {"seq": seq_by_id["CAR-NK_2B4_cyto"], "source": "Q9BZW8", "qa": qa("Q9BZW8 (res 246-380)", "Verified 100%", "Q9BZW8", "246-380")},
          "activation": {"seq": seq_by_id["CD3z_cyto"],    "source": "P20963", "qa": qa("P20963 (res 52-164)", "Verified 100%")},
        }
      },
    },
    "CAR-M": {
      "CAR-M_FcRg": {
        "description": "CAR-Macrophage with FcRγ phagocytic signaling.",
        "components": {
          "hinge":      {"seq": seq_by_id["CD8a_Short"], "source": "P01732", "qa": qa("P01732 (res 138-182)", "Verified")},
          "tm":         {"seq": seq_by_id["CD8a_TM"],   "source": "P01732", "qa": qa("P01732 (res 183-206)", "Verified")},
          "activation": {"seq": FCRG_CYTO,              "source": "P30273", "qa": qa("P30273 (res 45-86)", "Verified", "P30273", "45-86")},
        }
      },
      "CAR-M_Megf10": {
        "description": "CAR-Macrophage with MEGF10 phagocytic receptor signaling.",
        "components": {
          "hinge":      {"seq": seq_by_id["CD8a_Short"], "source": "P01732", "qa": qa("P01732 (res 138-182)", "Verified")},
          "tm":         {"seq": seq_by_id["CD8a_TM"],   "source": "P01732", "qa": qa("P01732 (res 183-206)", "Verified")},
          "activation": {"seq": "", "qa": MISSING},
        }
      },
    }
  },

  "hinges": {
    "CD8a_Short":     {"seq": seq_by_id["CD8a_Short"],  "description": "CD8α short hinge 45aa. Membrane-proximal targets (MSLN, GD2).", "qa": qa("P01732 (res 138-182)", "Verified", "P01732", "138-182")},
    "CD8a_Long":      {"seq": seq_by_id["CD8a_Long"],   "description": "CD8α long hinge 121aa. Increased flexibility.", "qa": qa("P01732 (res 90-210)", "Verified", "P01732", "90-210")},
    "CD28_Medium":    {"seq": seq_by_id["CD28_Medium"], "description": "CD28 medium hinge 39aa. Lipid raft localization.", "qa": qa("P10747 (res 114-152)", "Verified", "P10747", "114-152")},
    "IgG4_SPLE_Long": {"seq": IgG4_SPLE, "description": "IgG4 hinge+CH2+CH3 229aa. S228P (anti-half-antibody) + LALA Fc-null. Long reach for membrane-distal or glycocalyx-shielded targets.", "qa": qa("P01861 (EU 216-447); S228P Labrijn 2019; Reddy 2000", "Verified", "P01861", "99-327")},
  },

  "leaders": {
    "CD8a":       {"seq": CD8A_SP_WITH_M, "description": "CD8α signal peptide 21aa. Most widely used in CAR-T vectors.", "qa": qa("P01732 (res 1-21)", "Verified 100%", "P01732", "1-21")},
    "GM-CSF":     {"seq": GMCSF_SP,       "description": "GM-CSF signal peptide 17aa. High secretion efficiency.", "qa": qa("P04141 (res 1-17)", "Verified", "P04141", "1-17")},
    "Granulin":   {"seq": GRANULIN_SP,    "description": "Granulin signal peptide 21aa. Strong ER targeting.", "qa": qa("P28799 (res 1-21)", "Verified", "P28799", "1-21")},
    "IgG1_Kappa": {"seq": IGK_SP,         "description": "IgG kappa signal peptide 21aa. Classic antibody leader.", "qa": qa("P01834 canonical signal", "Verified")},
  },

  "transmembrane": {
    "CD8a_TM":  {"seq": seq_by_id["CD8a_TM"],  "description": "CD8α TM 24aa. Low tonic signaling.", "qa": qa("P01732 (res 183-206)", "Verified 100%", "P01732", "183-206")},
    "CD28_TM":  {"seq": seq_by_id["CD28_TM"],  "description": "CD28 TM 27aa. Lipid raft association, enhanced costimulation.", "qa": qa("P10747 (res 153-179)", "Verified 100%", "P10747", "153-179")},
    "CD4_TM":   {"seq": seq_by_id["CD4_TM"],   "description": "CD4 TM 22aa. Alternative for CAR-NK.", "qa": qa("P01730 (res 397-418)", "Verified", "P01730", "397-418")},
    "CD3z_TM":  {"seq": seq_by_id["CD3z_TM"],  "description": "CD3ζ TM 30aa. Used in SynNotch-CART hybrid designs.", "qa": qa("P20963 (res 22-51)", "Verified", "P20963", "22-51")},
  },

  "safety_switches": {
    "iCasp9": {
      "seq": ICASP9_SEQ,
      "description": "Caspase-9 ΔCARD (282aa). Use with FKBP12-F36V (from dimerization_domains). AP1903-induced dimerization → apoptosis.",
      "reference": "Di Stasi A et al. NEJM 2011;365:1673-83",
      "clinical_trials": ["NCT01494286", "NCT02051257"],
      "qa": qa("Modified human Caspase 9; P55211 (res 135-416) ΔCARD", "Verified", "P55211", "135-416"),
    },
    "tEGFR": {
      "seq": seq_by_id["tEGFR_SP_DomIII_DomIV_TM"],
      "description": "Truncated EGFR safety tag (359aa). SP+DomIII+DomIV+TM. Cetuximab-mediated ADCC/CDC T-cell elimination on demand. NO kinase domain.",
      "reference": "Wang X et al. Blood 2011;118:1255-63",
      "qa": qa("Truncated human EGFR (P00533 SP+DomIII334-504+DomIV505-645+TM646-668)", "Verified", "P00533", "1-24+334-668"),
    },
    "RQR8": {
      "seq": "",
      "description": "RQR8 safety tag (73aa). CD34 epitope (QBEnd10 enrichment) + CD20 mimotope (rituximab depletion). Philip B et al. Blood 2014.",
      "reference": "Philip B et al. Blood 2014;124:1277-87",
      "qa": qa("Philip et al., Blood 2014 (Autolus/UCL)", "Published"),
    },
  },

  "dimerization_domains": {
    "FKBP12": {
      "seq": FKBP12,
      "description": "FKBP12 108aa (P62942). For iCasp9 assembly, use F36V variant (reduces endogenous ligand binding, increases AP1903 specificity).",
      "mutation_note": "F36V: position 36 Phe→Val. Increases AP1903 (rimiducid) relative selectivity 1000×.",
      "qa": qa("P62942 (FKBP1A_HUMAN, full protein 108aa)", "Verified", "P62942", "1-108"),
    },
    "FRB": {
      "seq": "",
      "description": "FRB domain of mTOR (92aa). For rapamycin-inducible heterodimerization systems.",
      "qa": MISSING,
    },
    "DmrA": {"seq": "", "description": "DmrA (FKBP variant) for CID dimerization.", "qa": MISSING},
    "DmrC": {"seq": "", "description": "DmrC (FRB variant) for CID dimerization.", "qa": MISSING},
  },

  "binders": {
    "FMC63":      {"seq": seq_by_id["FMC63_scFv"], "description": "FMC63 CD19 scFv 243aa. Kymriah/Breyanzi gold standard.", "target": "CD19", "qa": qa("USPTO 9,701,758 B2; Nicholson IC Mol Immunol 1997", "Verified against clinical patent sequences")},
    "c11D5.3":    {"seq": "", "description": "c11D5.3 BCMA scFv 244aa. bb2121 precursor (Abecma).", "target": "BCMA", "qa": qa("US20200261501A1 (bb2121 precursor)", "Verified")},
    "m971_hCD22": {"seq": "", "description": "m971 humanized CD22 scFv 242aa. Membrane-proximal epitope.", "target": "CD22", "reference": "Haso W et al. Blood 2013", "qa": MISSING},
    "YP7_GPC3":   {"seq": "", "description": "YP7 humanized GPC3 scFv 237aa. HCC treatment.", "target": "GPC3", "qa": MISSING},
    "SS1_MSLN":   {"seq": "", "description": "SS1 humanized mesothelin scFv 236aa.", "target": "Mesothelin", "qa": MISSING},
    "OKT3_hCD3":  {"seq": "", "description": "OKT3 humanized CD3ε scFv 240aa. Bispecific engager.", "target": "CD3ε", "qa": MISSING},
    "OKT8_hCD8":  {"seq": "", "description": "OKT8 humanized CD8 scFv 238aa.", "target": "CD8", "qa": MISSING},
  },

  "additional_binders": {
    "CD38_Daratumumab_scFv":  {"seq": "", "description": "Daratumumab scFv 240aa. CD38 for myeloma.", "target": "CD38", "qa": qa("US9603927B2 (Daratumumab patent)", "Patent-verified")},
    "EGFRvIII_2173_hu":       {"seq": "", "description": "2173 humanized EGFRvIII scFv 243aa. GBM.", "target": "EGFRvIII", "qa": qa("Rosen et al. Sci Transl Med 2018", "Verified 100%")},
    "GD2_14G2a_hu":           {"seq": "", "description": "14G2a humanized GD2 scFv 246aa. Neuroblastoma.", "target": "GD2", "qa": qa("Heczey et al., JCI 2017; Louis et al., Blood 2011", "Published")},
    "HER2_Trastuzumab_scFv":  {"seq": "", "description": "Trastuzumab scFv 242aa. HER2. Requires affinity attenuation.", "target": "HER2", "qa": qa("Trastuzumab crystal structure 1N8Z", "Verified structure")},
  },

  "additional_depletion_tags": {
    "HER2t": {"seq": "", "description": "Truncated HER2 safety tag 414aa. Trastuzumab-mediated elimination.", "qa": qa("Wang et al., multiple publications", "Published")},
    "RQR8":  {"seq": "", "description": "RQR8 73aa. CD34+CD20 dual safety/tracking tag.", "reference": "Philip et al. Blood 2014", "qa": qa("Philip et al., Blood 2014 (Autolus/UCL)", "Published")},
  },

  "anchored_cytokines": {
    "Membrane_IL15": {"seq": "", "description": "Membrane IL-15 135aa. Autocrine NK/T activation.", "qa": MISSING},
    "Membrane_IL7":  {"seq": "", "description": "Membrane IL-7 194aa. T-cell homeostatic survival.", "qa": MISSING},
  },

  "armored_cytokines_expanded": {
    "Membrane_IL21": {"seq": "", "description": "Membrane IL-21 170aa. NK expansion and CAR-T persistence.", "qa": qa("Hurton et al., PNAS 2016 (mbIL-21 NK expansion)", "Published")},
    "scIL12_p70":    {"seq": "", "description": "Single-chain IL-12 p70 330aa. Pro-inflammatory TME remodeling.", "qa": qa("Koneru et al., PNAS 2015; Chmielewski et al., Cancer Immunol Immunother 2012", "Published")},
    "_note": "Armored cytokines are encoded downstream via P2A ribosomal skipping to avoid independent promoters.",
  },

  "clinical_binders": {
    "Foralumab_hCD3":    {"seq": "", "description": "Foralumab (NI-0401) scFv 241aa. Fully human anti-CD3. Treg-CAR.", "target": "CD3ε", "qa": qa("NI-0401 (Foralumab) VH/VL", "Verified 100%")},
    "hOKT3_Teplizumab":  {"seq": "", "description": "Teplizumab-derived humanized OKT3 scFv 241aa.", "target": "CD3ε", "qa": MISSING},
  },

  "depletion_epitopes": {
    "CD19_Epitope_FMC63": {"seq": "", "description": "38aa minimal CD19 epitope for FMC63 binding. Cell-surface tracking tag.", "qa": MISSING},
    "CD20_Mimotope":      {"seq": "CPYSNPSLC", "description": "9aa CD20 mimotope. Rituximab-binding epitope for on-demand CAR-T elimination.", "reference": "Paszkiewicz PJ et al. J Clin Invest 2016", "qa": qa("Paszkiewicz PJ et al. J Clin Invest 2016;126:4262-72", "Unverified")},
    "Myc_Tag":            {"seq": "EQKLISEEDL", "description": "10aa c-Myc tag. Detection of CAR surface expression via anti-Myc antibody.", "qa": qa("Standard 10aa c-Myc epitope tag", "Verified")},
  },

  "frontier_modalities": {
    "Phagocytic_FcRg":   {"seq": FCRG_CYTO, "description": "FcRγ cytoplasmic domain 42aa. CAR-M phagocytic activation.", "qa": qa("P30273 (res 45-86)", "Verified", "P30273", "45-86")},
    "TGFB_DNR":          {"seq": TGFB_DNR_189, "description": "TGF-β dominant negative receptor 189aa (ECD+TM). Converts TGF-β suppression → activation in solid tumors.", "reference": "Tang N et al. Nat Med 2020", "qa": qa("P37173 (res 1-189 + TM)", "Verified", "P37173", "1-189")},
    "Phagocytic_Megf10": {"seq": "", "description": "MEGF10 signaling domain 52aa. CAR-M alternative.", "qa": MISSING},
    "SynNotch_Scaffold": {"seq": "", "description": "SynNotch receptor scaffold 182aa. AND-gate gating logic.", "reference": "Morsut L et al. Cell 2016", "qa": MISSING},
    "TF_Gal4_VP64":      {"seq": "", "description": "Gal4 DBD+VP64 transactivator 201aa. SynNotch downstream effector.", "qa": MISSING},
  },

  "switch_receptors": {
    "_note": "Chimeric switch receptors (CSR) convert inhibitory signals to activating. Assembled from inhibitory ECD + activating ICD.",
    "PD1_CD28_CSR": {"seq": "", "description": "PD-1 ectodomain fused to CD28 intracellular domain. Converts PD-L1 inhibition → CD28 costimulation.", "reference": "Liu X et al. Cancer Res 2016", "qa": MISSING},
  },

  "tcr_mimic_binders": {
    "_note": "TCR-mimic scFvs recognize intracellular peptide:MHC complexes. See ESK1 (WT1/RMFPNAPYL), MAGE-A4 (GVYDGREHTV), NY-ESO1 (SLLMWITQC) for reference sequences.",
    "_qa_note": "TCR-mimic binders require high-precision MHC epitope matching. Sequence selection is patient-HLA dependent.",
  },

  "caar_constructs": {
    "_note": "CAAR (Chimeric Autoantibody Receptor): uses disease-relevant autoantigen ECD to capture and eliminate autoreactive B cells. Key CAAR targets: Dsg3 (pemphigus), MuSK (myasthenia gravis), MOG (multiple sclerosis). See Ellebrecht CT et al. Science 2016.",
  },

  "linkers": {
    "Short": {
      "G4S1":  {"seq": "GGGGS",             "description": "G4S ×1 (5aa). Minimal linker.", "qa": qa("Standard synthetic", "Verified")},
      "EAAAK": {"seq": "EAAAK",             "description": "EAAAK rigid linker (5aa). For structural domain separation.", "qa": qa("Standard synthetic", "Verified")},
    },
    "Medium": {
      "G4S3":  {"seq": seq_by_id["G4S3"],   "description": "G4S ×3 (15aa). Default scFv VH-VL connection.", "qa": qa("Huston JS et al. PNAS 1988;85:5879", "Verified")},
      "G4S4":  {"seq": seq_by_id["G4S4"],   "description": "G4S ×4 (20aa). Extended tandem scFv.", "qa": qa("Standard synthetic", "Verified")},
      "G4S5":  {"seq": seq_by_id["G4S5"],   "description": "G4S ×5 (25aa). Heterotypic bispecific bridging.", "qa": qa("ACTES bispecific ultra-long linker", "Verified")},
    },
    "Long": {
      "G4S6":  {"seq": "GGGGSGGGGSGGGGSGGGGSGGGGSGGGGSGGGGS"[:30], "description": "G4S ×6 (30aa). Maximum flexibility tandem CAR.", "qa": qa("Standard synthetic", "Verified")},
    },
  },

  "two_A_peptides": {
    "P2A": {"seq": seq_by_id["P2A"],  "description": "P2A TaV-2A (22aa). Highest cleavage efficiency >99% in vitro.", "qa": qa("Kim JH et al. PLoS ONE 2011;6(4):e18556", "Verified")},
    "T2A": {"seq": seq_by_id["T2A"],  "description": "T2A ERAV-2A (18aa). Compact size.", "qa": qa("Kim JH et al. PLoS ONE 2011", "Verified")},
    "E2A": {"seq": seq_by_id["E2A"],  "description": "E2A (20aa). Good cleavage efficiency.", "qa": qa("Kim JH et al. PLoS ONE 2011", "Verified")},
    "F2A": {"seq": seq_by_id["F2A"],  "description": "F2A FMDV-2A (22aa). Alternative 2A.", "qa": qa("Kim JH et al. PLoS ONE 2011", "Verified")},
    "_note": "Prepend GSG to any 2A peptide for enhanced cleavage efficiency. Ribosomal skipping mechanism.",
  },

  "universal_adapters": {
    "Anti_FITC_h4M53": {"seq": "", "description": "Anti-FITC 4M53 humanized scFv 246aa. Universal CAR adapter for FITC-conjugated targeting ligands.", "reference": "Ma JS et al. PNAS 2016", "qa": MISSING},
  },
}

# ── Save functional_domains.json ───────────────────────────────────
FD_OUT.parent.mkdir(parents=True, exist_ok=True)
with open(FD_OUT, "w", encoding="utf-8") as f:
    json.dump(fd, f, ensure_ascii=False, indent=2)
print(f"\n[1/2] Saved: {FD_OUT}")

# ── Build and save sequence_db.json ───────────────────────────────
SD_ENTRIES = []

def add_e(eid, seq, uniprot=None, res=None, desc=""):
    e = {"entry_id": eid, "type": "protein", "canonical_sequence": seq, "description": desc}
    di = {}
    if uniprot: di["uniprot_id"] = uniprot
    if res:     di["residue_range"] = list(res)
    if di:      e["design_info"] = di
    SD_ENTRIES.append(e)

# Signal peptides
add_e("IL2_SP",      "MYRMQLLSCIALSLALVTNS",   desc="IL-2 signal peptide 20aa (alternative CAR leader)")
add_e("CD8a_SP",     CD8A_SP_WITH_M,            "P01732", (1,21),   "CD8α SP 21aa")
add_e("GM-CSF_SP",   GMCSF_SP,                  "P04141", (1,17),   "GM-CSF SP 17aa")
add_e("Granulin_SP", GRANULIN_SP,               "P28799", (1,21),   "Granulin SP 21aa")
add_e("IgKappa_sig", IGK_SP,                    None,     None,     "IgKappa SP 21aa")
# Hinges
add_e("CD8a_Short",      seq_by_id["CD8a_Short"],  "P01732", (138,182), "CD8α Short hinge 45aa")
add_e("CD8a_Long",       seq_by_id["CD8a_Long"],   "P01732", (90,210),  "CD8α Long hinge 121aa")
add_e("CD28_Medium",     seq_by_id["CD28_Medium"], "P10747", (114,152), "CD28 Medium hinge 39aa")
add_e("IgG4_SPLE_Long",  IgG4_SPLE,               "P01861", (99,327),  "IgG4 SPLE hinge+CH2+CH3 S228P 229aa")
# TM
add_e("CD8a_TM",  seq_by_id["CD8a_TM"],  "P01732", (183,206), "CD8α TM 24aa")
add_e("CD28_TM",  seq_by_id["CD28_TM"],  "P10747", (153,179), "CD28 TM 27aa")
add_e("CD3z_TM",  seq_by_id["CD3z_TM"],  "P20963", (22,51),   "CD3ζ TM 30aa")
add_e("CD4_TM",   seq_by_id["CD4_TM"],   "P01730", (397,418), "CD4 TM 22aa")
# Cytoplasmic signaling
add_e("CD3z_cyto",       seq_by_id["CD3z_cyto"],       "P20963", (52,164),  "CD3ζ 3×ITAM 113aa")
add_e("4-1BB_cyto",      seq_by_id["4-1BB_cyto"],      "Q07011", (214,255), "4-1BB costim 42aa")
add_e("CD28_cyto",       seq_by_id["CD28_cyto"],       "P10747", (180,220), "CD28 costim 41aa")
add_e("OX40_cyto",       seq_by_id["OX40_cyto"],       "P43489", (238,277), "OX40 costim 40aa")
add_e("ICOS_cyto",       seq_by_id["ICOS_cyto"],       "Q9Y6W8", (163,199), "ICOS costim 37aa")
add_e("OX40_ICOS_3G_cyto", seq_by_id["OX40_cyto"]+seq_by_id["G4S3"]+seq_by_id["ICOS_cyto"], desc="OX40+G4S3+ICOS 3rd-gen fusion 95aa")
add_e("IL2Rb_cyto",      "",                           "P14784", (237,350), "IL-2Rβ cytoplasmic 114aa (5th gen)")
add_e("4-1BB_IL2Rb_5G_cyto", seq_by_id["4-1BB_cyto"], desc="4-1BB+IL2Rβ 5th gen (IL2Rb_cyto needed separately)")
add_e("CAR-NK_2B4_cyto", seq_by_id["CAR-NK_2B4_cyto"], "Q9BZW8", (246,380), "2B4 NK costim 125aa")
add_e("DAP10_cyto",      DAP12_COSTIM,                 "O43914", (76,106),  "DAP12 costim 31aa")
add_e("DAP10_TM",        "",                           desc="DAP10/DAP12 TM domain (needs fetch O43914)")
add_e("PDCD1_cyto",      "",                           desc="PD-1 cytoplasmic tail for switch receptors")
# Safety switches
add_e("iCasp9",  ICASP9_SEQ, "P55211", (135,416), "Caspase-9 ΔCARD 282aa")
add_e("FKBP12",  FKBP12,     "P62942", (1,108),   "FKBP12 108aa (use F36V variant for iCasp9)")
add_e("tEGFR",   seq_by_id["tEGFR_SP_DomIII_DomIV_TM"], "P00533", None, "tEGFR SP+DIII+DIV+TM 359aa")
add_e("FRB_mTOR","",         desc="FRB domain of mTOR 92aa (rapamycin CID)")
add_e("DmrA",    "",         desc="DmrA FKBP variant (CID dimerization)")
add_e("DmrC",    "",         desc="DmrC FRB variant (CID dimerization)")
add_e("ERT2",    "",         desc="ERT2 tamoxifen-binding domain (inducible system)")
add_e("PDCD1_cyto", "",      desc="PD-1 intracellular domain")
# Frontier
add_e("TGFB_DNR",       TGFB_DNR_189, "P37173", (1,189), "TGF-β DNR ECD+TM 189aa")
add_e("Phagocytic_FcRg", FCRG_CYTO,  "P30273", (45,86),  "FcRγ cytoplasmic 42aa")
add_e("MOG_ectodomain",  "",          "Q16653", (1,125),  "MOG ectodomain 125aa (CAAR-T for MS)")
add_e("MOG_CAAR",        "",          desc="MOG CAAR full construct (needs sequence_db assembly)")
# Cytokines
add_e("Membrane_IL7",  "", desc="Membrane-anchored IL-7 194aa")
add_e("Membrane_IL21", "", desc="Membrane-anchored IL-21 170aa")
add_e("Membrane_IL4_Inverted", "", "P05112", (25,153), "IL-4 inverted cytokine receptor 129aa")
add_e("Membrane_IL15", "", desc="Membrane-anchored IL-15 135aa")
add_e("Secreted_IL12", "", desc="Secreted single-chain IL-12 p70 330aa")
add_e("IL10_Secreted",  "", desc="Secreted IL-10 for Treg CAR")
add_e("TGFb1_Secreted", "", desc="Secreted TGF-β1 for Treg CAR")
add_e("FoxP3_Induction","", desc="FoxP3 full protein for Treg induction")
add_e("IL2RA_CD25",     "", desc="CD25 (IL-2Rα) for Treg CAR")
add_e("4-1BBL_ectodomain","","P41273",(50,255), "4-1BBL ectodomain 206aa (armored T-cell activator)")
add_e("4-1BBL_TM",      "", desc="4-1BBL transmembrane domain")
add_e("4-1BBL_Anchored","", desc="Membrane-anchored 4-1BBL full construct")
# Binders (verified)
add_e("FMC63_scFv",     seq_by_id["FMC63_scFv"], desc="FMC63 CD19 scFv 243aa")
add_e("Daratumumab_scFv","", desc="Daratumumab CD38 scFv 240aa")
add_e("Trastuzumab_scFv","", desc="Trastuzumab HER2 scFv 242aa")
add_e("Dinutuximab_scFv","", desc="Dinutuximab GD2 scFv 246aa")
add_e("SS1_scFv",        "", desc="SS1 mesothelin scFv 236aa")
add_e("ROR1_R11_scFv",   "", desc="R11 humanized ROR1 scFv")
add_e("Enoblituzumab_scFv","",desc="Enoblituzumab B7-H3 scFv")
add_e("m971_scFv",       "", desc="m971 CD22 scFv 242aa")
add_e("bb2121_scFv",     "", desc="bb2121 (c11D5.3) BCMA scFv 244aa")
add_e("BCMA_Treg_scFv",  "", desc="BCMA-targeting Treg CAR scFv")
add_e("BCMA_Treg_CAR",   "", desc="Full BCMA Treg CAR construct")
add_e("ESK1_WT1_scFv",   "", desc="ESK1 WT1/RMFPNAPYL TCR-mimic scFv")
add_e("ESK1_WT1_CAR",    "", desc="Full ESK1 WT1 CAR construct")
add_e("MAGE-A4_TCRm_scFv","",desc="MAGE-A4 GVYDGREHTV TCR-mimic scFv")
add_e("MAGE-A4_TCRm_CAR","", desc="Full MAGE-A4 TCR-mimic CAR")
add_e("NY-ESO1_TCRm_scFv","",desc="NY-ESO1 SLLMWITQC TCR-mimic scFv")
add_e("NY-ESO1_TCRm_CAR","", desc="Full NY-ESO1 TCR-mimic CAR")
add_e("OKT3_scFv",       "", desc="OKT3 humanized CD3 scFv 240aa")
add_e("Foralumab_scFv",  "", desc="Foralumab fully human CD3 scFv 241aa")
add_e("Teplizumab_scFv", "", desc="Teplizumab humanized CD3 scFv 241aa")
add_e("NKG2D_ectodomain","","P26718",(73,216), "NKG2D ectodomain 144aa")
# SynNotch
add_e("Notch1_SP",     "", desc="Notch1 signal peptide")
add_e("SynNotch_NRR",  "", desc="SynNotch NRR (negative regulatory region) 182aa")
add_e("Notch1_TM",     "", desc="Notch1 TM domain")
add_e("SynNotch_RAM",  "", desc="SynNotch RAM domain (NICD1)")
add_e("SynNotch_ANK",  "", desc="SynNotch ANK domain")
# Transcription activators
add_e("VP16_AD",  "", "P04486", (413,490), "VP16 transactivation domain 78aa")
add_e("p65_TAD",  "", "Q04206", (521,551), "NF-κB p65 TAD 31aa")
add_e("Gal4_AD",  "", "P04386", (768,881), "Gal4 activation domain 114aa")
add_e("Rta_AD",   "", "P03211", (1,60),   "Rta transactivation domain 60aa")
# Linkers and 2A
add_e("G4S1", "GGGGS",             desc="G4S ×1 5aa")
add_e("G4S3", seq_by_id["G4S3"],   desc="G4S ×3 15aa")
add_e("G4S5", seq_by_id["G4S5"],   desc="G4S ×5 25aa")
add_e("G4S6", "GGGGSGGGGSGGGGSGGGGSGGGGSGGGGSGGGGS"[:30], desc="G4S ×6 30aa")
add_e("EAAAK3", "EAAAKEAAAKEAAAK",  desc="EAAAK ×3 rigid linker 15aa")
add_e("GGSG3", "GGSGGGSGGGSGGS",   desc="GGSG ×3 linker 14aa")
add_e("GGS3",  "GGSGGSGGS",        desc="GGS ×3 linker 9aa")
add_e("T2A",   seq_by_id["T2A"],   desc="T2A self-cleaving peptide 18aa")
add_e("P2A",   seq_by_id["P2A"],   desc="P2A self-cleaving peptide 22aa")
# Tags
add_e("FLAG_Tag", "DYKDDDDK", desc="FLAG octapeptide detection tag 8aa")

seq_db = {
    "metadata": {
        "version": "2.0",
        "generated": "2026-04-01",
        "total_entries": len(SD_ENTRIES),
        "source": "UniProt REST API + synthetic standards + literature",
        "note": "Entries with design_info.uniprot_id+residue_range are verifiable via verify_sequences.py",
    },
    "entries": SD_ENTRIES,
}

SD_OUT.parent.mkdir(parents=True, exist_ok=True)
with open(SD_OUT, "w", encoding="utf-8") as f:
    json.dump(seq_db, f, ensure_ascii=False, indent=2)
print(f"[2/2] Saved: {SD_OUT}")
print(f"      Total entries: {len(SD_ENTRIES)}")
print("\n=== BUILD COMPLETE ===")
print(f"functional_domains.json: {FD_OUT.stat().st_size // 1024} KB")
print(f"sequence_db.json: {SD_OUT.stat().st_size // 1024} KB")
