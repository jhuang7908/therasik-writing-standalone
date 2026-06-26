#!/usr/bin/env python3
"""
demo_interface_visualization.py

Quick demo showing how to use the interface visualization tools.
Run this on a VHH-HER2 complex to generate colored visualization.
"""

import sys
from pathlib import Path

# Example usage patterns
EXAMPLES = {
    "vhh_her2_simple": {
        "description": "Simple VHH-HER2 complex (VHH in chain A, HER2 in chain B)",
        "command": """python scripts/colorize_interface_pdb.py \\
    --pdb complex_vhh_her2.pdb \\
    --ab_chains A \\
    --ag_chain B \\
    --output colored_vhh_her2.pdb"""
    },
    
    "fab_her2_two_chains": {
        "description": "FAB-HER2 complex (VH+VL in chains A,B; HER2 in C)",
        "command": """python scripts/colorize_interface_pdb.py \\
    --pdb complex_fab_her2.pdb \\
    --ab_chains A,B \\
    --ag_chain C \\
    --output colored_fab_her2.pdb"""
    },
    
    "detailed_analysis": {
        "description": "Generate detailed contact analysis + visualization scripts",
        "command": """python scripts/visualize_interface_contacts.py \\
    --pdb complex_vhh_her2.pdb \\
    --ab_chains A \\
    --ag_chain B \\
    --contact_dist 4.5 \\
    --output_prefix detailed_interface"""
    },
    
    "custom_distance": {
        "description": "Use custom contact distance (e.g., 5.0 Å for looser contacts)",
        "command": """python scripts/colorize_interface_pdb.py \\
    --pdb complex_vhh_her2.pdb \\
    --ab_chains A \\
    --ag_chain B \\
    --contact_dist 5.0 \\
    --output colored_vhh_her2_loose.pdb"""
    }
}


def print_pymol_instructions():
    """Print PyMOL visualization instructions."""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║      PYMOL VISUALIZATION INSTRUCTIONS                      ║
    ╚════════════════════════════════════════════════════════════╝
    
    1. Open the colored PDB:
       File → Open → colored_vhh_her2.pdb
    
    2. Apply B-factor spectrum coloring:
       spectrum b, white cyan blue orange red
    
    3. Adjust view:
       show sticks
       show surface
       set transparency, 0.3
       orient
    
    4. Export image:
       File → Export Image → PNG
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    COLOR LEGEND:
    
    🔴 RED/MAGENTA  (B ≈ 95) — CDR interface (hot spots)
    🔵 CYAN/BLUE    (B ≈ 55) — Framework interface  
    🟠 ORANGE/YELLOW (B ≈ 75) — Antigen interface
    ⚪ WHITE/GRAY    (B ≤ 20) — Non-interface regions
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)


def print_chimera_instructions():
    """Print ChimeraX visualization instructions."""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║      CHIMERAX VISUALIZATION INSTRUCTIONS                   ║
    ╚════════════════════════════════════════════════════════════╝
    
    1. Open the colored PDB:
       File → Open → colored_vhh_her2.pdb
    
    2. Apply B-factor color mapping:
       color bfactor palette rainbow
    
    3. Show interface clearly:
       show sticks
       show surface
    
    4. Load the script (if using detailed_analysis):
       File → Open → detailed_interface_chimera.cxc
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)


def main():
    if len(sys.argv) > 1:
        example_name = sys.argv[1]
        if example_name in EXAMPLES:
            ex = EXAMPLES[example_name]
            print(f"\n📋 Example: {ex['description']}\n")
            print(f"Command:\n{ex['command']}\n")
        else:
            print(f"❌ Unknown example: {example_name}")
            print(f"\nAvailable examples: {', '.join(EXAMPLES.keys())}")
            sys.exit(1)
    else:
        print("""
    ╔════════════════════════════════════════════════════════════╗
    ║     ANTIBODY-ANTIGEN INTERFACE VISUALIZATION TOOLKIT       ║
    ║                                                            ║
    ║  Problem: VHH FR + HER2 ECD colors too similar            ║
    ║           → Hard to see sidechain contacts                ║
    ║                                                            ║
    ║  Solution: Re-color by interface role (B-factor encoded)  ║
    ╚════════════════════════════════════════════════════════════╝
        """)
        
        print("📚 USAGE EXAMPLES:\n")
        for i, (name, ex) in enumerate(EXAMPLES.items(), 1):
            print(f"{i}. {name}")
            print(f"   {ex['description']}")
            print(f"   Run: python demo_interface_visualization.py {name}\n")
        
        print("\n" + "="*60)
        print_pymol_instructions()
        print("\n" + "="*60)
        print_chimera_instructions()
        
        print("\n" + "="*60)
        print("📖 FULL DOCUMENTATION:")
        print("   See: docs/INTERFACE_VISUALIZATION_GUIDE.md")
        print("="*60 + "\n")


if __name__ == "__main__":
    main()
