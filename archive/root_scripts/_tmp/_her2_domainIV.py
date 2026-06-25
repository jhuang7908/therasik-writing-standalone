# NP_004439.2 - fetched 2026-03-29 from NCBI EUtils
SEQ = (
    "MELAALCRWGLLLALLPPGAASTQVCTGTDMKLRLPASPETHLDMLRHLYQGCQVVQGNLELTYLPTNAS"
    "LSFLQDIQEVQGYVLIAHNQVRQVPLQRLRIVRGTQLFEDNYALAVLDNGDPLNNTTPVTGASPGGLREL"
    "QLRSLTEILKGGVLIQRNPQLCYQDTILWKDIFHKNNQLALTLIDTNRSRACHPCSPMCKGSRCWGESSE"
    "DCQSLTRTVCAGGCARCKGPLPTDCCHEQCAAGCTGPKHSDCLACLHFNHSGICELHCPALVTYNTDTFE"
    "SMPNPEGRYTFGASCVTACPYNYLSTDVGSCTLVCPLHNQEVTAEDGTQRCEKCSKPCARVCYGLGMEHL"
    "REVRAVTSANIQEFAGCKKIFGSLAFLPESFDGDPASNTAPLQPEQLQVFETLEEITGYLYISAWPDSLP"
    "DLSVFQNLQVIRGRILHNGAYSLTLQGLGISWLGLRSLRELGSGLALIHHNTHLCFVHTVPWDQLFRNPH"
    "QALLHTANRPEDECVGEGLACHQLCARGHCWGPGPTQCVNCSQFLRGQECVEECRVLQGLPREYVNARHC"
    "LPCHPECQPQNGSVTCFGPEADQCVACAHYKDPPFCVARCPSGVKPDLSYMPIWKFPDEEGACQPCPINC"
    "THSCVDLDDKGCPAEQRASPLTSIISAVVGILLVVVLGVVFGILIKRRQQKIRKYTMRRLLQETELVEPL"
    "TPSGAMPNQAQMRILKETELRKVKVLGSGAFGTVYKGIWIPDGENVKIPVAIKVLRENTSPKANKEILDE"
    "AYVMAGVGSPYVSRLLGICLTSTVQLVTQLMPYGCLLDHVRENRGRLGSQDLLNWCMQIAKGMSYLEDVR"
    "LVHRDLAARNVLVKSPNHVKITDFGLARLLDIDETEYHADGGKVPIKWMALESILRRRFTHQSDVWSYGV"
    "TVWELMTFGAKPYDGIPAREIPDLLEKGERLPQPPICTIDVYMIMVKCWMIDSECRPRFRELVSEFSRMA"
    "RDPQRFVVIQNEDLGPASPLDSTFYRSLLEDDDMGDLVDAEEYLVPQQGFFCPDPAPGAGGMVHHRHRSS"
    "STRSGGGDLTLGLEPSEEEAPRSPLAPSEGAGSDVFDGDLGMGAAKGLQSLPTHDPSPLQRYSEDPTVPL"
    "PSETDGYVAPLTCSPQPEYVNQPDVRPQPPSPREGPLPAARPAGATLERPKTLSPGKNGVVKDVFAFGGA"
    "VENPEYLTPQGGAAPQPHPPPAFSPAFDNLYYWDQDPPERGAPPSTFKGTPTAENPEYLGLDVPV"
)

print("Full precursor length:", len(SEQ))

# Signal peptide = aa 1-22 per UniProt
SIG = SEQ[0:22]
print("Signal peptide (aa1-22):", SIG)

# Mature ECD = aa 23-645 per UniProt
MATURE_START = 22  # 0-indexed
ECD_END = 645      # 0-indexed exclusive
ECD = SEQ[MATURE_START:ECD_END]
print("ECD (aa23-645): %d aa" % len(ECD))

# Transmembrane: UniProt annotates 646-667
TM = SEQ[645:667]
print("TM region (aa646-667):", TM)

# Find major domain landmarks in full precursor (1-indexed)
print()
print("=== Domain boundary search ===")
for motif, label in [
    ("GESSEDCQSLTRTVCAGGCARCK", "Domain II start (CR1)"),
    ("NCSQFLRGQECVEECR",        "Domain IV start (CR2, Cho2003)"),
    ("VARCPSGVKPDLS",           "Domain IV core (trastuzumab epitope region)"),
    ("KGCPAEQRASPLT",           "Domain IV C-terminus"),
    ("SIISAVVGILLVVV",          "TM region"),
]:
    p = SEQ.find(motif)
    if p >= 0:
        print("  %-45s -> full precursor aa %d (ECD aa %d)" % (
            label + " [" + motif[:12] + "...]", p + 1, p + 1 - 22))
    else:
        print("  %-45s -> NOT FOUND" % label)

# Domain IV: Cho 2003 defines it as the C-terminal cysteine-rich domain
# of the ECD. From PDB 1N8Z: roughly ECD residues 483-623
# = full precursor aa 505-645
# More precisely, UniProt Furin-like domain 2: 484-631 (mature) = 506-653? varies
# Conservative: use ECD 461-624 (per some papers) = full precursor 483-646

# Let us use the well-cited 1N8Z-based definition: ECD aa 483-623
# = full precursor [504:645] (0-indexed)
domIV_1 = SEQ[504:645]  # Cho 2003 definition
print()
print("Domain IV option A (Cho2003: ECD aa483-623 = full precursor 505-645):")
print(domIV_1)
print("Length:", len(domIV_1))

# Shorter definition: just the last cysteine-rich domain starting at ECVEECR
p_ecr = SEQ.find("ECVEECRVLQGLPREYVNAR")
p_tm  = SEQ.find("SIISAVVGILLVVV")
domIV_2 = SEQ[p_ecr:p_tm]
print()
print("Domain IV option B (CR2 only: ECVEECR...to TM, full precursor aa %d-%d):" % (p_ecr+1, p_tm))
print(domIV_2)
print("Length:", len(domIV_2))

print()
print("=== RECOMMENDED for ColabFold (VHH + HER2 binding domain) ===")
print("Use option A (broader ECD C-terminal domain, includes trastuzumab epitope):")
print()
VHH = "QVQLVQSGAEVVKPGSSVKLSCKASGFNIKDTYIHWVKQRPEQGREWIGRIYPTNGYTRYDPKFQDRATITADTSTSTAYLEVSRLRSEDTAVYYCSRWGGDGFYAMDYWGQGASVTVSS"
print(">muMAb4D5_VHH_VGRW_SR_R2")
print(VHH)
print(">HER2_ECD_DomainIV_NP004439.2_aa505-645")
print(domIV_1)
print()
print("ColabFold multimer (colon-separated):")
print(VHH + ":" + domIV_1)
