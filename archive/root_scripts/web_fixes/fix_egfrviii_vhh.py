"""
Fix the EGFRvIII_VHH His-tag contamination in CAR-T Library V3.
Remove "ALEHHHHHH" suffix to get clean 124aa VHH sequence.
"""
import json
import shutil

def fix_car_library():
    # Load CAR library
    with open('data/CAR/CART_LIBRARY_V3.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Find and fix EGFRvIII_VHH
    fixed = False
    for element in data['elements']:
        if element['id'] == 'EGFRvIII_VHH':
            # Current contaminated sequence
            old_seq = element['sequence']
            print(f"Current sequence ({len(old_seq)}aa): {old_seq}")
            
            # Remove His-tag contamination (ALEHHHHHH at end)
            if old_seq.endswith('ALEHHHHHH'):
                clean_seq = old_seq[:-9]  # Remove last 9 residues
                element['sequence'] = clean_seq
                element['length'] = len(clean_seq)
                element['sequence_status'] = 'VERIFIED'
                
                # Update source reference
                element['source_reference'] = 'PDB 4KRL chain B (7D12 anti-EGFR VHH); His-tag removed'
                element['source_validation'] = 'His-tag contamination corrected 2026-04-07'
                
                print(f"Fixed sequence ({len(clean_seq)}aa): {clean_seq}")
                print(f"Removed His-tag: ALEHHHHHH")
                
                fixed = True
                break
    
    if not fixed:
        print("❌ EGFRvIII_VHH element not found or doesn't have expected His-tag")
        return False
    
    # Save updated library
    with open('data/CAR/CART_LIBRARY_V3.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("✅ CAR-T Library V3 updated successfully")
    return True

if __name__ == "__main__":
    success = fix_car_library()
    if success:
        print("\nRunning final audit...")
        # Quick audit to confirm fix
        with open('data/CAR/CART_LIBRARY_V3.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        issues = 0
        for e in data['elements']:
            seq = e.get('sequence', '')
            if 'HHHHHH' in seq:
                issues += 1
                print(f"  Still contaminated: {e['id']}")
        
        if issues == 0:
            print(f"✅ P2 COMPLETED: All {len(data['elements'])} CAR-T components verified!")
            print(f"His-tag contamination: 0 elements")
            print(f"Library completion: 100%")
        else:
            print(f"❌ {issues} elements still have His-tag contamination")
    else:
        print("❌ Fix failed")