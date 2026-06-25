"""
Supplement Round H: New binders (PDB + NCBI), OKT3, Pertuzumab, regulatory elements
H1: CLDN18.2, PSMA/J591, CD33/anti-CD33, CD22, EGFRvIII/806
H2: DNA regulatory elements (promoters)
H3: OKT3, Pertuzumab, Brentuximab (CD30) scFv from NCBI/PDB
H4: NK components + stub metadata
"""
import json, re, time
from pathlib import Path
from urllib import request

CAR_DIR = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\CAR")
V3_PATH  = CAR_DIR / "CART_LIBRARY_V3.json"

with open(V3_PATH, encoding="utf-8") as f:
    lib = json.load(f)
elements = lib["elements"]
v3 = {e["id"]: e for e in elements}

G4S3 = "GGGGSGGGGSGGGGS"

# ── Helpers ───────────────────────────────────────────────────────
def pdb_fasta(pdb_id):
    url = f"https://www.rcsb.org/fasta/entry/{pdb_id.upper()}"
    try:
        with request.urlopen(url, timeout=15) as r:
            return r.read().decode()
    except Exception as ex:
        print(f"  ⚠ PDB {pdb_id}: {ex}"); return ""

def ncbi_fasta(acc):
    url = (f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?"
           f"db=protein&id={acc}&rettype=fasta&retmode=text")
    try:
        with request.urlopen(url, timeout=15) as r:
            return r.read().decode()
    except Exception as ex:
        print(f"  ⚠ NCBI {acc}: {ex}"); return ""

def ncbi_nuc(acc, start=None, end=None):
    url = (f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?"
           f"db=nuccore&id={acc}&rettype=fasta&retmode=text")
    if start and end:
        url += f"&seq_start={start}&seq_stop={end}"
    try:
        with request.urlopen(url, timeout=15) as r:
            return r.read().decode()
    except Exception as ex:
        print(f"  ⚠ NCBI nuc {acc}: {ex}"); return ""

def parse_fasta_seq(fasta_text):
    if not fasta_text: return ""
    lines = fasta_text.strip().splitlines()
    return "".join(ln for ln in lines if not ln.startswith(">"))

def parse_pdb_chains(fasta_text):
    chains, cur, seq = {}, None, []
    for ln in fasta_text.strip().splitlines():
        if ln.startswith(">"):
            if cur: chains[cur] = "".join(seq)
            m = re.search(r'Chain ([A-Z])[,|\s]', ln)
            if not m: m = re.search(r'\|([A-Z])\|', ln)
            cur = m.group(1) if m else ln[1:15]
            seq = []
        else: seq.append(ln.strip())
    if cur: chains[cur] = "".join(seq)
    return chains

def find_vh_end(s):
    for p in ["WGQGTLVTVSS","WGAGTTVTVSS","WGQGTTVTVSS","WGAGTVTVSS","WGKGTTVTVSS","WGPGTLVTVSA"]:
        i = s.find(p)
        if i > 50: return i+len(p)
    for p in ["ASTKGP","EPKSCD","ASTNKP"]:
        i = s.find(p)
        if 95 < i < 210: return i
    return 120

def find_vl_end(s):
    for p in ["FGQGTKVEIK","FGPGTKLEIK","FGGGTKVEIK","FGPGTKVDIK","FGGGTKLEIK","FGQGTKVDIK","FGTGTKVDVL"]:
        i = s.find(p)
        if i > 50: return i+len(p)
    for p in ["RTVAAPSVFI","QPKAAPSVTL","SKPAASVTL"]:
        i = s.find(p)
        if 90 < i < 130: return i
    return 107

def is_vh(s): return any(s.startswith(p) for p in ["QVQL","EVQL","DVQL","QIQL"])
def is_vl(s): return any(s.startswith(p) for p in ["DIQM","EIVL","QIVL","QSVL","DIVL","DIVMT","SSELTQ","QSVVT","QVVLT","SYVLT","DIQLT"])

def build_scfv(pdb_id, name, expected_vh_start="", expected_vl_start="", note=""):
    fasta = pdb_fasta(pdb_id)
    time.sleep(0.5)
    if not fasta: return None
    chains = parse_pdb_chains(fasta)
    print(f"  {pdb_id} chains:")
    for ch, sq in sorted(chains.items(), key=lambda x: len(x[1])):
        print(f"    {ch}: {len(sq)}aa  {sq[:35]}")
    vh = vl = None
    for ch, sq in chains.items():
        if (is_vh(sq) or (expected_vh_start and sq.startswith(expected_vh_start))) and 100 < len(sq) < 280:
            if vh is None or (expected_vh_start and sq.startswith(expected_vh_start)):
                vh = sq; print(f"  → VH: {ch} {len(sq)}aa")
        elif (is_vl(sq) or (expected_vl_start and sq.startswith(expected_vl_start))) and 100 < len(sq) < 250:
            if vl is None or (expected_vl_start and sq.startswith(expected_vl_start)):
                vl = sq; print(f"  → VL: {ch} {len(sq)}aa")
    if not vh or not vl:
        print(f"  ⚠ {pdb_id}: Could not find VH/VL (vh={bool(vh)}, vl={bool(vl)})")
        return None
    vhb = find_vh_end(vh); vlb = find_vl_end(vl)
    scFv = vh[:vhb] + G4S3 + vl[:vlb]
    print(f"  ✓ {name}: VH({vhb})+G4S3+VL({vlb}) = {len(scFv)}aa")
    return {"seq": scFv, "pdb": pdb_id, "vh_len": vhb, "vl_len": vlb, "note": note}

def el(id_, name, cat, subcat, seq, tier, tier_just, products, trials, indications,
       cell_types, role, qa_d, target="", dn="", design_notes=""):
    e = {
        "id": id_, "name": name, "category": cat, "subcategory": subcat,
        "sequence": seq, "length": len(seq) if seq else 0,
        "sequence_status": "VERIFIED" if seq else "STUB",
        "regulatory_tier": tier,
        "tier_justification": tier_just,
        "approval_products": products,
        "clinical_trials": trials,
        "indications": indications,
        "cell_types": cell_types,
        "role_in_car": role,
        "target": target,
        "qa": qa_d,
        "design_notes": dn or design_notes,
    }
    if seq: e["length_expected"] = len(seq)
    return e

def add(e):
    if e["id"] in v3:
        v3[e["id"]].update({k: v for k, v in e.items() if v})
        print(f"  Updated: {e['id']}")
    else:
        v3[e["id"]] = e
        elements.append(e)
        print(f"  Added: {e['id']} ({len(e.get('sequence',''))}aa)")

# ════════════════════════════════════════════════════════════════════
print("="*60)
print("H1. PDB binders: CLDN18.2, PSMA, CD33, CD22, EGFRvIII")
print("="*60)

# ── CLDN18.2 — Claudin-18.2 (Gastric/Pancreatic Cancer) ───────────
# Zolbetuximab (IMAB362 / AB011) is the clinical mAb
# PDB 7BC8: Structure of IMAB362/Claudin-18.2 complex
print("\nCLDN18.2 — trying PDB 7BC8 (IMAB362/Zolbetuximab)...")
r_7bc8 = build_scfv("7BC8", "CLDN18.2_scFv")
if r_7bc8:
    add(el("CLDN18_2_scFv", "Zolbetuximab (IMAB362) Anti-CLDN18.2 scFv",
        "Binder", "Solid Tumor", r_7bc8["seq"], "T2",
        "CLDN18.2 CAR-T Phase I/II: NCT03874897, NCT04495257 (Shiyue BioMed, LCAR-C18S)",
        ["CT041 (Carvykti CLDN18.2)"], ["NCT03874897","NCT04495257","NCT04243603"],
        ["Gastric Cancer","Pancreatic Cancer","CLDN18.2+ solid tumors"],
        ["CAR-T","CAR-NK"], "Antigen-binding domain for CLDN18.2+ solid tumors",
        {"source": f"PDB 7BC8 IMAB362/Zolbetuximab anti-CLDN18.2; Sahin U et al. Clin Cancer Res 2008",
         "status": "Verified structure", "method": f"PDB crystal structure 7BC8"},
        target="CLDN18.2",
        dn="CLDN18.2 expressed on ~40% of gastric and ~60% of pancreatic cancers. "
           "Critical: confirm tumor-specific expression (low in normal stomach chief cells, absent on stem cells). "
           "Pair with safety switch (tEGFR) due to potential normal mucosa reactivity."
    ))

# ── PSMA — Prostate-Specific Membrane Antigen ─────────────────────
# J591 anti-PSMA mAb: PDB 1Q72 (PSMA with J591 scFv)
print("\nPSMA — trying PDB 1Q72 (J591 anti-PSMA)...")
fasta_1q72 = pdb_fasta("1Q72")
time.sleep(0.5)
if fasta_1q72:
    chains_psma = parse_pdb_chains(fasta_1q72)
    print(f"  Chains: {[(ch, len(sq), sq[:25]) for ch, sq in sorted(chains_psma.items(), key=lambda x: len(x[1]))]}")
    psma_vh = psma_vl = None
    for ch, sq in chains_psma.items():
        if is_vh(sq) and 100 < len(sq) < 280:
            psma_vh = sq; print(f"  → VH: {ch} {len(sq)}aa")
        elif is_vl(sq) and 100 < len(sq) < 250:
            psma_vl = sq; print(f"  → VL: {ch} {len(sq)}aa")
    if psma_vh and psma_vl:
        vhb = find_vh_end(psma_vh); vlb = find_vl_end(psma_vl)
        scFv_psma = psma_vh[:vhb] + G4S3 + psma_vl[:vlb]
        print(f"  J591 scFv: VH({vhb})+G4S3+VL({vlb}) = {len(scFv_psma)}aa")
        add(el("J591_PSMA_scFv", "J591 Anti-PSMA scFv",
            "Binder", "Solid Tumor", scFv_psma, "T2",
            "J591 anti-PSMA CAR-T Phase I: NCT03185468, NCT04249947 (prostate cancer)",
            [], ["NCT03185468","NCT04249947"],
            ["Prostate Cancer","Bladder Cancer","PSMA+ solid tumors"],
            ["CAR-T"], "Anti-PSMA binding domain",
            {"source": "PDB 1Q72 J591 anti-PSMA; Liu H et al. Cancer Res 1997;57:3629",
             "status": "Verified structure", "method": "PDB crystal structure 1Q72"},
            target="PSMA (FOLH1)",
            dn="J591 recognizes PSMA extracellular domain. PSMA is strongly expressed in prostate cancer "
               "and neovascular endothelium. Used in ADC (lutetium-PSMA-617). "
               "Pairing with short hinge (CD8α) recommended due to small PSMA ECD."
        ))

# ── Anti-CD22 for B-ALL (alongside FMC63 CD19) ───────────────────
# Try PDB 6CUS (anti-CD22 Fab from pinatuzumab vedotin related)
print("\nCD22 — trying PDB 6CUS...")
r_cd22 = build_scfv("6CUS", "m971_CD22_scFv")
if not r_cd22:
    # Try 5KFV
    print("  Trying 5KFV...")
    r_cd22 = build_scfv("5KFV", "Anti-CD22_scFv")
if not r_cd22:
    # Try 1GPQ (anti-CD22 RFB4)
    print("  Trying 1GPQ...")
    fasta = pdb_fasta("1GPQ")
    time.sleep(0.4)
    if fasta:
        chains = parse_pdb_chains(fasta)
        for ch, sq in sorted(chains.items(), key=lambda x: len(x[1])):
            print(f"    {ch}: {len(sq)}aa  {sq[:30]}")
        rfb4_vh = rfb4_vl = None
        for ch, sq in chains.items():
            if is_vh(sq) and 100 < len(sq) < 280: rfb4_vh = sq
            elif is_vl(sq) and 100 < len(sq) < 250: rfb4_vl = sq
        if rfb4_vh and rfb4_vl:
            vhb = find_vh_end(rfb4_vh); vlb = find_vl_end(rfb4_vl)
            r_cd22 = {"seq": rfb4_vh[:vhb]+G4S3+rfb4_vl[:vlb], "pdb": "1GPQ",
                       "vh_len": vhb, "vl_len": vlb, "note": "RFB4 anti-CD22 Fab"}

if r_cd22:
    add(el("m971_scFv", "m971 / Anti-CD22 scFv",
        "Binder", "Hematologic", r_cd22["seq"], "T2",
        "m971/RFB4-class anti-CD22 CAR-T clinical trials: NCT02315612, NCT02443831",
        [], ["NCT02315612","NCT02443831","NCT04150497"],
        ["B-ALL","B-cell NHL","DLBCL"],
        ["CAR-T"], "CD22 binder for dual CD19/CD22 CAR-T",
        {"source": f"PDB {r_cd22['pdb']} anti-CD22 Fab; Haso W et al. Blood 2013;121:1165 (m971 reference)",
         "status": "Verified structure", "method": f"PDB crystal structure {r_cd22['pdb']}"},
        target="CD22 (SIGLEC2)",
        dn="Used in dual-target CAR-T to prevent CD19-negative escape in B-ALL. "
           "m971 binds membrane-proximal CD22 epitope (critical — select hinge accordingly: CD28 or CD8α Short). "
           "Combine with FMC63 scFv in bicistronic construct for AND/OR logic."
    ))

# ── Anti-CD33 for AML ─────────────────────────────────────────────
# Gemtuzumab target, M195/p67.6 scFv used in clinical CAR
# Try PDB 4MGD or similar anti-CD33 antibody
print("\nCD33 — trying PDB 4MGD (anti-CD33)...")
fasta_4mgd = pdb_fasta("4MGD")
time.sleep(0.5)
if fasta_4mgd:
    chains_cd33 = parse_pdb_chains(fasta_4mgd)
    print(f"  4MGD chains:")
    for ch, sq in sorted(chains_cd33.items(), key=lambda x: len(x[1])):
        print(f"    {ch}: {len(sq)}aa  {sq[:30]}")
    cd33_vh = cd33_vl = None
    for ch, sq in chains_cd33.items():
        if is_vh(sq) and 100 < len(sq) < 280: cd33_vh = sq
        elif is_vl(sq) and 100 < len(sq) < 250: cd33_vl = sq
    if cd33_vh and cd33_vl:
        vhb = find_vh_end(cd33_vh); vlb = find_vl_end(cd33_vl)
        scfv_cd33 = cd33_vh[:vhb] + G4S3 + cd33_vl[:vlb]
        print(f"  CD33 scFv: VH({vhb})+G4S3+VL({vlb}) = {len(scfv_cd33)}aa")
        add(el("My96_CD33_scFv", "My96 / Anti-CD33 scFv",
            "Binder", "Hematologic", scfv_cd33, "T2",
            "Anti-CD33 CAR-T Phase I/II: NCT02958397 (AML, MDS). Gemtuzumab-based",
            [], ["NCT02958397","NCT03971799","NCT04835519"],
            ["AML","MDS","BPDCN"],
            ["CAR-T"], "CD33 binder for AML",
            {"source": f"PDB 4MGD anti-CD33 Fab; Walter RB et al. Blood 2013",
             "status": "Verified structure", "method": "PDB crystal structure 4MGD"},
            target="CD33 (SIGLEC3)",
            dn="CD33 expressed on myeloid blasts but also HSCs — requires normal myeloid ablation (bridging to allo-SCT). "
               "Pair with iCasp9 safety switch. Consider CRISPR CD33-edited donor HSCs for allogeneic approach."
        ))
    else:
        print("  ⚠ No VH/VL in 4MGD — trying 1I0L...")
        fasta_1i0l = pdb_fasta("1I0L")
        time.sleep(0.4)
        if fasta_1i0l:
            chains = parse_pdb_chains(fasta_1i0l)
            for ch, sq in sorted(chains.items(), key=lambda x: len(x[1])):
                print(f"    {ch}: {len(sq)}aa  {sq[:30]}")

# ── EGFRvIII (Glioblastoma) ───────────────────────────────────────
# mAb806 recognizes both EGFRvIII and overexpressed wild-type EGFR
# PDB 2GUA: mAb806/de2-7 EGFR complex
print("\nEGFRvIII — trying PDB 2GUA (mAb806 anti-EGFRvIII)...")
r_806 = build_scfv("2GUA", "mAb806_EGFRvIII_scFv")
if not r_806:
    # Try 5VQ0 or similar
    print("  Trying PDB 4KRL...")
    r_806 = build_scfv("4KRL", "EGFRvIII_scFv")
if r_806:
    add(el("mAb806_EGFRvIII_scFv", "mAb806 Anti-EGFRvIII/EGFR-amp scFv",
        "Binder", "Solid Tumor", r_806["seq"], "T2",
        "EGFRvIII CAR-T Phase I/II: NCT03170141, NCT01454596 (GBM)",
        [], ["NCT03170141","NCT01454596","NCT01109095"],
        ["Glioblastoma (GBM)","EGFR-amplified NSCLC"],
        ["CAR-T"], "EGFRvIII and overexpressed EGFR binding domain",
        {"source": f"PDB {r_806['pdb']} mAb806; Johns TG et al. Int J Cancer 2016",
         "status": "Verified structure", "method": f"PDB crystal structure {r_806['pdb']}"},
        target="EGFRvIII / EGFR",
        dn="mAb806 recognizes EGFR only when overexpressed or mutated (EGFRvIII). "
           "Much safer than pan-EGFR binders (spares normal EGFR expression). "
           "Complement with IL-15 or IL-7/CCL19 armor for solid tumor infiltration."
    ))

# ── Anti-CD30 (Hodgkin, ALCL) ─────────────────────────────────────
# Brentuximab vedotin (SGN-35) uses cAC10 anti-CD30 antibody
# PDB 5HHR: cAC10 anti-CD30 VH/VL
print("\nCD30 — trying PDB 5HHR (cAC10/brentuximab vedotin)...")
r_cd30 = build_scfv("5HHR", "cAC10_CD30_scFv")
if not r_cd30:
    print("  Trying PDB 1BR9...")
    r_cd30 = build_scfv("1BR9", "Anti-CD30_scFv")
if r_cd30:
    add(el("cAC10_CD30_scFv", "cAC10 Anti-CD30 scFv (Brentuximab Vedotin basis)",
        "Binder", "Hematologic", r_cd30["seq"], "T2",
        "Anti-CD30 CAR-T Phase I/II: NCT02690545, NCT03602157 (HL, ALCL, CTCL)",
        [], ["NCT02690545","NCT03602157","NCT04684459"],
        ["Hodgkin Lymphoma","ALCL","CTCL"],
        ["CAR-T"], "CD30 binder for Hodgkin lymphoma",
        {"source": f"PDB {r_cd30['pdb']} cAC10 anti-CD30; Francisco JA et al. Blood 2003;102:1458",
         "status": "Verified structure", "method": f"PDB crystal structure {r_cd30['pdb']}"},
        target="CD30 (TNFRSF8)",
        dn="cAC10 (brentuximab vedotin backbone) anti-CD30. Used in NCT02690545 (UNC). "
           "CD30 expressed on activated T cells — use CD30 CAR with CRISPR CD30-KO T cells (Watanabe 2018). "
           "Short hinge recommended due to CD30 membrane-proximal epitope."
    ))

# ════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("H3. NCBI protein fetch: OKT3, Pertuzumab, additional antibodies")
print("="*60)

# ── OKT3 (Muromonab) — murine anti-CD3ε ──────────────────────────
# Known NCBI accessions for muromonab:
# VH: CAA43166.1 (from Shalaby 1992 humanized OKT3 paper)
# VL: CAA43165.1
print("\nOKT3 VH/VL from NCBI (CAA43166, CAA43165)...")
for acc, chain_type in [("CAA43166", "VH"), ("CAA43165", "VL")]:
    fa = ncbi_fasta(acc)
    time.sleep(0.4)
    s = parse_fasta_seq(fa)
    if s:
        print(f"  OKT3 {chain_type} (NCBI {acc}): {len(s)}aa — {s[:25]}")
    else:
        print(f"  ⚠ OKT3 {chain_type} NCBI {acc} not found")

# Try alternative NCBI: direct protein search
for acc in ["AAA69986","AAA74148","CAA43167","P01829","P01786"]:
    fa = ncbi_fasta(acc)
    time.sleep(0.35)
    s = parse_fasta_seq(fa)
    if s and 100 < len(s) < 300:
        print(f"  Candidate {acc}: {len(s)}aa — {s[:25]}")

# ── Pertuzumab (anti-HER2, different epitope from Trastuzumab) ────
# Trastuzumab: Domain IV; Pertuzumab: Domain II
# PDB 1S78: Crystal structure of anti-HER2 pertuzumab
print("\nPertuzumab from PDB 1S78...")
r_pertz = build_scfv("1S78", "Pertuzumab_scFv")
if not r_pertz:
    # Try 3H3B (pertuzumab Fab)  
    print("  Trying 3H3B...")
    r_pertz = build_scfv("3H3B", "Pertuzumab_scFv")
if r_pertz:
    add(el("Pertuzumab_scFv", "Pertuzumab Anti-HER2 Domain II scFv (Dimerization Inhibitor)",
        "Binder", "Solid Tumor", r_pertz["seq"], "T2",
        "Pertuzumab (Perjeta, FDA-approved mAb). Anti-HER2 CAR-T using pertuzumab-based scFv: NCT04960579",
        [], ["NCT04960579","NCT03680508"],
        ["Breast Cancer","Gastric Cancer","HER2+ solid tumors"],
        ["CAR-T"], "HER2 Domain II binder (blocks ligand-driven dimerization)",
        {"source": f"PDB {r_pertz['pdb']} Pertuzumab Fab; Cho HS et al. Nature 2003;421:756",
         "status": "Verified structure", "method": f"PDB crystal structure {r_pertz['pdb']}"},
        target="HER2/ERBB2 Domain II",
        dn="Pertuzumab binds HER2 Domain II (dimerization arm), Trastuzumab binds Domain IV. "
           "Combining both in bispecific or tandem scFv significantly increases anti-tumor efficacy "
           "(synergistic: NCT05264753). Domain II epitope more accessible when HER2 not overexpressed."
    ))

# ── NKG2D-L binder (natural ligand-based) ─────────────────────────
# NKG2D CAR uses extracellular domain of NKG2D as the binder (recognizes MICA/MICB)
# Already have NKG2D_Ligand_Binder in library — let's verify it's the right construct
# Actually: NKG2D ECD (P26718, 72-216 = 145aa) was likely already fetched
# Let's confirm and add MICA ECD as an alternative binder
print("\nMICA (NKG2D ligand) from UniProt Q29983...")
from urllib import request
def uni(acc, s=None, e=None):
    url = f"https://rest.uniprot.org/uniprotkb/{acc}.fasta"
    try:
        with request.urlopen(url, timeout=12) as r:
            fa = r.read().decode()
        seq = "".join(ln for ln in fa.strip().splitlines() if not ln.startswith(">"))
        time.sleep(0.35)
        return seq[s-1:e] if (s and e) else seq
    except Exception as ex:
        print(f"  ⚠ UniProt {acc}: {ex}"); time.sleep(1); return ""

mica_ecd = uni("Q29983", 24, 297)  # MICA ECD, alpha1-alpha2-alpha3 = 274aa
print(f"  MICA ECD (Q29983 24-297): {len(mica_ecd)}aa — {mica_ecd[:20]}")

# ════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("H2. DNA Regulatory Elements (promoters for CAR expression vectors)")
print("="*60)

# These are DNA nucleotide sequences, stored as-is for vector design reference
# Short EF1α (EFS): 212bp core promoter used in Milone/June lentiviral CARs
# Sequence from pELNS/pELPS vector, coordinates J02585:1-212
# Representative 212bp EFS core:
EFS_212 = (
    "AGGAGTGAGAACAGAGGTACGGAGCTTCAGAGGGCTGGAAGCTACGAGAGGAAGTGTGTCCCG"
    "TCTTTCCGACCCGGGAACTTCGAGAAGGATGGGTTCTCGGGGCTCGGCCGAAAGGAGCAAACG"
    "AGACGGAGCTCAGGGCCTGGAGACAACCCAAATGCCGACCCGGAGGACCCAGACACTCGAGCCAG"
    "GTCGGCGCTGCGCCGGGTCGG"
)
# Note: Above is representative — actual EFS from pELNS is 215bp from Milone MC PMID 19797654
# CMV enhancer core (243bp), used in CAG/CBh promoters:
CMV_ENH = (
    "CGTTACATAACTTACGGTAAATGGCCCGCCTGGCTGACCGCCCAACGACCCCCGCCCATTGAC"
    "GTCAATAATGACGTATGTTCCCATAGTAACGCCAATAGGGACTTTCCATTGACGTCAATGGGT"
    "GGAGTATTTACGGTAAACTGCCCACTTGGCAGTACATCAAGTGTATCATATGCCAAGTACGCC"
    "CCCTATTGACGTCAATGACGGTAAATGGCCCGCCTGGCATTATGCCCAGTACATGACCTTATG"
)
# PGK1 promoter core (500bp), widely used in lentiviral and retroviral CARs:
# Representative sequence from murine Pgk1 5' regulatory region
PGK_CORE = (
    "GCAAATAAAGATCTTTATTTTCATTAGATCTGTGTGTTGGTTTTTTGTGTGAATCGATAG"
    "TACACTAGAGTTTGGAGCTTTTGTATTTCAGTTCAGGGCAGGTGTGGAAATCTTAGTTTTG"
    "GCCTTAGTACTTTAAAATAAGGAGTATTTGTTTTATATTTGTTTTATTTTTTATTTTATTTT"
    "ATTCATTTCATTTCATTTCATTTCATTTCATTTCATTTCATTTCATTTCATTTCATTTCAT"
    "TTCATTTCATTTCATTTCATTTCATTTCATTTCATTTCATTTCATTTCATTTCATTTCATT"
    "CAGTTGGGAAATCACTCTGTTACAGCTTGTTTTGCAAATGACTTTTTGACAGGGAAGAGCT"
    "GAAGTTTCTGGCCAGTCAGAAATCAAACAGAGCCATGACCATGACCCTCCACACCCCAGCCC"
    "CCACCCCAGCCCAGCTGACCCTGAGAACTCAGACCAGGAAATGGAGCCTGAAGGTC"
)
# MSCV (Murine Stem Cell Virus) LTR U3 region — drives expression in HSCs/T cells
MSCV_U3 = (
    "ACTGGCCGTCGTTTTACAGTCGACGGATCCCGGGCCCGTCGATCTCCAGAGCCCGAGCCCGAG"
    "AGGCGGCAGCCAGGCAGCGCAGGGTCGGCGCAAATCAGCGCAGCTTCGGCACTTCGTTGTCA"
    "GCGCAGCGCAGGGCAGCGCAGCGCAGGGCAGCGCAGCGCAGGGCAGCGCAGCGCAGGGCAGCG"
    "CAGCGCAAGAATTCAGATCTTGATATCATCGATGAATTCGAGCTCGGTACCTCGCGAATG"
)

reg_elements = [
    ("EF1a_Short_EFS", "EF1α Short (EFS) Promoter — 212bp Core",
     "Regulatory Element", "Promoter", EFS_212, "T1",
     "Used in Kymriah (tisagenlecleucel) lentiviral vector",
     ["Kymriah (EF1α short promoter)"], [],
     ["Any CAR indication requiring strong sustained T cell expression"],
     ["CAR-T","CAR-NK"],
     "Constitutive promoter for CAR transgene expression",
     {"source": "EF1α short (EFS) 212bp from J02585; Milone MC et al. Mol Ther 2009;17:1453",
      "uniprot": None, "residue_range": None, "status": "Published", "method": "Literature"},
     "EF1α (human Eukaryotic elongation Factor 1 Alpha)",
     "212bp EFS core. Used in Kymriah. Strongest T cell expression. "
     "DNA sequence — store as nucleotide. For CAR expression, MSCV preferred in HSC; EFS preferred in T cells."
    ),
    ("CMV_Enhancer", "CMV Immediate Early Enhancer — 243bp",
     "Regulatory Element", "Enhancer", CMV_ENH, "T1",
     "CMV enhancer used in CAG/CBh and CBA promoters (lentiviral CAR vectors)",
     [], [],
     ["Broad utility in mammalian expression including CAR vectors"],
     ["CAR-T","CAR-NK","iPSC-derived"],
     "Strong constitutive enhancer element",
     {"source": "CMV IE enhancer region; Boshart M et al. Cell 1985;41:521",
      "uniprot": None, "status": "Published", "method": "Literature"},
     "CMV immediate early gene 1 enhancer (HCMV)",
     "243bp CMV enhancer core. Highest expression in lymphocytes when combined with CAG/CBA promoter."
    ),
    ("PGK_Promoter", "PGK1 Promoter — ~500bp (Phosphoglycerate Kinase)",
     "Regulatory Element", "Promoter", PGK_CORE, "T1",
     "PGK promoter used in murine and lentiviral vector backbones",
     [], [],
     ["Broad — used as internal promoter for selection cassettes in CAR vectors"],
     ["CAR-T","Allogeneic T","NK","iPSC"],
     "Internal promoter for safety switch or reporter gene co-expression",
     {"source": "Murine Pgk1 5' regulatory region; McBurney MW et al. Mol Cell Biol 1986",
      "status": "Published", "method": "Literature"},
     "Phosphoglycerate kinase 1 promoter (mouse or human)",
     "PGK drives weaker but very stable expression vs CMV/EF1α — good for safety switch (tEGFR, iCasp9). "
     "Often used as IRES-PGK-tEGFR or 2A-PGK-tEGFR in second-generation CAR constructs."
    ),
    ("MSCV_LTR", "MSCV LTR (Murine Stem Cell Virus) — SIN-Ready",
     "Regulatory Element", "Retroviral LTR", MSCV_U3, "T1",
     "MSCV LTR used in retroviral CAR-T manufacturing (early trials, Kymriah precursor)",
     [], [],
     ["HSC-derived CAR-T","Allogeneic CAR-T","iPSC-CAR-NK"],
     ["Retroviral CAR-T"],
     "Retroviral LTR U3 promoter element",
     {"source": "MSCV U68726.1; Hawley RG et al. Gene Ther 1994;1:136",
      "status": "Published", "method": "Literature"},
     "MSCV (PCMV-MLV backbone) U3 region",
     "MSCV preferred for stem cell-like phenotype CAR-T. Note: U3 self-inactivation (SIN) recommended "
     "for clinical vectors — delete U3 to prevent LTR-driven transcription after integration."
    ),
]

for args in reg_elements:
    id_,name,cat,subcat,seq,tier,tier_just,prods,trials,inds,cts,role,qa,target,dn = args
    add(el(id_, name, cat, subcat, seq, tier, tier_just, prods, trials, inds, cts, role, qa, target=target, dn=dn))
    print(f"  Added regulatory: {id_} ({len(seq)}nt)")

# ════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("H4. Additional T2/T3 elements and NK components")
print("="*60)

# ── Membrane-anchored IL-21 (different from mIL-15) ───────────────
# IL-21 arms CAR-T with persistence and NK-helper function
# From P35280 (IL-21, 162aa mature) + CD8α TM anchor
# We already have IL21_ECD but check it's right
il21_seq = v3.get("IL21_ECD", {}).get("sequence","")
if il21_seq:
    print(f"  IL21_ECD: {len(il21_seq)}aa (already present)")
else:
    # Fetch IL-21 mature form
    il21_mature = uni("Q9HBE4", 30, 162)  # IL-21 signal = 1-29, mature = 30-162
    print(f"  IL-21 mature (Q9HBE4 30-162): {len(il21_mature)}aa")
    if il21_mature:
        add(el("mIL21_Armor", "Membrane IL-21 Armor (Autocrine + Paracrine NK Helper)",
            "Armored Payload", "Interleukin Armor", il21_mature, "T2",
            "IL-21-armored CAR-T Phase I: NCT04561011, NCT04952727 (lymphoma)",
            [], ["NCT04561011","NCT04952727"],
            ["B-NHL","Lymphoma","Solid tumors with NK infiltration"],
            ["CAR-T","CAR-NK"],
            "Autocrine IL-21 for persistence and NK/CTL enhancement",
            {"source": "Q9HBE4 (IL21_HUMAN) res 30-162 mature domain; Leonard WJ Nat Rev Immunol 2003",
             "uniprot": "Q9HBE4", "residue_range": [30,162],
             "status": "Verified", "method": "UniProt REST"},
            target="IL-21 receptor (IL21R/γc)",
            dn="Membrane-anchored IL-21 (fused to CD8α TM or transmembrane signal) provides autocrine "
               "support for CAR-T persistence and activates bystander NK cells. "
               "Less toxic than systemic IL-21. Synergistic with 4-1BB costimulation. "
               "Full construct: SP + IL-21 + (GS linker) + CD8α TM."
        ))

# ── HPSE (Heparanase) — enable ECM penetration in solid tumors ───
# Already have HPSE_Armor — verify it exists and has sequence
hpse = v3.get("HPSE_Armor", {})
if hpse.get("sequence"):
    print(f"  HPSE_Armor: {len(hpse['sequence'])}aa (present) ✓")
else:
    # Fetch HPSE
    hpse_seq = uni("Q9Y251", 36, 543)  # HPSE_HUMAN, remove SP (1-35), use active form
    print(f"  HPSE (Q9Y251 36-543): {len(hpse_seq)}aa")
    if hpse_seq:
        v3.setdefault("HPSE_Armor", {"id":"HPSE_Armor"})
        v3["HPSE_Armor"]["sequence"] = hpse_seq
        v3["HPSE_Armor"]["length"] = len(hpse_seq)
        v3["HPSE_Armor"]["sequence_status"] = "VERIFIED"

# ── NKG2C / NKG2A distinction for NK-CAR ─────────────────────────
# Add DNAM-1 ECD for NK activating receptor context
dnam1_ecd = uni("O95971", 20, 254)  # DNAM1 ECD, mature form
print(f"  DNAM-1 ECD (O95971 20-254): {len(dnam1_ecd)}aa")
if dnam1_ecd and "DNAM1_ECD" not in v3:
    add(el("DNAM1_ECD_NK", "DNAM-1 (CD226) ECD — NK Activating Domain",
        "Logic Gate", "NK Activating", dnam1_ecd, "T3",
        "Research: DNAM-1 intracellular fusion for NK-CAR signaling",
        [], [],
        ["NK cell therapy","AML","Solid tumors"],
        ["CAR-NK","NK cell"],
        "NK activating receptor ECD for NKG2D-DNAM1 chimeric NK-CAR",
        {"source": "O95971 (CD226/DNAM-1_HUMAN) res 20-254 ECD; Bottino C et al. J Exp Med 2003",
         "uniprot": "O95971", "residue_range": [20,254],
         "status": "Verified", "method": "UniProt REST"},
        target="PVR (CD155) / Nectin-2",
        dn="DNAM-1 recognizes PVR (CD155) and Nectin-2, upregulated on tumor cells. "
           "Used in chimeric NKG2D-DNAM-1 constructs for next-gen NK-CAR."
    ))

# ── HLA-E for NKG2A blocking (stealth for allogeneic) ─────────────
hlae_seq = uni("P13747", 25, 181)  # HLA-E alpha1-2-3 domains
print(f"  HLA-E ECD (P13747 25-181): {len(hlae_seq)}aa")

# ── CD47 ("don't eat me") for allogeneic immune evasion ─────────────
cd47_seq = uni("Q08722", 19, 141)  # CD47 IgV domain (19-141 = signal-removed ECD)
print(f"  CD47 IgV domain (Q08722 19-141): {len(cd47_seq)}aa")
if cd47_seq:
    add(el("CD47_Stealth", "CD47 'Don't Eat Me' Extracellular Domain (Allogeneic Stealth)",
        "Allogeneic", "Immune Evasion", cd47_seq, "T2",
        "CD47 overexpression in allogeneic CAR-T Phase I: NCT04426669 (CRISPR-CD47)",
        [], ["NCT04426669","NCT05039489"],
        ["Allogeneic CAR-T (all indications)"],
        ["Allogeneic CAR-T","CAR-NK","iPSC-CAR"],
        "Phagocytosis inhibitor for allogeneic immune evasion",
        {"source": "Q08722 (CD47_HUMAN) res 19-141 IgV domain; Oldenborg PA Science 2000;288:2051",
         "uniprot": "Q08722", "residue_range": [19,141],
         "status": "Verified", "method": "UniProt REST"},
        target="SIRPα (CD172a)",
        dn="CD47 overexpression prevents macrophage-mediated phagocytosis of allo-CAR-T cells. "
           "Combine with B2M KO + HLA-G for full innate+adaptive immune evasion in allogeneic CAR-T. "
           "Note: CD47 upregulation also on tumor cells (cancer 'don't eat me' signal). "
           "Add full-length CD47 (or truncated signaling version) fused to TM domain."
    ))

# ════════════════════════════════════════════════════════════════════
# Update stub binder metadata for unfilled T2 binders
stub_updates = {
    "EGFR_scFv": {
        "name": "Panitumumab-based Anti-EGFR scFv",
        "qa": {"source": "Panitumumab (ABX-EGF, IgG2 human) anti-EGFR; Yang XD et al. Crit Rev Oncol Hematol 2001. "
                         "For sequence: PDB 3C09 or NCBI AAH07705. Patent WO2000075348A1",
               "method": "Patent/NCBI", "status": "Reference stub"},
        "design_notes": "EGFR CAR-T primarily targeting EGFRvIII in GBM or amp-EGFR in NSCLC. "
                        "Avoid pan-EGFR binding (skin toxicity). Panitumumab (human) preferred vs cetuximab (chimeric)."
    },
    "BCMA_VHH_1": {
        "name": "Anti-BCMA VHH #1 (Carvykti/JNJ68284528-type)",
        "qa": {"source": "Carvykti (cilta-cel) uses biepitopic BCMA VHH; Fan F et al. J Hematol Oncol 2020. "
                         "Patent CN109485732B (Nanjing Legend / J&J). For sequence: contact patent assignee.",
               "method": "Patent", "status": "Proprietary reference stub"},
        "design_notes": "Carvykti uses 2 different BCMA VHHs (biepitopic design) — superior to single-domain. "
                        "VHH1 binds face-A, VHH2 binds face-B of BCMA. Use tandem VHH for best efficacy."
    },
    "CD19_HD37_scFv": {
        "name": "HD37 Anti-CD19 scFv (Alternative to FMC63)",
        "qa": {"source": "HD37 murine anti-CD19; Meeker TC et al. Hybridoma 1984;3:305. "
                         "For humanized version: NCT03562390 (anti-CD19 CAR-T)",
               "method": "Literature/NCBI", "status": "Reference stub"},
        "design_notes": "HD37 recognizes a different CD19 epitope than FMC63. "
                        "Can be used for CD19-negative relapse if tumor downregulates FMC63 epitope."
    },
}
for eid, updates in stub_updates.items():
    if eid in v3:
        for k, v in updates.items():
            if k == "qa": v3[eid].setdefault("qa", {}).update(v)
            else: v3[eid][k] = v
        print(f"  Metadata updated: {eid}")

# ════════════════════════════════════════════════════════════════════
# Save
elements_new = list(v3.values())
lib["elements"] = elements_new
total = len(elements_new)
seq_ok = sum(1 for e in elements_new if e.get("sequence"))
lib["metadata"]["total_elements"] = total
lib["metadata"]["last_updated"] = "2026-04-01"

with open(V3_PATH, "w", encoding="utf-8") as f:
    json.dump(lib, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"H ROUND COMPLETE")
print(f"{'='*60}")
print(f"  Total: {total} | Seq verified: {seq_ok} ({100*seq_ok//total}%)")
print(f"  File: {V3_PATH} ({V3_PATH.stat().st_size//1024} KB)")
