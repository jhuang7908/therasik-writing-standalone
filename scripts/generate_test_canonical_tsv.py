#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate test canonical TSV files from FASTA headers.
This is a helper script for Step 2 when actual canonical tool output is not available.
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def extract_framework_ids(fasta_path: Path) -> list[str]:
    """Extract framework_id from FASTA headers."""
    content = fasta_path.read_text(encoding='utf-8')
    headers = re.findall(r'>(.+?)\|', content)
    return headers

def generate_test_tsv(framework_ids: list[str], chain_type: str, output_path: Path):
    """
    Generate test TSV with 4-column minimal contract: id, cdr, class, confidence.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    lines = ["id\tcdr\tclass\tconfidence"]
    
    # CDR mapping based on chain type
    if chain_type == "VH":
        required_cdrs = ["H1", "H2"]
        optional_cdrs = ["H3"]  # H3 is optional, but we'll skip it for test
    else:  # VL
        required_cdrs = ["L1", "L2"]
        optional_cdrs = ["L3"]  # L3 is optional
    
    # Generate test canonical classes (simplified mapping)
    # In real scenario, these would come from actual canonical tool
    test_classes = {
        "H1": ["H1-13-1", "H1-13-2", "H1-13-3", "H1-13-4"],
        "H2": ["H2-10-1", "H2-10-2", "H2-10-3"],
        "L1": ["L1-11-1", "L1-11-2", "L1-11-3"],
        "L2": ["L2-7-1", "L2-7-2", "L2-7-3"],
        "L3": ["L3-9-1", "L3-9-2"],  # Caution: synthetic CDR3
    }
    
    for fw_id in framework_ids:
        for cdr in required_cdrs:
            # Simple hash-based assignment for consistency
            class_idx = hash(fw_id + cdr) % len(test_classes[cdr])
            class_name = test_classes[cdr][class_idx]
            confidence = "0.85"  # Test confidence value
            lines.append(f"{fw_id}\t{cdr}\t{class_name}\t{confidence}")
        
        # Optionally add L3 for VL (caution)
        if chain_type == "VL" and "L3" in optional_cdrs:
            class_idx = hash(fw_id + "L3") % len(test_classes["L3"])
            class_name = test_classes["L3"][class_idx]
            confidence = "0.75"  # Lower confidence for L3 (synthetic)
            lines.append(f"{fw_id}\tL3\t{class_name}\t{confidence}")
    
    output_path.write_text("\n".join(lines) + "\n", encoding='utf-8')
    print(f"✅ Generated {len(framework_ids)} frameworks, {len(lines)-1} total rows -> {output_path}")

def main():
    vh_fasta = PROJECT_ROOT / "output" / "framework_library" / "canonical" / "framework_vh_canonical_input.fasta"
    vl_fasta = PROJECT_ROOT / "output" / "framework_library" / "canonical" / "framework_vl_canonical_input.fasta"
    out_dir = PROJECT_ROOT / "output" / "framework_library" / "canonical"
    
    if not vh_fasta.exists() or not vl_fasta.exists():
        print("❌ FASTA files not found. Run Step 1 first.")
        return 1
    
    vh_ids = extract_framework_ids(vh_fasta)
    vl_ids = extract_framework_ids(vl_fasta)
    
    print(f"Found {len(vh_ids)} VH frameworks, {len(vl_ids)} VL frameworks")
    
    vh_tsv = out_dir / "vh_canonical.tsv"
    vl_tsv = out_dir / "vl_canonical.tsv"
    
    generate_test_tsv(vh_ids, "VH", vh_tsv)
    generate_test_tsv(vl_ids, "VL", vl_tsv)
    
    print("\n[SUCCESS] Test TSV files generated.")
    print(f"⚠️  NOTE: These are TEST data. Replace with actual canonical tool output for production.")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
