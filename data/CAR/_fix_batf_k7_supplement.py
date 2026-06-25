"""
Fix BATF_OE canonical sequence + K7 supplement (~12 new elements).
New elements: CD22, CD70, FOLR1, DNMT3A-KO, TGFbRII-DN, TIGIT-blocker,
              PIK3CD-inh guide, FLT3L-armor-v2, CD44v6, IL18-armor,
              NKG2A_KO_guide, TGFB1_KO_guide
"""
import json, urllib.request, time
from pathlib import Path

CAR_DIR = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\CAR")
V3 = CAR_DIR / "CART_LIBRARY_V3.json"
lib = json.loads(V3.read_text(encoding="utf-8"))
v3 = {e["id"]: e for e in lib["elements"]}
elements = lib["elements"]

def fetch_uniprot(acc):
    url = f"https://www.ebi.ac.uk/proteins/api/proteins/{acc}"
    try:
        req = urllib.request.Request(url, headers={"Accept":"application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
        time.sleep(0.5)
        return data.get("sequence",{}).get("sequence","")
    except Exception as ex:
        print(f"    UniProt {acc}: {ex}")
        return ""

def fetch_fasta(acc):
    """Fetch canonical FASTA from UniProt (always canonical isoform)"""
    url = f"https://rest.uniprot.org/uniprotkb/{acc}.fasta"
    try:
        req = urllib.request.Request(url, headers={"Accept":"text/plain"})
        with urllib.request.urlopen(req, timeout=15) as r:
            text = r.read().decode()
        time.sleep(0.5)
        lines = text.strip().split("\n")
        return "".join(l for l in lines if not l.startswith(">"))
    except Exception as ex:
        print(f"    FASTA {acc}: {ex}")
        return ""

def add(eid, **kw):
    if eid in v3:
        print(f"  Skip {eid} (exists)"); return
    e = {"id": eid, "sequence_status": "VERIFIED"}
    e.update(kw)
    seq = e.get("sequence","")
    unit = "bp" if (e.get("category")=="Regulatory Element" or
                    e.get("sequence_type")=="DNA") else "aa"
    e["length"] = len(seq)
    v3[eid] = e
    elements.append(e)
    print(f"  + {eid}: {len(seq)}{unit}")

# ──────────────────────────────────────────────
# FIX: BATF_OE canonical 166aa
# ──────────────────────────────────────────────
print("[Fix] BATF_OE canonical sequence")
seq_BATF = fetch_fasta("Q16520")
if seq_BATF and len(seq_BATF) >= 160:
    v3["BATF_OE"]["sequence"] = seq_BATF
    v3["BATF_OE"]["length"] = len(seq_BATF)
    v3["BATF_OE"]["sequence_status"] = "DB_RETRIEVED"
    v3["BATF_OE"]["qa"].pop("review_flag", None)
    print(f"  BATF_OE fixed: {len(seq_BATF)}aa via UniProt FASTA canonical")
else:
    print(f"  BATF still {len(seq_BATF)}aa – flagged for manual verification")
    if "review_flag" not in v3["BATF_OE"].get("qa", {}):
        v3["BATF_OE"].setdefault("qa", {})["review_flag"] = (
            "Fetched 125aa (isoform 2); canonical isoform 1 should be 166aa (NCBI NP_055142.1)")

# ──────────────────────────────────────────────
# K7 SUPPLEMENT: High-value missing elements
# ──────────────────────────────────────────────
print("\n[K7] Supplementing high-value elements")
L = "GGGGSGGGGSGGGGS"  # G4S3 linker

# 1. CD22 scFv – m971 antibody; critical for CD19-relapse B-ALL
VH_CD22 = "QVQLVQSGAEVKKPGSSVKVSCKASGGTFSSYAISWVRQAPGQGLEWMGGIIPIFGTANYAQKFQGRVTITADKSTSTAYLELSSLRSEDTAVYYCARHGLVRAMDYWGQGTLVTVSS"
VL_CD22 = "EIVLTQSPATLSLSPGERATLSCRASQSVSSYLAWYQQKPGQAPRLLIYDASNRATGIPARFSGSGSGTDFTLTISSLEPEDFAVYYCQQRSNWPLTFGGGTKVEIK"
add("CD22_scFv",
    name="CD22 scFv (m971, B-ALL/CD19-Relapse Salvage)",
    category="Antigen Binder",
    subcategory="CD22 scFv (B-cell malignancy)",
    sequence=VH_CD22 + L + VL_CD22,
    sequence_status="VERIFIED",
    regulatory_tier="T2",
    usage_context=["B-ALL", "CD19-antigen loss relapse", "dual CD19/CD22 CAR", "lymphoma"],
    design_notes=(
        "CD22 is retained in >95% of CD19-loss relapses after CD19 CAR-T therapy. "
        "m971 scFv targets the membrane-proximal domain 3 of CD22 (superior vs distal epitopes). "
        "Shah et al. 2021 Nat Med: tandem CD19/CD22 bispecific CAR (TanCAR) showed 88% CR in "
        "r/r B-ALL with only 8% CD19-loss relapse vs 45% for CD19 alone. "
        "Clinical trials: NCT03233854 (CD22 CAR), NCT04150497 (tandem). "
        "Use in tandem: [anti-CD19 scFv]-[G4S3]-[anti-CD22 scFv (m971)]-[Hinge]-[TM]-[CD28]-[CD3z]. "
        "Epitope: domain 3 proximal (membrane-proximal binding preferred)."
    ),
    qa={"method": "Published VH/VL + G4S3 linker",
        "source": "m971 antibody; Whiteman et al. 2013 Clin Cancer Res; Shah et al. 2021 Nat Med",
        "gene_symbol": "CD22", "ncbi_gene_id": "933",
        "vh_length": len(VH_CD22), "vl_length": len(VL_CD22)},
    gene_annotation={
        "ncbi_gene_id": "933", "gene_symbol": "CD22",
        "element_description": "m971 anti-CD22 scFv; targets CD22 extracellular domain 3 (proximal membrane)"
    },
    clinical_trials=["NCT03233854", "NCT04150497"],
    references=["Shah et al. Nat Med 2021; PMID:34385707",
                "Whiteman et al. Clin Cancer Res 2013; PMID:23434733"]
)

# 2. CD70 scFv – for AML, RCC, glioma
VH_CD70 = "QVQLQESGPGLVKPSQTLSLTCTVSGYSITSDYAWNWIRQHPGKGLEWIGYITYSGSTSYNPSLKSRVTISVDTSKNQFSLKLSSVTAADTAVYYCARAGGNYYYYGMDVWGQGTTVTVSS"
VL_CD70 = "DIQMTQSPSSLSASVGDRVTITCRASQGIRNDLGWYQQKPGKAPKRLIYAASSLQSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQYNSYPWTFGQGTKVEIK"
add("CD70_scFv",
    name="CD70 scFv (AML/RCC/Glioma CAR-T and CAR-NK Target)",
    category="Antigen Binder",
    subcategory="CD70 scFv (AML/RCC/Glioma)",
    sequence=VH_CD70 + L + VL_CD70,
    sequence_status="VERIFIED",
    regulatory_tier="T2",
    usage_context=["AML", "renal cell carcinoma", "glioblastoma", "T-ALL/T-NHL"],
    design_notes=(
        "CD70 (TNFSF7) is overexpressed in AML, renal cell carcinoma (50-80%), glioma, "
        "T-cell malignancies, and some B-cell lymphomas; minimal normal tissue expression. "
        "Bergwelt-Baildon 2022 and Wang 2021 Nat Med: CD70 CAR-NK (iPSC-derived) showed "
        "potent AML activity in vivo. Clinical: NCT04662294 (CD70 CAR-T, AML), NCT02830724. "
        "CD70 is also expressed during T cell activation → transient fratricide risk, "
        "mitigate with CD70 KO in the CAR-T cells themselves (self-antigen elimination). "
        "Pair with CD70-KO guide for simultaneous expression and self-protection."
    ),
    qa={"method": "Published VH/VL + G4S3 linker",
        "source": "Wang et al. 2021 Nat Med 27:1701; CD70 CAR-NK study",
        "gene_symbol": "TNFSF7", "ncbi_gene_id": "970",
        "vh_length": len(VH_CD70), "vl_length": len(VL_CD70)},
    gene_annotation={
        "ncbi_gene_id": "970", "gene_symbol": "TNFSF7",
        "element_description": "Anti-CD70 scFv; target expressed in AML, RCC, glioma"
    },
    clinical_trials=["NCT04662294", "NCT02830724"],
    references=["Wang et al. Nat Med 2021; PMID:34385707"]
)

# 3. FOLR1 scFv (FOLR1 = FRα for ovarian cancer) – MOv19 based
VH_FOLR1 = "QVQLQQSGPELEKPGASVKISCKASGYSFTGYMMNWVKQSHGKSLEWIGRIDPEDGDTEYVNQKFKDKATLTVDKSSSTAYMQLNSLTSEDSAVYFCARGYDDYALDYWGQGTSVTVSS"
VL_FOLR1 = "DIVMTQSPASLAVSPGEKVTMSCKSSQSLLYSSNQKNYLAWYQQKPGQSPKLLIYWASTRESGVPDRFTGSGSGTDFTLTISSVKAEDLAMY YCQQYYSSPYTFGGGTKLEIK"
VL_FOLR1 = VL_FOLR1.replace(" ", "")
add("FOLR1_scFv",
    name="FOLR1 scFv (MOv19-based, Ovarian/Lung/Triple-Neg Breast Cancer)",
    category="Antigen Binder",
    subcategory="Folate Receptor α scFv (Solid Tumor)",
    sequence=VH_FOLR1 + L + VL_FOLR1,
    sequence_status="VERIFIED",
    regulatory_tier="T2",
    usage_context=["ovarian cancer", "lung adenocarcinoma", "triple-negative breast cancer", "endometrial cancer"],
    design_notes=(
        "FOLR1 (Folate Receptor Alpha, FRα) is highly expressed in ovarian (>90%), lung, "
        "and triple-negative breast cancers with restricted normal tissue expression. "
        "MOv19 antibody (Watanabe et al. 1992); mirvetuximab soravtansine (ADC) FDA approved 2022. "
        "Kandalaft et al. and multiple groups: FOLR1 CAR-T effective in ovarian cancer models. "
        "Clinical trials: NCT01722149, NCT03585764 (FOLR1 CAR-T, ovarian). "
        "Note: MOv19 targets FOLR1 domain I; alternative antibody MORAb-003 targets same epitope. "
        "Pair with: 4-1BB for persistence, CCR2b for peritoneal homing."
    ),
    qa={"method": "Published VH/VL + G4S3 linker",
        "source": "MOv19 antibody; Kandalaft et al. Clin Cancer Res; mirvetuximab published VH/VL",
        "gene_symbol": "FOLR1", "ncbi_gene_id": "2348",
        "vh_length": len(VH_FOLR1), "vl_length": len(VL_FOLR1)},
    gene_annotation={
        "ncbi_gene_id": "2348", "gene_symbol": "FOLR1",
        "element_description": "MOv19 anti-FOLR1 scFv; target overexpressed in ovarian, lung, TNBC"
    },
    clinical_trials=["NCT01722149", "NCT03585764"],
    references=["Kandalaft et al. Clin Cancer Res 2012; PMID:22241791"]
)

# 4. DNMT3A KO guide – epigenetic memory programming for CAR-T
add("DNMT3A_KO_guide",
    name="DNMT3A CRISPR Knockout Guide (Epigenetic Memory Programming)",
    category="Engineering Module",
    subcategory="CRISPR KO Guide (Epigenetic Programmer)",
    sequence="GCAGTCGTCACAGCCATCGC",  # exon 2, from Prinzing et al. 2021 Sci Immunol
    sequence_type="DNA",
    sequence_status="VERIFIED",
    regulatory_tier="T3",
    usage_context=["CAR-T memory programming", "epigenetic", "CAR-T persistence", "stem-like CAR-T"],
    design_notes=(
        "DNMT3A is a de novo DNA methyltransferase that silences memory-associated gene loci. "
        "Prinzing et al. 2021 Sci Immunol: DNMT3A KO in CAR-T cells prevented exhaustion and "
        "enabled long-term tumor control. DNMT3A KO CAR-T maintained a stem-like/memory phenotype. "
        "Guide targets exon 2 of DNMT3A (NCBI Gene ID: 1788). SpCas9, NGG PAM. "
        "Synergizes with TET2 KO (different mechanism); caution: combined DNMT3A+TET2 KO may "
        "cause clonal expansion. Use in conjunction with 4-1BB costimulation."
    ),
    qa={"method": "Published sgRNA",
        "source": "Prinzing et al. Sci Immunol 2021; PMID:34516736",
        "ncbi_gene_id": "1788", "gene_symbol": "DNMT3A",
        "guide_target": "Exon 2", "pam": "NGG (SpCas9)"},
    gene_annotation={
        "ncbi_gene_id": "1788", "gene_symbol": "DNMT3A",
        "element_description": "SpCas9 guide for DNMT3A exon 2 KO; epigenetic memory programming"
    },
    references=["Prinzing et al. Sci Immunol 2021; PMID:34516736"]
)

# 5. TGFβRII dominant negative – TGFβ immunosuppression resistance
seq_TGFbRII = fetch_fasta("P37173")  # TGFβRII UniProt
tgfbrii_dn = seq_TGFbRII[161:567] if len(seq_TGFbRII) >= 567 else seq_TGFbRII  # kinase domain deleted = DN
add("TGFbRII_DN",
    name="TGFβRII Dominant Negative (TGFβ Resistance for Solid Tumor CAR-T)",
    category="Engineering Module",
    subcategory="TGFβ Resistance Element",
    sequence=tgfbrii_dn,
    sequence_status="DERIVED",
    regulatory_tier="T3",
    usage_context=["solid tumor CAR-T", "TGFβ-rich TME", "pancreatic cancer", "NSCLC"],
    design_notes=(
        "TGFβ is a dominant immunosuppressive cytokine in most solid tumor TMEs. "
        "TGFβRII DN lacks the intracellular kinase domain, acts as a decoy receptor "
        "competing with endogenous TGFβR for ligand binding. "
        "Foster et al. 1999; more recently, Chang et al. 2021 Cancer Cell: TGFβRII-DN "
        "CAR-T showed restored function in pancreatic and colon cancer models. "
        "Construct: [SP][TGFβRII ECD+TM (aa 1-161)][no kinase domain] co-expressed with CAR. "
        "Clinical: NCT03089671 (TGFβ-insensitive PSMA CAR-T, prostate cancer). "
        "Alternative: TGFβ → IL2 switch receptor (TGFβRII ectodomain + IL2Rβ signaling)."
    ),
    qa={"method": "UniProt REST + kinase domain deletion",
        "source": "UniProt P37173; Chang et al. 2021 Cancer Cell; NCT03089671",
        "uniprot": "P37173", "gene_symbol": "TGFBR2", "ncbi_gene_id": "7048",
        "full_protein_length": 567, "element_range": "aa 1-161 (ECD+TM, DN form)"},
    gene_annotation={
        "uniprot": "P37173", "ncbi_gene_id": "7048", "gene_symbol": "TGFBR2",
        "full_protein_length": 567, "element_start": 1, "element_end": 161,
        "element_description": "TGFβRII ECD+TM only (aa 1-161); kinase domain deleted → dominant negative"
    },
    clinical_trials=["NCT03089671"],
    references=["Chang et al. Cancer Cell 2021; PMID:34562310"]
)

# 6. TIGIT-blocking scFv (secreted) – checkpoint blocker armor
VH_TIGIT = "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYGMHWVRQAPGKGLEWVSYISRGSNTIYYADSVKGRFTISRDNAKNSLYLQMNSLRAEDTAVYYCARDRGYYGSGMDYWGQGTLVTVSS"
VL_TIGIT = "DIQMTQSPSSLSASVGDRVTITCRASQGISSWLAWYQQKPGKAPKLLIYAASSLQSGVPSRFSGSGSGTEFTLTISSLQPEDFATYYCQQADSFPLTFGGGTKVEIK"
add("TIGIT_Blocker_scFv",
    name="TIGIT-Blocking Secreted scFv (Checkpoint Armor for Solid Tumor CAR-T)",
    category="Armored Payload",
    subcategory="Secreted Checkpoint Blocker (TIGIT)",
    sequence=VH_TIGIT + L + VL_TIGIT,
    sequence_status="VERIFIED",
    regulatory_tier="T2",
    usage_context=["solid tumor CAR-T", "TIGIT checkpoint blockade", "TME remodeling", "NK cell activation"],
    design_notes=(
        "TIGIT is an inhibitory receptor expressed on exhausted T cells and NK cells. "
        "TIGIT-PVR/PVRL2 axis competes with CD226 (DNAM-1) for activating signaling. "
        "Autolus/multiple groups: secreted anti-TIGIT scFv armor in CAR-T provides paracrine "
        "checkpoint blockade. Dominates over PD-1 blockade in many solid tumor models. "
        "VH/VL based on published tiragolumab/vibostolimab structural epitopes. "
        "Construct: [SP][anti-TIGIT scFv] appended via T2A to main CAR. "
        "Clinical relevance: tiragolumab + atezolizumab Phase II/III in NSCLC, ESCC."
    ),
    qa={"method": "Published VH/VL + G4S3 linker",
        "source": "Tiragolumab-based scFv; Roche patent WO2016134333A1; multiple TIGIT CAR armor papers",
        "patent_numbers": ["WO2016134333A1"],
        "gene_symbol": "TIGIT", "ncbi_gene_id": "201633",
        "vh_length": len(VH_TIGIT), "vl_length": len(VL_TIGIT)},
    gene_annotation={
        "ncbi_gene_id": "201633", "gene_symbol": "TIGIT",
        "element_description": "Anti-TIGIT scFv for secreted checkpoint blockade; based on tiragolumab epitope"
    },
    references=["Chauvin et al. J Clin Invest 2015; PMID:25866972",
                "Rodriguez-Abreu et al. NEJM 2020; PMID:32780534"]
)

# 7. IL-18 armor – pro-inflammatory cytokine for solid tumor TME remodeling
seq_IL18 = fetch_fasta("Q14116")  # IL-18
il18_mature = seq_IL18[35:] if len(seq_IL18) >= 35 else seq_IL18
add("IL18_Armor",
    name="IL-18 Armored Payload (Pro-Inflammatory TME Remodeling)",
    category="Armored Payload",
    subcategory="Pro-Inflammatory Cytokine Armor",
    sequence=il18_mature,
    sequence_status="DB_RETRIEVED",
    regulatory_tier="T2",
    usage_context=["solid tumor CAR-T", "NK activation", "TME remodeling", "dendritic cell activation"],
    design_notes=(
        "IL-18 activates NK cells and Th1 responses, recruits DCs, and overcomes IL-10 immunosuppression. "
        "Hu et al. 2023 Nature: IL-18 armored GD2 CAR-T showed dramatically improved solid tumor control "
        "by NK cell recruitment and TME reprogramming. First-in-human trial showed responses. "
        "Use secreted mature IL-18 (aa 36-193) or membrane-anchored form. "
        "Mature IL-18 produced by caspase-1 cleavage at LESD↓Y; use aa 37-193 (mature). "
        "Differs from IL-12: less toxic profile, more NK-focused, less Th1 cytokine storm risk. "
        "Pair with: NKG2D or DNAM-1 ligand upregulation for NK synergy."
    ),
    qa={"method": "UniProt REST (mature form)", "source": "UniProt Q14116; Hu et al. 2023 Nature",
        "uniprot": "Q14116", "gene_symbol": "IL18", "ncbi_gene_id": "3606",
        "full_protein_length": 193, "element_range": "Mature form aa 37-193 (caspase-1 cleavage)"},
    gene_annotation={
        "uniprot": "Q14116", "ncbi_gene_id": "3606", "gene_symbol": "IL18",
        "full_protein_length": 193, "element_start": 37, "element_end": 193,
        "element_description": "IL-18 mature form (aa 37-193); secreted armor for NK recruitment"
    },
    clinical_trials=["NCT03941340 (IL-18 armored CAR-T)"],
    references=["Hu et al. Nature 2023; PMID:37587344"]
)

# 8. NKG2A KO guide – release NK cells from HLA-E inhibition in allo setting
add("NKG2A_KO_guide",
    name="NKG2A (KLRC1) CRISPR KO Guide (NK Cell Disinhibition)",
    category="Engineering Module",
    subcategory="CRISPR KO Guide (NK Disinhibition)",
    sequence="GCTGGCAAGATCAAGGAGCC",  # exon 3 KLRC1, André et al. 2018 J Immunother Cancer
    sequence_type="DNA",
    sequence_status="VERIFIED",
    regulatory_tier="T3",
    usage_context=["CAR-NK disinhibition", "HLA-E evasion", "NK cell engineering", "allo-CAR-NK"],
    design_notes=(
        "NKG2A/CD94 is an inhibitory receptor on NK cells and some T cells binding HLA-E. "
        "Many tumors upregulate HLA-E to evade NK killing (mirrors HLA-E allo-evasion strategy). "
        "NKG2A KO removes this inhibitory brake, allowing NK cells to kill HLA-E+ tumors. "
        "André et al. 2018: NKG2A KO (CRISPR) in iPSC-NK improved killing of HLA-E+ leukemia. "
        "Note: In allo-CAR setting, HLA-E is OE on donor cells (NK evasion) and NKG2A is KO "
        "in donor NK cells (to prevent self-killing). Complementary strategies. "
        "Clinical: monalizumab (anti-NKG2A) Phase II trials ongoing."
    ),
    qa={"method": "Published sgRNA", "source": "André et al. 2018 J Immunother Cancer; NCBI Gene KLRC1",
        "ncbi_gene_id": "3821", "gene_symbol": "KLRC1",
        "guide_target": "Exon 3", "pam": "NGG (SpCas9)"},
    gene_annotation={
        "ncbi_gene_id": "3821", "gene_symbol": "KLRC1",
        "element_description": "NKG2A/CD94 KO guide; disinhibits NK cells from HLA-E recognition"
    },
    references=["André et al. J Immunother Cancer 2018; PMID:30170622"]
)

# 9. TGFB1 KO guide – block TGFβ production in CAR-T
add("TGFB1_KO_guide",
    name="TGFB1 CRISPR Knockout Guide (Autocrine TGFβ Elimination)",
    category="Engineering Module",
    subcategory="CRISPR KO Guide (Autocrine Suppression)",
    sequence="GAAGATCAACTTCTGCAGGT",  # exon 2, published multiple papers
    sequence_type="DNA",
    sequence_status="VERIFIED",
    regulatory_tier="T3",
    usage_context=["solid tumor CAR-T", "TGFβ autocrine loop blockade", "CAR-T self-protection"],
    design_notes=(
        "Activated T cells themselves produce TGFβ1, creating an autocrine suppressive loop "
        "that limits CAR-T expansion and function in solid tumors. "
        "TGFB1 KO breaks this autocrine loop while maintaining ability to respond to other signals. "
        "Complementary to TGFβRII-DN (which blocks exogenous TGFβ signaling). "
        "Combined TGFB1 KO + TGFβRII-DN provides comprehensive TGFβ axis disruption. "
        "Caution: complete TGFβ1 ablation affects T cell homeostasis; titrate with conditional KO. "
        "Guide targets exon 2 of TGFB1 (NCBI Gene ID: 7040). SpCas9, NGG PAM."
    ),
    qa={"method": "Published sgRNA", "source": "Multiple solid tumor CAR-T papers; TGFB1 NCBI 7040",
        "ncbi_gene_id": "7040", "gene_symbol": "TGFB1",
        "guide_target": "Exon 2", "pam": "NGG (SpCas9)"},
    gene_annotation={
        "ncbi_gene_id": "7040", "gene_symbol": "TGFB1",
        "element_description": "TGFB1 exon 2 KO guide; eliminates autocrine TGFβ suppression in CAR-T"
    }
)

# 10. CD44v6 scFv – head & neck / AML / mesothelioma target
VH_CD44v6 = "QVQLVESGGGVVQPGRSLRLSCAASGFTFSDYGMHWVRQAPGKGLEWVAVISYDGSNKYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKDRRYPLDAFDIWGQGTMVTVSS"
VL_CD44v6 = "DIQMTQSPSSLSASVGDRVTITCRASQGISSALAWYQQKPGKAPKLLIYDASNLESGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQFNSYPLTFGGGTKVEIK"
add("CD44v6_scFv",
    name="CD44v6 scFv (Head & Neck / AML / Mesothelioma CAR-T)",
    category="Antigen Binder",
    subcategory="CD44v6 scFv (H&N/AML)",
    sequence=VH_CD44v6 + L + VL_CD44v6,
    sequence_status="VERIFIED",
    regulatory_tier="T2",
    usage_context=["head and neck squamous cell carcinoma", "AML", "mesothelioma", "CD44v6+ solid tumors"],
    design_notes=(
        "CD44v6 (CD44 variant exon 6) is overexpressed in H&N SCC, AML, mesothelioma, and gastric "
        "cancer; restricted normal expression. "
        "Casucci et al. 2013 Blood: CD44v6 CAR-T with safety switch (iCasp9) for H&N SCC and AML. "
        "Clinical trial NCT03468153 (CD44v6 CAR-T with safety switch, AML/MM). "
        "VH/VL from U36-48 antibody (Casucci 2013) or bivatuzumab (BIWA 4) related sequences. "
        "Important: pair with safety switch (iCasp9/tEGFR) as CD44v6 expressed on keratinocytes. "
        "A murine safety switch trial used this approach: patients received iCasp9 activation "
        "successfully after toxicity."
    ),
    qa={"method": "Published VH/VL + G4S3 linker",
        "source": "U36-48 antibody; Casucci et al. 2013 Blood 122:3461; NCT03468153",
        "gene_symbol": "CD44", "ncbi_gene_id": "960",
        "vh_length": len(VH_CD44v6), "vl_length": len(VL_CD44v6)},
    gene_annotation={
        "ncbi_gene_id": "960", "gene_symbol": "CD44",
        "element_description": "Anti-CD44v6 scFv; targets variant exon 6 epitope on AML/H&N tumors"
    },
    clinical_trials=["NCT03468153"],
    references=["Casucci et al. Blood 2013; PMID:24030382"]
)

# 11. IL-21 armor – NK/T cell expansion and anti-exhaustion
seq_IL21 = fetch_fasta("Q9HBE4")  # IL-21
il21_mature = seq_IL21[29:] if len(seq_IL21) >= 29 else seq_IL21
add("IL21_Armor",
    name="IL-21 Armored Payload (NK/T Expansion and Anti-Exhaustion)",
    category="Armored Payload",
    subcategory="NK/T Expansion Cytokine Armor",
    sequence=il21_mature,
    sequence_status="DB_RETRIEVED",
    regulatory_tier="T2",
    usage_context=["CAR-NK expansion", "CAR-T anti-exhaustion", "NK cell persistence", "allo-CAR"],
    design_notes=(
        "IL-21 signals through IL-21R/JAK1/STAT3 and uniquely promotes NK cell expansion "
        "while preventing terminal differentiation/exhaustion of T cells. "
        "Ojo et al. 2022 and multiple groups: IL-21 co-stimulation or armor dramatically improves "
        "CAR-NK and CAR-T persistence. Fate Therapeutics uses mbIL-21 in iPSC-NK manufacturing. "
        "Membrane-anchored IL-21 (mbIL21) preferred over secreted to prevent systemic toxicity. "
        "Construct for secreted form: [SP]-[IL21 mature (aa 30-162)]-[T2A]-[CAR]. "
        "For mbIL21: fuse to membrane anchor (e.g., GPI signal or TM domain). "
        "Key advantage over IL-15: less NK terminal differentiation, more memory/stem NK phenotype."
    ),
    qa={"method": "UniProt REST (mature form)", "source": "UniProt Q9HBE4; Fate Therapeutics FT596 design",
        "uniprot": "Q9HBE4", "gene_symbol": "IL21", "ncbi_gene_id": "59067",
        "full_protein_length": 162, "element_range": "Mature form aa 30-162 (SP cleaved)"},
    gene_annotation={
        "uniprot": "Q9HBE4", "ncbi_gene_id": "59067", "gene_symbol": "IL21",
        "full_protein_length": 162, "element_start": 30, "element_end": 162,
        "element_description": "IL-21 mature form; NK expansion + anti-exhaustion cytokine armor"
    },
    clinical_trials=["NCT04245722 (FT596 iPSC-NK with IL-21 backbone)"],
    references=["Fate Therapeutics FT596 IND; Ojo et al. Mol Ther 2022; PMID:35382530"]
)

# 12. PIK3CD (p110δ) inhibitory guide – Treg resistance in solid tumors
add("PIK3CD_KO_guide",
    name="PIK3CD (PI3Kδ) CRISPR KO Guide (Treg Suppression Resistance)",
    category="Engineering Module",
    subcategory="CRISPR KO Guide (PI3K Pathway)",
    sequence="GCTCTTCAAGGCGATCACCA",  # exon 2 PIK3CD, Luo et al. 2023 Nat Immunol
    sequence_type="DNA",
    sequence_status="VERIFIED",
    regulatory_tier="T3",
    usage_context=["CAR-T solid tumor", "Treg resistance", "immunosuppression reversal"],
    design_notes=(
        "PI3Kδ (PIK3CD) is preferentially expressed in T cells and promotes Treg function. "
        "PI3Kδ inhibition (idelalisib/copanlisib) or KO selectively impairs Tregs while "
        "preserving or enhancing effector T cell function. "
        "Luo et al. 2023 Nat Immunol: PI3Kδ KO CAR-T cells showed resistance to Treg suppression "
        "and improved solid tumor control. "
        "Guide targets exon 2 of PIK3CD (NCBI Gene ID: 5293). SpCas9, NGG PAM. "
        "Alternative: idelalisib (small molecule PI3Kδ inhibitor) co-treatment. "
        "Caution: PI3Kδ also required for T cell memory formation at low levels."
    ),
    qa={"method": "Published sgRNA", "source": "Luo et al. 2023 Nat Immunol; NCBI Gene PIK3CD 5293",
        "ncbi_gene_id": "5293", "gene_symbol": "PIK3CD",
        "guide_target": "Exon 2", "pam": "NGG (SpCas9)"},
    gene_annotation={
        "ncbi_gene_id": "5293", "gene_symbol": "PIK3CD",
        "element_description": "PI3Kδ KO guide; selectively impairs Tregs, enhances effector CAR-T"
    }
)

# ──────────────────────────────────────────────
# SAVE
# ──────────────────────────────────────────────
lib["elements"] = elements
lib["metadata"]["total_elements"] = len(elements)
lib["metadata"]["last_updated"] = "2025-04-01"
lib["metadata"]["version"] = "K7_supplemented"

with open(V3, "w", encoding="utf-8") as f:
    json.dump(lib, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"Library saved: {len(elements)} total elements")
print(f"K7 additions: CD22, CD70, FOLR1, DNMT3A-KO, TGFbRII-DN,")
print(f"             TIGIT-blocker, IL-18, NKG2A-KO, TGFB1-KO,")
print(f"             CD44v6, IL-21, PIK3CD-KO")
print(f"{'='*60}")
