#!/usr/bin/env python3
"""
Audit CAR-T Library V3 sequence completeness and evidence tier status.
This addresses the user's P2 task: CAR-T 237 + .
"""
import json

def main:
    with open('data/CAR/CART_LIBRARY_V3.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    els = data['elements']
    print(f"Total elements: {len(els)}")
    print(f"Version: {data['metadata'].get('version', 'unknown')}")
    print

    # Count by status and tier
    status_count = {}
    tier_count = {}
    seq_issues = []
    empty_seq = []
    his_tag_contaminated = []
    length_mismatches = []

    for e in els:
        element_id = e.get('id', 'unknown')
        st = e.get('sequence_status', 'UNKNOWN')
        tier = e.get('regulatory_tier', 'UNKNOWN')
        
        status_count[st] = status_count.get(st, 0) + 1
        tier_count[tier] = tier_count.get(tier, 0) + 1
        
        seq = e.get('sequence', '')
        
        # Check for issues
        if not seq or seq.strip == '':
            empty_seq.append(element_id)
            seq_issues.append(f"{element_id}: EMPTY")
        elif len(seq) < 5:
            seq_issues.append(f"{element_id}: TOO_SHORT ({len(seq)}aa)")
        elif 'HHHHHH' in seq:  # His-tag contamination
            his_tag_contaminated.append(element_id)
            seq_issues.append(f"{element_id}: HIS_TAG")
        elif st == 'LENGTH_MISMATCH':
            exp = e.get('length_expected', 0)
            act = len(seq)
            length_mismatches.append((element_id, act, exp))
            seq_issues.append(f"{element_id}: LENGTH {act} vs {exp} expected")

    # Report
    print("Sequence Status Distribution:")
    for k in sorted(status_count.keys):
        v = status_count[k]
        pct = 100 * v / len(els)
        print(f"  {k:<20} {v:>3} ({pct:5.1f}%)")

    print("\nEvidence Tier Distribution:")
    for k in sorted(tier_count.keys):
        v = tier_count[k]
        pct = 100 * v / len(els)
        print(f"  {k:<5} {v:>3} ({pct:5.1f}%)")

    print(f"\n=== SEQUENCE ISSUES SUMMARY ===")
    print(f"Total issues found: {len(seq_issues)}")
    print(f"Empty sequences: {len(empty_seq)}")
    print(f"His-tag contaminated: {len(his_tag_contaminated)}")
    print(f"Length mismatches: {len(length_mismatches)}")
    
    if empty_seq:
        print(f"\nEmpty sequences ({len(empty_seq)}):")
        for eid in empty_seq[:15]:
            print(f"  {eid}")
        if len(empty_seq) > 15:
            print(f"  ... +{len(empty_seq)-15} more")
    
    if his_tag_contaminated:
        print(f"\nHis-tag contaminated ({len(his_tag_contaminated)}):")
        for eid in his_tag_contaminated[:10]:
            print(f"  {eid}")
        if len(his_tag_contaminated) > 10:
            print(f"  ... +{len(his_tag_contaminated)-10} more")
    
    if length_mismatches:
        print(f"\nLength mismatches ({len(length_mismatches)}):")
        for eid, actual, expected in length_mismatches[:10]:
            print(f"  {eid}: {actual}aa vs {expected}aa expected")
        if len(length_mismatches) > 10:
            print(f"  ... +{len(length_mismatches)-10} more")

    # Check for evidence quality issues
    print(f"\n=== EVIDENCE TIER ANALYSIS ===")
    stub_count = status_count.get('STUB', 0)
    verified_count = status_count.get('VERIFIED', 0)
    if stub_count > 0:
        print(f"STUB sequences (no sequence yet): {stub_count}")
    if verified_count > 0:
        print(f"VERIFIED sequences: {verified_count}")

    # Priority for P2 task completion
    priority_needed = len(empty_seq) + len(his_tag_contaminated) + len(length_mismatches)
    completion_pct = 100 * (len(els) - priority_needed) / len(els)
    
    print(f"\n=== P2 TASK COMPLETION STATUS ===")
    print(f"Elements needing sequence fixes: {priority_needed}")
    print(f"Library completion: {completion_pct:.1f}%")
    
    if priority_needed == 0:
        print("✅ P2: All CAR-T components have valid sequences!")
    else:
        print(f"❌ P2: {priority_needed} components need sequence/evidence fixes")

if __name__ == "__main__":
    main