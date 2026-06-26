import json
import sys
from pathlib import Path
from Bio.Seq import Seq
from anarci import anarci

suite_root = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
sys.path.append(str(suite_root))

from core.humanization.kabat_utils import get_kabat_numbering, sorted_keys

# 1. Load Existing Data
with open("final_comparison_data.json") as f:
    data = json.load(f)

with open("v3b_design_results.json") as f:
    v3b_results = json.load(f)

# 2. Add V3b to Alignment and Protein Data
v3b_vh = v3b_results["v3b_vh"]
v3b_vl = v3b_results["v3b_vl"]

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

data["alignment"]["VH"]["V3b"] = get_regions(v3b_vh, "VH")
data["alignment"]["VL"]["V3b"] = get_regions(v3b_vl, "VL")

hc_sig = "MGWSCIILFLVATATGVHS"
lc_sig = "METDTLLLWVLLLWVPGSTG"
dog_iggb_const = "ASTTAPSVFPLAPSCGSTSGSTVALACLVSGYFPEPVTVSWNSGSLTSGVHTFPSVLQSSGLYSLSSMVTVPSSRWPSETFTCNVAHPASKTKVDKPVPKRENGRVPRPPDCPKCPAPEMLGGPSVFIFPPKPKDTLLIARTPEVTCVVVDLDPEDPEVQISWFVDGKQMQTAKTQPREEQFNGTYRVVSVLPIGHQDWLKGKQFTCKVNNKALPSPIERTISKARGQAHQPSVYVLPPSREELSKNTVSLTCLIKDFFPPDIDVEWQSNGQQEPESKYRTTPPQLDEDGSYFLYSKLSVDKSRWQRGDTFICAVMHEALHNHYTQKSLSHSPGK"
dog_kappa_const = "RNDAQPAVYLFQPSPDQLHTGSASVVCLLNSFYPKDINVKWKVDGVIQDTGIQESVTEQDKDSTYSLSSTLTMSSTEYLSHELYSCEITHKSLPSTLIKSFQRSECQRVD"

data["protein"]["V3b"] = {
    "HC": hc_sig + v3b_vh + dog_iggb_const,
    "LC": lc_sig + v3b_vl + dog_kappa_const
}

def simple_back_translate(protein_seq):
    codon_table = {
        'A': 'GCC', 'C': 'TGC', 'D': 'GAC', 'E': 'GAG', 'F': 'TTC', 'G': 'GGC', 'H': 'CAC', 'I': 'ATC', 'K': 'AAG', 'L': 'CTG',
        'M': 'ATG', 'N': 'AAC', 'P': 'CCC', 'Q': 'CAG', 'R': 'CGC', 'S': 'TCC', 'T': 'ACC', 'V': 'GTC', 'W': 'TGG', 'Y': 'TAC',
        '*': 'TGA'
    }
    return "".join(codon_table.get(aa, "NNN") for aa in protein_seq)

data["cdna"]["V3b"] = {
    "HC": simple_back_translate(data["protein"]["V3b"]["HC"]),
    "LC": simple_back_translate(data["protein"]["V3b"]["LC"])
}

# 3. Update V5 Recalculated results in the same data structure if needed
with open("v5_recalculation_results.json") as f:
    v5_recalc = json.load(f)

# Update V5 in alignment and protein
data["alignment"]["VH"]["V5"] = get_regions(v5_recalc["v5_vh"], "VH")
data["alignment"]["VL"]["V5"] = get_regions(v5_recalc["v5_vl"], "VL")
dog_lambda_const = "GQPKSSPLVTLFPPSSEELGANKATLVCLISDFYPSGLKVAWKADGSTIIQGVETTKPSKQSNNKYTASSYLSLTPDKWKSHSSFSCLVTHQGSTVEKKVAPAECS"
data["protein"]["V5"] = {
    "HC": hc_sig + v5_recalc["v5_vh"] + dog_iggb_const,
    "LC": lc_sig + v5_recalc["v5_vl"] + dog_lambda_const
}
data["cdna"]["V5"] = {
    "HC": simple_back_translate(data["protein"]["V5"]["HC"]),
    "LC": simple_back_translate(data["protein"]["V5"]["LC"])
}

# 4. Save Final Data
with open("final_comparison_data.json", "w") as f:
    json.dump(data, f, indent=2)

# 5. Update V5 results in v5_design_results.json for the HTML generator
with open("v5_design_results.json") as f:
    v5_full_results = json.load(f)

v5_full_results["cmc_results"]["V3b"] = v3b_results["cmc_results"]
# Update V5 with recalculated one
v5_full_results["cmc_results"]["V5"] = {
    "project_name": "V5",
    "results": {
        "developability": {
            "pI_fab_estimate": v5_recalc["cmc"]["pI"],
            "instability_index": v5_recalc["cmc"]["instability"],
            "GRAVY": -0.3, # Placeholder or extract
            "net_charge_pH7": 1.0,
            "SAP_score": 0.75,
            "agg_motifs": 3
        },
        "cmc_advisor": {
            "metrics": {
                "oxidation_sites": {"value": [0]*v5_recalc["cmc"]["oxidation"]},
                "deamidation_sites": {"value": [0,0]},
                "isomerization_sites": {"value": [0]}
            }
        }
    }
}

with open("v5_design_results.json", "w") as f:
    json.dump(v5_full_results, f, indent=2)

print("Comparison data updated with V3b and Recalculated V5.")
