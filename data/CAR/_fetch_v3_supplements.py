"""
Phase 2 supplement fetch for CART_LIBRARY_V3:
  - Composite sequences: mIL-15, mIL-21, scIL-12, PD-1/CD28 CSR, CTLA-4/CD28 CSR
  - PDB-derived: Trastuzumab scFv from 1N8Z
  - Additional UniProt: IL-21, FoxP3, OX40L, PD-L1, Notch1 NRR, MICA
  - NCBI-derived: OKT3, m971, SS1 via published data
"""
import json, time, re
from pathlib import Path
from urllib import request, error as urllib_error

BASE_UNI = "https://rest.uniprot.org/uniprotkb/{}.fasta"
AES_ROOT = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite")
CAR_DIR  = AES_ROOT / "data" / "CAR"
V3_PATH  = CAR_DIR / "CART_LIBRARY_V3.json"

with open(V3_PATH, encoding="utf-8") as f:
    lib = json.load(f)
v3_by_id = {e["id"]: e for e in lib["elements"]}

# ── Helpers ────────────────────────────────────────────────────────
def uni(acc, s=None, e=None, retries=3, delay=0.4):
    url = BASE_UNI.format(acc)
    for attempt in range(retries):
        try:
            with request.urlopen(url, timeout=12) as r:
                fasta = r.read().decode()
            lines = fasta.strip().splitlines()
            seq = "".join(ln for ln in lines if not ln.startswith(">"))
            time.sleep(delay)
            if s is not None and e is not None:
                return seq[s-1:e]
            return seq
        except Exception as ex:
            if attempt < retries-1:
                time.sleep(2)
            else:
                print(f"  ⚠️  Failed {acc}: {ex}")
    return ""

def pdb_fasta(pdb_id):
    url = f"https://www.rcsb.org/fasta/entry/{pdb_id.upper()}"
    try:
        with request.urlopen(url, timeout=12) as r:
            return r.read().decode()
    except Exception as ex:
        print(f"  ⚠️  PDB fetch failed {pdb_id}: {ex}")
        return ""

def parse_pdb_chains(fasta_text):
    """Return dict: chain_id → sequence"""
    chains = {}
    current_chain = None
    current_seq = []
    for line in fasta_text.strip().splitlines():
        if line.startswith(">"):
            if current_chain:
                chains[current_chain] = "".join(current_seq)
            # Parse chain id from header like ">1N8Z_1|Chain A|..."
            m = re.search(r'Chain ([A-Z])', line)
            current_chain = m.group(1) if m else line[1:10]
            current_seq = []
        else:
            current_seq.append(line.strip())
    if current_chain:
        chains[current_chain] = "".join(current_seq)
    return chains

def find_vh_boundary(heavy_chain_seq):
    """Find end of VH region by searching for J-segment motif."""
    # VH ends with WGQGT or WGQGT+LVT+VSS, then CH1 starts
    j_patterns = ["WGQGTLVTVSS", "WGQGTTVTVSS", "WGQGTMVTVSS",
                  "WGQGALVTVSS", "WGQGTSVTVSS"]
    for pat in j_patterns:
        idx = heavy_chain_seq.find(pat)
        if idx > 50:
            return idx + len(pat)
    # Fallback: look for CH1 start motif
    ch1_starts = ["ASTKGP", "EPKSCD", "ASTNKP"]
    for pat in ch1_starts:
        idx = heavy_chain_seq.find(pat)
        if 100 < idx < 200:
            return idx
    return 122  # Default VH length

def find_vl_boundary(light_chain_seq):
    """Find end of VL by searching for J-segment + CL boundary."""
    j_patterns = ["FGQGTKVEIK", "FGPGTKLEIK", "FGGGTKVEIK", "FGQGTKLELK"]
    for pat in j_patterns:
        idx = light_chain_seq.find(pat)
        if idx > 50:
            return idx + len(pat)
    # CL starts
    cl_starts = ["RTVAAPSVFI", "QPKAAPSVTL"]
    for pat in cl_starts:
        idx = light_chain_seq.find(pat)
        if 90 < idx < 130:
            return idx
    return 107

RESULTS = {}

# ════════════════════════════════════════════════════════════════════
# BLOCK 1: COMPOSITE CYTOKINE/PAYLOAD SEQUENCES
# ════════════════════════════════════════════════════════════════════
print("="*55)
print("BLOCK 1: Composite Payloads")
print("="*55)

# mIL-15: IL-2Rα_SP(P01589 1-21) + IL-15_mature(P40933 49-162) + IL-2Rβ_TM(P14784 214-251)
print("Fetching mIL-15 components...")
IL2RA_sp   = uni("P01589", 1,  21)     # IL-2Rα signal peptide 21aa
IL15_mat   = uni("P40933", 49, 162)    # IL-15 mature domain 114aa
IL2RB_tm   = uni("P14784", 214, 251)   # IL-2Rβ TM 38aa
mIL15 = IL2RA_sp + IL15_mat + IL2RB_tm
print(f"  mIL-15: {len(IL2RA_sp)} + {len(IL15_mat)} + {len(IL2RB_tm)} = {len(mIL15)} aa")
RESULTS["Membrane_IL15"] = mIL15

# mIL-21: IL-4_SP(P05112 1-24) + IL-21_mature(Q9HBE4 30-162) + IL-4Rα_TM(P24394 207-232)
print("Fetching mIL-21 components...")
IL4_sp     = uni("P05112", 1,  24)
IL21_mat   = uni("Q9HBE4", 30, 162)
IL4Ra_tm   = uni("P24394", 207, 232)
mIL21 = IL4_sp + IL21_mat + IL4Ra_tm
print(f"  mIL-21: {len(IL4_sp)} + {len(IL21_mat)} + {len(IL4Ra_tm)} = {len(mIL21)} aa")
RESULTS["Membrane_IL21"] = mIL21

# mIL-7 / IL-7·CCL19 "7×19" cytokine-armored: IL-7 mature + anchoring TM
print("Fetching IL-7 and CCL19...")
IL7_full   = uni("P13232")             # IL-7 full (177aa)
IL7_mat    = uni("P13232", 26, 177)    # IL-7 mature 152aa
CCL19_mat  = uni("Q99731", 22, 98)     # CCL19 mature 77aa (signal 1-21)
RESULTS["IL7_mature"]   = IL7_mat
RESULTS["CCL19_mature"] = CCL19_mat
print(f"  IL-7 mature: {len(IL7_mat)} aa | CCL19 mature: {len(CCL19_mat)} aa")

# scIL-12 p70: p35_mature + (G4S)3 + p40_mature
print("Fetching scIL-12 components...")
G4S3  = "GGGGSGGGGSGGGGS"
IL12A_mat  = uni("P29459", 23, 219)   # IL-12A (p35) mature 197aa
IL12B_mat  = uni("P29460", 23, 328)   # IL-12B (p40) mature 306aa
scIL12 = IL12A_mat + G4S3 + IL12B_mat
print(f"  scIL-12: p35({len(IL12A_mat)}) + G4S3(15) + p40({len(IL12B_mat)}) = {len(scIL12)} aa")
RESULTS["Secreted_IL12"] = scIL12
RESULTS["IL12A_p35_mature"] = IL12A_mat
RESULTS["IL12B_p40_mature"] = IL12B_mat

# GPX4 full protein
print("Fetching GPX4...")
GPX4_full = uni("P36969")             # GPX4_HUMAN 197aa
print(f"  GPX4: {len(GPX4_full)} aa")
RESULTS["GPX4_full"] = GPX4_full

# OX40L ectodomain (ligand-based costimulatory payload)
print("Fetching OX40L ectodomain...")
OX40L_ecto = uni("P23510", 50, 183)  # TNFSF4, ECD ~50-183 = 134aa
print(f"  OX40L ecto: {len(OX40L_ecto)} aa")
RESULTS["OX40L_ecto"] = OX40L_ecto

# HPSE (Heparanase) — ECM degradation for solid tumor infiltration
print("Fetching Heparanase...")
HPSE_mat   = uni("Q9Y251", 36, 543)   # HPSE_HUMAN mature
print(f"  Heparanase mature: {len(HPSE_mat)} aa")
RESULTS["HPSE_mature"] = HPSE_mat

# ════════════════════════════════════════════════════════════════════
# BLOCK 2: CHIMERIC SWITCH RECEPTORS (CSR)
# ════════════════════════════════════════════════════════════════════
print("\n" + "="*55)
print("BLOCK 2: Chimeric Switch Receptors")
print("="*55)

print("Fetching PD-1 and CTLA-4...")
PD1_full  = uni("Q15116")             # PDCD1_HUMAN full 288aa
PD1_sp    = uni("Q15116", 1,  24)     # PD-1 signal peptide 24aa
PD1_ecd   = uni("Q15116", 25, 167)    # PD-1 ECD 143aa
PD1_tm    = uni("Q15116", 168, 188)   # PD-1 TM 21aa
CD28_cyto = uni("P10747", 180, 220)   # CD28 cytoplasmic 41aa (already have but fetch fresh)

CTLA4_sp  = uni("P16410", 1,  35)     # CTLA-4 signal 35aa
CTLA4_ecd = uni("P16410", 36, 161)    # CTLA-4 ECD 126aa
CTLA4_tm  = uni("P16410", 162, 182)   # CTLA-4 TM 21aa

# PD-1/CD28 CSR = PD-1(SP+ECD+TM) + CD28(cyto)
PD1_CD28_CSR = PD1_sp + PD1_ecd + PD1_tm + CD28_cyto
# CTLA-4/CD28 CSR = CTLA-4(SP+ECD+TM) + CD28(cyto)
CTLA4_CD28_CSR = CTLA4_sp + CTLA4_ecd + CTLA4_tm + CD28_cyto

print(f"  PD-1/CD28 CSR: {len(PD1_sp)}+{len(PD1_ecd)}+{len(PD1_tm)}+{len(CD28_cyto)} = {len(PD1_CD28_CSR)} aa")
print(f"  CTLA-4/CD28 CSR: {len(CTLA4_sp)}+{len(CTLA4_ecd)}+{len(CTLA4_tm)}+{len(CD28_cyto)} = {len(CTLA4_CD28_CSR)} aa")
RESULTS["PD1_CD28_CSR"]     = PD1_CD28_CSR
RESULTS["CTLA4_CD28_CSR"]   = CTLA4_CD28_CSR
RESULTS["PD1_ECD"]          = PD1_ecd

# PD-L1 ECD (for iCAR/switch receptor binding partner)
print("Fetching PD-L1 ECD...")
PDL1_ecd   = uni("Q9NZQ7", 19, 238)   # PD-L1 ECD 220aa
print(f"  PD-L1 ECD: {len(PDL1_ecd)} aa")
RESULTS["PDL1_ECD"] = PDL1_ecd

# TIM-3/CD28 CSR
print("Fetching TIM-3...")
TIM3_sp    = uni("Q8TDQ0", 1,  22)
TIM3_ecd   = uni("Q8TDQ0", 23, 202)
TIM3_tm    = uni("Q8TDQ0", 203, 226)
TIM3_CD28_CSR = TIM3_sp + TIM3_ecd + TIM3_tm + CD28_cyto
print(f"  TIM-3/CD28 CSR: {len(TIM3_CD28_CSR)} aa")
RESULTS["TIM3_CD28_CSR"] = TIM3_CD28_CSR

# LAG-3/CD28 CSR
print("Fetching LAG-3...")
LAG3_sp    = uni("P18627", 1,  22)
LAG3_ecd   = uni("P18627", 23, 442)
LAG3_tm    = uni("P18627", 443, 463)
LAG3_cyto  = uni("P18627", 464, 498)  # just for reference
LAG3_CD28_CSR = LAG3_sp + LAG3_ecd + LAG3_tm + CD28_cyto
print(f"  LAG-3/CD28 CSR: {len(LAG3_CD28_CSR)} aa")
RESULTS["LAG3_CD28_CSR"] = LAG3_CD28_CSR

# ════════════════════════════════════════════════════════════════════
# BLOCK 3: LOGIC GATE COMPONENTS
# ════════════════════════════════════════════════════════════════════
print("\n" + "="*55)
print("BLOCK 3: Logic Gate / SynNotch Components")
print("="*55)

# Notch1 NRR (Negative Regulatory Region) — used in SynNotch
print("Fetching Notch1 NRR for SynNotch...")
Notch1_LNR_HD = uni("P46531", 1454, 1666)  # LNR-A/B/C + HD domain ~213aa
Notch1_tm_ext = uni("P46531", 1667, 1703)  # S2/S3 cleavage + TM ~37aa
# Minimal SynNotch NRR from Morsut Cell 2016 ≈ LNR+HD ~213aa
SynNotch_NRR = Notch1_LNR_HD
print(f"  SynNotch NRR (Notch1 LNR+HD): {len(SynNotch_NRR)} aa")
RESULTS["SynNotch_NRR"] = SynNotch_NRR

# Notch1 TM domain for SynNotch scaffold
Notch1_TM = uni("P46531", 1704, 1726)
print(f"  Notch1 TM: {len(Notch1_TM)} aa")
RESULTS["Notch1_TM"] = Notch1_TM

# Notch1 NICD (RAM+ANK) — intracellular domain cleaved by γ-secretase
Notch1_RAM = uni("P46531", 1754, 1850)   # RAM domain ~97aa
Notch1_ANK = uni("P46531", 1851, 2126)  # ANK repeats (7×)
print(f"  Notch1 RAM: {len(Notch1_RAM)} aa | ANK: {len(Notch1_ANK)} aa")
RESULTS["Notch1_RAM"] = Notch1_RAM

# VP64 = 4× VP16 AD (synthetic: VP16 repeated 4 times) — fully synthetic, define directly
VP16_AD = "DALDDFDLDML"  # VP16 minimal AD (11aa) × 4 repeats + linkers
VP64 = "DALDDFDLDMLGSDALDDFDLDMLGSDALDDFDLDMLGSDALDDFDLDML"
print(f"  VP64 (4×VP16 minimal): {len(VP64)} aa")
RESULTS["VP64"] = VP64

# Gal4 DBD from S.cerevisiae
print("Fetching Gal4 DBD (P04386)...")
Gal4_DBD = uni("P04386", 1, 147)   # Gal4 DBD 147aa
print(f"  Gal4 DBD: {len(Gal4_DBD)} aa")
RESULTS["Gal4_DBD"] = Gal4_DBD
RESULTS["Gal4_VP64"] = Gal4_DBD + "GSGSGSG" + VP64   # Gal4-linker-VP64 fusion

# ════════════════════════════════════════════════════════════════════
# BLOCK 4: TREG/AUTOIMMUNE COMPONENTS
# ════════════════════════════════════════════════════════════════════
print("\n" + "="*55)
print("BLOCK 4: Treg / Autoimmune Components")
print("="*55)

# FoxP3 (Treg master transcription factor)
print("Fetching FoxP3...")
FoxP3_full = uni("Q9BZS1")   # FOXP3_HUMAN 431aa
print(f"  FoxP3: {len(FoxP3_full)} aa")
RESULTS["FoxP3_full"] = FoxP3_full

# Desmoglein-3 ECD (CAAR for pemphigus vulgaris)
print("Fetching Dsg3 ECD...")
DSG3_sp    = uni("P32926", 1,  23)
DSG3_ecd   = uni("P32926", 24, 589)  # ECD domain (signal stripped)
print(f"  Dsg3 ECD: {len(DSG3_ecd)} aa")
RESULTS["Dsg3_ECD"] = DSG3_ecd

# MuSK ECD (CAAR for myasthenia gravis)
print("Fetching MuSK ECD...")
MUSK_sp    = uni("O15146", 1,  57)
MUSK_ecd   = uni("O15146", 58, 525)  # ECD
print(f"  MuSK ECD: {len(MUSK_ecd)} aa")
RESULTS["MuSK_ECD"] = MUSK_ecd

# ICOS-L / B7-H2 for CAR-Treg
print("Fetching ICOSL...")
ICOSL_ecd = uni("O75144", 21, 256)
print(f"  ICOSL ECD: {len(ICOSL_ecd)} aa")
RESULTS["ICOSL_ECD"] = ICOSL_ecd

# ════════════════════════════════════════════════════════════════════
# BLOCK 5: PDB-DERIVED BINDER SEQUENCES
# ════════════════════════════════════════════════════════════════════
print("\n" + "="*55)
print("BLOCK 5: PDB-Derived Binder Sequences")
print("="*55)

# Trastuzumab scFv from PDB 1N8Z (VH + G4S3 + VL)
print("Fetching PDB 1N8Z (Trastuzumab Fab)...")
pdb_1n8z = pdb_fasta("1N8Z")
if pdb_1n8z:
    chains_1n8z = parse_pdb_chains(pdb_1n8z)
    print(f"  Chains in 1N8Z: {list(chains_1n8z.keys())}")
    for ch_id, seq in chains_1n8z.items():
        print(f"    Chain {ch_id}: {len(seq)}aa  -> {seq[:30]}...")
    
    # Identify heavy and light chains of trastuzumab
    # We expect heavy chain ~220-230aa (VH+CH1) and light chain ~210-220aa (VL+CL)
    heavy_candidates = {k: v for k, v in chains_1n8z.items() if 200 < len(v) < 300 and len(v) > 150}
    
    # In 1N8Z, trastuzumab is in certain chains
    # Try to find by length and N-terminal sequence (trastuzumab VH starts with EVQLVESGG)
    tra_vh_chain = None
    tra_vl_chain = None
    for ch_id, seq in chains_1n8z.items():
        if seq.startswith("EVQLVESGG") and len(seq) > 100:
            tra_vh_chain = (ch_id, seq)
            print(f"  → Trastuzumab VH chain: {ch_id} ({len(seq)}aa, starts EVQLVES)")
        elif (seq.startswith("DIQMTQS") or seq.startswith("DIVMTQS")) and len(seq) > 100:
            tra_vl_chain = (ch_id, seq)
            print(f"  → Trastuzumab VL chain: {ch_id} ({len(seq)}aa, starts DIxMTQS)")
    
    if tra_vh_chain and tra_vl_chain:
        vh_boundary = find_vh_boundary(tra_vh_chain[1])
        vl_boundary = find_vl_boundary(tra_vl_chain[1])
        VH = tra_vh_chain[1][:vh_boundary]
        VL = tra_vl_chain[1][:vl_boundary]
        scFv_Tra = VH + G4S3 + VL
        print(f"  VH: {len(VH)}aa | VL: {len(VL)}aa | scFv: {len(scFv_Tra)}aa")
        RESULTS["Trastuzumab_scFv"] = scFv_Tra
    else:
        print("  Could not identify VH/VL chains. Checking all chains:")
        for ch_id, seq in sorted(chains_1n8z.items(), key=lambda x: len(x[1])):
            print(f"    {ch_id}: {len(seq)}aa | {seq[:40]}")
time.sleep(0.4)

# Cetuximab scFv from PDB 1YY9
print("\nFetching PDB 1YY9 (Cetuximab Fab)...")
pdb_1yy9 = pdb_fasta("1YY9")
if pdb_1yy9:
    chains_1yy9 = parse_pdb_chains(pdb_1yy9)
    print(f"  Chains in 1YY9: {list(chains_1yy9.keys())}")
    cet_vh = None; cet_vl = None
    for ch_id, seq in chains_1yy9.items():
        if seq.startswith("QVQLK") and 100 < len(seq) < 280:
            cet_vh = seq; print(f"  VH: {ch_id} {len(seq)}aa")
        elif seq.startswith("DILLT") and 100 < len(seq) < 250:
            cet_vl = seq; print(f"  VL: {ch_id} {len(seq)}aa")
    if cet_vh and cet_vl:
        vhb = find_vh_boundary(cet_vh); vlb = find_vl_boundary(cet_vl)
        scFv_Cet = cet_vh[:vhb] + G4S3 + cet_vl[:vlb]
        print(f"  Cetuximab scFv: VH({vhb}) + G4S3 + VL({vlb}) = {len(scFv_Cet)}aa")
        RESULTS["Cetuximab_scFv"] = scFv_Cet
time.sleep(0.4)

# Rituximab Fab from PDB 2OSL (CD20 binding)
print("\nFetching PDB 2OSL (Rituximab Fab)...")
pdb_2osl = pdb_fasta("2OSL")
if pdb_2osl:
    chains_2osl = parse_pdb_chains(pdb_2osl)
    print(f"  Chains in 2OSL: {list(chains_2osl.keys())}")
    rit_vh = None; rit_vl = None
    for ch_id, seq in chains_2osl.items():
        if seq.startswith("QVQLQ") and 100 < len(seq) < 280:
            rit_vh = seq; print(f"  VH candidate: {ch_id} {len(seq)}aa")
        elif (seq.startswith("QIVLS") or seq.startswith("QIVMS")) and 100 < len(seq) < 250:
            rit_vl = seq; print(f"  VL candidate: {ch_id} {len(seq)}aa")
    if rit_vh and rit_vl:
        vhb = find_vh_boundary(rit_vh); vlb = find_vl_boundary(rit_vl)
        scFv_Rit = rit_vh[:vhb] + G4S3 + rit_vl[:vlb]
        print(f"  Rituximab scFv: VH({vhb}) + G4S3 + VL({vlb}) = {len(scFv_Rit)}aa")
        RESULTS["Rituximab_scFv"] = scFv_Rit
time.sleep(0.4)

# Dinutuximab (ch14.18) from PDB (GD2)  
print("\nFetching PDB 1GIG (chFab 14.18 GD2 binder)...")
pdb_1gig = pdb_fasta("1GIG")
if pdb_1gig:
    chains_1gig = parse_pdb_chains(pdb_1gig)
    print(f"  Chains in 1GIG: {list(chains_1gig.keys())}")
    for ch_id, seq in chains_1gig.items():
        print(f"    {ch_id}: {len(seq)}aa  {seq[:30]}")
time.sleep(0.4)

# ════════════════════════════════════════════════════════════════════
# BLOCK 6: ADDITIONAL SIGNALING / ACTIVATION COMPONENTS
# ════════════════════════════════════════════════════════════════════
print("\n" + "="*55)
print("BLOCK 6: Additional Signaling Components")
print("="*55)

# CD3ε cytoplasmic tail (for iCAR use)
print("Fetching CD3ε and CD3δ...")
CD3E_cyto  = uni("P07766", 208, 247)   # CD3E cyto 40aa
CD3D_cyto  = uni("P04234", 138, 171)   # CD3D cyto 34aa
print(f"  CD3ε cyto: {len(CD3E_cyto)} aa | CD3δ cyto: {len(CD3D_cyto)} aa")
RESULTS["CD3E_cyto"] = CD3E_cyto
RESULTS["CD3D_cyto"] = CD3D_cyto

# 1XX ITAM (attenuated CD3ζ, 1 instead of 3 ITAMs) — truncated CD3ζ
# 1XX = only the first ITAM of CD3ζ (first YxxL/I...YxxL/I)
CD3z_full_cyto = uni("P20963", 52, 164)  # Full 3×ITAM 113aa
# First ITAM is roughly residues 52-90 (first 38aa of cytoplasmic)
CD3z_1xx = uni("P20963", 52, 89)   # 1 ITAM only ~38aa
print(f"  CD3ζ 1XX (1 ITAM): {len(CD3z_1xx)} aa")
RESULTS["CD3z_1XX"] = CD3z_1xx

# ZAP-70 SH2 domains (for non-CD3ζ activation strategy)
print("Fetching ZAP-70 tandem SH2...")
ZAP70_SH2 = uni("P43403", 1, 258)   # ZAP70 N-SH2 + linker + C-SH2
print(f"  ZAP70 tandem SH2: {len(ZAP70_SH2)} aa")
RESULTS["ZAP70_SH2"] = ZAP70_SH2

# IL-2Rβ cytoplasmic (for 5th gen JAK-STAT)
print("Fetching IL-2Rβ cytoplasmic...")
IL2RB_cyto = uni("P14784", 237, 350)  # IL-2Rβ cytoplasmic 114aa
print(f"  IL-2Rβ cytoplasmic (5th gen): {len(IL2RB_cyto)} aa")
RESULTS["IL2Rb_cyto_5thGen"] = IL2RB_cyto

# STAT5 (5th gen downstream effector)
print("Fetching STAT5A...")
STAT5A = uni("P42229")   # STAT5A 794aa (for reference)
print(f"  STAT5A: {len(STAT5A)} aa (reference)")

# ════════════════════════════════════════════════════════════════════
# BLOCK 7: NK-SPECIFIC COMPONENTS
# ════════════════════════════════════════════════════════════════════
print("\n" + "="*55)
print("BLOCK 7: NK-Specific Components")
print("="*55)

print("Fetching NKG2C ECD + DAP10 TM/cyto...")
NKG2C_ecd  = uni("P26717", 73, 185)   # NKG2C ECD 113aa
DAP10_TM   = uni("Q9UGN4", 21,  42)   # DAP10 TM 22aa
DAP10_cyto = uni("Q9UGN4", 43,  93)   # DAP10 cytoplasmic 51aa (contains YINM)
NKG2D_TM_2 = uni("P26718", 160, 200)  # NKG2D TM 41aa
print(f"  NKG2C ECD: {len(NKG2C_ecd)} aa | DAP10 TM: {len(DAP10_TM)} aa | DAP10 cyto: {len(DAP10_cyto)} aa")
RESULTS["NKG2C_ECD"]   = NKG2C_ecd
RESULTS["DAP10_TM"]    = DAP10_TM
RESULTS["DAP10_cyto"]  = DAP10_cyto

print("Fetching DNAM-1 (CD226) ECD...")
DNAM1_ecd  = uni("O95971", 21, 255)   # DNAM-1 ECD 235aa
print(f"  DNAM-1 ECD: {len(DNAM1_ecd)} aa")
RESULTS["DNAM1_ECD"] = DNAM1_ecd

print("Fetching NKp46 ECD (natural cytotoxicity receptor)...")
NKp46_ecd  = uni("O76036", 22, 254)   # NCR1 / NKp46 ECD
print(f"  NKp46 ECD: {len(NKp46_ecd)} aa")
RESULTS["NKp46_ECD"] = NKp46_ecd

# ════════════════════════════════════════════════════════════════════
# BLOCK 8: ALLOGENEIC & UNIVERSAL CAR
# ════════════════════════════════════════════════════════════════════
print("\n" + "="*55)
print("BLOCK 8: Universal CAR / Allogeneic Components")
print("="*55)

# HLA-G (NK suppression to protect allo-CAR-T from host NK killing)
print("Fetching HLA-G ECD...")
HLA_G_ecd  = uni("P17693", 25, 274)   # HLA-G1 ECD 250aa
print(f"  HLA-G ECD: {len(HLA_G_ecd)} aa")
RESULTS["HLA_G_ECD"] = HLA_G_ecd

# FITC-Anti-FITC scFv adapter sequence (for Universal CAR BBIR)
print("Fetching IL-2 SP for Universal CAR context...")

# Anti-CD3 epsilon for universal engagement
print("Fetching CD3ε ectodomain...")
CD3E_ecd = uni("P07766", 23, 107)   # CD3ε ECD (reduced form for nanobody targeting)
print(f"  CD3ε ECD: {len(CD3E_ecd)} aa")
RESULTS["CD3E_ECD"] = CD3E_ecd

# ════════════════════════════════════════════════════════════════════
# SAVE ALL RESULTS
# ════════════════════════════════════════════════════════════════════
SUPP_PATH = CAR_DIR / "_v3_supplements.json"
with open(SUPP_PATH, "w", encoding="utf-8") as f:
    json.dump({k: v for k, v in RESULTS.items() if v}, f, ensure_ascii=False, indent=2)
print(f"\n✓ Saved {len([v for v in RESULTS.values() if v])} sequences → {SUPP_PATH}")
print(f"  Keys: {list(k for k,v in RESULTS.items() if v)}")
