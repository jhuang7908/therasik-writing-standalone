import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path('.').resolve()
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from core.numbering.anarcii_adapter import number_sequence
except ImportError:
    print("CRITICAL: core.numbering.anarcii_adapter not found!")
    sys.exit(1)

seqs = {
    'Calpurbatug_VH': 'QSQVQLVESGPGLVKPSETLSLTCRVSGDSNRPSYWSWIRQAPGKGPEWIGYIYNSGDTNYNPSLKSRVTISVDTSKNQFSLKLSSVTAADTAVYYCARGAPYCSSSSCYRSGMDVWGQGTTVTVSS',
    'Elipovimab_VL': 'SDISVAPGETARISCGEKSLGSRAVQWYQHRAGQAPSLIIYNNQDRPSGIPERFSGSNSGNTATLTISRVEAGDEADYYCQVWDSGNDHVFGGGTQLTVL',
    'Zinlirvimab_VL': 'SYVRPLSVALGETARISCGRQALGSRAVQWYQHRPGQAPILLIYNNQDRPSGIPERFSGSNSGNTATLTISRVEAGDEADYYCHVWDSGNDRVFGGGTKLTVL'
}

for name, seq in seqs.items():
    print(f"\n--- Investigating {name} ---")
    print(f"Sequence: {seq}")
    try:
        # We need to see what ANARCII returns or why it fails
        # Using specific checks to see chain type detection
        from anarcii import Anarcii
        ana = Anarcii()
        res = ana.number(seq)
        print(f"Direct ANARCII result keys: {list(res.keys())}")
        
        # Check if it was identified as a valid chain
        for k, v in res.items():
            if 'numbering' in v and v['numbering']:
                print(f"Chain {k}: SUCCESS")
            else:
                print(f"Chain {k}: FAILED (No numbering)")
                
        # Also try via our adapter
        pos_to_aa, residue_table = number_sequence(seq, scheme="imgt")
        print("Adapter SUCCESS")
    except Exception as e:
        print(f"Error: {e}")
