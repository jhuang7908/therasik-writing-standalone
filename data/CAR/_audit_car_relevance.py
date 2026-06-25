"""
Audit: which elements are directly CAR-relevant vs generic biology
Rule: every element must have a defined structural/functional position in a CAR vector
"""
import json
from pathlib import Path

CAR_DIR = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\CAR")
with open(CAR_DIR / "CART_LIBRARY_V3.json", encoding="utf-8") as f:
    lib = json.load(f)
elements = lib["elements"]

# CAR construct position tags
CAR_POSITIONS = {
    "MUST": "Core CAR structural component (every CAR needs this class)",
    "COMMON": "Used in >50% of published CAR designs",
    "SPECIALIZED": "Used in specific CAR architectures (armored, allogeneic, logic-gated)",
    "MARGINAL": "Generic biology tool, weak CAR-specific relevance",
}

# Manual relevance assessment per element
RELEVANCE = {
    # BINDERS — all CAR-relevant ✓
    "FMC63_scFv": ("MUST", "Antigen-recognition domain, position 1 of CAR"),
    "SJ25C1_scFv": ("COMMON", "Alt CD19 binder, CAR position 1"),
    "c11D5_3_scFv": ("COMMON", "BCMA binder, position 1"),
    "JNJ68284528_VHH": ("COMMON", "BCMA VHH binder, Carvykti reference"),
    "Trastuzumab_scFv": ("COMMON", "HER2 binder, position 1"),
    "Daratumumab_scFv": ("COMMON", "CD38 binder, position 1"),
    "SS1_scFv": ("COMMON", "Mesothelin binder, position 1"),
    "14G2a_hu_scFv": ("COMMON", "GD2 binder, position 1"),
    "m971_scFv": ("COMMON", "CD22 binder, position 1"),
    "OKT3_hu_scFv": ("COMMON", "CD3 binder for TCR-mimic or UniCAR adapter"),
    "YP7_scFv": ("COMMON", "GPC3 binder for HCC CAR-T"),
    "NKG2D_Ligand_Binder": ("COMMON", "NKG2D ligand — NK-cell CAR recognition"),
    "APRIL_Ligand_Binder": ("COMMON", "BCMA+TACI dual targeting via natural ligand"),
    "ESK1_WT1_TCRmimic": ("SPECIALIZED", "TCR-mimic binder, AML WT1 pMHC targeting"),
    "MAGE-A4_TCRmimic": ("SPECIALIZED", "TCR-mimic binder, intracellular antigen"),
    "Anti_FRa_MOv19_scFv": ("COMMON", "FolRα binder, ovarian cancer CAR-T"),
    "Cetuximab_scFv": ("COMMON", "EGFR binder — also depletion tag use"),
    "Rituximab_scFv": ("COMMON", "CD20 binder / safety switch component"),
    "ch14_18_GD2_scFv": ("COMMON", "GD2 binder, alt to 14G2a"),
    "NKG2C_ECD_binder": ("SPECIALIZED", "CMV/HCMV-sensing NK binder"),
    "NKp46_ECD_binder": ("SPECIALIZED", "CAR-NK activating receptor binder"),
    "DNAM1_ECD_binder": ("SPECIALIZED", "CAR-NK activating receptor binder"),
    "Pertuzumab_scFv": ("COMMON", "HER2 domain II binder"),
    "HPSE_Armor": ("MARGINAL", "This is armored payload (enzyme), not a binder — recategorize"),
    "EGFRvIII_VHH": ("COMMON", "EGFRvIII VHH binder for GBM CAR-T"),
    "MICA_NKG2DL": ("SPECIALIZED", "NKG2D ligand decoy binder"),
    "J591_PSMA_scFv": ("COMMON", "PSMA binder for prostate CAR-T"),
    "CLDN18_2_scFv": ("COMMON", "CLDN18.2 VHH for gastric cancer"),
    "cAC10_CD30_scFv": ("COMMON", "CD30 binder, Hodgkin CAR-T"),
    "Dsg3_ECD_CAAR": ("SPECIALIZED", "CAAR binder, autoimmune pemphigus"),
    "MuSK_ECD_CAAR": ("SPECIALIZED", "CAAR binder, myasthenia gravis"),
    # HINGE — all MUST
    "CD8a_Short": ("MUST", "Hinge position, membrane-proximal epitopes"),
    "CD8a_Long": ("MUST", "Hinge position, membrane-distal epitopes"),
    "CD28_Medium": ("MUST", "Hinge position, medium distance"),
    "IgG4_SPLE_Long": ("MUST", "Hinge position, long flexible, S228P Fc-null"),
    "IgD_Hinge": ("COMMON", "Hinge alternative, protease-resistant"),
    # TM — all MUST
    "CD8a_TM": ("MUST", "TM anchoring, low tonic signaling"),
    "CD28_TM": ("MUST", "TM anchoring, lipid raft, CD28 costim"),
    "CD4_TM": ("COMMON", "TM alternative"),
    "CD3z_TM": ("COMMON", "TM for CD3-based CAR-NK"),
    "NKG2D_TM": ("COMMON", "TM for NK-optimized CAR"),
    # COSTIMULATORY — all MUST/COMMON
    "4-1BB_cyto": ("MUST", "Costimulatory position, Kymriah/Abecma"),
    "CD28_cyto": ("MUST", "Costimulatory position, Yescarta/Tecartus"),
    "OX40_cyto": ("COMMON", "Costimulatory alternative, persistence"),
    "ICOS_cyto": ("COMMON", "Costimulatory, Treg/Th17 CAR"),
    "2B4_cyto": ("COMMON", "Costimulatory, CAR-NK optimization"),
    "DAP12_costim": ("COMMON", "Costimulatory, NK/Macrophage CAR"),
    "CD27_cyto": ("COMMON", "Costimulatory alternative"),
    "DAP10_costim_full": ("COMMON", "Costimulatory, CAR-NK"),
    # ACTIVATION — all MUST
    "CD3z_cyto": ("MUST", "Activation domain, all 6 FDA-approved CARs"),
    "FcRg_cyto": ("COMMON", "Activation, CAR-NK/CAR-M"),
    "CD3z_1XX": ("SPECIALIZED", "Calibrated 1-ITAM for tuned activation"),
    "IL2Rb_cyto_5thGen": ("SPECIALIZED", "5th gen CAR JAK-STAT integration"),
    "ZAP70_tandem_SH2": ("SPECIALIZED", "ZAP70 recruitment for alternative signaling"),
    # ARMORED PAYLOAD — all SPECIALIZED
    "TGFB_DNR": ("SPECIALIZED", "Anti-TGFβ armor, solid tumor CAR-T"),
    "Membrane_IL15": ("SPECIALIZED", "IL-15 armor, persistence/survival"),
    "Membrane_IL21": ("SPECIALIZED", "IL-21 armor, NK/effector memory"),
    "Secreted_IL12": ("SPECIALIZED", "TRUCK IL-12 payload"),
    "4-1BBL_Anchored": ("SPECIALIZED", "Self-driving costim armor"),
    "GPX4_Enhanced": ("SPECIALIZED", "Anti-ferroptosis armor"),
    "OX40L_Anchored": ("SPECIALIZED", "OX40L costim armor"),
    "HPSE_Secreted": ("SPECIALIZED", "Matrix-degrading armor, solid tumor"),
    "IL7_CCL19_Armor": ("SPECIALIZED", "7×19 armor, T cell recruitment"),
    "ICOSL_Costim": ("SPECIALIZED", "ICOS ligand costim armor"),
    "mIL21_Armor": ("SPECIALIZED", "Membrane IL-21 armor"),
    # SAFETY SWITCH — all MUST/COMMON
    "tEGFR": ("MUST", "Safety switch, cetuximab elimination"),
    "iCasp9": ("COMMON", "Safety switch, AP1903 inducible"),
    "FKBP12": ("COMMON", "Safety switch component for iCasp9"),
    "RQR8": ("COMMON", "Dual safety+tracking switch"),
    "HSV-TK": ("COMMON", "Safety switch, ganciclovir"),
    # LOGIC GATES
    "PD1_CD28_CSR": ("SPECIALIZED", "Checkpoint reversal logic gate"),
    "CTLA4_CD28_CSR": ("SPECIALIZED", "Checkpoint reversal logic gate"),
    "iCAR_PSMA": ("SPECIALIZED", "NOT gate inhibitory CAR"),
    "SynNotch_NRR": ("SPECIALIZED", "AND gate, dual antigen SynNotch"),
    "Gal4_VP64_TF": ("SPECIALIZED", "Transcription factor for SynNotch output"),
    "TIM3_CD28_CSR": ("SPECIALIZED", "TIM3 checkpoint reversal"),
    "Notch1_TM_domain": ("SPECIALIZED", "SynNotch TM component"),
    "Notch1_RAM_domain": ("SPECIALIZED", "SynNotch RAM component"),
    "DNAM1_ECD_NK": ("SPECIALIZED", "CAR-NK activating receptor ECD"),
    # REGULATORY
    "EF1a_Promoter": ("MUST", "CAR transgene promoter, all clinical vectors"),
    "PGK_Promoter": ("COMMON", "CAR promoter alternative"),
    "MSCV_LTR": ("COMMON", "CAR promoter for stem-like T cells"),
    "SFFV_Promoter": ("COMMON", "Hematopoietic CAR promoter"),
    "EFS_Promoter": ("COMMON", "Compact EF1α for size-limited vectors"),
    "NFAT_RE_Promoter": ("SPECIALIZED", "Activation-inducible payload promoter"),
    "UCOE_EF1a": ("SPECIALIZED", "Anti-silencing for iPSC-CAR"),
    "Tet_On_System": ("SPECIALIZED", "Inducible CAR expression"),
    "EF1a_Short_EFS": ("COMMON", "212bp compact promoter"),
    "CMV_Enhancer": ("COMMON", "CMV enhancer for CAR vector"),
    "WPRE": ("MUST", "mRNA stability, all clinical vectors"),
    "BGH_polyA": ("MUST", "PolyA signal, all clinical vectors"),
    "SV40_polyA": ("COMMON", "Alt polyA signal"),
    # LEADERS/LINKERS
    "CD8a_SP": ("MUST", "Signal peptide for CAR surface expression"),
    "GM-CSF_SP": ("COMMON", "Alt signal peptide"),
    "Granulin_SP": ("COMMON", "Alt signal peptide, secreted armor"),
    "IgKappa_SP": ("COMMON", "Kappa light chain SP"),
    "IL2_SP": ("COMMON", "IL-2 SP for secreted payloads"),
    "G4S1": ("MUST", "Flexible linker for scFv VH-VL"),
    "G4S3": ("MUST", "Standard scFv linker (GGGGS×3)"),
    "G4S4": ("COMMON", "Longer scFv linker"),
    "G4S5": ("COMMON", "Long scFv linker"),
    "G4S6": ("MARGINAL", "Very long, rarely used in CAR scFv"),
    "EAAAK": ("COMMON", "Rigid linker alternative"),
    "EAAAK3": ("COMMON", "Rigid linker (×3 repeat)"),
    "Whitlow": ("COMMON", "Whitlow 218 linker for scFv"),
    "218": ("COMMON", "218 linker variant"),
    "218_linker": ("MARGINAL", "Duplicate of 218 entry"),
    "GGSG3": ("COMMON", "GGSG3 short flexible linker"),
    "GGS3": ("COMMON", "GGS3 short linker"),
    "XTEN_12": ("COMMON", "XTEN flexible linker"),
    "KFN_linker": ("SPECIALIZED", "Furin-P2A linker for polyprotein"),
    "GSG_prefix": ("MARGINAL", "3aa GSG prefix — not standalone component"),
    "P2A": ("COMMON", "Ribosomal skipping for bicistronic CAR"),
    "T2A": ("COMMON", "Ribosomal skipping variant"),
    "E2A": ("COMMON", "Ribosomal skipping variant"),
    "F2A": ("COMMON", "Ribosomal skipping variant"),
    # DEPLETION TAGS
    "tEGFR_DeplTag": ("MUST", "Safety/depletion tag"),
    "CD20_Mimotope": ("COMMON", "Rituximab-eliminatable tag"),
    "Myc_Tag": ("MARGINAL", "General lab tag — not CAR-specific"),
    "FLAG_Tag": ("MARGINAL", "General lab tag — not CAR-specific"),
    # ALLOGENEIC
    "TRAC_CRISPR_Target": ("SPECIALIZED", "KO target for allo-CAR (GvHD prevention)"),
    "B2M_CRISPR_Target": ("SPECIALIZED", "KO target for allo-CAR (rejection prevention)"),
    "HLA_G_NK_Shield": ("SPECIALIZED", "NK evasion for allo-CAR"),
    "PDL1_ECD_Shield": ("SPECIALIZED", "PD-L1 expression for allo-CAR immune evasion"),
    "CIITA_CRISPR_Target": ("SPECIALIZED", "HLA-II KO for allo-CAR"),
    "CD52_CRISPR_Target": ("SPECIALIZED", "Alemtuzumab resistance for allo-CAR"),
    "CD47_Stealth": ("SPECIALIZED", "Don't-eat-me signal for allo-CAR"),
    "HLA_G_Stealth": ("SPECIALIZED", "NK/CTL evasion for allo-CAR"),
    # CAAR/TREG
    "Dsg3_ECD_CAAR": ("SPECIALIZED", "Autoimmune CAAR binder"),
    "MuSK_ECD_CAAR": ("SPECIALIZED", "Autoimmune CAAR binder"),
    "FoxP3_TF": ("SPECIALIZED", "Treg CAR master TF"),
}

# Print audit
print(f"{'Relevance':<12} {'ID':<32} {'CAR Role'}")
print("="*80)
by_tier = {"MUST": [], "COMMON": [], "SPECIALIZED": [], "MARGINAL": []}
for eid, (tier, role) in RELEVANCE.items():
    by_tier[tier].append((eid, role))

for tier in ["MARGINAL"]:
    print(f"\n⚠ [{tier}] — Review for removal or recategorization:")
    for eid, role in by_tier[tier]:
        e = {e_["id"]: e_ for e_ in elements}.get(eid, {})
        print(f"  {eid:<32} {role}")

print(f"\n=== Summary ===")
for tier in ["MUST", "COMMON", "SPECIALIZED", "MARGINAL"]:
    print(f"  {tier:<12}: {len(by_tier[tier])} elements")
print(f"  Total audited: {len(RELEVANCE)}")
print(f"  Library total: {len(elements)}")
