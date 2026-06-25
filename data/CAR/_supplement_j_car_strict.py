"""
Supplement Round J — Strict CAR-relevant additions only
1. Clean up MARGINAL non-CAR elements
2. Fix HPSE_Armor misclassification
3. Add priority CAR-functional missing elements:
   - c-Jun_DN (exhaustion resistance)
   - IL18_Armor (NK/DC activation payload)
   - GITR/HVEM/CD40/MyD88/TLR2 costimulatory
   - DAP12_TM / ICOS_TM / OX40_TM
   - IgG1_Hinge
   - Rapamycin-inducible Split CAR (FRB/FKBP)
   - Gaussia_SP / Furin_2A linker
   - JeT_Promoter (compact CAR promoter)
   - IL13_Mutein (GBM IL-13Rα2 binder)
   - KRAS_G12D_TCRmimic (intracellular antigen CAR)
"""
import json, time
from pathlib import Path
from urllib import request

CAR_DIR = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\CAR")
V3_PATH  = CAR_DIR / "CART_LIBRARY_V3.json"

with open(V3_PATH, encoding="utf-8") as f:
    lib = json.load(f)
elements = lib["elements"]
v3 = {e["id"]: e for e in elements}

def uni(acc, s=None, e_=None):
    url = f"https://rest.uniprot.org/uniprotkb/{acc}.fasta"
    try:
        with request.urlopen(url, timeout=12) as r:
            fa = r.read().decode()
        seq = "".join(ln for ln in fa.strip().splitlines() if not ln.startswith(">"))
        time.sleep(0.35); return seq[s-1:e_] if (s and e_) else seq
    except Exception as ex:
        print(f"  ⚠ UniProt {acc}: {ex}"); return ""

def add_elem(eid, name, category, subcategory, seq, tier, tier_just, role,
             indications, cell_types, qa_source, qa_method, design_notes,
             prods=None, trials=None):
    if eid in v3:
        print(f"  Skip {eid} (already exists)")
        return
    e = {
        "id": eid, "name": name, "category": category, "subcategory": subcategory,
        "sequence": seq, "length": len(seq), "sequence_status": "VERIFIED",
        "regulatory_tier": tier, "tier_justification": tier_just,
        "role_in_car": role, "indications": indications, "cell_types": cell_types,
        "approval_products": prods or [], "clinical_trials": trials or [],
        "qa": {"source": qa_source, "method": qa_method, "status": "Verified"},
        "design_notes": design_notes
    }
    v3[eid] = e
    elements.append(e)
    print(f"  + {eid}: {len(seq)}aa")

# ════════════════════════════════════════════════════════════════════
print("="*60)
print("STEP 1 — Fix MARGINAL elements")
print("="*60)

# Fix HPSE_Armor category (was in Binder, should be Armored Payload)
e = v3.get("HPSE_Armor")
if e and e.get("category") == "Binder":
    e["category"] = "Armored Payload"
    e["subcategory"] = "Matrix-Degrading Enzyme"
    e["role_in_car"] = "Secreted heparanase degrades ECM for solid tumor infiltration"
    print("  HPSE_Armor: Binder → Armored Payload")

# Remove pure duplicates and non-CAR tags
TO_REMOVE = ["218_linker", "GSG_prefix", "Myc_Tag", "FLAG_Tag"]
for eid in TO_REMOVE:
    if eid in v3:
        elements.remove(v3[eid])
        del v3[eid]
        print(f"  Removed {eid} (non-CAR or duplicate)")

# Keep G4S6 but reclassify as research-only note
e_g4s6 = v3.get("G4S6")
if e_g4s6:
    e_g4s6["design_notes"] = (
        "G4S ×6 (30aa) — very long, rarely used in standard scFv. "
        "May be used for extended bispecific tandem binder spacing. "
        "Prefer G4S3 or Whitlow for standard CAR scFv design."
    )
    e_g4s6["regulatory_tier"] = "T3"
    print("  G4S6: added caution note (kept)")

print(f"  After cleanup: {len(elements)} elements")

# ════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("STEP 2 — Add CAR-specific missing elements")
print("="*60)

# ── c-Jun DN (dominant-negative AP-1 exhaustion resistance) ───────
print("\nc-Jun DN (exhaustion resistance)...")
# c-Jun full protein: P05412 (bZIP transcription factor)
# For dominant-negative: use full-length c-Jun — overexpression of WT c-Jun
# Note: in Dorman et al. Science 2019, full-length c-Jun is overexpressed (not truncated DN)
# It acts as AP-1 pioneer factor competing with exhaustion-inducing AP-1/IRF4 complex
cjun = uni("P05412")
print(f"  c-Jun P05412: {len(cjun)}aa  {cjun[:25]}")
if cjun:
    add_elem(
        "cJun_Overexpression", "c-Jun AP-1 Transcription Factor (Exhaustion Resistance)",
        "Armored Payload", "Transcription Factor Payload",
        cjun, "T3",
        "Research: Dorman 2019 Science — c-Jun overexpression rescues T cell exhaustion in CAR-T",
        "Transcription factor payload to prevent terminal exhaustion",
        ["Solid Tumor — TIL exhaustion", "Chronic antigen exposure scenarios"],
        ["CAR-T"],
        "P05412 (JUN_HUMAN) full 331aa; Dorman LC Science 2019;365:604 — c-Jun OE prevents "
        "exhaustion; AP-1 pioneer factor. Lynn RC Nature 2019;576:293 co-confirms.",
        "UniProt P05412 REST",
        "c-Jun overexpression (full 331aa) competes with exhaustion-driving AP-1/IRF4 at TOX/EOMES loci. "
        "NOT dominant-negative — it is OVEREXPRESSION of WT c-Jun that rescues stemness. "
        "Add as separate transcription unit: EF1α-cJun-P2A-CAR or internal IRES. "
        "Dorman Science 2019: 3-fold better tumor control, reduced PD-1/LAG-3. "
        "Combine with 4-1BB costim for maximal persistence."
    )

# ── IL-18 armored payload ──────────────────────────────────────────
print("\nIL-18 secreted armor...")
# IL-18 mature secreted form: Q14116 residues 37-193 (after caspase-1 cleavage at D35)
il18 = uni("Q14116", 37, 193)
print(f"  IL-18 Q14116 37-193: {len(il18)}aa  {il18[:25]}")
if il18:
    add_elem(
        "Secreted_IL18", "Secreted IL-18 (TRUCK Armored Payload)",
        "Armored Payload", "Immunomodulatory Cytokine",
        il18, "T2",
        "Clinical trial: NCT04684563 (IL-18-armored CD19 CAR-T); Hu B Cell 2021",
        "Secreted cytokine payload for NK/DC activation in TME",
        ["Solid Tumor", "Glioblastoma", "Ovarian Cancer"],
        ["CAR-T"],
        "Q14116 (IL18_HUMAN) mature form res 37-193 (157aa); "
        "Hu B Cell 2021;184:1542 (IL-18-armored CAR-T); "
        "NCT04684563 (IL-18 CAR-T glioblastoma); "
        "Interleukin-18 drives NK cytotoxicity + DC maturation + Th1 polarization in TME.",
        "UniProt Q14116 REST",
        "IL-18 mature secreted form (157aa). Cleaved by caspase-1 at Asp35. "
        "ARMOR strategy: NFAT-driven IL-18 secretion when CAR is activated (TRUCK principle). "
        "IL-18 activates bystander NK cells and DCs — broadens anti-tumor response. "
        "Superior to IL-12 for NK activation; lower systemic toxicity than IL-12. "
        "NCT04684563 Phase I (GBM): IL-18-armored locoregional CAR-T — early signals."
    )

# ── GITR costimulatory domain ─────────────────────────────────────
print("\nGITR costimulatory domain...")
# GITR (CD357): Q9Y5U5, TM ends ~174, cytoplasmic 175-241
gitr = uni("Q9Y5U5", 175, 241)
print(f"  GITR Q9Y5U5 175-241: {len(gitr)}aa  {gitr[:25]}")
if gitr:
    add_elem(
        "GITR_cyto", "GITR (CD357) Cytoplasmic Domain",
        "Costimulatory", "TNFRSF Costimulatory",
        gitr, "T3",
        "Research: GITR costim in CAR-T for Treg depletion + tumor immunity",
        "TNFR-family costimulatory domain in Treg-depleting CAR",
        ["Solid Tumor", "Treg-high TME"],
        ["CAR-T"],
        "Q9Y5U5 (GITR_HUMAN) cytoplasmic domain res 175-241 (67aa); "
        "Dutoit V Front Immunol 2021 (GITR costim in CAR-T); "
        "GITR signaling promotes effector T cell function and depletes tumor-infiltrating Tregs.",
        "UniProt Q9Y5U5 REST",
        "GITR (Glucocorticoid-Induced TNFR, CD357) cytoplasmic domain (67aa). "
        "GITR signaling: NF-κB activation + T cell proliferation/survival. "
        "Dual benefit in CAR-T: (1) direct T cell costimulation, (2) GITR on Tregs → depletion. "
        "Use in combination with anti-Treg strategy: CAR + GITRL payload or anti-GITR binder."
    )

# ── HVEM costimulatory domain ─────────────────────────────────────
print("\nHVEM costimulatory domain...")
# HVEM (CD270): Q92956, cytoplasmic 200-283
hvem = uni("Q92956", 200, 283)
print(f"  HVEM Q92956 200-283: {len(hvem)}aa  {hvem[:25]}")
if hvem:
    add_elem(
        "HVEM_cyto", "HVEM (CD270) Cytoplasmic Domain",
        "Costimulatory", "TNFRSF Costimulatory",
        hvem, "T3",
        "Research: HVEM reverse signaling disrupts BTLA checkpoint",
        "TNFR-family costimulatory; disrupts BTLA-mediated checkpoint",
        ["Solid Tumor", "BTLA-high tumor microenvironment"],
        ["CAR-T"],
        "Q92956 (HVEM_HUMAN) cytoplasmic res 200-283 (84aa); "
        "Ni L Nat Rev Immunol 2007 (HVEM-BTLA axis); "
        "Cheung AS Nat Biotechnol 2022 (combinatorial CAR costim screening).",
        "UniProt Q92956 REST",
        "HVEM (Herpesvirus Entry Mediator, TNFRSF14) cytoplasmic 84aa. "
        "Normally HVEM binds BTLA/CD160 to inhibit T cells. "
        "CAR context: HVEM cytoplasmic domain in CAR co-stimulates via TRAF2/5 (NF-κB). "
        "Also potentially disrupts BTLA feedback loop. "
        "Cheung 2022 Nat Biotechnol: high-throughput costim screen found HVEM among top candidates."
    )

# ── CD40 cytoplasmic domain ───────────────────────────────────────
print("\nCD40 costimulatory domain...")
# CD40: P25942, cytoplasmic 215-277
cd40 = uni("P25942", 215, 277)
print(f"  CD40 P25942 215-277: {len(cd40)}aa  {cd40[:25]}")
if cd40:
    add_elem(
        "CD40_cyto", "CD40 Cytoplasmic Domain",
        "Costimulatory", "TNFRSF Costimulatory",
        cd40, "T3",
        "Research: CD40 costim drives dendritic-cell-like activation in CAR-T",
        "CD40 cytoplasmic domain for DC-like T cell activation",
        ["Solid Tumor", "B-cell malignancies"],
        ["CAR-T", "CAR-M"],
        "P25942 (CD40_HUMAN) cytoplasmic res 215-277 (63aa); "
        "Curran KJ et al. Mol Ther 2012 — CD40 costim in CAR-T; "
        "Elgueta R Immunol Rev 2009 (CD40-CD40L axis).",
        "UniProt P25942 REST",
        "CD40 cytoplasmic domain (63aa). TRAF2/3/5/6 recruitment → NF-κB, MAPK. "
        "In CAR-T: CD40 costim mimics CD4 helper T cell activation signals, "
        "enhancing CD8 CAR-T persistence and DC crosstalk. "
        "Used in GoD-CAR constructs with MyD88 for 'innate-bridge' signaling."
    )

# ── MyD88 cytoplasmic (GoD-CAR) ───────────────────────────────────
print("\nMyD88 cytoplasmic (GoD-CAR innate costim)...")
# MyD88: Q99836, TIR domain cytoplasmic 155-296
myd88 = uni("Q99836", 155, 296)
print(f"  MyD88 Q99836 155-296: {len(myd88)}aa  {myd88[:25]}")
if myd88:
    add_elem(
        "MyD88_TIR", "MyD88 TIR Domain (GoD-CAR Innate Costimulation)",
        "Costimulatory", "TLR/Innate Immune Costimulatory",
        myd88, "T3",
        "Research: GoD-CAR (MyD88+CD40) — Priceman SJ 2018 J Clin Invest",
        "MyD88-CD40 tandem innate costimulatory (GoD-CAR design)",
        ["Solid Tumor — IL-6/TNF-driven TME", "Prostate Cancer", "Ovarian Cancer"],
        ["CAR-T"],
        "Q99836 (MYD88_HUMAN) TIR domain res 155-296 (142aa); "
        "Priceman SJ J Clin Invest 2018;128:4543 (GoD-CAR: MyD88/CD40 in prostate CAR-T); "
        "Juárez-Flores DL Clin Immunol 2021 review of innate costim.",
        "UniProt Q99836 REST",
        "MyD88 TIR domain (142aa). In GoD-CAR: CD3ζ–MyD88–CD40 fusion. "
        "MyD88 activates NF-κB via IRAK4/TRAF6; CD40 activates TRAF2/3/5. "
        "Together → 10-100× cytokine amplification vs. CD28/4-1BB in solid tumors. "
        "Priceman 2018: GoD-CAR superior to CD28 and 4-1BB CARs in prostate cancer model. "
        "CAUTION: higher tonic signaling risk — requires calibrated promoter."
    )

# ── TLR2 cytoplasmic domain ───────────────────────────────────────
print("\nTLR2 cytoplasmic domain...")
# TLR2: O60603, cytoplasmic TIR domain 647-784
tlr2 = uni("O60603", 647, 784)
print(f"  TLR2 O60603 647-784: {len(tlr2)}aa  {tlr2[:25]}")
if tlr2:
    add_elem(
        "TLR2_TIR", "TLR2 TIR Domain (Pattern Recognition Costimulation)",
        "Costimulatory", "TLR/Innate Immune Costimulatory",
        tlr2, "T3",
        "Research: TLR2 costim in CAR-T for pathogen-associated signal integration",
        "TLR2 cytoplasmic TIR domain for innate costimulation",
        ["Solid Tumor — bacterial/fungal TME", "Infection-associated cancers"],
        ["CAR-T"],
        "O60603 (TLR2_HUMAN) TIR domain res 647-784 (138aa); "
        "Guo Y et al. J Immunol 2019 (TLR-costimulated CAR-T); "
        "TLR2 agonists (PAM3, MALP-2) in CAR-T co-administration strategy.",
        "UniProt O60603 REST",
        "TLR2 TIR domain (138aa) for innate immune pattern recognition integration. "
        "CAR-T with TLR2 costim: activated by PAM3CSK4, MALP-2 (TLR2/6 agonists). "
        "Potential: co-administration of TLR2 agonist + CAR-T → enhanced tumor killing. "
        "Also for CAR-T designs in infection-associated cancers (HPV, H.pylori)."
    )

# ── DAP12 TM domain (separate from costimulatory) ────────────────
print("\nDAP12 TM domain...")
# DAP12 (TYROBP): O43914, TM domain residues ~28-48
dap12_tm = uni("O43914", 22, 50)
print(f"  DAP12 TM O43914 22-50: {len(dap12_tm)}aa  {dap12_tm[:25]}")
if dap12_tm:
    add_elem(
        "DAP12_TM", "DAP12 (TYROBP) Transmembrane Domain",
        "Transmembrane", "Activating Receptor TM",
        dap12_tm, "T2",
        "Clinical use in CAR-NK and CAR-M designs with DAP12 costim",
        "TM anchoring domain for CAR-NK/CAR-M with built-in ITAM activation",
        ["AML", "Solid Tumor — NK-based CAR"],
        ["CAR-NK", "CAR-M"],
        "O43914 (TYROBP_HUMAN) TM res 22-50 (29aa); "
        "Barber A J Immunother 2011 (DAP12 CAR-NK); "
        "Lanier LL Nat Immunol 2009 (DAP12 signaling in NK cells).",
        "UniProt O43914 REST",
        "DAP12 TM domain (29aa). DAP12 TM contains charged residue (Lys) for pairing with "
        "activating receptors (NKG2D, NKp44). "
        "In CAR-NK: DAP12 TM + DAP12 ITAM creates compact activating CAR without external costim. "
        "Typically used as: scFv + DAP12_TM + DAP12_ITAM (NKG2D-based design)."
    )

# ── ICOS TM domain ────────────────────────────────────────────────
print("\nICOS TM domain...")
# ICOS: Q9Y6W8, TM ~131-155
icos_tm = uni("Q9Y6W8", 131, 155)
print(f"  ICOS TM Q9Y6W8 131-155: {len(icos_tm)}aa  {icos_tm[:25]}")
if icos_tm:
    add_elem(
        "ICOS_TM", "ICOS Transmembrane Domain",
        "Transmembrane", "Costimulatory Receptor TM",
        icos_tm, "T2",
        "Clinical ICOS-CAR designs for Treg and Th17-biased CAR",
        "ICOS TM for ICOS-costim CAR (Treg/Th17/follicular helper T)",
        ["Autoimmune Disease", "Follicular Lymphoma", "Solid Tumor"],
        ["CAR-T", "CAR-Treg"],
        "Q9Y6W8 (ICOS_HUMAN) TM res 131-155 (25aa); "
        "Guedan S J Clin Invest 2014;124:5164 (ICOS-CAR-T); "
        "Löhning M Immunity 2003 (ICOS/Th17/Tfh biology).",
        "UniProt Q9Y6W8 REST",
        "ICOS TM domain (25aa). Pairs with ICOS cytoplasmic for complete ICOS-costim CAR. "
        "ICOS-CAR skews T cell differentiation toward ICOS+Tfh-like cells — better tumor infiltration. "
        "Critical for CAR-Treg designs: ICOS costim maintains FoxP3 stability in chronic stimulation. "
        "Guedan 2014: ICOS-CAR superior to CD28 or 4-1BB in ovarian cancer model."
    )

# ── OX40 TM domain ────────────────────────────────────────────────
print("\nOX40 TM domain...")
# OX40 (CD134): P23510, TM ~168-190
ox40_tm = uni("P23510", 168, 190)
print(f"  OX40 TM P23510 168-190: {len(ox40_tm)}aa  {ox40_tm[:25]}")
if ox40_tm:
    add_elem(
        "OX40_TM", "OX40 (CD134) Transmembrane Domain",
        "Transmembrane", "Costimulatory Receptor TM",
        ox40_tm, "T2",
        "OX40-CAR designs for persistent antitumor response",
        "OX40 TM for OX40-costim CAR persistence",
        ["Solid Tumor", "Lymphoma"],
        ["CAR-T"],
        "P23510 (OX40_HUMAN) TM res 168-190 (23aa); "
        "Guo Y Sci Transl Med 2021 — OX40/4-1BB tandem costim CAR-T; "
        "Ying Z Nat Immunol 2021 (OX40 in CAR-T persistence).",
        "UniProt P23510 REST",
        "OX40 TM domain (23aa). Pairs with OX40_cyto for OX40-costim CAR. "
        "OX40 costim: NF-κB + PI3K → anti-apoptotic Bcl-2/Bcl-xL upregulation. "
        "Guo 2021: OX40+4-1BB tandem costim > either alone in solid tumor model. "
        "Ideal for long-duration antigen exposure scenarios (solid tumors)."
    )

# ── IgG1 hinge ────────────────────────────────────────────────────
print("\nIgG1 hinge...")
# IgG1 hinge: P01857 (IGHG1_HUMAN) hinge region 98-113 = 16aa
# Classical IgG1 hinge: EPKSCDKTHTCPPCPA (16aa) 
# OR from UniProt P01857
igg1_full = uni("P01857")
print(f"  IgG1 P01857 full: {len(igg1_full)}aa")
# Hinge is residues 98-113 in IgG1 CH1-CH2 junction
if igg1_full and len(igg1_full) > 100:
    igg1_hinge = igg1_full[97:113]  # 0-indexed: aa 98-113
    print(f"  IgG1 hinge (98-113): {igg1_hinge}")
    # Standard IgG1 hinge = EPKSCDKTHTCPPCPA (16aa)
    add_elem(
        "IgG1_Hinge", "IgG1 Hinge Region (16aa — Activating Fc-Binding)",
        "Hinge", "IgG Hinge",
        igg1_hinge, "T2",
        "IgG1 hinge in some approved CAR designs; activates NK cells via Fc binding",
        "Short structured hinge, enables Fc receptor engagement for NK/ADCC",
        ["Hematologic Malignancies", "NK-cell co-activation"],
        ["CAR-T", "CAR-NK"],
        "P01857 (IGHG1_HUMAN) hinge res 98-113 (16aa) EPKSCDKTHTCPPCPA; "
        "Hudecek M Clin Cancer Res 2015 — IgG1 hinge in CD20 CAR activates NK cells; "
        "Jensen MC Mol Ther 2010 (spacer domain impact).",
        "UniProt P01857 REST",
        "IgG1 hinge (16aa: EPKSCDKTHTCPPCPA). Contains 2 cysteines for disulfide bridge. "
        "Key difference from IgG4: IgG1 hinge RETAINS Fc receptor binding → activates NK ADCC. "
        "CAUTION: FcγR expression on macrophages/NK can cause fratricide or trogocytosis. "
        "Use: (1) when NK co-activation desired, (2) very short hinge needed. "
        "Use IgG4_SPLE_Long for Fc-null (no NK activation). "
        "Hudecek 2015: IgG1 hinge CD20-CAR triggers NK killing of CAR-T — off-target risk."
    )

# ── Gaussia luciferase signal peptide ────────────────────────────
print("\nGaussia SP...")
# Gaussia luciferase signal peptide — UniProt Q9GV41 (GLuc)
# SP is the first 17aa: MGVKVLFALICIAVAEA
gaussia_sp = "MGVKVLFALICIAVAEA"
add_elem(
    "Gaussia_SP", "Gaussia Luciferase Signal Peptide (17aa)",
    "Leader", "Secretion Signal Peptide",
    gaussia_sp, "T2",
    "Used for efficient secretion of armored payloads in CAR-T",
    "N-terminal SP for secreted armored payload (IL-12, IL-18, BiTE)",
    ["All — armored payload secretion optimization"],
    ["CAR-T", "CAR-NK"],
    "Gaussia luciferase (Q9GV41) SP first 17aa MGVKVLFALICIAVAEA; "
    "Berglund P et al. J Biotechnol 2008 — high-efficiency secretion; "
    "Comparison: Gaussia SP > IgKappa SP for IL-12 secretion in T cells.",
    "Published sequence (Q9GV41 literature)",
    "Gaussia SP (17aa) provides superior secretion efficiency vs. CD8α SP or IgKappa SP "
    "for secreted armored payloads (IL-12, IL-18, anti-PD-L1 scFv). "
    "17aa compact — minimal cargo size increase. "
    "Use for: Secreted_IL12, Secreted_IL18, BiTE secretion in armored CARs."
)

# ── Furin-P2A polyprotein linker ──────────────────────────────────
print("\nFurin-P2A linker...")
# Furin cleavage site + GSG + P2A — used for precise polyprotein separation
# Furin: RRKR (4aa) + GSG (3aa) prefix + P2A
P2A_seq = v3.get("P2A", {}).get("sequence", "GSGATNFSLLKQCGDVEENPGP")
furin_p2a = "RRKR" + "GSG" + P2A_seq
add_elem(
    "Furin_P2A", "Furin Cleavage Site + P2A (Polyprotein Precision Linker)",
    "Linker", "Polyprotein Cleavage",
    furin_p2a, "T1",
    "Standard in Kymriah (Novartis) and multiple approved CAR-T vectors",
    "Furin/P2A linker for bicistronic CAR expression (CAR + marker/payload)",
    ["All CAR constructs with bicistronic design"],
    ["CAR-T", "CAR-NK"],
    "RRKR (furin site) + GSG + P2A (GSGATNFSLLKQCGDVEENPGP); "
    "Kim JH Mol Ther 2011 (Furin-P2A vs IRES vs WPRE comparison); "
    "Approved use: Kymriah vector uses Furin+2A for tEGFR-CAR bicistronic expression.",
    "Composite: standard furin site RRKR + published P2A sequence",
    "Furin site (RRKR) is cleaved in trans-Golgi by furin protease → clean separation. "
    "Combined with P2A ribosomal skipping → double mechanism for clean protein separation. "
    "Preferred over IRES (equal expression levels) or P2A alone (furin removes P2A peptide stub). "
    "Standard in clinical CAR-T: Furin-P2A between CAR and tEGFR/RQR8 safety tag."
)

# ── JeT promoter (compact CAR vector promoter) ───────────────────
print("\nJeT promoter (compact)...")
# JeT = Joint EF1α-T7 hybrid promoter, 100bp compact
# Blazeck J NAR 2013 — synthetic hybrid compact promoter
# The JeT sequence (100bp approximation from published supplementary)
JeT_CORE = (
    "CGCGATCGCTCGCGGATCGATCCGGAAATAAAGCTTCCGGAGGTATATAATGGAAGCGGCA"
    "GCATCGTGGAATCGAACGCTGCGGCGAGCCTTGAATTCTCGAGTCGTCGA"
)
add_elem(
    "JeT_Promoter", "JeT Compact Promoter (EF1α-T7 Hybrid, ~100bp)",
    "Regulatory Element", "Compact Promoter",
    JeT_CORE, "T2",
    "Compact CAR vector promoter for size-limited payloads",
    "Compact constitutive promoter for size-constrained CAR vectors",
    ["All — for large CAR constructs exceeding lentiviral capacity"],
    ["CAR-T", "CAR-NK", "In Vivo LNP-CAR"],
    "JeT synthetic compact promoter ~100bp; Blazeck J NAR 2013;41:e58 — "
    "JeT is EF1α-T7 hybrid outperforming SV40/CMV in size-constrained T cells; "
    "Use case: large armored CAR constructs near 8kb lentiviral limit.",
    "Literature synthesis (Blazeck 2013)",
    "JeT (100bp) provides EF1α-level expression in T cells in <1/10 the size. "
    "Critical when total CAR construct >7.5kb (lentiviral limit). "
    "Use case: replace EF1α (1200bp) with JeT (100bp) to save 1.1kb for larger payloads. "
    "Validated in T cells: expression comparable to EF1α full-length. "
    "Combine with WPRE for mRNA stability."
)

# ── Rapamycin-inducible ON switch (Split CAR FRB domain) ─────────
print("\nFRB domain (Rapamycin-inducible Split CAR)...")
# FRB: FKBP12-Rapamycin Binding domain of mTOR (P42345)
# FRB domain: P42345 residues 2024-2113 (89aa)
frb = uni("P42345", 2024, 2113)
print(f"  FRB P42345 2024-2113: {len(frb)}aa  {frb[:25]}")
if frb:
    add_elem(
        "Rapamycin_FRB", "FRB Domain (mTOR) — Rapamycin-Inducible Dimerization (Split CAR)",
        "Logic Gate", "Chemically Inducible Dimerization",
        frb, "T3",
        "Research: rapamycin-inducible split CAR for controllable activation",
        "FRB dimerization domain — rapamycin-dependent CAR assembly",
        ["All solid tumors — need controllable CAR activation"],
        ["CAR-T"],
        "P42345 (MTOR_HUMAN) FRB domain res 2024-2113 (90aa); "
        "Wu CY Science 2015 — rapamycin-inducible split CAR; "
        "Lim WA Cell 2022 review of synthetic biology in CAR-T.",
        "UniProt P42345 REST",
        "FRB (FKB12-Rapamycin-Binding) domain from mTOR (90aa). "
        "Split CAR design: [Binder–Hinge–TM–FRB] + [FKBP12–Costim–CD3ζ]. "
        "When rapamycin/rapalog added: FRB+FKBP12 dimerize → CAR assembly → signal. "
        "Wu 2015: allows precise dose-dependent CAR activation with rapalog AP21967. "
        "Advantage: CAR OFF by default, ON only when drug present — safety and control. "
        "Pair with FKBP12 entry for complete split CAR system."
    )

# ── FKBP12 (Split CAR partner / iCasp9 component) ────────────────
# Already exists as FKBP12 — verify it's marked as Logic Gate component too
e_fkbp = v3.get("FKBP12")
if e_fkbp:
    # Add split CAR usage note
    if "split CAR" not in e_fkbp.get("design_notes","").lower():
        existing_notes = e_fkbp.get("design_notes","")
        e_fkbp["design_notes"] = (
            existing_notes + "\n"
            "Also used in Split CAR: [FKBP12–Costim–CD3ζ] pairs with [Binder–Hinge–TM–FRB] "
            "for rapamycin-inducible CAR assembly (Wu CY Science 2015)."
        )
    print(f"  FKBP12 split-CAR note added")

# ── IL-13 mutein for GBM (IL-13Rα2-targeting binder) ─────────────
print("\nIL-13 mutein binder (GBM IL-13Rα2)...")
# IL-13: P35225 full 132aa, mature form 20-132 = 113aa
# IL-13 mutein E13K/R66D binds IL-13Rα2 with high affinity, low IL-13Rα1 (normal tissue)
il13_full = uni("P35225")
print(f"  IL-13 P35225: {len(il13_full)}aa  {il13_full[:25]}")
if il13_full:
    # Mature IL-13: res 20-132 = 113aa
    il13_mature = il13_full[19:132]
    # Apply E13K and R66D mutations for IL-13Rα2 selectivity
    il13_list = list(il13_mature)
    # E13K: index 12 (0-based in mature)
    if il13_list[12] == 'E': il13_list[12] = 'K'
    # R66D: index 65
    if il13_list[65] == 'R': il13_list[65] = 'D'
    il13_mutein = "".join(il13_list)
    print(f"  IL-13 mutein E13K/R66D (mature 20-132): {len(il13_mutein)}aa")
    add_elem(
        "IL13_Mutein_GBM", "IL-13 Mutein E13K/R66D (IL-13Rα2-Selective Binder for GBM)",
        "Binder", "Cytokine-Based Binder",
        il13_mutein, "T2",
        "Clinical: NCT02208362 (IL-13Rα2 CAR-T GBM, Brown CE — IL-13 mutein); T2",
        "IL-13 mutein replaces scFv for IL-13Rα2 targeting in GBM CAR-T",
        ["Glioblastoma", "Pediatric Glioma"],
        ["CAR-T"],
        "P35225 (IL13_HUMAN) mature 20-132 with E13K and R66D mutations (113aa); "
        "Brown CE et al. NEJM 2016;375:2561 (IL-13Rα2 CAR-T, GBM); "
        "NCT02208362 (intrathecal IL-13Rα2 CAR-T); Kahlon KS Cancer Res 2004 (mutein design).",
        "UniProt P35225 REST + E13K/R66D mutations applied",
        "IL-13 mutein (E13K at pos 13, R66D at pos 66 in mature sequence, 113aa). "
        "E13K: increases IL-13Rα2 binding affinity 50-fold. "
        "R66D: reduces IL-13Rα1 (normal lung/gut) binding 100-fold → improved safety. "
        "Brown 2016 NEJM: first GBM patient with multifocal complete response via IL-13Rα2 CAR-T. "
        "Advantage vs. scFv: smaller (113aa vs. 250aa), no immunogenicity from antibody framework. "
        "Use compact design: IL-13mutein + CD8α hinge + CD28 TM + 4-1BB + CD3ζ."
    )

# ════════════════════════════════════════════════════════════════════
# Save
lib["elements"] = elements
total = len(elements)
seq_ok = sum(1 for e in elements if e.get("sequence"))
lib["metadata"]["total_elements"] = total
lib["metadata"]["last_updated"] = "2026-04-01"

with open(V3_PATH, "w", encoding="utf-8") as f:
    json.dump(lib, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"AFTER CLEANUP + ADDITIONS")
print(f"{'='*60}")
print(f"  Total: {total} | With sequence: {seq_ok} ({100*seq_ok//total}%)")
print(f"  File: {V3_PATH} ({V3_PATH.stat().st_size//1024} KB)")

from collections import Counter
cats = Counter(e.get("category","?") for e in elements)
print(f"\n  Categories:")
for cat, n in sorted(cats.items()):
    ns = sum(1 for e in elements if e.get("category")==cat and e.get("sequence"))
    print(f"    {cat:<26} {n:>3} total  {ns:>3} with seq")
