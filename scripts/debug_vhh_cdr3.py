
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "reports" / "anarci_compat"))

try:
    import anarci
except ImportError:
    print("Could not import anarci shim.")
    sys.exit(1)

# 131I-GMIB-Anti-HER2-VHH1
seq = "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNAKNTLYLQMNSLRAEDTAVYYCAAYDIYGDGAMDYWGQGTLVTVSS"

print(f"Analyzing Sequence: {seq[:20]}...{seq[-20:]}")

# Run Kabat
print("\n--- KABAT Numbering ---")
results_k = anarci.anarci([("seq", seq)], scheme="kabat", output=False)
if results_k and results_k[0]:
    numbering = results_k[0][0][0][0] # Unpack shim structure
    cdr3 = []
    for (pos, ins), aa in numbering:
        if aa == "-": continue
        if 95 <= pos <= 102:
            cdr3.append(f"{pos}{ins.strip()}:{aa}")
            
    print(f"CDR3 (95-102): {' '.join(cdr3)}")
    print(f"Length: {len(cdr3)}")
    
    # Print surrounding
    surround = []
    for (pos, ins), aa in numbering:
        if aa == "-": continue
        if 90 <= pos <= 110:
            surround.append(f"{pos}{ins.strip()}{aa}")
    print(f"Region 90-110: {' '.join(surround)}")

# Run IMGT
print("\n--- IMGT Numbering ---")
results_i = anarci.anarci([("seq", seq)], scheme="imgt", output=False)
if results_i and results_i[0]:
    numbering = results_i[0][0][0][0]
    cdr3 = []
    for (pos, ins), aa in numbering:
        if aa == "-": continue
        # IMGT CDR3 is 105-117
        if 105 <= pos <= 117:
            cdr3.append(f"{pos}{ins.strip()}:{aa}")
            
    print(f"CDR3 (105-117): {' '.join(cdr3)}")
    print(f"Length: {len(cdr3)}")
    
    surround = []
    for (pos, ins), aa in numbering:
        if aa == "-": continue
        if 100 <= pos <= 120:
            surround.append(f"{pos}{ins.strip()}{aa}")
    print(f"Region 100-120: {' '.join(surround)}")
