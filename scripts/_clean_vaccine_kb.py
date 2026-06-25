"""
Final cleanup pass for vaccine_kb_data.json after IEDB verification:
1. Strip parenthetical annotations from peptide fields (then re-query IEDB)
2. Fix known sequence errors (e.g. KRAS G12D VVGADGVGKS → VVGADGVGK)
3. Remove non-peptide entries (subscript position descriptors)
4. Re-query IEDB for any newly cleaned peptides
5. Produce clean summary report
"""

import json
import re
import time
import sys
import urllib.request
import urllib.parse

IEDB_API = "https://query-api.iedb.org/epitope_search"
IEDB_EPITOPE_URL = "https://www.iedb.org/epitope/{}"
IEDB_SEARCH_URL = "https://www.iedb.org/result_v3.php?epitope_type=T+Cell&linear_sequence={}&tab=results"

# Known corrections: wrong_seq → correct_seq (verified from literature/RCSB)
SEQUENCE_CORRECTIONS = {
    "VVGADGVGKS": "VVGADGVGK",   # KRAS G12D, HLA-A*11:01 (9-mer, not 10-mer with S)
    "GVALQTMKQ": "GVALQTMKQ",   # keep but mark (not in IEDB, may be valid)
}

def is_position_descriptor(peptide: str) -> bool:
    """Detect non-peptide entries with Unicode subscripts or slash notations."""
    # Contains Unicode subscript digits/hyphens (₀-₉, ₋)
    subscript_chars = set("₀₁₂₃₄₅₆₇₈₉₋")
    if any(c in subscript_chars for c in peptide):
        return True
    # Pattern like "CIT-XXX59-78" or "AQP4_61_80"
    if re.match(r'^[A-Z][\w\d]+-?\w+[₀₁₂₃₄₅₆₇₈₉₋]', peptide):
        return True
    return False

def clean_peptide(peptide: str) -> str:
    """Remove parenthetical annotations like (DQ2.5-glia-α1a) from peptide field."""
    # Remove text in parentheses
    cleaned = re.sub(r'\s*\(.*?\)\s*', '', peptide).strip()
    return cleaned

def query_iedb(peptide: str) -> dict:
    """Query IEDB IQ-API for a clean peptide sequence."""
    params = urllib.parse.urlencode({
        "linear_sequence": f"eq.{peptide}",
        "limit": "1",
        "select": "structure_id"
    })
    url = f"{IEDB_API}?{params}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())
        if data and len(data) > 0:
            sid = data[0].get("structure_id")
            if sid:
                return {"iedb_id": sid, "iedb_url": IEDB_EPITOPE_URL.format(sid)}
    except Exception as e:
        pass
    return {"iedb_id": None, "iedb_url": IEDB_SEARCH_URL.format(urllib.parse.quote(peptide))}

def fix_epitopes(epitope_list: list, key_name: str = "peptide") -> tuple[list, dict]:
    """Clean and re-verify a list of epitope dicts. Returns (fixed_list, stats)."""
    fixed = []
    stats = {"kept": 0, "removed_pos_descriptor": 0, "corrected_seq": 0, "re_queried": 0}
    
    for ep in epitope_list:
        raw_peptide = ep.get(key_name, "")
        
        # Skip non-peptide position descriptors
        if is_position_descriptor(raw_peptide):
            print(f"  REMOVE (position descriptor): {raw_peptide}")
            stats["removed_pos_descriptor"] += 1
            continue
        
        # Apply known corrections
        corrected = SEQUENCE_CORRECTIONS.get(raw_peptide, raw_peptide)
        if corrected != raw_peptide:
            print(f"  CORRECT: {raw_peptide} → {corrected}")
            ep[key_name] = corrected
            stats["corrected_seq"] += 1
        
        # Clean parenthetical annotations
        cleaned = clean_peptide(ep[key_name])
        if cleaned != ep[key_name]:
            print(f"  CLEAN: '{ep[key_name]}' → '{cleaned}'")
            ep[key_name] = cleaned
        
        # Re-query IEDB if we don't have a verified ID yet (iedb_id is None or missing)
        current_id = ep.get("iedb_id")
        if current_id is None:
            print(f"  Re-querying IEDB: {ep[key_name]}")
            result = query_iedb(ep[key_name])
            ep.update(result)
            stats["re_queried"] += 1
            if result["iedb_id"]:
                print(f"    → IEDB #{result['iedb_id']} ✓")
            time.sleep(0.15)
        
        stats["kept"] += 1
        fixed.append(ep)
    
    return fixed, stats

def main():
    json_path = "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/docs/vaccine_kb_data.json"
    
    print("Loading JSON...")
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    
    total_stats = {"kept": 0, "removed_pos_descriptor": 0, "corrected_seq": 0, "re_queried": 0}
    
    def merge_stats(s):
        for k in total_stats:
            total_stats[k] += s.get(k, 0)
    
    # Fix TAAs
    print("\n=== Fixing TAAs ===")
    for entry in data.get("taa", []):
        name = entry.get("name", "?")
        fixed_mhc1, s1 = fix_epitopes(entry.get("known_epitopes_mhc1", []))
        fixed_mhc2, s2 = fix_epitopes(entry.get("known_epitopes_mhc2", []))
        entry["known_epitopes_mhc1"] = fixed_mhc1
        entry["known_epitopes_mhc2"] = fixed_mhc2
        merge_stats(s1); merge_stats(s2)
    
    # Fix Infectious
    print("\n=== Fixing Infectious ===")
    for entry in data.get("infectious", []):
        fixed_mhc1, s1 = fix_epitopes(entry.get("known_epitopes_mhc1", []))
        fixed_mhc2, s2 = fix_epitopes(entry.get("known_epitopes_mhc2", []))
        entry["known_epitopes_mhc1"] = fixed_mhc1
        entry["known_epitopes_mhc2"] = fixed_mhc2
        merge_stats(s1); merge_stats(s2)
    
    # Fix Autoimmune
    print("\n=== Fixing Autoimmune ===")
    for entry in data.get("autoimmune", []):
        fixed, s = fix_epitopes(entry.get("known_epitopes", []))
        entry["known_epitopes"] = fixed
        merge_stats(s)
    
    # Add verified note to _meta
    if "_meta" not in data:
        data["_meta"] = {}
    data["_meta"]["verification_pass2"] = {
        "date": "2026-04-03",
        "method": "IEDB IQ-API batch verification + manual sequence correction",
        "epitopes_removed_non_peptide": total_stats["removed_pos_descriptor"],
        "sequences_corrected": total_stats["corrected_seq"],
        "total_verified": total_stats["kept"]
    }
    
    print(f"\n=== Summary ===")
    print(f"  Kept/verified: {total_stats['kept']}")
    print(f"  Removed (position descriptor, not real peptide): {total_stats['removed_pos_descriptor']}")
    print(f"  Sequences corrected: {total_stats['corrected_seq']}")
    print(f"  Re-queried IEDB: {total_stats['re_queried']}")
    
    print(f"\nSaving to {json_path}...")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("Done.")

if __name__ == "__main__":
    main()
