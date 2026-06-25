import json
import sys
from pathlib import Path
from datetime import datetime

suite_root = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
sys.path.append(str(suite_root))

from core.humanization.kabat_utils import get_kabat_numbering, sorted_keys, assemble_humanized_v
from core.evaluation import AbEvaluator, AntibodyType
from anarci import anarci

# 1. Configuration
DOG_9MER_DB_PATH = suite_root / "data/reference/pet_9mer_db/dog_9mer_v1.json"
AMINO_ACIDS = list("ACDEFGHIKLMNPQRSTVWY")

# Protected positions (Kabat)
VERNIER_VH = {2, 27, 28, 29, 30, 47, 48, 49, 67, 69, 71, 73, 78, 93, 94}
VERNIER_VL = {2, 4, 36, 46, 49, 69, 71, 98}
CDR_VH = [(26, 35), (50, 65), (95, 102)]
CDR_VL = [(24, 34), (50, 56), (89, 97)]

def is_in_cdr(pos, chain):
    ranges = CDR_VH if chain == "VH" else CDR_VL
    for lo, hi in ranges:
        if lo <= pos <= hi:
            return True
    return False

def load_dog_9mer_db():
    with open(DOG_9MER_DB_PATH) as f:
        data = json.load(f)
    return data["nine_mer_counts"]

def get_kabat(seq):
    results = anarci([("seq", seq)], scheme="kabat")
    if results[0] and results[0][0]:
        numbering = results[0][0][0][0]
        # Convert to the (int, str) format expected by our utils
        kd = {}
        for (pos, ins), aa in numbering:
            kd[(pos, ins.strip())] = aa
        return kd
    return None

def vote_for_sequence(seq, chain, db):
    kd = get_kabat(seq)
    if not kd:
        return seq, []
    
    protected = VERNIER_VH if chain == "VH" else VERNIER_VL
    cys_pos = {22, 92} if chain == "VH" else {23, 88}
    
    # Linear sequence and mapping
    sorted_k = sorted_keys(kd)
    full_seq = "".join(kd[k] for k in sorted_k)
    
    new_seq_list = list(full_seq)
    changes = []
    
    for i, k in enumerate(sorted_k):
        pos, ins = k
        if is_in_cdr(pos, chain) or pos in protected or pos in cys_pos:
            continue
        
        original_aa = kd[k]
        
        # 9-mer voting
        scores = {}
        for aa in AMINO_ACIDS:
            temp_seq = full_seq[:i] + aa + full_seq[i+1:]
            start_idx = max(0, i - 8)
            end_idx = min(len(full_seq) - 9, i)
            
            votes = 0
            for j in range(start_idx, end_idx + 1):
                nine_mer = temp_seq[j:j+9]
                votes += db.get(nine_mer, 0)
            scores[aa] = votes
        
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_aa, top_votes = ranked[0]
        
        # Threshold for replacement: must have significant support and be better than original
        original_votes = scores.get(original_aa, 0)
        
        if top_aa != original_aa and top_votes > original_votes and top_votes >= 5:
            # CMC Veto: No new N-glyc (NxS/T where x!=P)
            # Check local context in temp_seq
            temp_seq_final = full_seq[:i] + top_aa + full_seq[i+1:]
            # Simplified N-glyc check
            if "N" in temp_seq_final[max(0, i-2):min(len(temp_seq_final), i+3)]:
                # Potential N-glyc, skip for now to be safe
                continue
                
            new_seq_list[i] = top_aa
            changes.append({
                "pos": f"{pos}{ins}",
                "old": original_aa,
                "new": top_aa,
                "votes_old": original_votes,
                "votes_new": top_votes
            })
            
    return "".join(new_seq_list), changes

# 2. V5 Design Execution
db = load_dog_9mer_db()

# V4 Sequences (Base for V5)
v4_vh = "EVQLVESGGDLVKPAGSLRLSCVASGFSLIGYDLNWVRQAPEKGLQLVAIIWGDGTTDYNSAVKSRFTISKDFAKNTVYLQMRAEDTAMYYCAKGGYWYATSYYFDYWGQGTSVTVSS"
v4_vl = "QSVLTQPTSVSGSLGQRVTISCRASQSISNNLNWYQQLPGKAPKLLVYYTSRFHSGVPDRFSGSNSGNSATLTITGLQAEDEADYYCQQEHTLPYTFGAGTKLEIK"

print("Designing V5 VH...")
v5_vh, vh_changes = vote_for_sequence(v4_vh, "VH", db)
print(f"VH Changes: {len(vh_changes)}")
for c in vh_changes:
    print(f"  {c['pos']}: {c['old']} -> {c['new']} (Votes: {c['votes_old']} -> {c['votes_new']})")

print("\nDesigning V5 VL...")
v5_vl, vl_changes = vote_for_sequence(v4_vl, "VL", db)
print(f"VL Changes: {len(vl_changes)}")
for c in vl_changes:
    print(f"  {c['pos']}: {c['old']} -> {c['new']} (Votes: {c['votes_old']} -> {c['votes_new']})")

# 3. CMC Evaluation
def run_eval(name, vh, vl, ab_type, species):
    print(f"Evaluating {name}...")
    ev = AbEvaluator(
        project_name=name,
        vh_seq=vh,
        vl_seq=vl,
        ab_type=ab_type,
        germline_species=species,
        strict_qa=False
    )
    result = ev.run(modules=["developability", "cdr_scan", "cmc_advisor", "germline"])
    return {
        "project_name": result.project_name,
        "results": result.results,
        "overall_status": result.overall_status,
        "overall_flags": result.overall_flags
    }

# Tanezumab (Human Control)
tanezumab_vh = "QVQLQESGPGLVRPSQTLSLTCTVSGFSLIGYDLNWVRQPPGRGLEWIGIIWGDGTTDYNSAVKSRVTMLKDTSKNQFSLRLSSVTAADTAVYYCARGGYWYATSYYFDYWGQGTLVTVSS"
tanezumab_vl = "DIQMTQSPSSLSASVGDRVTITCRASQSISNNLNWYQQKPGKAPKLLIYYTSRFHSGVPSRFSGSGSGTDFTFTISSLQPEDIATYYCQQEHTLPYTFGQGTKLEIK"

# V3 (IGHV3-9 + IGKV3-18)
v3_vh = "EVQLVESGGDLVKPGGSLRLSCVASGFSLIGYDLNWVRQAPGKGLQWLGIIWGDGTTDYNSAVKSRVTISKDSAKNTFYLQLQSLRAEETAVYYCARGGYWYATSYYFDYWGQGTSVTVSS"
v3_vl = "EIVLTQSPASLSLSQEEKVTITCRASQSISNNLNWYQQKPGQAPKLLIYYTSRFHSGVPSRFSGSGSGTDFSFTISSLEPEDVAVYYCQQEHTLPYTFGQGTKVELK"

results = {}
results["Tanezumab"] = run_eval("Tanezumab", tanezumab_vh, tanezumab_vl, AntibodyType.FULLY_HUMAN, "Homo_sapiens")
results["V3"] = run_eval("V3", v3_vh, v3_vl, AntibodyType.DOG, "Canis_lupus_familiaris")
results["V4"] = run_eval("V4", v4_vh, v4_vl, AntibodyType.DOG, "Canis_lupus_familiaris")
results["V5"] = run_eval("V5", v5_vh, v5_vl, AntibodyType.DOG, "Canis_lupus_familiaris")

with open("v5_design_results.json", "w") as f:
    json.dump({
        "v5_vh": v5_vh,
        "v5_vl": v5_vl,
        "vh_changes": vh_changes,
        "vl_changes": vl_changes,
        "cmc_results": results
    }, f, indent=2)

print("\nV5 Design and Evaluation complete. Results saved to v5_design_results.json")
