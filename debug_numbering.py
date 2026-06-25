
from core.vhh.vhh_scaffold_match_and_craft import _build_vhh_residue_map_and_regions
import json

SP34_VH = "DIKLQSGAELARPGASVKMSCKTSGYTFTRYTMHWVKQRPGQGLEWIGYINPSRGYTNYNQKFKDKATLTTDKSSSTAYMQLSSLTSEDSAVYYCARYYDDHYCLDYWGQGTTLTVSS"

def check_regions(name, seq):
    print(f"--- {name} ---")
    rmap, regions = _build_vhh_residue_map_and_regions(seq)
    print(f"Regions: {regions}")
    
    # Build donor CDR2
    cdr_lo, cdr_hi = regions["CDR2"]
    ordered_rows = rmap._ordered_rows
    cdr_residues = [aa for (pos, _ins, aa) in ordered_rows if cdr_lo <= pos <= cdr_hi]
    print(f"CDR2 ({cdr_lo}-{cdr_hi}): {''.join(cdr_residues)}")

check_regions("SP34", SP34_VH)
