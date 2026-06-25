import json
import sys
from pathlib import Path
from Bio.Seq import Seq
from Bio import SeqIO
from anarci import anarci

suite_root = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
sys.path.append(str(suite_root))

from core.humanization.kabat_utils import get_kabat_numbering, sorted_keys, is_in_cdr

# 1. Sequences
tanezumab_vh = "QVQLQESGPGLVRPSQTLSLTCTVSGFSLIGYDLNWVRQPPGRGLEWIGIIWGDGTTDYNSAVKSRVTMLKDTSKNQFSLRLSSVTAADTAVYYCARGGYWYATSYYFDYWGQGTLVTVSS"
tanezumab_vl = "DIQMTQSPSSLSASVGDRVTITCRASQSISNNLNWYQQKPGKAPKLLIYYTSRFHSGVPSRFSGSGSGTDFTFTISSLQPEDIATYYCQQEHTLPYTFGQGTKLEIK"

bedin_vh = "EVQLVESGGDLVKPGGSLRLSCVASGFTFSSHGMHWVRQSPGKGLQWVAVINSGGSSTYYTDAVKGRFTISRDNAKNTVYLQMNSLRAEDTAMYYCAKESVGGWEQLVGPHFDYWGQGTLVIVSS"
bedin_vl = "QSVLTQPTSVSGSLGQRVTISCSGSTNNIGILGASWYQLFPGKAPKLLVYGNGNRPSGVPDRFSGADSGDSVTLTITGLQAEDEADYYCQSFDTTLGAHVFGGGTHLTVL"

v3_vh = "EVQLVESGGDLVKPGGSLRLSCVASGFSLIGYDLNWVRQAPGKGLQWLGIIWGDGTTDYNSAVKSRVTISKDSAKNTFYLQLQSLRAEETAVYYCARGGYWYATSYYFDYWGQGTSVTVSS"
v3_vl = "EIVLTQSPASLSLSQEEKVTITCRASQSISNNLNWYQQKPGQAPKLLIYYTSRFHSGVPSRFSGSGSGTDFSFTISSLEPEDVAVYYCQQEHTLPYTFGQGTKVELK"

v4_vh = "EVQLVESGGDLVKPAGSLRLSCVASGFSLIGYDLNWVRQAPEKGLQLVAIIWGDGTTDYNSAVKSRFTISKDFAKNTVYLQMRAEDTAMYYCAKGGYWYATSYYFDYWGQGTSVTVSS"
v4_vl = "QSVLTQPTSVSGSLGQRVTISCRASQSISNNLNWYQQLPGKAPKLLVYYTSRFHSGVPDRFSGSNSGNSATLTITGLQAEDEADYYCQQEHTLPYTFGAGTKLEIK"

v5_vh = "EVQLVESGGDLVKPGGSLRLSCVASGFSLIGYDLNWVRQAPGKGLQLVAIIWGDGTTDYNSAVKSRFTISKDFAKNTVYLQLRAEDTAVYYCAKGGYWYATSYYFDYWGQGTLVTVSS"
v5_vl = "QSVLTQPASSVSGSLGQRVTISCRASQSISNNLNWYQQLPGKAPKLLVYYTSRFHSGVPDRFSGSGSGNSATLTISGLQAEDEADYYCQQEHTLPYTFGQGTKLEIK"

# 2. Constant Regions (Extracted from GB and Fasta)
# Dog IgG-B Constant (from GB)
# ASTTAPSVFPLAPSCGSTSGSTVALACLVSGYFPEPVTVSWNSGSLTSGVHTFPSVLQSSGLYSLSSMVTVPSSRWPSETFTCNVAHPASKTKVDKPVPKRENGRVPRPPDCPKCPAPEMLGGPSVFIFPPKPKDTLLIARTPEVTCVVVDLDPEDPEVQISWFVDGKQMQTAKTQPREEQFNGTYRVVSVLPIGHQDWLKGKQFTCKVNNKALPSPIERTISKARGQAHQPSVYVLPPSREELSKNTVSLTCLIKDFFPPDIDVEWQSNGQQEPESKYRTTPPQLDEDGSYFLYSKLSVDKSRWQRGDTFICAVMHEALHNHYTQKSLSHSPGK
dog_iggb_const = "ASTTAPSVFPLAPSCGSTSGSTVALACLVSGYFPEPVTVSWNSGSLTSGVHTFPSVLQSSGLYSLSSMVTVPSSRWPSETFTCNVAHPASKTKVDKPVPKRENGRVPRPPDCPKCPAPEMLGGPSVFIFPPKPKDTLLIARTPEVTCVVVDLDPEDPEVQISWFVDGKQMQTAKTQPREEQFNGTYRVVSVLPIGHQDWLKGKQFTCKVNNKALPSPIERTISKARGQAHQPSVYVLPPSREELSKNTVSLTCLIKDFFPPDIDVEWQSNGQQEPESKYRTTPPQLDEDGSYFLYSKLSVDKSRWQRGDTFICAVMHEALHNHYTQKSLSHSPGK"

# Dog Kappa Constant (from GB)
# RNDAQPAVYLFQPSPDQLHTGSASVVCLLNSFYPKDINVKWKVDGVIQDTGIQESVTEQDKDSTYSLSSTLTMSSTEYLSHELYSCEITHKSLPSTLIKSFQRSECQRVD
dog_kappa_const = "RNDAQPAVYLFQPSPDQLHTGSASVVCLLNSFYPKDINVKWKVDGVIQDTGIQESVTEQDKDSTYSLSSTLTMSSTEYLSHELYSCEITHKSLPSTLIKSFQRSECQRVD"

# Dog Lambda Constant (from IGHC_aa.fasta IGLC1*01)
# GQPKSSPLVTLFPPSSEELGANKATLVCLISDFYPSGLKVAWKADGSTIIQGVETTKPSKQSNNKYTASSYLSLTPDKWKSHSSFSCLVTHQGSTVEKKVAPAECS
dog_lambda_const = "GQPKSSPLVTLFPPSSEELGANKATLVCLISDFYPSGLKVAWKADGSTIIQGVETTKPSKQSNNKYTASSYLSLTPDKWKSHSSFSCLVTHQGSTVEKKVAPAECS"

# 3. Signal Peptides (from GB)
# HC: MGWSCIILFLVATATGVHS
# LC: METDTLLLWVLLLWVPGSTG
hc_sig = "MGWSCIILFLVATATGVHS"
lc_sig = "METDTLLLWVLLLWVPGSTG"

# 4. Alignment Function
def get_regions(seq, chain):
    results = anarci([("seq", seq)], scheme="kabat")
    if results[0] and results[0][0]:
        numbering = results[0][0][0][0]
        kd = {}
        for (pos, ins), aa in numbering:
            kd[(pos, ins.strip())] = aa
        
        regions = {"FR1": "", "CDR1": "", "FR2": "", "CDR2": "", "FR3": "", "CDR3": "", "FR4": ""}
        if chain == "VH":
            r_map = {"FR1": (1, 25), "CDR1": (26, 35), "FR2": (36, 49), "CDR2": (50, 65), "FR3": (66, 94), "CDR3": (95, 102), "FR4": (103, 113)}
        else:
            r_map = {"FR1": (1, 23), "CDR1": (24, 34), "FR2": (35, 49), "CDR2": (50, 56), "FR3": (57, 88), "CDR3": (89, 97), "FR4": (98, 107)}
        
        for r_name, (lo, hi) in r_map.items():
            regions[r_name] = "".join(kd[k] for k in sorted_keys(kd) if lo <= k[0] <= hi)
        return regions
    return None

# 5. cDNA Generation (Simple Back-translation for now, or use a tool if available)
# Since I don't have a full codon optimizer, I'll use a basic one or just note it.
# Actually, I can use the DNA from the GB files for Tanezumab.
# For others, I'll provide a placeholder or a simple translation.

def simple_back_translate(protein_seq):
    # This is a very basic back-translation, not optimized for expression.
    # In a real scenario, we'd use a codon optimization tool.
    codon_table = {
        'A': 'GCC', 'C': 'TGC', 'D': 'GAC', 'E': 'GAG', 'F': 'TTC', 'G': 'GGC', 'H': 'CAC', 'I': 'ATC', 'K': 'AAG', 'L': 'CTG',
        'M': 'ATG', 'N': 'AAC', 'P': 'CCC', 'Q': 'CAG', 'R': 'CGC', 'S': 'TCC', 'T': 'ACC', 'V': 'GTC', 'W': 'TGG', 'Y': 'TAC',
        '*': 'TGA'
    }
    return "".join(codon_table.get(aa, "NNN") for aa in protein_seq)

# 6. Process all
variants = {
    "Tanezumab": (tanezumab_vh, tanezumab_vl, "kappa"),
    "Bedinvetmab": (bedin_vh, bedin_vl, "lambda"),
    "V3": (v3_vh, v3_vl, "kappa"),
    "V4": (v4_vh, v4_vl, "lambda"),
    "V5": (v5_vh, v5_vl, "lambda")
}

alignment_results = {"VH": {}, "VL": {}}
full_protein = {}
full_cdna = {}

for name, (vh, vl, lc_type) in variants.items():
    alignment_results["VH"][name] = get_regions(vh, "VH")
    alignment_results["VL"][name] = get_regions(vl, "VL")
    
    # Full Protein
    vh_full = hc_sig + vh + dog_iggb_const
    cl_const = dog_kappa_const if lc_type == "kappa" else dog_lambda_const
    vl_full = lc_sig + vl + cl_const
    
    full_protein[name] = {"HC": vh_full, "LC": vl_full}
    
    # cDNA (Back-translated)
    full_cdna[name] = {"HC": simple_back_translate(vh_full), "LC": simple_back_translate(vl_full)}

# 7. Save results
with open("final_comparison_data.json", "w") as f:
    json.dump({
        "alignment": alignment_results,
        "protein": full_protein,
        "cdna": full_cdna
    }, f, indent=2)

print("Final comparison data generated.")
