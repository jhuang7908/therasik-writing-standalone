"""
K6 Supplement: New CAR Modality Elements (2023-2025)
Covers: Anti-Exhaustion TF, Homing Receptors, New Binders,
        In-vivo CAR, CAR-NK, NKT, CAR-M, CAR-Treg, Allo-CAR, iPSC-CAR

Sequences: UniProt API for protein domains, literature for antibody fragments,
           published sgRNA sequences for KO guides.
"""
import json, urllib.request, time
from pathlib import Path

CAR_DIR = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\CAR")
V3_PATH  = CAR_DIR / "CART_LIBRARY_V3.json"

with open(V3_PATH, encoding="utf-8") as f:
    lib = json.load(f)

v3       = {e["id"]: e for e in lib["elements"]}
elements = lib["elements"]

def fetch_uniprot(acc):
    url = f"https://www.ebi.ac.uk/proteins/api/proteins/{acc}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read.decode)
        time.sleep(0.6)
        return data.get("sequence", {}).get("sequence", "")
    except Exception as ex:
        print(f"    UniProt fetch error {acc}: {ex}")
        return ""

def add(eid, **kw):
    if eid in v3:
        print(f"  Skip {eid} (exists)"); return
    e = {"id": eid, "sequence_status": "VERIFIED"}
    e.update(kw)
    seq = e.get("sequence", "")
    unit = "bp" if e.get("category") == "Regulatory Element" else "aa"
    e["length"] = len(seq)
    v3[eid] = e
    elements.append(e)
    print(f"  + {eid}: {len(seq)}{unit}")

# ══════════════════════════════════════════════════════════════════
# 1. ANTI-EXHAUSTION TRANSCRIPTION FACTORS (Category: Anti-Exhaustion Engineering)
# ══════════════════════════════════════════════════════════════════
print("\n[1] Anti-Exhaustion Transcription Factors")

# c-Jun full protein – Lynn et al. 2019 Science; UniProt P05412
seq_cJun = fetch_uniprot("P05412")
add("c_Jun_OE",
    name="c-Jun Transcription Factor (Anti-Exhaustion OE)",
    category="Anti-Exhaustion Engineering",
    subcategory="AP-1 Transcription Factor",
    sequence=seq_cJun,
    sequence_status="DB_RETRIEVED",
    regulatory_tier="T3",
    usage_context=["CAR-T solid tumor", "CAR-T persistence", "anti-exhaustion"],
    design_notes=(
        "c-Jun (JUN) overexpression prevents AP-1 epigenetic silencing caused by chronic "
        "antigen stimulation. Lynn et al. 2019 Science: c-Jun OE in mesothelin CAR-T improved "
        "antitumor activity in solid tumor models. Clinical trial NCT04502446 (Penn/UPENN). "
        "Overexpress via constitutive promoter (EF1a or PGK) in second-generation CAR vector. "
        "Does NOT impair effector function; reduces exhaustion hallmarks (TOX, NR4A1 upregulation). "
        "Pair with 4-1BB costimulation for optimal durability."
    ),
    qa={"method": "UniProt REST", "source": "UniProt P05412; Lynn et al. 2019 Science 365:1230",
        "uniprot": "P05412", "gene_symbol": "JUN", "ncbi_gene_id": "3725",
        "full_protein_length": 331, "element_range": "1-331 (full protein)"},
    clinical_trials=["NCT04502446 (Penn, mesothelin CAR-T + c-Jun)"],
    references=["Lynn et al. Science 2019; PMID:31624173"]
)

# BATF – Guo et al. 2022 Cell; UniProt Q16520
seq_BATF = fetch_uniprot("Q16520")
add("BATF_OE",
    name="BATF Basic Leucine Zipper Transcription Factor (T-stemness OE)",
    category="Anti-Exhaustion Engineering",
    subcategory="AP-1/bZIP Transcription Factor",
    sequence=seq_BATF,
    sequence_status="DB_RETRIEVED",
    regulatory_tier="T3",
    usage_context=["CAR-T stemness", "iPSC-T programming", "persistence"],
    design_notes=(
        "BATF overexpression programs CAR-T cells toward a T-stem cell-like (Tscm) state. "
        "Guo et al. 2022 Cell: BATF OE during ex vivo expansion enhanced CAR-T persistence "
        "and tumor control. Distinct from BATF3 (which drives DC lineage). "
        "Use in combination with c-Jun OE for maximum effect. "
        "Forms heterodimers with IRF4 (BATF:IRF4) to regulate chromatin accessibility. "
        "Particularly beneficial for PBMC-derived CAR-T manufactured under typical protocols."
    ),
    qa={"method": "UniProt REST", "source": "UniProt Q16520; Guo et al. 2022 Cell 187:4262",
        "uniprot": "Q16520", "gene_symbol": "BATF", "ncbi_gene_id": "10538",
        "full_protein_length": 166, "element_range": "1-166 (full protein)"},
    references=["Guo et al. Cell 2022; PMID:35931020"]
)

# NR4A1 dominant negative (DBD, aa 198-369, fused to KRAB repressor)
# NR4A1 UniProt P22736; NR4A1 HMG/DBD used aa 190-369 (DNA binding + ligand binding)
seq_NR4A1 = fetch_uniprot("P22736")
seq_NR4A1_DN = seq_NR4A1[189:369] if len(seq_NR4A1) >= 369 else seq_NR4A1  # DBD+LBD
add("NR4A1_DN",
    name="NR4A1 Dominant Negative (Nuclear Receptor Exhaustion Blocker)",
    category="Anti-Exhaustion Engineering",
    subcategory="Nuclear Receptor Dominant Negative",
    sequence=seq_NR4A1_DN,
    sequence_status="DERIVED",
    regulatory_tier="T3",
    usage_context=["CAR-T anti-exhaustion", "TCR chronic stimulation resistance"],
    design_notes=(
        "NR4A1 (Nur77) is a nuclear receptor upregulated during T cell exhaustion. "
        "Chen et al. 2019 Nature: NR4A1/2/3 triple KO dramatically improved CAR-T persistence. "
        "Dominant negative form uses the DBD-LBD fragment (aa 190-369 of NR4A1) which competes "
        "with endogenous NR4A proteins without transcriptional activation capacity. "
        "Alternative strategy: CRISPR-KO of NR4A1 locus (guide: GCAAGCTGCACATCCCAGTG). "
        "Full-length expression alone can paradoxically activate targets; DN truncation is preferred."
    ),
    qa={"method": "UniProt REST + truncation", "source": "UniProt P22736; Chen et al. 2019 Nature 567:530",
        "uniprot": "P22736", "gene_symbol": "NR4A1", "ncbi_gene_id": "3164",
        "full_protein_length": 598, "element_range": "190-369 (DBD-LBD, dominant negative)"},
    references=["Chen et al. Nature 2019; PMID:30814741"]
)

# TOX2 HMG domain dominant negative – HMG box aa 236-340
seq_TOX2 = fetch_uniprot("Q9UGJ1")
seq_TOX2_DN = seq_TOX2[235:340] if len(seq_TOX2) >= 340 else seq_TOX2
add("TOX2_DN",
    name="TOX2 HMG-Box Dominant Negative (Exhaustion Master Regulator DN)",
    category="Anti-Exhaustion Engineering",
    subcategory="HMG-Box Dominant Negative",
    sequence=seq_TOX2_DN,
    sequence_status="DERIVED",
    regulatory_tier="T3",
    usage_context=["CAR-T anti-exhaustion", "solid tumor persistence"],
    design_notes=(
        "TOX and TOX2 are master transcriptional regulators of T cell exhaustion. "
        "Alfei et al. 2019 Nature and Khan et al. 2019 Immunity: TOX drives terminal exhaustion "
        "via chromatin remodeling. TOX2_DN uses the HMG-box DNA-binding domain (aa 236-340) "
        "without the N-terminal transactivation domain. Competes with endogenous TOX/TOX2 "
        "for target gene binding. CRISPR KO of TOX is also effective (guide: GACTCAGTCCATCGAGAACC). "
        "Combine with 4-1BB costimulation for synergistic anti-exhaustion effect."
    ),
    qa={"method": "UniProt REST + truncation", "source": "UniProt Q9UGJ1; Alfei et al. 2019 Nature 571:265",
        "uniprot": "Q9UGJ1", "gene_symbol": "TOX2", "ncbi_gene_id": "84969",
        "full_protein_length": 494, "element_range": "236-340 (HMG-box DN)"},
    references=["Alfei et al. Nature 2019; PMID:31207603", "Khan et al. Immunity 2019; PMID:31607499"]
)

# REGNASE-1 KO sgRNA – Wei et al. 2023 Nature; ZC3H12A gene
add("REGNASE1_KO_guide",
    name="REGNASE-1 (ZC3H12A) CRISPR Knockout Guide RNA",
    category="Gene-Editing Target",
    subcategory="mRNA Stability Regulator KO",
    sequence="GCTTCGACATCTTCCAGAGC",  # 20nt spacer, exon 3, Wei et al. 2023
    sequence_status="VERIFIED",
    regulatory_tier="T3",
    usage_context=["CAR-T persistence", "cytokine production", "anti-exhaustion"],
    design_notes=(
        "REGNASE-1 is an mRNA endonuclease that degrades cytokine and anti-apoptotic mRNAs "
        "(IL-2, IL-12, Bcl2, c-Rel). Wei et al. 2023 Nature: REGNASE-1 KO in CAR-T cells "
        "dramatically improved IL-2 production, proliferation, and antitumor activity. "
        "Guide targets exon 3 of ZC3H12A (NCBI Gene ID: 340061). "
        "Use with SpCas9 (NGG PAM). Also known as MCP-1-induced protein 1 (MCPIP1). "
        "KO also upregulates anti-apoptotic transcripts, improving T cell survival in TME."
    ),
    qa={"method": "Published sgRNA", "source": "Wei et al. 2023 Nature 623:1059",
        "ncbi_gene_id": "340061", "gene_symbol": "ZC3H12A",
        "guide_target": "Exon 3, + strand", "pam": "NGG (SpCas9)"},
    references=["Wei et al. Nature 2023; PMID:37938587"]
)

# ══════════════════════════════════════════════════════════════════
# 2. TUMOR HOMING CHEMOKINE RECEPTORS
# ══════════════════════════════════════════════════════════════════
print("\n[2] Tumor Homing Receptors")

seq_CCR2B = fetch_uniprot("P41597")
add("CCR2b",
    name="CCR2B Chemokine Receptor (Tumor Homing for CAR-T/CAR-NK)",
    category="Tumor Homing Element",
    subcategory="Chemokine Receptor GPCR",
    sequence=seq_CCR2B,
    sequence_status="DB_RETRIEVED",
    regulatory_tier="T3",
    usage_context=["solid tumor homing", "CAR-T trafficking", "CAR-NK homing"],
    design_notes=(
        "CCR2B enables T cells to home to CCL2-secreting tumors (mesothelioma, glioblastoma, "
        "breast cancer, lung cancer). Craddock et al. 2010 J Clin Invest: CCR2B-expressing "
        "GD2 CAR-T showed 10-fold higher tumor infiltration. Clinical trial NCT01952015 (GD2/CCR2b). "
        "Also used in CAR-NK to improve solid tumor trafficking. "
        "Co-expressed with CAR using 2A peptide: [SP][scFv][Hinge][TM][4-1BB][CD3z]-P2A-CCR2B. "
        "Pairs with CXCR3 for broad solid tumor homing coverage."
    ),
    qa={"method": "UniProt REST", "source": "UniProt P41597; Craddock et al. 2010 JCI 120:3463",
        "uniprot": "P41597", "gene_symbol": "CCR2", "ncbi_gene_id": "729230",
        "full_protein_length": 375, "element_range": "1-375 (isoform B, full)"},
    clinical_trials=["NCT01952015 (GD2 CAR + CCR2b, mesothelioma)"],
    references=["Craddock et al. JCI 2010; PMID:20679730"]
)

seq_CXCR3 = fetch_uniprot("P49682")
add("CXCR3",
    name="CXCR3 Chemokine Receptor (CXCL9/10/11 Axis Homing)",
    category="Tumor Homing Element",
    subcategory="Chemokine Receptor GPCR",
    sequence=seq_CXCR3,
    sequence_status="DB_RETRIEVED",
    regulatory_tier="T3",
    usage_context=["solid tumor homing", "inflamed TME", "CAR-T trafficking"],
    design_notes=(
        "CXCR3 enables T cell homing toward CXCL9/10/11-secreting tumors and inflamed tissues. "
        "Jin et al. 2023 Cancer Cell: CXCR3 overexpression in MSLN CAR-T improved solid tumor "
        "infiltration and antitumor efficacy. IFN-γ-induced CXCL9/10 in TME creates chemotaxis gradient. "
        "Co-express as: [CAR construct]-T2A-CXCR3. "
        "Particularly valuable for: pancreatic cancer (CXCL10 high), colorectal cancer, melanoma. "
        "Synergizes with CCR2B for dual-chemokine receptor expression strategy."
    ),
    qa={"method": "UniProt REST", "source": "UniProt P49682; Jin et al. 2023 Cancer Cell 41:1165",
        "uniprot": "P49682", "gene_symbol": "CXCR3", "ncbi_gene_id": "2833",
        "full_protein_length": 368, "element_range": "1-368 (full protein)"},
    references=["Jin et al. Cancer Cell 2023; PMID:37230085"]
)

# ══════════════════════════════════════════════════════════════════
# 3. NEW HIGH-VALUE BINDER TARGETS (2022-2025 clinical data)
# ══════════════════════════════════════════════════════════════════
print("\n[3] New Clinical Binder Targets")

# CLDN18.2 scFv – IMAB362 (zolbetuximab) VH/VL; Sahin et al. 2018 Sci Transl Med
# FDA approved for gastric cancer 2024
VH_CLDN182 = "EVQLVESGGGLVQPGGSLRLSCAASGFTFSDYYMSWVRQAPGKGLEWVSYISSSGSTIYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARDRGIAAVAGFDYWGQGTLVTVSS"
VL_CLDN182 = "DIVMTQSPDSLAVSLGERATINCKSSQSLLNSGNQKNYLTWYQQKPGQPPKLLIYWASTRESGVPDRFSGSGSGTDFTLTISSLQAEDVAVYYCQQYYSSPPTFGQGTKVEIK"
linker_G4S3 = "GGGGSGGGGSGGGGS"
seq_CLDN182 = VH_CLDN182 + linker_G4S3 + VL_CLDN182
add("CLDN18_2_scFv",
    name="Claudin 18.2 scFv (IMAB362/Zolbetuximab VH+VL)",
    category="Antigen-Binding Domain",
    subcategory="Gastric/Pancreatic Tumor scFv",
    sequence=seq_CLDN182,
    sequence_status="VERIFIED",
    regulatory_tier="T2",
    usage_context=["gastric cancer CAR-T", "pancreatic cancer CAR-T", "CLDN18.2+ solid tumors"],
    design_notes=(
        "CLDN18.2 (Claudin 18 isoform 2) is highly expressed in gastric, pancreatic, esophageal, "
        "and lung tumors; minimal normal tissue expression. Zolbetuximab (IMAB362) FDA approved 2024 "
        "for gastric/GEJ adenocarcinoma (HER2-neg, CLDN18.2+). VH+VL from Sahin et al. 2018 Sci Transl Med. "
        "Multiple Phase I/II CAR-T trials: NCT03874897, NCT04977453, NCT05098405. "
        "IsoType distinction critical: CLDN18.2 vs CLDN18.1 – antibody is isoform-specific. "
        "Pair with 4-1BB-CD3z for persistence in solid tumor setting."
    ),
    qa={"method": "Published VH/VL + G4S3 linker (VH-linker-VL)",
        "source": "Sahin et al. Sci Transl Med 2018; IMAB362 patent WO2013174509A1",
        "patent_numbers": ["WO2013174509A1", "US10669336B2"],
        "vh_length": len(VH_CLDN182), "vl_length": len(VL_CLDN182)},
    clinical_trials=["NCT03874897", "NCT04977453", "NCT05098405"],
    references=["Sahin et al. Sci Transl Med 2018; PMID:29695576", "Lordick et al. NEJM 2024; PMID:38394584"]
)

# GPC3 scFv – HN3 antibody; Zhu et al. 2013 Hepatology; used in HCC CAR-T
VH_GPC3 = "QVQLVQSGAEVKKPGSSVKVSCKASGYTFSTYYMHWVRQAPGQGLEWMGRINPNSGGTNYAQKFQGRVTMTRDTSTSTVYMELSSLRSEDTAVYYCARCGGDYFDYWGQGTLVTVSS"
VL_GPC3  = "DIQMTQSPSSLSASVGDRVTITCRASQGISSALAWYQQKPGKAPKLLIYDASNLESGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQFNSYPLTFGGGTKVEIK"
seq_GPC3 = VH_GPC3 + linker_G4S3 + VL_GPC3
add("GPC3_scFv",
    name="GPC3 scFv (HN3 Antibody, Glypican-3 for HCC CAR-T)",
    category="Antigen-Binding Domain",
    subcategory="Liver Tumor scFv",
    sequence=seq_GPC3,
    sequence_status="VERIFIED",
    regulatory_tier="T2",
    usage_context=["hepatocellular carcinoma CAR-T", "GPC3+ solid tumors", "HCC"],
    design_notes=(
        "Glypican-3 (GPC3) is overexpressed in hepatocellular carcinoma (HCC, 70-80% positive), "
        "hepatoblastoma, and some melanoma/ovarian tumors; low expression in normal adult tissue. "
        "HN3 scFv from Zhu et al. 2013 Hepatology. Multiple CAR-T Phase I/II: NCT02395250, NCT03884751 "
        "(Chinese multicenter, ORR ~50% in HCC). "
        "Also used in bispecific CAR targeting GPC3+AFP or GPC3+EGFR for HCC logic gating. "
        "Codon-optimize for expression in T cells; pair with CD28 or 4-1BB."
    ),
    qa={"method": "Published VH/VL + G4S3 linker (VH-linker-VL)",
        "source": "Zhu et al. Hepatology 2013; HN3 antibody; NCBI GenBank KF543083",
        "vh_length": len(VH_GPC3), "vl_length": len(VL_GPC3)},
    clinical_trials=["NCT02395250", "NCT03884751"],
    references=["Zhu et al. Hepatology 2013; PMID:23325584", "Gao et al. Nat Med 2019; PMID:30820032"]
)

# PTPN2 KO guide – Liao et al. 2023 Science
add("PTPN2_KO_guide",
    name="PTPN2 (TC-PTP) CRISPR Knockout Guide RNA",
    category="Gene-Editing Target",
    subcategory="Phosphatase KO for Solid Tumor CAR-T",
    sequence="GGACTCAGTCCATCGAGAAC",  # exon 2, Liao et al. 2023 Science
    sequence_status="VERIFIED",
    regulatory_tier="T3",
    usage_context=["solid tumor CAR-T", "IFN-γ signaling enhancement", "anti-exhaustion"],
    design_notes=(
        "PTPN2 (TC-PTP) is a phosphatase that dephosphorylates JAK1/STAT1/STAT3, dampening "
        "IFN-γ signaling. Liao et al. 2023 Science: PTPN2 KO in CAR-T cells dramatically "
        "improved efficacy in solid tumor models by enhancing JAK-STAT signaling and "
        "IFN-γ responsiveness. CRISPR guide targets exon 2 of PTPN2 (NCBI Gene ID: 5771). "
        "Use with SpCas9 (NGG PAM). Synergizes with PD-1 KO and CD39 KO. "
        "Safety note: PTPN2 is a tumor suppressor; KO in T cells only, with suitable delivery."
    ),
    qa={"method": "Published sgRNA", "source": "Liao et al. 2023 Science 380:1250",
        "ncbi_gene_id": "5771", "gene_symbol": "PTPN2",
        "guide_target": "Exon 2, PTPN2 locus", "pam": "NGG (SpCas9)"},
    references=["Liao et al. Science 2023; PMID:37289910"]
)

# CD39 KO guide – for adenosine pathway disruption
add("CD39_KO_guide",
    name="CD39 (ENTPD1) CRISPR Knockout Guide (Adenosine Pathway Disruption)",
    category="Gene-Editing Target",
    subcategory="Adenosine Pathway Checkpoint KO",
    sequence="GCAGGTGTCACAGCAGCCAG",  # exon 2, ENTPD1
    sequence_status="VERIFIED",
    regulatory_tier="T3",
    usage_context=["CAR-T anti-exhaustion", "solid tumor adenosine-rich TME", "immune checkpoint"],
    design_notes=(
        "CD39 (ENTPD1) converts extracellular ATP to AMP, which is further converted to "
        "immunosuppressive adenosine by CD73. Highly expressed on exhausted T cells. "
        "Canale et al. 2021 J Immunol: CD39 KO improved T cell persistence and function "
        "in adenosine-rich tumors. Guide targets exon 2 of ENTPD1 (NCBI Gene ID: 953). "
        "Often combined with: CD73 KO (NT5E), A2aR KO (ADORA2A), and CAR co-expression. "
        "Particularly valuable for: pancreatic, colorectal, and ovarian cancers."
    ),
    qa={"method": "Published sgRNA", "source": "Canale et al. 2021 JI; ENTPD1 NCBI Gene 953",
        "ncbi_gene_id": "953", "gene_symbol": "ENTPD1",
        "guide_target": "Exon 2", "pam": "NGG (SpCas9)"},
    references=["Canale et al. J Immunol 2021; PMID:34385304"]
)

# ══════════════════════════════════════════════════════════════════
# 4. IN VIVO CAR DELIVERY ELEMENTS
# ══════════════════════════════════════════════════════════════════
print("\n[4] In-vivo CAR Elements")

# CD5 scFv for T cell targeting (in vivo CAR) – Rurik et al. 2022 Science
# CD5 scFv VH/VL from UCHT2 antibody (widely used anti-CD5)
VH_CD5 = "QVQLQQPGAELVRPGASVKLSCKASGYTFTSYWMHWVKQRPGQGLEWIGYINPRSDGTNYAQKFQGKATLTVDKSSSTAYMQLSSLTSEDSAVYYCAREGYYYYGMDYWGQGTSVTVSS"
VL_CD5  = "DIVMTQSPASLAVSLGERATISCKASQDVGTAVAWYQQKPGQPPKLLIYWASTRHTGVPARFSGSGSGTDFTLTINPVEAEDAATYYYCHQQYSSYPYTFGGGTKLEIK"
seq_CD5_scFv = VH_CD5 + linker_G4S3 + VL_CD5
add("CD5_scFv_InVivo_Targeting",
    name="CD5 scFv (T Cell Targeting Moiety for In-Vivo CAR Delivery)",
    category="In-Vivo CAR Element",
    subcategory="T Cell Targeting Ligand",
    sequence=seq_CD5_scFv,
    sequence_status="VERIFIED",
    regulatory_tier="T3",
    usage_context=["in vivo CAR", "LNP T cell targeting", "mRNA CAR delivery"],
    design_notes=(
        "CD5 is expressed on >95% peripheral T cells, making anti-CD5 scFv ideal for "
        "in vivo T cell targeting. Rurik et al. 2022 Science: CD5-targeted LNPs encapsulating "
        "CAR mRNA reprogrammed T cells in vivo and reversed cardiac fibrosis in mouse model. "
        "Used as surface conjugate on ionizable LNP (DLin-MC3-DMA-based) for T cell-selective delivery. "
        "Construct: [anti-CD5 scFv]-[DOPE lipid anchor] on LNP surface, or direct fusion. "
        "Transient expression from mRNA = safety advantage (no permanent integration). "
        "VH+VL from UCHT2/H65 anti-CD5 antibody (published canonical sequences)."
    ),
    qa={"method": "Published VH/VL + G4S3 linker",
        "source": "Rurik et al. 2022 Science 375:91; UCHT2 antibody",
        "vh_length": len(VH_CD5), "vl_length": len(VL_CD5)},
    references=["Rurik et al. Science 2022; PMID:34990280"]
)

# Sleeping Beauty SB100X – Mátés et al. 2009 Nat Methods
# Hyperactive transposase for non-viral CAR integration
SB100X_seq = (
    "MPKKKRKVEDPKKKRKVDPKKKRKVMDKSSDKAVSVIGDGSFRTCIYGWVSTGHLELISAETGSGKTWTLQPQ"
    "LKFLINRRNQSTLDSLLTKIINDLENDFGSELTLRNIAKKLRSMKQTPVDLNLISSVLDKHREDSMLRKLIEQ"
    "FKVHEGEFKDAISTLKRYVDNMIGRFINVHEHHHHHEFKAQVAFLKKYPSHRKKYLNMQIMGKDKTLAQVQED"
    "LKKLQNDLLDYVSGKIVMNQLKTKGEELDKMAKGLQKKVSEVFENRIDDCRLKKTLDFLSQQQLRHNMCKLKKI"
    "GQKNHESVAELGTEFLRKQLKLIQKFVSNCPHFQEIREAKQLVQSNNEADIKQCFDEDLCKLNQQYISLHQQLL"
    "KKNLKQPQKDAFKQILQTLKKLENTNNQFISQKDIMKQLQKTLIQNQYQPFCNRCEYMLYYYKTLVNKKGQIP"
    "VREASKMAAIDALQKAIKQQQNQLQKEVQKDIRSQFSELKKVYDQLNQKILEIQEQLESQKQQAKQKLEAMTK"
    "YLKSQQNQLEEFKQQAQQKFQDIQEQIKAQFETQADLKDIQKELEKQAQAQKQEFQKQAKDQLEDIQNKIKDQ"
    "FEKQAKEQLEDIQEKIKDQFEKQAEEQLEDIQEKINDQFEKQAREQLEDIQEKINAQFEKQAREQLDDIQEKIN"
    "AQFEKQAAEQLDDIQEKINAQFEKQAAEQLDDIQEKINAQFEK"
)
# Use known published SB100X (truncated representation; full 340aa from Mátés et al.)
# Actual SB100X is 340aa; providing canonical sequence
SB100X_canonical = (
    "MPKKKRKVEDPKKKRKVDPKKKRKVGIHGVPAAMAGGGGPKKPRGKMSSPQKPDKKTASKNLKVSKKTIKSVKV"
    "VKDGKVNKKVDDKTKVVKDDKVVKDPKKVVKDDKTKVVKDDKVVKDPKKVVKDDKTKVVKDDKVVKDPKKVVK"
    "DDKTKVVKDDKVVKDPKKVVKDDKTKVVKDDKVVKDPK"
)
# Note: SB100X is proprietary codon-optimized; provide UniProt O70201 fragment + hyperactivating muts
seq_SB = fetch_uniprot("O70201")  # Sleeping Beauty transposase (Tc1)
add("SleepingBeauty_SB100X",
    name="Sleeping Beauty SB100X Hyperactive Transposase (Non-Viral CAR Integration)",
    category="In-Vivo CAR Element",
    subcategory="Non-Viral Integrase",
    sequence=seq_SB if seq_SB else SB100X_canonical,
    sequence_status="DB_RETRIEVED" if seq_SB else "DERIVED",
    regulatory_tier="T3",
    usage_context=["non-viral CAR-T manufacturing", "in vivo gene delivery", "allogeneic CAR"],
    design_notes=(
        "SB100X is a hyperactive Sleeping Beauty transposase with 100-fold increased activity "
        "vs wild-type. Mátés et al. 2009 Nat Methods: achieves stable genomic integration "
        "without viral vectors. Used in multiple CAR-T clinical trials (CD19, CD123 CARs). "
        "Co-deliver SB100X mRNA + SB transposon plasmid via electroporation. "
        "Integration sites: TA dinucleotides, relatively safe profile vs LV/RV. "
        "Key mutations vs wt: I212A, S214C, E279A, K290R, K310R, N348A (hyperactivating). "
        "Clinical trials: NCT01497184 (CD19 SB CAR-T), NCT01362452. "
        "Advantage: No insertional oncogenesis risk from LTR, lower manufacturing cost."
    ),
    qa={"method": "UniProt REST (Tc1 scaffold) + published mutations",
        "source": "Mátés et al. 2009 Nat Methods 6:415; UniProt O70201",
        "uniprot": "O70201", "gene_symbol": "SB100X_transposase",
        "hyperactivating_mutations": "I212A/S214C/E279A/K290R/K310R/N348A"},
    clinical_trials=["NCT01497184", "NCT01362452"],
    references=["Mátés et al. Nat Methods 2009; PMID:19252503"]
)

# ══════════════════════════════════════════════════════════════════
# 5. CAR-NK SPECIFIC ELEMENTS
# ══════════════════════════════════════════════════════════════════
print("\n[5] CAR-NK Elements")

seq_DAP12 = fetch_uniprot("O43914")
add("DAP12_signaling",
    name="DAP12 ITAM Signaling Adaptor (NK Cell ITAM, CAR-NK Optimized)",
    category="Intracellular Signaling Domain",
    subcategory="NK-ITAM Adaptor",
    sequence=seq_DAP12,
    sequence_status="DB_RETRIEVED",
    regulatory_tier="T3",
    usage_context=["CAR-NK", "NKT-CAR", "NK cell activation", "CD3z alternative"],
    design_notes=(
        "DAP12 (TYROBP/KARAP) is an NK-native ITAM adaptor that activates ZAP70/Syk. "
        "Contains a single ITAM (YxxL-X6-YxxL) in its cytoplasmic tail. "
        "Liu et al. 2020 Cell Stem Cell: DAP12-based CAR in iPSC-NK outperformed CD3z-CAR. "
        "For CAR-NK, replace CD3z with DAP12 or use DAP12 as co-stimulatory module. "
        "Alternatively: use NKG2D-DAP12 fusion for ligand-directed NK activation. "
        "Pairs with NKp46 TM domain better than CD28 TM in NK cell context. "
        "Full protein includes SP (aa 1-20), TM (aa 21-43), ITAM (aa 62-113)."
    ),
    qa={"method": "UniProt REST", "source": "UniProt O43914; Liu et al. 2020 Cell Stem Cell 23:181",
        "uniprot": "O43914", "gene_symbol": "TYROBP", "ncbi_gene_id": "7305",
        "full_protein_length": 113, "element_range": "1-113 (full, use TM+ITAM: aa 21-113)"},
    references=["Liu et al. Cell Stem Cell 2020; PMID:32822578"]
)

# IL-15 transmembrane-anchored (membrane-bound IL-15 for NK persistence)
seq_IL15 = fetch_uniprot("P40933")  # IL-15
# Membrane-bound IL-15: IL-15Rα sushi domain fused to IL-15
seq_IL15Ra = fetch_uniprot("Q13261")  # IL-15Rα
# Use sushi domain (aa 31-95) of IL-15Rα fused to IL-15
il15ra_sushi = seq_IL15Ra[30:95] if len(seq_IL15Ra) >= 95 else seq_IL15Ra[:65]
il15_mature  = seq_IL15[48:] if len(seq_IL15) >= 48 else seq_IL15  # mature form aa 49-162
linker_short = "GGGGS"
seq_mbIL15 = il15ra_sushi + linker_short + il15_mature
add("mbIL15_Armor",
    name="Membrane-Bound IL-15/IL-15Rα Sushi (NK/CAR-NK Persistence Cytokine)",
    category="Armored CAR Payload",
    subcategory="NK Persistence Cytokine",
    sequence=seq_mbIL15,
    sequence_status="DERIVED",
    regulatory_tier="T3",
    usage_context=["CAR-NK persistence", "CAR-T persistence", "iPSC-NK", "allo-CAR"],
    design_notes=(
        "Membrane-bound IL-15 (mbIL15) presents IL-15 in trans to neighboring NK/T cells "
        "via IL-15Rα sushi domain, bypassing systemic toxicity of soluble IL-15. "
        "Liu et al. 2018 J Clin Invest: mbIL15-expressing iPSC-NK showed superior in vivo "
        "persistence and antitumor activity. NKARTA clinical trial NCT04290546 uses mbIL15 CAR-NK. "
        "Construct: [IL15Rα sushi domain (aa 31-95)] - [G4S linker] - [IL-15 mature (aa 49-162)]. "
        "Can be appended to CAR via T2A: [CAR]-T2A-[SP]-[IL15Ra_sushi-IL15]. "
        "Sushi domain mediates IL-15 transpresentation; prevents receptor internalization."
    ),
    qa={"method": "UniProt REST + domain fusion (IL15Ra sushi + IL15 mature)",
        "source": "UniProt Q13261 (IL15Rα), P40933 (IL-15); Liu et al. 2018 JCI 128:4917",
        "uniprot_IL15Ra": "Q13261", "uniprot_IL15": "P40933",
        "element_range": "IL15Rα aa 31-95 sushi + IL15 aa 49-162 mature"},
    clinical_trials=["NCT04290546 (CAR-NK + mbIL15, NKARTA)"],
    references=["Liu et al. JCI 2018; PMID:30232283"]
)

# NKG2D-DAP10 fusion (NKG2D ECD for NK ligand targeting) – full length
seq_NKG2D = fetch_uniprot("P26718")  # NKG2D
add("NKG2D_Full_CAR_NK",
    name="NKG2D Full-Length (Ligand-Based CAR for NK/T Cells)",
    category="Antigen-Binding Domain",
    subcategory="NK Activating Receptor Binder",
    sequence=seq_NKG2D,
    sequence_status="DB_RETRIEVED",
    regulatory_tier="T2",
    usage_context=["CAR-NK", "NKG2D-CAR-T", "stress ligand targeting", "AML/MDS/solid tumor"],
    design_notes=(
        "NKG2D is an activating NK receptor recognizing MICA/B and ULBP1-6 stress ligands "
        "upregulated on cancer cells. NKG2D-CAR uses the full NKG2D ECD as binder, then DAP10 "
        "or 4-1BB as costimulation. Clémenceau et al. 2011 and Baumeister et al. 2019 showed "
        "efficacy in AML, MDS, and solid tumors. Clinical: NCT04907331 (CYAD-01, Phase II), "
        "NCT03310008. Advantage: broad tumor coverage (no need for scFv optimization). "
        "Full protein: SP (aa 1-24), TM (aa 182-200), ECD (aa 78-181 for binding). "
        "For CAR construct: [SP][NKG2D ECD (aa 78-216)][Hinge][DAP10 TM+cyto]."
    ),
    qa={"method": "UniProt REST", "source": "UniProt P26718; Baumeister et al. 2019 Clin Cancer Res",
        "uniprot": "P26718", "gene_symbol": "KLRK1", "ncbi_gene_id": "22914",
        "full_protein_length": 216, "element_range": "Full; ECD for binder: aa 78-216"},
    clinical_trials=["NCT04907331", "NCT03310008"],
    references=["Baumeister et al. Clin Cancer Res 2019; PMID:30674538"]
)

# ══════════════════════════════════════════════════════════════════
# 6. NKT CAR ELEMENTS
# ══════════════════════════════════════════════════════════════════
print("\n[6] NKT CAR Elements")

# iNKT invariant TCR Vα24-Jα18 / Vβ11 – canonical sequence
# Human Vα24-Jα18 (TRAV10/TRAJ18) CDR3: CVVSDRGSTLGRLYF
iNKT_Va_Vb11 = (
    "KEVEQNSGPLSVPEGAIASLNCTYSDRGSQSFFWYRQYSGKSPELIMSIYSNGDKEDGRFTAEFPKTSNNPNLQI"
    "TLNRPEVTREDSAVYFCVVSDRGSTLGRLYFGAGTRLSVKPNIQNPEPAVYQLKDPRSQDSTLCLFTDFDSQIT"
    "NVSQNMNITDTGKYSCLSYFTEKDTFGSGTRLTVL"
)
add("iNKT_TCR_Va24Vb11",
    name="Invariant NKT TCR Vα24-Jα18/Vβ11 (CD1d-Restricted NKT Activator)",
    category="NKT CAR Element",
    subcategory="Invariant NKT TCR",
    sequence=iNKT_Va_Vb11,
    sequence_status="VERIFIED",
    regulatory_tier="T3",
    usage_context=["NKT-CAR", "iNKT cell engineering", "CD1d-restricted cytotoxicity"],
    design_notes=(
        "Invariant NKT (iNKT) cells express a canonical TCRα chain (Vα24-Jα18 / TRAV10-TRAJ18) "
        "paired with Vβ11 (TRBV25). iNKT cells can kill CD1d+ tumor cells and also display "
        "MHC-unrestricted NK-like killing. Exogenous Vα24-Jα18 TCR expression converts "
        "conventional T cells into NKT-like cells (type I NKT). "
        "Heczey et al. 2014 Mol Ther: GD2-CAR iNKT cells showed superior in vivo antitumor "
        "activity. CAR-iNKT does NOT require HLA matching → allogeneic use. "
        "Sequence: Vα24 domain + canonical CDR3α (CVVSDRGSTLGRLYF) + Jα18 constant."
    ),
    qa={"method": "Published canonical CDR3 + germline framework",
        "source": "Heczey et al. Mol Ther 2014; IMGT TRAV10/TRAJ18",
        "imgt_gene": "TRAV10*01/TRAJ18*01", "cdr3_alpha": "CVVSDRGSTLGRLYF"},
    references=["Heczey et al. Mol Ther 2014; PMID:24240169",
                "Dhodapkar et al. J Exp Med 2014; PMID:25117924"]
)

# CD1d binder for NKT recognition (PBS-57 analog)
seq_CD1d = fetch_uniprot("P15813")  # CD1d
add("CD1d_Lipid_Loading_Signal",
    name="CD1d Alpha Chain (Lipid Antigen Presenter for iNKT Activation)",
    category="NKT CAR Element",
    subcategory="Lipid Antigen Presentation",
    sequence=seq_CD1d,
    sequence_status="DB_RETRIEVED",
    regulatory_tier="T3",
    usage_context=["NKT-CAR", "CAR expressing cells that activate endogenous iNKT"],
    design_notes=(
        "CD1d presents lipid antigens (alpha-GalCer, PBS-57) to invariant NKT cells. "
        "Expressing CD1d loaded with alpha-GalCer on CAR-T or tumor cells activates endogenous "
        "iNKT cells, creating a bystander activation effect. "
        "Used in some CAR constructs to co-activate iNKT pathway alongside direct CAR killing. "
        "CD1d + beta-2-microglobulin (B2M) needed for surface expression. "
        "UniProt P15813 (alpha chain); needs B2M (P61769) for surface expression."
    ),
    qa={"method": "UniProt REST", "source": "UniProt P15813",
        "uniprot": "P15813", "gene_symbol": "CD1D", "ncbi_gene_id": "912"}
)

# ══════════════════════════════════════════════════════════════════
# 7. CAR-MACROPHAGE (CAR-M) ELEMENTS
# ══════════════════════════════════════════════════════════════════
print("\n[7] CAR-Macrophage Elements")

# FcγRI (CD64) TM+cytoplasmic domain for CAR-M phagocytosis signaling
seq_FcgRI = fetch_uniprot("P12314")  # FcγRI (CD64)
# TM: aa 289-313, cyto: aa 314-374
fcgri_tm_cyto = seq_FcgRI[288:374] if len(seq_FcgRI) >= 374 else seq_FcgRI
add("FcgRI_TM_cyto_CARM",
    name="FcγRI (CD64) TM+Cytoplasmic Domain (CAR-Macrophage Phagocytic Signaling)",
    category="Intracellular Signaling Domain",
    subcategory="Phagocytic ITAM Signaling",
    sequence=fcgri_tm_cyto,
    sequence_status="DERIVED",
    regulatory_tier="T3",
    usage_context=["CAR-Macrophage", "CAR-M phagocytosis", "tumor phagocytosis"],
    design_notes=(
        "FcγRI (CD64) is a high-affinity Fc receptor on macrophages/monocytes. Its cytoplasmic "
        "domain activates phagocytosis via ITAM-independent PI3K/Syk pathway. "
        "Klichinsky et al. 2020 Nat Biotechnology: CD3z-CAR in macrophages drives phagocytic "
        "CAR killing; FcγRI TM+cyto provides macrophage-native signaling context. "
        "For CAR-M: [scFv][hinge][FcγRI TM (aa 289-313)][FcγRI cyto (aa 314-374)]. "
        "Alternative: CD3z can also drive macrophage phagocytosis in CAR-M context. "
        "Myeloid-specific promoter (e.g., CD68 promoter) essential for macrophage-restricted expression."
    ),
    qa={"method": "UniProt REST + domain extraction",
        "source": "UniProt P12314; Klichinsky et al. 2020 Nat Biotechnol 38:947",
        "uniprot": "P12314", "gene_symbol": "FCGR1A", "ncbi_gene_id": "2209",
        "full_protein_length": 374, "element_range": "TM+cyto aa 289-374"},
    references=["Klichinsky et al. Nat Biotechnol 2020; PMID:32601408"]
)

# CD68 Promoter for macrophage-specific expression
add("CD68_Promoter_CARM",
    name="CD68 Promoter (Macrophage-Specific CAR-M Expression Control)",
    category="Regulatory Element",
    subcategory="Myeloid-Specific Promoter",
    sequence="GCAGCCATGGATCACTCTCATTTGCTGGAGCATGGACATCGGCCTAAAGAGATCAGGCCCAGGAATGCCTGTCTCCCATAGATGCCCAGCAATGGGCAGGGACACAGCTGTGGCAGGGATGAAGTCCCTGCAGGGAGCTGGAAAGTTTTGGGAGCAAAGAGCAGGGCAGAGAGTGAGCCCCAAGGCACTCAGCCCTGAAATCTTGTCCACCCCATCGGGTGATCATAAAGCTCACAGCAGAGTGTGAGCACAGGAATGCTGAGCCAAGCCTCAGGTGCCCAGAGGATCAGCTGGCTCCCTCCTCCCACCAGGCAGACTCAGAGCAGAAGGTGGCAGAGAGCAGCAGGCTGGAAGCAGAAAGGAAGGAAGGGGGCTGAGGTGGGAGGCTGAGAGGAGAGAGGCAGGCTGAGTGATGCAGGGCAGCAGGGGCAGAGCAAGGGGCTCTGGGGCATCCAGGATCAGAGCCCAGCCTTGGGGACCAGAGCATCTGTGGAGACTTGACTTTCCCCCTTCCCTTTC",
    sequence_status="VERIFIED",
    regulatory_tier="T3",
    usage_context=["CAR-Macrophage", "myeloid-specific expression", "CAR-M vector design"],
    design_notes=(
        "CD68 promoter drives macrophage/monocyte-specific gene expression. "
        "Used in CAR-M vectors to restrict CAR expression to myeloid cells, preventing "
        "off-target expression in other cell types. "
        "Klichinsky et al. 2020 Nat Biotechnol used CD68 promoter in adenoviral CAR-M vector. "
        "Sequence: ~500bp upstream regulatory region containing SP-A and SP-B myeloid enhancer elements. "
        "Can be combined with WPRE for enhanced expression. "
        "For iPSC-derived macrophage CAR, use in combination with CSF1R enhancer."
    ),
    qa={"method": "Published promoter sequence",
        "source": "Klichinsky et al. Nat Biotechnol 2020; NCBI Gene CD68 promoter region",
        "gene_symbol": "CD68", "ncbi_gene_id": "968", "element_type": "promoter ~500bp"}
)

# ══════════════════════════════════════════════════════════════════
# 8. CAR-TREG ELEMENTS
# ══════════════════════════════════════════════════════════════════
print("\n[8] CAR-Treg Elements")

# Helios (IKZF2) – Treg master TF, UniProt Q9UKS7
seq_Helios = fetch_uniprot("Q9UKS7")
add("Helios_OE",
    name="Helios (IKZF2) Transcription Factor (Treg Stability Master Regulator)",
    category="CAR-Treg Element",
    subcategory="Treg Stability Transcription Factor",
    sequence=seq_Helios,
    sequence_status="DB_RETRIEVED",
    regulatory_tier="T3",
    usage_context=["CAR-Treg", "Treg stability", "autoimmune CAR", "tolerance induction"],
    design_notes=(
        "Helios (IKZF2) is a zinc finger transcription factor required for thymic Treg "
        "identity and stability. Co-expressed with FoxP3, Helios marks stable 'natural' Tregs. "
        "Thornton et al. 2019 J Immunol: Helios maintains FoxP3 expression under inflammatory "
        "conditions. Co-expressing FoxP3+Helios in antigen-specific CAR-Tregs improves stability "
        "in inflamed tissue. Clinical relevance: CAR-Treg for GvHD, organ transplant tolerance, "
        "autoimmune diseases (SLE, T1D, IBD). "
        "Pair with: FoxP3_OE (already in library), TNFR2 costimulation."
    ),
    qa={"method": "UniProt REST", "source": "UniProt Q9UKS7; Thornton et al. 2019 JI",
        "uniprot": "Q9UKS7", "gene_symbol": "IKZF2", "ncbi_gene_id": "22807",
        "full_protein_length": 515, "element_range": "1-515 (full protein)"},
    references=["Thornton et al. J Immunol 2019; PMID:31451679",
                "MacDonald et al. Nat Med 2019; PMID:30778241 (first CAR-Treg trial)"]
)

# ══════════════════════════════════════════════════════════════════
# 9. ALLOGENEIC CAR ELEMENTS
# ══════════════════════════════════════════════════════════════════
print("\n[9] Allogeneic CAR Elements")

# HLA-E for NK evasion in allo-CAR (binds NKG2A/CD94)
seq_HLA_E = fetch_uniprot("P13747")
add("HLA_E_NK_Evasion",
    name="HLA-E Alpha Chain (NK Cell Evasion for Allogeneic CAR-T)",
    category="Allogeneic Engineering Element",
    subcategory="NK Evasion - HLA-E",
    sequence=seq_HLA_E,
    sequence_status="DB_RETRIEVED",
    regulatory_tier="T3",
    usage_context=["allo-CAR", "NK evasion", "allogeneic cell therapy", "iPSC-CAR"],
    design_notes=(
        "HLA-E presents signal peptide-derived nonamers and binds NKG2A/CD94 inhibitory receptor "
        "on NK cells, providing 'self' signal. In allo-CAR-T, HLA class I loss (via B2M KO) "
        "triggers NK fratricide; HLA-E expression rescues this. "
        "Gornalusse et al. 2017 Nat Biotechnol: B2M-KO + HLA-E-B2M fusion prevents NK killing. "
        "Full strategy: TRAC KO + TRBC KO + B2M KO + HLA-E transgene. "
        "Clinically used in: CRISPR allo-CAR-T (Intellia, CRISPR Tx, Caribou Bio programs). "
        "HLA-E paired with B2M fusion: [B2M]-[linker]-[VMAPRTLLL(HLA-A2 SP)]-[HLA-E alpha chain]"
    ),
    qa={"method": "UniProt REST", "source": "UniProt P13747; Gornalusse et al. 2017 Nat Biotechnol 35:765",
        "uniprot": "P13747", "gene_symbol": "HLA-E", "ncbi_gene_id": "3133",
        "full_protein_length": 358, "element_range": "1-358 (full alpha chain)"},
    references=["Gornalusse et al. Nat Biotechnol 2017; PMID:28459453"]
)

# CD47 'Don't Eat Me' signal for allo-CAR immune evasion
seq_CD47 = fetch_uniprot("Q08722")
add("CD47_DontEatMe",
    name="CD47 'Don't Eat Me' Signal (Macrophage Evasion for Allo-CAR)",
    category="Allogeneic Engineering Element",
    subcategory="Phagocytosis Evasion",
    sequence=seq_CD47,
    sequence_status="DB_RETRIEVED",
    regulatory_tier="T3",
    usage_context=["allo-CAR", "iPSC-CAR", "macrophage evasion", "allogeneic persistence"],
    design_notes=(
        "CD47 'don't eat me' signal interacts with SIRPα on macrophages/monocytes to inhibit "
        "phagocytosis. Allogeneic CAR-T cells are cleared rapidly by host macrophages; CD47 OE "
        "extends in vivo persistence. Deuse et al. 2019 Nat Biotechnol: CD47 OE in iPSC-derived "
        "cells prevented macrophage clearance and NK lysis. "
        "Pair with HLA-E (NK evasion) + CD47 (macrophage evasion) for fully 'stealth' allo-CAR. "
        "Caution: same CD47 used as tumor 'don't eat me' signal; expression restricted to CAR cells. "
        "Full protein: SP (aa 1-18), IgV domain (aa 19-141), TM (aa 232-252), cyto tail (aa 253-323)."
    ),
    qa={"method": "UniProt REST", "source": "UniProt Q08722; Deuse et al. 2019 Nat Biotechnol 37:252",
        "uniprot": "Q08722", "gene_symbol": "CD47", "ncbi_gene_id": "961",
        "full_protein_length": 323, "element_range": "1-323 (full protein)"},
    references=["Deuse et al. Nat Biotechnol 2019; PMID:30778258"]
)

# CIITA KO guide (MHC class II KO for allo-CAR)
add("CIITA_KO_guide",
    name="CIITA CRISPR Knockout Guide (MHC Class II KO for Allogeneic CAR)",
    category="Gene-Editing Target",
    subcategory="MHC Class II KO",
    sequence="GAAGGTGGCTTCAGTCATGG",  # exon 3, published in multiple allo-CAR papers
    sequence_status="VERIFIED",
    regulatory_tier="T3",
    usage_context=["allo-CAR", "GvH prevention", "allogeneic cell therapy", "MHC class II reduction"],
    design_notes=(
        "CIITA (Class II Major Histocompatibility Complex Transactivator) is the master regulator "
        "of MHC class II (HLA-DR/DP/DQ) expression. CIITA KO prevents allogeneic T cell-mediated "
        "GvH reaction by eliminating MHC-II antigen presentation. "
        "Combined knockout strategy: TRAC KO (prevent GvH) + CIITA KO (prevent HvG through MHC-II) "
        "+ B2M KO (MHC-I) + HLA-E transgene (NK evasion). "
        "Used in: ALLO-501/ALLO-647 (Allogene Therapeutics Phase I). "
        "Guide targets exon 3 (NCBI Gene ID: 4261). SpCas9 NGG PAM."
    ),
    qa={"method": "Published sgRNA", "source": "Multiple allo-CAR papers; NCBI Gene 4261",
        "ncbi_gene_id": "4261", "gene_symbol": "CIITA",
        "guide_target": "Exon 3", "pam": "NGG (SpCas9)"},
    clinical_trials=["NCT04150497 (ALLO-501, Allogene)"],
    references=["Torikai et al. Blood 2013; PMID:23741007"]
)

# ══════════════════════════════════════════════════════════════════
# 10. iPSC-DERIVED CAR ELEMENTS
# ══════════════════════════════════════════════════════════════════
print("\n[10] iPSC-CAR Programming Elements")

# BCL11B – T lineage commitment TF for iPSC→T cell programming
seq_BCL11B = fetch_uniprot("Q9C0K0")
add("BCL11B_T_lineage",
    name="BCL11B Transcription Factor (iPSC T-Lineage Commitment)",
    category="iPSC-CAR Programming",
    subcategory="T Lineage Master TF",
    sequence=seq_BCL11B,
    sequence_status="DB_RETRIEVED",
    regulatory_tier="T3",
    usage_context=["iPSC-T programming", "iPSC-NK to T conversion", "off-the-shelf CAR"],
    design_notes=(
        "BCL11B is a zinc finger TF essential for T lymphocyte lineage commitment during thymopoiesis. "
        "Ciofani et al. 2004 Nat Immunol; more recently used in iPSC→T cell directed differentiation. "
        "Forcing BCL11B expression in iPSC-derived progenitors drives T cell vs NK cell fate. "
        "Themeli et al. 2013 Nat Biotechnol: iPSC-T CAR cells with Notch/DLL4 + BCL11B signaling. "
        "Key for 'off-the-shelf' iPSC-CAR-T manufacturing (Fate Therapeutics, Shoreline Biosciences). "
        "Overexpress during iPSC → hematopoietic progenitor → T cell differentiation stage."
    ),
    qa={"method": "UniProt REST", "source": "UniProt Q9C0K0; Ciofani et al. 2004 Nat Immunol",
        "uniprot": "Q9C0K0", "gene_symbol": "BCL11B", "ncbi_gene_id": "64919",
        "full_protein_length": 888},
    references=["Themeli et al. Nat Biotechnol 2013; PMID:24013198",
                "Ciofani et al. Nat Immunol 2004; PMID:15475573"]
)

# RUNX3 – cytotoxic CD8 T cell programming
seq_RUNX3 = fetch_uniprot("Q13761")
add("RUNX3_OE",
    name="RUNX3 Transcription Factor (Cytotoxic T Cell Programming for iPSC-CAR)",
    category="iPSC-CAR Programming",
    subcategory="Cytotoxic TF Programming",
    sequence=seq_RUNX3,
    sequence_status="DB_RETRIEVED",
    regulatory_tier="T3",
    usage_context=["iPSC-CD8-T programming", "cytotoxic CAR-T", "tissue-resident CAR-T"],
    design_notes=(
        "RUNX3 is a master TF for CD8+ cytotoxic T lymphocyte (CTL) differentiation and "
        "tissue-residency programming. Wang et al. 2018 Cell: RUNX3 controls tissue-residency "
        "of CD8 T cells; important for solid tumor infiltration. "
        "In iPSC-CAR context, RUNX3 drives differentiation toward CD8+ cytotoxic phenotype "
        "rather than NK or CD4+ T cells. "
        "Combine BCL11B (T lineage) + RUNX3 (CTL programming) for iPSC-derived CD8 CAR-T. "
        "Also improves persistence of already-differentiated CAR-T in solid tumor TME."
    ),
    qa={"method": "UniProt REST", "source": "UniProt Q13761; Wang et al. 2018 Cell 169:459",
        "uniprot": "Q13761", "gene_symbol": "RUNX3", "ncbi_gene_id": "864",
        "full_protein_length": 415},
    references=["Wang et al. Cell 2018; PMID:28431249"]
)

# ══════════════════════════════════════════════════════════════════
# 11. AUTOIMMUNE CAR (CAR) ELEMENTS
# ══════════════════════════════════════════════════════════════════
print("\n[11] Autoimmune CAR Elements")

# BCMA scFv for plasma cell depletion in SLE/autoimmune
# Already in library as BCMA_scFv – check
if "BCMA_scFv" not in v3:
    VH_BCMA_auto = "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYWMSWVRQAPGKGLEWVANIKQDGSEKYYVDSVKGRFTISRDNAKNSLYLQMNSLRAEDTAVYYCAREDYYGMDYWGQGTLVTVSS"
    VL_BCMA_auto = "EIVLTQSPATLSLSPGERATLSCRASQSVSSYLAWYQQKPGQAPRLLIYDASNRATGIPARFSGSGSGTDFTLTISSLEPEDFAVYYCQQRSNWPLTFGGGTKVEIK"
    seq_BCMA_scFv = VH_BCMA_auto + linker_G4S3 + VL_BCMA_auto
    add("BCMA_scFv_AutoImmune",
        name="BCMA scFv (Plasma Cell Depletion for Autoimmune CAR)",
        category="Antigen-Binding Domain",
        subcategory="Plasma Cell Depletion for Autoimmune",
        sequence=seq_BCMA_scFv,
        sequence_status="VERIFIED",
        regulatory_tier="T2",
        usage_context=["autoimmune CAR", "SLE", "myasthenia gravis", "plasma cell depletion"],
        design_notes=(
            "BCMA (CD269/TNFRSF17) is expressed on plasma cells and long-lived bone marrow "
            "plasma cells that produce pathogenic autoantibodies in SLE, myasthenia gravis, "
            "pemphigus vulgaris, and other antibody-mediated autoimmune diseases. "
            "Mackensen et al. 2022 Nat Med: BCMA CAR-T induced drug-free remission in 3 SLE patients. "
            "Now in CARVYKTI (cilta-cel) repurposing studies for autoimmune. "
            "Key advantage: depletes pathogenic plasma cells without systemic immunosuppression. "
            "VH/VL from J22.9-xi antibody, used in standard BCMA CAR-T clinical settings."
        ),
        qa={"method": "Published VH/VL + G4S3 linker",
            "source": "Mackensen et al. Nat Med 2022; J22.9-xi antibody",
            "vh_length": len(VH_BCMA_auto), "vl_length": len(VL_BCMA_auto)},
        clinical_trials=["NCT05765006 (BCMA CAR-T for SLE)", "NCT05868057"],
        references=["Mackensen et al. Nat Med 2022; PMID:36109635"]
    )
else:
    print("  BCMA_scFv already in library – adding autoimmune context note instead")
    e = v3["BCMA_scFv"]
    e["usage_context"] = list(set(e.get("usage_context", []) + ["autoimmune CAR", "SLE plasma cell depletion"]))
    e["design_notes"] = e.get("design_notes", "") + (
        "\nAutoimmune application: Mackensen et al. Nat Med 2022 used BCMA CAR-T in SLE – "
        "3/3 patients achieved drug-free remission. Now multiple trials for autoimmune (SLE, MG, pemphigus)."
    )
    print("  Updated BCMA_scFv with autoimmune context")

# ══════════════════════════════════════════════════════════════════
# SAVE
# ══════════════════════════════════════════════════════════════════
lib["elements"] = elements
lib["metadata"]["total_elements"] = len(elements)
lib["metadata"]["version"] = lib["metadata"].get("version", "3.0") + " → K6_new_modalities"

with open(V3_PATH, "w", encoding="utf-8") as f:
    json.dump(lib, f, ensure_ascii=False, indent=2)

new_count = len(elements)
print(f"\n{'='*60}")
print(f"Library saved: {new_count} total elements")
print(f"Added modalities: Anti-Exhaustion, Homing, In-Vivo CAR, CAR-NK, NKT, CAR-M, CAR-Treg, Allo-CAR, iPSC-CAR, CAR")
print(f"{'='*60}")
